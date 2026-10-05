"""Translations. Add a language by adding its code to LANGUAGES and every entry in STRINGS."""

from __future__ import annotations

import locale
import sys

LANGUAGES = {"en": "English", "pl": "Polski"}
DEFAULT_LANGUAGE = "en"

_current = DEFAULT_LANGUAGE

STRINGS: dict[str, dict[str, str]] = {
    # Header
    "app.subtitle": {
        "en": "Resize, convert and compress many images at once",
        "pl": "Zmieniaj rozmiar, konwertuj i kompresuj wiele obrazów naraz",
    },
    "app.description": {
        "en": "Resize, convert and compress images in batches.",
        "pl": "Zmiana rozmiaru, konwersja i kompresja wielu obrazów naraz.",
    },
    # Cards
    "card.images": {"en": "Images", "pl": "Obrazy"},
    "card.preview": {"en": "Preview", "pl": "Podgląd"},
    "card.resize": {"en": "Resize", "pl": "Rozmiar"},
    "card.output": {"en": "Output", "pl": "Zapis"},
    # Buttons
    "btn.add_images": {"en": "Add images…", "pl": "Dodaj obrazy…"},
    "btn.add_folder": {"en": "Add folder…", "pl": "Dodaj folder…"},
    "btn.remove": {"en": "Remove", "pl": "Usuń"},
    "btn.clear": {"en": "Clear all", "pl": "Wyczyść"},
    "btn.choose": {"en": "Choose…", "pl": "Wybierz…"},
    "btn.cancel": {"en": "Cancel", "pl": "Anuluj"},
    "btn.resize": {"en": "Resize images", "pl": "Przetwórz obrazy"},
    "btn.resize_n": {"en": "Resize {count}", "pl": "Przetwórz {count}"},
    # Table
    "col.file": {"en": "File", "pl": "Plik"},
    "col.dims": {"en": "Dimensions", "pl": "Wymiary"},
    "col.filesize": {"en": "File size", "pl": "Rozmiar pliku"},
    "col.result": {"en": "Result", "pl": "Wynik"},
    "empty.drop": {
        "en": "No images yet. Drag images or folders here, or use Add images.",
        "pl": "Brak obrazów. Przeciągnij tu obrazy lub foldery albo użyj przycisku Dodaj obrazy.",
    },
    "empty.no_drop": {
        "en": "No images yet. Use Add images or Add folder.",
        "pl": "Brak obrazów. Użyj przycisku Dodaj obrazy lub Dodaj folder.",
    },
    # Preview
    "preview.hint": {"en": "Select an image to preview the result.", "pl": "Wybierz obraz, aby zobaczyć podgląd wyniku."},
    "preview.error": {"en": "Can't preview {name}: {error}", "pl": "Nie można wyświetlić podglądu {name}: {error}"},
    # Resize settings
    "label.preset": {"en": "Preset", "pl": "Szablon"},
    "label.mode": {"en": "Mode", "pl": "Tryb"},
    "label.width": {"en": "Width (px)", "pl": "Szerokość (px)"},
    "label.height": {"en": "Height (px)", "pl": "Wysokość (px)"},
    "label.scale": {"en": "Scale", "pl": "Skala"},
    "switch.lock": {"en": "Lock aspect ratio", "pl": "Zachowaj proporcje"},
    "switch.upscale": {
        "en": "Enlarge images smaller than the target",
        "pl": "Powiększaj obrazy mniejsze od docelowych",
    },
    "mode.fit": {"en": "Fit within", "pl": "Dopasuj"},
    "mode.fill": {"en": "Fill and crop", "pl": "Wypełnij i przytnij"},
    "mode.exact": {"en": "Exact size", "pl": "Dokładny rozmiar"},
    "mode.percent": {"en": "Percentage", "pl": "Procentowo"},
    "mode.fit.help": {
        "en": "Fits the image inside the box, keeping proportions.",
        "pl": "Mieści obraz w podanym polu, zachowując proporcje.",
    },
    "mode.fill.help": {
        "en": "Fills the box and crops the overflow from the center.",
        "pl": "Wypełnia całe pole i przycina nadmiar od środka.",
    },
    "mode.exact.help": {
        "en": "Forces the exact size. May distort the image.",
        "pl": "Wymusza dokładny rozmiar. Może zniekształcić obraz.",
    },
    "mode.percent.help": {
        "en": "Scales both sides by the same percentage.",
        "pl": "Skaluje oba boki o ten sam procent.",
    },
    # Output settings
    "label.format": {"en": "Format", "pl": "Format"},
    "format.original": {"en": "Same as original", "pl": "Jak oryginał"},
    "label.quality": {"en": "Quality", "pl": "Jakość"},
    "quality.help": {
        "en": "Lower = smaller files. 80–90 is a good balance.",
        "pl": "Niższa = mniejsze pliki. 80–90 to dobry kompromis.",
    },
    "switch.metadata": {
        "en": "Keep EXIF metadata (camera, date, GPS)",
        "pl": "Zachowaj metadane EXIF (aparat, data, GPS)",
    },
    "switch.strip_gps": {
        "en": "Remove GPS location (recommended)",
        "pl": "Usuń lokalizację GPS (zalecane)",
    },
    "switch.limit_size": {"en": "Limit file size", "pl": "Ogranicz rozmiar pliku"},
    "label.max_size": {"en": "Maximum size per file (MB)", "pl": "Maksymalny rozmiar pliku (MB)"},
    "limit.help": {
        "en": "Lowers quality first, then resolution.",
        "pl": "Najpierw obniża jakość, potem rozdzielczość.",
    },
    "label.suffix": {"en": "File name suffix", "pl": "Dopisek do nazwy pliku"},
    "suffix.example": {"en": "photo.jpg  →  photo{suffix}{ext}", "pl": "zdjecie.jpg  →  zdjecie{suffix}{ext}"},
    "label.save_to": {"en": "Save to", "pl": "Zapisz w"},
    "dest.next_to": {"en": "Next to the originals", "pl": "Obok oryginałów"},
    "dest.custom": {"en": "Custom folder", "pl": "Wybranym folderze"},
    "folder.none": {"en": "No folder selected", "pl": "Nie wybrano folderu"},
    "switch.overwrite": {"en": "Overwrite files with the same name", "pl": "Nadpisuj pliki o tej samej nazwie"},
    # Presets
    "preset.custom": {"en": "Custom", "pl": "Własny"},
    "preset.slide_169": {"en": "Presentation slide 16:9", "pl": "Slajd prezentacji 16:9"},
    "preset.slide_43": {"en": "Presentation slide 4:3", "pl": "Slajd prezentacji 4:3"},
    "preset.thesis": {"en": "Thesis / publication figure", "pl": "Ilustracja do pracy dyplomowej / publikacji"},
    "preset.poster": {"en": "Conference poster graphic", "pl": "Grafika na plakat konferencyjny"},
    "preset.elearning": {"en": "Moodle / e-learning", "pl": "Moodle / e-learning"},
    "preset.id_photo": {
        "en": "ID photo 35 × 45 mm (413 × 531 px, 300 dpi)",
        "pl": "Zdjęcie legitymacyjne 35 × 45 mm (413 × 531 px, 300 dpi)",
    },
    "preset.uhd_4k": {"en": "4K UHD", "pl": "4K UHD"},
    "preset.hd": {"en": "HD", "pl": "HD"},
    "preset.web": {"en": "Web / blog", "pl": "Strona WWW / blog"},
    "preset.email": {"en": "Email attachment", "pl": "Załącznik e-mail"},
    "preset.ig_post": {"en": "Instagram post", "pl": "Instagram – post"},
    "preset.ig_portrait": {"en": "Instagram portrait", "pl": "Instagram – pionowy"},
    "preset.ig_story": {"en": "Instagram story", "pl": "Instagram – relacja"},
    "preset.fb_cover": {"en": "Facebook cover", "pl": "Facebook – zdjęcie w tle"},
    "preset.yt_thumb": {"en": "YouTube thumbnail", "pl": "YouTube – miniatura"},
    "preset.x_post": {"en": "X / Twitter post", "pl": "X / Twitter – post"},
    "preset.li_banner": {"en": "LinkedIn banner", "pl": "LinkedIn – baner"},
    "preset.avatar": {"en": "Avatar", "pl": "Awatar"},
    "preset.thumb": {"en": "Thumbnail", "pl": "Miniatura"},
    # Status bar
    "status.ready": {"en": "Ready", "pl": "Gotowy"},
    "status.skipped": {
        "en": "Skipped {n} file(s) that could not be read as images.",
        "pl": "Pominięte pliki, których nie da się odczytać jako obrazów: {n}.",
    },
    "status.processing": {"en": "Resizing {index} of {total}: {name}", "pl": "Przetwarzanie {index} z {total}: {name}"},
    "status.cancelling": {"en": "Cancelling after the current image…", "pl": "Anulowanie po bieżącym obrazie…"},
    "summary.count": {"en": "{count} · {size}", "pl": "{count} · {size}"},
    # Validation
    "err.empty": {"en": "{field} is empty.", "pl": "Pole „{field}” jest puste."},
    "err.dimension": {
        "en": "{field} must be between 1 and {max} px.",
        "pl": "{field} musi mieścić się w zakresie od 1 do {max} px.",
    },
    "err.percent": {"en": "Percentage must be between 1 and 1000.", "pl": "Procent musi mieścić się w zakresie od 1 do 1000."},
    "err.quality": {"en": "Quality must be between 1 and 100.", "pl": "Jakość musi mieścić się w zakresie od 1 do 100."},
    "err.mode": {"en": "Unknown resize mode: {value}", "pl": "Nieznany tryb zmiany rozmiaru: {value}"},
    "err.format": {"en": "Unknown output format: {value}", "pl": "Nieznany format wyjściowy: {value}"},
    "err.suffix": {
        "en": 'The file name suffix cannot contain any of these characters: < > : " / \\ | ? *',
        "pl": 'Dopisek do nazwy pliku nie może zawierać znaków: < > : " / \\ | ? *',
    },
    "err.max_size": {
        "en": "Maximum file size must be between {min} and {max} MB.",
        "pl": "Maksymalny rozmiar pliku musi mieścić się w zakresie od {min} do {max} MB.",
    },
    "field.width": {"en": "Width", "pl": "Szerokość"},
    "field.height": {"en": "Height", "pl": "Wysokość"},
    # Dialogs
    "dialog.add_images": {"en": "Add images", "pl": "Dodaj obrazy"},
    "dialog.add_folder": {"en": "Add all images from a folder", "pl": "Dodaj wszystkie obrazy z folderu"},
    "dialog.choose_output": {"en": "Choose where to save resized images", "pl": "Wybierz, gdzie zapisać gotowe obrazy"},
    "dialog.check_settings": {"en": "Check your settings", "pl": "Sprawdź ustawienia"},
    "dialog.no_folder": {"en": "No folder selected", "pl": "Nie wybrano folderu"},
    "dialog.no_folder.msg": {"en": "Choose a folder to save to.", "pl": "Wybierz folder, w którym mają zostać zapisane obrazy."},
    "dialog.replace": {"en": "Replace original files?", "pl": "Zastąpić oryginalne pliki?"},
    "dialog.replace.msg": {
        "en": "There is no file name suffix and overwriting is on, so your original images "
        "will be replaced. This cannot be undone. Continue?",
        "pl": "Dopisek do nazwy jest pusty, a nadpisywanie jest włączone, więc oryginalne obrazy "
        "zostaną zastąpione. Tego nie da się cofnąć. Kontynuować?",
    },
    "dialog.complete": {"en": "Resize complete", "pl": "Zakończono"},
    "dialog.nothing_saved": {"en": "Nothing was saved", "pl": "Nic nie zapisano"},
    "summary.done": {"en": "Done. {done} of {total} images were saved.", "pl": "Gotowe. Zapisane obrazy: {done} z {total}."},
    "summary.cancelled": {
        "en": "Cancelled. {done} of {total} images were saved.",
        "pl": "Anulowano. Zapisane obrazy: {done} z {total}.",
    },
    "summary.size": {"en": "Total size: {before} → {after} ({change})", "pl": "Łączny rozmiar: {before} → {after} ({change})"},
    "summary.gps": {
        "en": "GPS location removed from {count}.",
        "pl": "Usunięto lokalizację GPS z {count}.",
    },
    "summary.limit_missed": {
        "en": "{count} could not be made smaller than {limit}.",
        "pl": "Nie udało się zmniejszyć poniżej {limit}: {count}.",
    },
    "summary.limit_shrunk": {
        "en": "To fit the size limit, the resolution was reduced for {count}.",
        "pl": "Aby zmieścić się w limicie rozmiaru, zmniejszono rozdzielczość: {count}.",
    },
    "summary.failed": {"en": "{n} image(s) failed:", "pl": "Nie udało się przetworzyć ({n}):"},
    "summary.more": {"en": "…and {n} more.", "pl": "…i {n} więcej."},
    "summary.open": {"en": "Open the folder with the resized images?", "pl": "Otworzyć folder z gotowymi obrazami?"},
    # Menus
    "menu.file": {"en": "File", "pl": "Plik"},
    "menu.help": {"en": "Help", "pl": "Pomoc"},
    "cmd.add_images": {"en": "Add images…", "pl": "Dodaj obrazy…"},
    "cmd.add_folder": {"en": "Add folder…", "pl": "Dodaj folder…"},
    "cmd.resize": {"en": "Resize images", "pl": "Przetwórz obrazy"},
    "cmd.clear": {"en": "Clear list", "pl": "Wyczyść listę"},
    "cmd.github": {"en": "Project on GitHub", "pl": "Projekt na GitHubie"},
    "cmd.exit": {"en": "Exit", "pl": "Zakończ"},
    "cmd.homepage": {"en": "Visit homepage", "pl": "Strona projektu"},
    "cmd.about": {"en": "About {name}", "pl": "O programie {name}"},
    "about.text": {
        "en": "{name} {version}\n\n{description}\n\nAuthor: {author}\n{url}",
        "pl": "{name} {version}\n\n{description}\n\nAutor: {author}\n{url}",
    },
}

