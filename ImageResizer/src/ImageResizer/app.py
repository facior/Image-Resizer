import asyncio
import os
import sys
import webbrowser
from pathlib import Path

import toga
from toga.sources import AccessorColumn
from toga.style import Pack
from toga.style.pack import CENTER, COLUMN, ROW

from ImageResizer import __version__, i18n
from ImageResizer import settings as settings_store
from ImageResizer import theme as t
from ImageResizer.core import (
    FORMAT_ORIGINAL,
    FORMATS,
    LOSSY_FORMATS,
    MAX_DIMENSION,
    MAX_LIMIT_MB,
    MIN_LIMIT_MB,
    MODE_EXACT,
    MODE_PERCENT,
    MODES,
    SUPPORTED_EXTENSIONS,
    ImageInfo,
    ResizeSettings,
    collect_images,
    human_size,
    read_info,
    render_preview,
    resize_image,
    target_size,
)
from ImageResizer.dnd import enable_file_drop
from ImageResizer.i18n import plural, tr
from ImageResizer.presets import CUSTOM, PRESET_KEYS, PRESETS, preset_label

APP_NAME = "Image Resizer"
AUTHOR = "Łukasz Kubieniec"
GITHUB_URL = "https://github.com/facior/Image-Resizer"
DEST_NEXT_TO = "next_to"
DEST_CUSTOM = "custom"
PREVIEW_BOX = (560, 300)
FILE_TYPES = [ext.lstrip(".") for ext in SUPPORTED_EXTENSIONS]

# Our own menu commands: id -> translation key
COMMAND_TEXTS = {
    "ir.add_images": "cmd.add_images",
    "ir.add_folder": "cmd.add_folder",
    "ir.resize": "cmd.resize",
    "ir.clear": "cmd.clear",
    "ir.github": "cmd.github",
}


class Slot(toga.Box):
    """Holds one widget that can be shown or removed.

    Toga's native layout ignores `display: none`, so optional controls are
    detached from the window instead of hidden.
    """

    def __init__(self, child):
        super().__init__(children=[child], style=Pack(direction=COLUMN))
        self.child = child

    def set_visible(self, visible: bool) -> None:
        if visible and not self.children:
            self.add(self.child)
        elif not visible and self.children:
            self.remove(self.child)


def keyed_selection(options, on_change, style) -> toga.Selection:
    """A Selection showing translated labels while storing stable keys."""
    return toga.Selection(
        items=[{"label": label, "key": key} for key, label in options],
        accessor="label",
        on_change=on_change,
        style=style,
    )


def get_key(selection: toga.Selection):
    return selection.value.key if selection.value is not None else None


def set_key(selection: toga.Selection, key) -> None:
    selection.value = selection.items.find({"key": key})


def format_mb(value: float) -> str:
    """2.0 -> "2", 0.5 -> "0,5" in Polish."""
    return i18n.format_decimal(value, 2).rstrip("0").rstrip(",.")


def open_folder(path: Path) -> None:
    if sys.platform == "win32":
        os.startfile(path)
    else:
        webbrowser.open(path.as_uri())


class ImageResizerApp(toga.App):
    def startup(self):
        saved = settings_store.load(self.paths.config)
        self.settings = saved.settings
        self.language_pref = saved.language
        i18n.set_language(saved.language or i18n.detect_language())

        self.items: list[ImageInfo] = []
        self.processing = False
        self.cancel_requested = False
        self.custom_folder = None
        self._syncing = False
        self._preview_task: asyncio.Task | None = None

        screen_w, screen_h = self.screens[0].size if self.screens else (1280, 900)
        size = (min(1200, screen_w - 60), min(800, screen_h - 100))
        # Centered: the default cascade position can push the footer under the taskbar.
        position = (max(0, (screen_w - size[0]) // 2), max(0, (screen_h - size[1]) // 2 - 20))
        self.main_window = toga.MainWindow(title=self.formal_name, size=size, position=position)
        self.main_window.content = self.build_ui()
        self.create_commands()
        self.translate_menus()
        self.hook_drop = enable_file_drop(self.main_window, self.add_paths)

        self.load_settings_into_ui(saved.preset)
        self.refresh_list()
        self.main_window.show()

    # ------------------------------------------------------------------ layout

    def section(self, title, *children, flex=0):
        """A white card with a heading. Inner spacing comes from the content margin."""
        content = toga.Box(
            children=[toga.Label(title, style=t.heading()), *children],
            style=Pack(direction=COLUMN, gap=t.SPACE_SM, margin=t.SPACE_LG, flex=1),
        )
        return toga.Box(children=[content], style=Pack(direction=COLUMN, background_color=t.CARD, flex=flex))

    def labeled(self, label, widget, helper=None):
        children = [toga.Label(label, style=t.text()), widget]
        if helper is not None:
            children.append(helper)
        return toga.Box(children=children, style=Pack(direction=COLUMN, gap=t.SPACE_XS))

    def build_ui(self):
        # Header
        title = toga.Label(APP_NAME, style=t.heading(font_size=16))
        subtitle = toga.Label(tr("app.subtitle"), style=t.muted(font_size=t.FONT_SIZE))
        self.language_select = keyed_selection(
            i18n.LANGUAGES.items(), self.on_language_change, t.field(width=110)
        )
        set_key(self.language_select, i18n.current_language())
        github = toga.Button("GitHub", on_press=self.open_github, style=t.button(width=90))
        header = toga.Box(
            children=[
                toga.Box(children=[title, subtitle], style=Pack(direction=COLUMN, flex=1, gap=2)),
                self.language_select,
                github,
            ],
            style=Pack(direction=ROW, align_items=CENTER, flex=1, gap=t.SPACE_MD, margin=(t.SPACE_MD, t.SPACE_XL)),
        )
        header_bar = toga.Box(children=[header], style=Pack(background_color=t.CARD))

        # Image list
        self.add_button = toga.Button(
            tr("btn.add_images"), on_press=self.on_add_files, style=t.secondary_button(width=130)
        )
        self.add_folder_button = toga.Button(
            tr("btn.add_folder"), on_press=self.on_add_folder, style=t.button(width=120)
        )
        self.remove_button = toga.Button(
            tr("btn.remove"), on_press=self.on_remove, enabled=False, style=t.button(width=90)
        )
        self.clear_button = toga.Button(tr("btn.clear"), on_press=self.on_clear, enabled=False, style=t.button(width=90))
        toolbar = toga.Box(
            children=[
                self.add_button,
                self.add_folder_button,
                toga.Box(style=Pack(flex=1)),
                self.remove_button,
                self.clear_button,
            ],
            style=Pack(direction=ROW, gap=t.SPACE_SM, align_items=CENTER),
        )
        self.empty_label = toga.Label("", style=t.muted(font_size=t.FONT_SIZE, margin=(t.SPACE_SM, 0)))
        self.empty_slot = Slot(self.empty_label)
        self.table = toga.Table(
            columns=[
                AccessorColumn(tr("col.file"), "name"),
                AccessorColumn(tr("col.dims"), "dims"),
                AccessorColumn(tr("col.filesize"), "filesize"),
                AccessorColumn(tr("col.result"), "output"),
            ],
            multiple_select=True,
            on_select=self.on_select,
            style=Pack(flex=1, font_family=t.FONT, font_size=t.FONT_SIZE),
        )
        self.summary_label = toga.Label("", style=t.muted())
        images_card = self.section(
            tr("card.images"), toolbar, self.empty_slot, self.table, self.summary_label, flex=1
        )

        # Preview
        # Flexible height so the window can shrink; the image scales to fit.
        self.preview = toga.ImageView(style=Pack(flex=1, background_color=t.MUTED))
        self.preview_caption = toga.Label(tr("preview.hint"), style=t.muted())
        preview_card = self.section(tr("card.preview"), self.preview, self.preview_caption, flex=1)

        left = toga.Box(
            children=[images_card, preview_card],
            style=Pack(direction=COLUMN, flex=1, gap=t.SPACE_LG),
        )

        right = toga.ScrollContainer(
            horizontal=False,
            content=toga.Box(
                children=[self.build_resize_card(), self.build_output_card()],
                style=Pack(direction=COLUMN, gap=t.SPACE_LG, background_color=t.BACKGROUND),
            ),
            style=Pack(width=380, background_color=t.BACKGROUND),
        )

        body = toga.Box(
            children=[left, right],
            style=Pack(direction=ROW, flex=1, gap=t.SPACE_LG, margin=t.SPACE_LG),
        )

        # Footer
        self.status_label = toga.Label(tr("status.ready"), style=t.text(flex=1))
        self.progress = toga.ProgressBar(max=1, value=0, style=Pack(width=240))
        self.resize_button = toga.Button(
            tr("btn.resize"), on_press=self.on_resize, enabled=False, style=t.primary_button(width=220)
        )
        footer = toga.Box(
            children=[self.status_label, self.progress, self.resize_button],
            style=Pack(direction=ROW, align_items=CENTER, flex=1, gap=t.SPACE_LG, margin=(t.SPACE_MD, t.SPACE_XL)),
        )
        footer_bar = toga.Box(children=[footer], style=Pack(background_color=t.CARD))

        return toga.Box(
            children=[header_bar, toga.Divider(), body, toga.Divider(), footer_bar],
            style=Pack(direction=COLUMN, background_color=t.BACKGROUND),
        )

    def build_resize_card(self):
        self.preset_select = keyed_selection(
            [(key, preset_label(key)) for key in PRESET_KEYS], self.on_preset_change, t.field()
        )
        self.mode_select = keyed_selection(
            [(mode, tr(f"mode.{mode}")) for mode in MODES], self.on_mode_change, t.field()
        )
        self.mode_help = toga.Label("", style=t.muted())

        self.width_input = toga.NumberInput(
            min=1, max=MAX_DIMENSION, step=1, on_change=self.on_width_change, style=t.field(flex=1)
        )
        self.height_input = toga.NumberInput(
            min=1, max=MAX_DIMENSION, step=1, on_change=self.on_height_change, style=t.field(flex=1)
        )
        width_field = self.labeled(tr("label.width"), self.width_input)
        height_field = self.labeled(tr("label.height"), self.height_input)
        width_field.style.flex = 1
        height_field.style.flex = 1
        self.size_box = toga.Box(
            children=[width_field, toga.Label("×", style=t.text(margin_top=24)), height_field],
            style=Pack(direction=ROW, gap=t.SPACE_SM),
        )
        self.size_slot = Slot(self.size_box)

        self.lock_switch = toga.Switch(tr("switch.lock"), value=True, style=t.text())
        self.lock_slot = Slot(self.lock_switch)

        self.percent_slider = toga.Slider(min=1, max=200, on_change=self.on_settings_change, style=Pack(flex=1))
        self.percent_label = toga.Label("", style=t.text(width=60, text_align="right"))
        self.percent_box = toga.Box(
            children=[
                toga.Label(tr("label.scale"), style=t.text()),
                toga.Box(
                    children=[self.percent_slider, self.percent_label],
                    style=Pack(direction=ROW, align_items=CENTER, gap=t.SPACE_SM),
                ),
            ],
            style=Pack(direction=COLUMN, gap=t.SPACE_XS),
        )
        self.percent_slot = Slot(self.percent_box)

        self.upscale_switch = toga.Switch(tr("switch.upscale"), on_change=self.on_settings_change, style=t.text())

        return self.section(
            tr("card.resize"),
            self.labeled(tr("label.preset"), self.preset_select),
            self.labeled(tr("label.mode"), self.mode_select, self.mode_help),
            self.size_slot,
            self.lock_slot,
            self.percent_slot,
            self.upscale_switch,
        )

    def build_output_card(self):
        self.format_select = keyed_selection(
            [(key, tr("format.original") if key == FORMAT_ORIGINAL else key) for key in FORMATS],
            self.on_settings_change,
            t.field(),
        )
        self.quality_slider = toga.Slider(min=1, max=100, on_change=self.on_settings_change, style=Pack(flex=1))
        self.quality_label = toga.Label("", style=t.text(width=40, text_align="right"))
        self.quality_box = toga.Box(
            children=[
                toga.Label(tr("label.quality"), style=t.text()),
                toga.Box(
                    children=[self.quality_slider, self.quality_label],
                    style=Pack(direction=ROW, align_items=CENTER, gap=t.SPACE_SM),
                ),
                toga.Label(tr("quality.help"), style=t.muted()),
            ],
            style=Pack(direction=COLUMN, gap=t.SPACE_XS),
        )
        self.metadata_switch = toga.Switch(tr("switch.metadata"), on_change=self.on_settings_change, style=t.text())
        self.gps_switch = toga.Switch(tr("switch.strip_gps"), value=True, on_change=self.on_settings_change,
                                      style=t.text(margin_left=24))
        self.gps_slot = Slot(self.gps_switch)

        self.limit_switch = toga.Switch(tr("switch.limit_size"), on_change=self.on_settings_change, style=t.text())
        # A TextInput, not NumberInput: Toga's WinForms NumberInput can't read decimals
        # when Windows uses a decimal comma (Polish locale) and reports them as empty.
        self.max_size_input = toga.TextInput(on_change=self.on_settings_change, style=t.field(width=120))
        self.limit_slot = Slot(
            toga.Box(
                children=[
                    self.labeled(tr("label.max_size"), self.max_size_input),
                    toga.Label(tr("limit.help"), style=t.muted()),
                ],
                style=Pack(direction=COLUMN, gap=t.SPACE_XS, margin_left=24),
            )
        )

        self.suffix_input = toga.TextInput(on_change=self.on_settings_change, style=t.field())
        self.suffix_example = toga.Label("", style=t.muted())

        self.dest_select = keyed_selection(
            [(DEST_NEXT_TO, tr("dest.next_to")), (DEST_CUSTOM, tr("dest.custom"))],
            self.on_dest_change,
            t.field(),
        )
        self.folder_label = toga.Label("", style=t.muted(flex=1))
        self.folder_button = toga.Button(tr("btn.choose"), on_press=self.on_choose_folder, style=t.button(width=90))
        self.folder_box = toga.Box(
            children=[self.folder_label, self.folder_button],
            style=Pack(direction=ROW, align_items=CENTER, gap=t.SPACE_SM),
        )
        self.folder_slot = Slot(self.folder_box)
        self.overwrite_switch = toga.Switch(
            tr("switch.overwrite"), on_change=self.on_settings_change, style=t.text()
        )

        return self.section(
            tr("card.output"),
            self.labeled(tr("label.format"), self.format_select),
            self.quality_box,
            self.limit_switch,
            self.limit_slot,
            self.metadata_switch,
            self.gps_slot,
            self.labeled(tr("label.suffix"), self.suffix_input, self.suffix_example),
            self.labeled(tr("label.save_to"), self.dest_select),
            self.folder_slot,
            self.overwrite_switch,
        )

    # ------------------------------------------------------------- menus

    def create_commands(self):
        file_group = toga.Group.FILE
        self.commands.add(
            toga.Command(
                self.on_add_files, "", id="ir.add_images", shortcut=toga.Key.MOD_1 + "o",
                group=file_group, order=1,
            ),
            toga.Command(
                self.on_add_folder, "", id="ir.add_folder", shortcut=toga.Key.MOD_1 + toga.Key.SHIFT + "o",
                group=file_group, order=2,
            ),
            toga.Command(
                self.on_resize, "", id="ir.resize", shortcut=toga.Key.MOD_1 + "r", group=file_group, order=3
            ),
            toga.Command(self.on_clear, "", id="ir.clear", group=file_group, order=4),
            toga.Command(self.open_github, "", id="ir.github", group=toga.Group.HELP),
        )

    def translate_menus(self):
        # Toga has no public setter for group labels; the standard groups are shared objects.
        toga.Group.FILE._text = tr("menu.file")
        toga.Group.HELP._text = tr("menu.help")
        texts = {
            toga.Command.EXIT: tr("cmd.exit"),
            toga.Command.VISIT_HOMEPAGE: tr("cmd.homepage"),
            toga.Command.ABOUT: tr("cmd.about", name=APP_NAME),
            **{cmd_id: tr(key) for cmd_id, key in COMMAND_TEXTS.items()},
        }
        for cmd_id, text in texts.items():
            if cmd_id in self.commands:
                self.commands[cmd_id].text = text
        # Rebuild the native menu. Before startup finishes there is no handler yet,
        # and Toga builds the menu itself with the texts set above.
        if self.commands.on_change:
            self.commands.on_change()

    def about(self):
        message = tr(
            "about.text", name=APP_NAME, version=__version__, description=tr("app.description"),
            author=AUTHOR, url=GITHUB_URL,
        )
        asyncio.ensure_future(self.main_window.dialog(toga.InfoDialog(tr("cmd.about", name=APP_NAME), message)))

    # ------------------------------------------------------------- language

    def on_language_change(self, widget, **kwargs):
        code = get_key(widget)
        if self._syncing or code is None or code == i18n.current_language():
            return
        # Rebuild after this event handler returns; the widget that fired it is replaced.
        self.loop.call_soon(self.apply_language, code)

    def apply_language(self, code):
        try:
            self.settings = self.read_settings()
        except ValueError:
            pass  # keep the last valid settings
        preset = get_key(self.preset_select)
        selected = [self.items.index(item) for item in self.selected_items()]

        i18n.set_language(code)
        self.language_pref = code
        window_size = self.main_window.size
        self.main_window.content = self.build_ui()
        self.main_window.size = window_size  # replacing content would otherwise grow the window
        if self.hook_drop:
            self.hook_drop(self.main_window.content)
        self.translate_menus()
        self.load_settings_into_ui(preset)
        self.refresh_list()
        if selected:
            self.table.selection = self.table.data[selected[0]]
        self.save_settings()

    # ---------------------------------------------------------------- settings

    def save_settings(self, settings: ResizeSettings | None = None):
        settings_store.save(
            self.paths.config,
            settings_store.Saved(settings or self.settings, get_key(self.preset_select) or "", self.language_pref),
        )

    def load_settings_into_ui(self, preset):
        s = self.settings
        self._syncing = True
        try:
            set_key(self.mode_select, s.mode)
            self.width_input.value = s.width
            self.height_input.value = s.height
            self.percent_slider.value = s.percent
            self.upscale_switch.value = s.allow_upscale
            set_key(self.format_select, s.output_format)
            self.quality_slider.value = s.quality
            self.metadata_switch.value = s.keep_metadata
            self.gps_switch.value = s.strip_gps
            self.limit_switch.value = s.limit_file_size
            self.max_size_input.value = format_mb(s.max_file_mb)
            self.suffix_input.value = s.suffix
            self.overwrite_switch.value = s.overwrite
            self.custom_folder = s.output_dir
            set_key(self.dest_select, DEST_CUSTOM if s.output_dir else DEST_NEXT_TO)
            set_key(self.preset_select, preset if preset in PRESET_KEYS else self.matching_preset())
        finally:
            self._syncing = False
        self.on_settings_change()

    def read_settings(self) -> ResizeSettings:
        """Build settings from the controls. Raises ValueError with a readable message."""
        def as_int(widget, field_key):
            if widget.value is None:
                raise ValueError(tr("err.empty", field=tr(field_key)))
            return int(widget.value)

        settings = ResizeSettings(
            mode=get_key(self.mode_select),
            width=as_int(self.width_input, "field.width"),
            height=as_int(self.height_input, "field.height"),
            percent=round(self.percent_slider.value),
            allow_upscale=self.upscale_switch.value,
            output_format=get_key(self.format_select),
            quality=round(self.quality_slider.value),
            keep_metadata=self.metadata_switch.value,
            strip_gps=self.gps_switch.value,
            limit_file_size=self.limit_switch.value,
            max_file_mb=self.read_max_size(),
            suffix=self.suffix_input.value.strip(),
            output_dir=self.custom_folder if get_key(self.dest_select) == DEST_CUSTOM else None,
            overwrite=self.overwrite_switch.value,
        )
        settings.validate()
        if any(c in settings.suffix for c in '<>:"/\\|?*'):
            raise ValueError(tr("err.suffix"))
        return settings

    def read_max_size(self) -> float:
        if not self.limit_switch.value:
            return self.settings.max_file_mb  # keep the remembered value while the limit is off
        text = self.max_size_input.value.strip().replace(",", ".")
        if not text:
            raise ValueError(tr("err.empty", field=tr("label.max_size")))
        try:
            value = float(text)
        except ValueError:
            raise ValueError(tr("err.max_size", min=format_mb(MIN_LIMIT_MB), max=MAX_LIMIT_MB)) from None
        if not MIN_LIMIT_MB <= value <= MAX_LIMIT_MB:
            raise ValueError(tr("err.max_size", min=format_mb(MIN_LIMIT_MB), max=MAX_LIMIT_MB))
        return value

    def matching_preset(self):
        current = (get_key(self.mode_select), self.width_input.value, self.height_input.value)
        for key, values in PRESETS.items():
            if values == current:
                return key
        return CUSTOM

    def on_settings_change(self, widget=None, **kwargs):
        if self._syncing:
            return
        mode = get_key(self.mode_select)
        self.mode_help.text = tr(f"mode.{mode}.help")
        self.size_slot.set_visible(mode != MODE_PERCENT)
        self.percent_slot.set_visible(mode == MODE_PERCENT)
        self.lock_slot.set_visible(mode == MODE_EXACT)
        self.percent_label.text = f"{round(self.percent_slider.value)} %"
        self.quality_label.text = str(round(self.quality_slider.value))

        fmt = FORMATS[get_key(self.format_select)]
        self.quality_slider.enabled = not self.processing and (fmt is None or fmt[0] in LOSSY_FORMATS)
        self.folder_slot.set_visible(get_key(self.dest_select) == DEST_CUSTOM)
        self.gps_slot.set_visible(self.metadata_switch.value)
        self.limit_slot.set_visible(self.limit_switch.value)
        self.folder_label.text = str(self.custom_folder) if self.custom_folder else tr("folder.none")

        suffix = self.suffix_input.value.strip()
        self.suffix_example.text = tr("suffix.example", suffix=suffix, ext=fmt[1] if fmt else ".jpg")

        try:
            self.settings = self.read_settings()
        except ValueError as exc:
            self.status_label.text = str(exc)
            self.status_label.style.color = t.DESTRUCTIVE
            self.update_results(valid=False)
            return
        if not self.processing:
            self.status_label.text = tr("status.ready")
            self.status_label.style.color = t.FOREGROUND
        self.update_results(valid=True)
        self.schedule_preview()

    def on_preset_change(self, widget, **kwargs):
        key = get_key(widget)
        if self._syncing or key in (None, CUSTOM):
            return
        mode, width, height = PRESETS[key]
        self._syncing = True
        try:
            set_key(self.mode_select, mode)
            self.width_input.value = width
            self.height_input.value = height
        finally:
            self._syncing = False
        self.on_settings_change()

    def mark_custom(self):
        if not self._syncing:
            self._syncing = True
            try:
                set_key(self.preset_select, self.matching_preset())
            finally:
                self._syncing = False

    def on_mode_change(self, widget, **kwargs):
        self.mark_custom()
        self.on_settings_change()

    def reference_ratio(self):
        """Aspect ratio used by the lock: the selected image, else the first one."""
        item = (self.selected_items() or self.items or [None])[0]
        if item:
            return item.size[0] / item.size[1]
        return None

    def on_width_change(self, widget, **kwargs):
        if not self._syncing and self.lock_switch.value and get_key(self.mode_select) == MODE_EXACT:
            ratio = self.reference_ratio()
            if ratio and widget.value:
                self._syncing = True
                try:
                    self.height_input.value = max(1, round(int(widget.value) / ratio))
                finally:
                    self._syncing = False
        self.mark_custom()
        self.on_settings_change()

    def on_height_change(self, widget, **kwargs):
        if not self._syncing and self.lock_switch.value and get_key(self.mode_select) == MODE_EXACT:
            ratio = self.reference_ratio()
            if ratio and widget.value:
                self._syncing = True
                try:
                    self.width_input.value = max(1, round(int(widget.value) * ratio))
                finally:
                    self._syncing = False
        self.mark_custom()
        self.on_settings_change()

    async def on_dest_change(self, widget, **kwargs):
        if not self._syncing and get_key(widget) == DEST_CUSTOM and not self.custom_folder:
            await self.on_choose_folder(widget)
        self.on_settings_change()

    async def on_choose_folder(self, widget, **kwargs):
        folder = await self.main_window.dialog(
            toga.SelectFolderDialog(tr("dialog.choose_output"), initial_directory=self.custom_folder)
        )
        if folder:
            self.custom_folder = Path(folder)
        elif not self.custom_folder:
            set_key(self.dest_select, DEST_NEXT_TO)
        self.on_settings_change()

    # -------------------------------------------------------------- image list

    async def on_add_files(self, widget, **kwargs):
        if self.processing:
            return
        paths = await self.main_window.dialog(
            toga.OpenFileDialog(tr("dialog.add_images"), file_types=FILE_TYPES, multiple_select=True)
        )
        if paths:
            self.add_paths(paths)

    async def on_add_folder(self, widget, **kwargs):
        if self.processing:
            return
        folder = await self.main_window.dialog(toga.SelectFolderDialog(tr("dialog.add_folder")))
        if folder:
            self.add_paths([folder])

    def add_paths(self, paths):
        if self.processing:
            return
        known = {item.path.resolve() for item in self.items}
        skipped = 0
        for path in collect_images(paths):
            if path.resolve() in known:
                continue
            try:
                self.items.append(read_info(path))
                known.add(path.resolve())
            except Exception:
                skipped += 1
        self.refresh_list()
        if skipped:
            self.status_label.text = tr("status.skipped", n=skipped)
            self.status_label.style.color = t.DESTRUCTIVE

    def selected_items(self):
        rows = self.table.selection or []
        return [self.items[self.table.data.index(row)] for row in rows]

    def on_select(self, widget, **kwargs):
        selected = self.selected_items()
        self.remove_button.enabled = bool(selected) and not self.processing
        if selected:
            self.show_preview_for(selected[0])

    def on_remove(self, widget, **kwargs):
        selected = {id(item) for item in self.selected_items()}
        self.items = [item for item in self.items if id(item) not in selected]
        self.refresh_list()

    def on_clear(self, widget, **kwargs):
        if self.processing:
            return
        self.items = []
        self.refresh_list()

    def refresh_list(self):
        self.table.data = [
            {
                "name": item.path.name,
                "dims": f"{item.size[0]} × {item.size[1]}",
                "filesize": human_size(item.file_bytes),
                "output": "",
            }
            for item in self.items
        ]
        count = len(self.items)
        self.empty_label.text = tr("empty.drop" if self.hook_drop else "empty.no_drop")
        self.empty_slot.set_visible(not count)
        total = sum(item.file_bytes for item in self.items)
        self.summary_label.text = (
            tr("summary.count", count=plural("images", count), size=human_size(total)) if count else ""
        )
        self.clear_button.enabled = bool(count) and not self.processing
        self.remove_button.enabled = False
        if not count:
            self.preview.image = None
            self.preview_caption.text = tr("preview.hint")
        self.update_results(valid=True)
        if count:
            self.schedule_preview()

    def update_results(self, valid: bool):
        for row, item in zip(self.table.data, self.items):
            row.output = "–" if not valid else "{} × {}".format(*target_size(item.size, self.settings))
        # The WinForms table clears its cache on row changes but doesn't repaint.
        native = getattr(self.table._impl, "native", None)
        if hasattr(native, "Invalidate"):
            native.Invalidate()
        count = len(self.items)
        if not self.processing:
            self.resize_button.text = tr("btn.resize_n", count=plural("images", count)) if count else tr("btn.resize")
            enabled = valid and bool(count)
            self.resize_button.enabled = enabled
            # A custom background hides the native disabled look, so show it explicitly.
            self.resize_button.style.background_color = t.ACCENT if enabled else t.MUTED
            self.resize_button.style.color = t.ON_ACCENT if enabled else t.MUTED_FOREGROUND

    # ----------------------------------------------------------------- preview

    def schedule_preview(self):
        """Debounced so dragging a slider doesn't decode the image dozens of times."""
        if self._preview_task and not self._preview_task.done():
            self._preview_task.cancel()
        item = (self.selected_items() or self.items or [None])[0]
        if item:
            self._preview_task = asyncio.ensure_future(self._render_preview(item, delay=0.15))

    def show_preview_for(self, item):
        if self._preview_task and not self._preview_task.done():
            self._preview_task.cancel()
        self._preview_task = asyncio.ensure_future(self._render_preview(item, delay=0))

    async def _render_preview(self, item: ImageInfo, delay: float):
        await asyncio.sleep(delay)
        settings = self.settings
        try:
            img = await self.loop.run_in_executor(None, render_preview, item.path, settings, PREVIEW_BOX)
        except Exception as exc:
            self.preview.image = None
            self.preview_caption.text = tr("preview.error", name=item.path.name, error=exc)
            return
        self.preview.image = toga.Image(img)
        new_w, new_h = target_size(item.size, settings)
        self.preview_caption.text = (
            f"{item.path.name}   ·   {item.size[0]} × {item.size[1]}  →  {new_w} × {new_h} px"
        )

    # -------------------------------------------------------------- processing

    def set_busy(self, busy: bool):
        self.processing = busy
        for widget in (
            self.language_select, self.add_button, self.add_folder_button, self.clear_button,
            self.remove_button, self.preset_select, self.mode_select, self.width_input, self.height_input,
            self.lock_switch, self.percent_slider, self.upscale_switch, self.format_select,
            self.quality_slider, self.metadata_switch, self.gps_switch, self.limit_switch,
            self.max_size_input, self.suffix_input, self.dest_select,
            self.folder_button, self.overwrite_switch,
        ):
            widget.enabled = not busy
        if busy:
            self.resize_button.text = tr("btn.cancel")
            self.resize_button.style.background_color = t.MUTED
            self.resize_button.style.color = t.FOREGROUND
        else:
            self.on_settings_change()
            self.clear_button.enabled = bool(self.items)
            self.remove_button.enabled = bool(self.selected_items())

    async def on_resize(self, widget, **kwargs):
        if self.processing:
            self.cancel_requested = True
            self.status_label.text = tr("status.cancelling")
            return
        if not self.items:
            return
        try:
            settings = self.read_settings()
        except ValueError as exc:
            await self.main_window.dialog(toga.ErrorDialog(tr("dialog.check_settings"), str(exc)))
            return
        if get_key(self.dest_select) == DEST_CUSTOM and not settings.output_dir:
            await self.main_window.dialog(toga.ErrorDialog(tr("dialog.no_folder"), tr("dialog.no_folder.msg")))
            return
        if settings.overwrite and settings.output_dir is None and not settings.suffix:
            replace = await self.main_window.dialog(
                toga.ConfirmDialog(tr("dialog.replace"), tr("dialog.replace.msg"))
            )
            if not replace:
                return

        self.save_settings(settings)
        items = list(self.items)
        total = len(items)
        results, errors = [], []
        self.cancel_requested = False
        self.progress.max = total
        self.progress.value = 0
        self.status_label.style.color = t.FOREGROUND
        self.set_busy(True)
        try:
            for index, item in enumerate(items, start=1):
                if self.cancel_requested:
                    break
                self.status_label.text = tr("status.processing", index=index, total=total, name=item.path.name)
                try:
                    result = await self.loop.run_in_executor(None, resize_image, item.path, settings)
                except Exception as exc:
                    errors.append(f"{item.path.name}: {exc}")
                else:
                    results.append(result)
                self.progress.value = index
        finally:
            self.set_busy(False)

        await self.show_summary(results, errors, total, settings)

    async def show_summary(self, results, errors, total, settings):
        before = sum(r.bytes_before for r in results)
        after = sum(r.bytes_after for r in results)
        done = len(results)
        headline = tr("summary.cancelled" if self.cancel_requested else "summary.done", done=done, total=total)
        self.status_label.text = headline
        self.status_label.style.color = t.DESTRUCTIVE if errors else t.SUCCESS

        lines = [headline]
        if done:
            change = (after - before) / before * 100 if before else 0
            lines.append(
                tr("summary.size", before=human_size(before), after=human_size(after), change=f"{change:+.0f}%")
            )
        gps = sum(r.gps_removed for r in results)
        if gps:
            lines.append(tr("summary.gps", count=plural("photos_from", gps)))
        if settings.limit_file_size:
            limit_text = f"{format_mb(settings.max_file_mb)} MB"
            missed = sum(r.limit_met is False for r in results)
            shrunk = sum(r.new_size != target_size(r.original_size, settings) for r in results)
            if shrunk:
                lines.append(tr("summary.limit_shrunk", count=plural("images", shrunk)))
            if missed:
                lines.append(tr("summary.limit_missed", count=plural("images", missed), limit=limit_text))
        if errors:
            lines.append("")
            lines.append(tr("summary.failed", n=len(errors)))
            lines.extend(errors[:8])
            if len(errors) > 8:
                lines.append(tr("summary.more", n=len(errors) - 8))

        if not done:
            await self.main_window.dialog(toga.ErrorDialog(tr("dialog.nothing_saved"), "\n".join(lines)))
            return
        lines.append("")
        lines.append(tr("summary.open"))
        if await self.main_window.dialog(toga.QuestionDialog(tr("dialog.complete"), "\n".join(lines))):
            open_folder(results[0].destination.parent)

    # ------------------------------------------------------------------- misc

    def open_github(self, widget, **kwargs):
        webbrowser.open(GITHUB_URL)

    def on_exit(self):
        try:
            self.save_settings(self.read_settings())
        except ValueError:
            self.save_settings()
        return True


def main():
    return ImageResizerApp(
        formal_name=APP_NAME,
        app_id="image.resizer.imageresizer",
        app_name="ImageResizer",
        icon="resources/logo",
        author=AUTHOR,
        version=__version__,
        home_page=GITHUB_URL,
        description="Resize, convert and compress images in batches.",
    )


if __name__ == "__main__":
    main().main_loop()