# Plural forms: English has one/other, Polish has one/few/many.
PLURALS: dict[str, dict[str, tuple[str, ...]]] = {
    "images": {
        "en": ("{n} image", "{n} images"),
        "pl": ("{n} obraz", "{n} obrazy", "{n} obrazów"),
    },
    # Genitive, after "z" / "from": "z 1 zdjęcia", "z 5 zdjęć"
    "photos_from": {
        "en": ("{n} photo", "{n} photos"),
        "pl": ("{n} zdjęcia", "{n} zdjęć", "{n} zdjęć"),
    },
}

_DECIMAL_SEPARATOR = {"en": ".", "pl": ","}


def set_language(code: str) -> None:
    global _current
    _current = code if code in LANGUAGES else DEFAULT_LANGUAGE


def current_language() -> str:
    return _current


def tr(key: str, **kwargs) -> str:
    entry = STRINGS[key]
    text = entry.get(_current) or entry[DEFAULT_LANGUAGE]
    return text.format(**kwargs) if kwargs else text


def plural(key: str, n: int) -> str:
    forms = PLURALS[key].get(_current) or PLURALS[key][DEFAULT_LANGUAGE]
    if len(forms) == 3:  # Polish rules
        if n == 1:
            form = forms[0]
        elif n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
            form = forms[1]
        else:
            form = forms[2]
    else:
        form = forms[0] if n == 1 else forms[1]
    return form.format(n=n)


def format_decimal(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f}".replace(".", _DECIMAL_SEPARATOR.get(_current, "."))


def detect_language() -> str:
    """Pick the language of the operating system, falling back to English."""
    code = ""
    if sys.platform == "win32":
        try:
            import ctypes

            lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            code = {0x15: "pl", 0x09: "en"}.get(lang_id & 0x3FF, "")
        except Exception:
            code = ""
    if not code:
        try:
            name = (locale.getlocale()[0] or "").lower()
        except ValueError:
            name = ""
        code = "pl" if name.startswith(("pl", "polish")) else ""
    return code if code in LANGUAGES else DEFAULT_LANGUAGE
