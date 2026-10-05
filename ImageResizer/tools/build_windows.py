"""Builds the Windows installer (MSI with a Polish setup wizard) and a portable ZIP.

Usage, from the ImageResizer folder with the project's virtualenv active:

    python tools/build_windows.py

Output goes to dist/:
    ImageResizer-<version>.msi   installer (per-user or per-machine)
    ImageResizer-<version>.zip   portable version, for PCs where installing is not allowed

Why not just `briefcase package windows`: Briefcase builds the MSI with the
Western European code page (1252), which fails on the "Ł" in the author's name,
and it always produces an English setup wizard. This script patches the
generated WiX sources and runs WiX itself with the Polish culture.
"""

from __future__ import annotations

import glob
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
APP = "ImageResizer"
APP_DIR = ROOT / "build" / APP / "windows" / "app"
DIST = ROOT / "dist"
LOGO = ROOT / "src" / APP / "resources" / "logo.png"
WIX_CACHE = Path(os.environ["LOCALAPPDATA"]) / "BeeWare" / "briefcase" / "Cache" / "tools" / "wix"

TEAL = (13, 148, 136)
TEAL_DARK = (15, 118, 110)
WHITE = (255, 255, 255)
MINT = (240, 253, 250)

POLISH_STRINGS = {
    "InstallScopeDlgPerMachineDescription": (
        "[ProductName] zostanie zainstalowany dla wszystkich użytkowników komputera. "
        "Wymaga to uprawnień administratora."
    ),
    "MaintenanceWelcomeDlgTitle": "{\\WixUI_Font_Bigger}Odinstalowywanie programu [ProductName]",
    "MaintenanceWelcomeDlgDescription": (
        "Program [ProductName] jest już zainstalowany. Ten kreator pozwoli go odinstalować. "
        "Kliknij Dalej, aby kontynuować, lub Anuluj, aby zakończyć."
    ),
}


def run(*args: str | Path, cwd: Path = ROOT) -> None:
    print(">", " ".join(str(a) for a in args), flush=True)
    subprocess.run([str(a) for a in args], cwd=cwd, check=True)


def briefcase(*args: str) -> None:
    run(sys.executable, "-m", "briefcase", *args, "--no-input")


def make_bitmaps(target: Path) -> None:
    """Setup wizard artwork in the app colors (sizes required by WixUI)."""
    logo = Image.open(LOGO).convert("RGBA")
    font_path = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "segoeuib.ttf"

    def font(size):
        try:
            return ImageFont.truetype(str(font_path), size)
        except OSError:
            return ImageFont.load_default()

    # Welcome/finish dialog: the left 164 px are free for artwork, text is drawn by Windows on the right.
    dialog = Image.new("RGB", (493, 312), WHITE)
    draw = ImageDraw.Draw(dialog)
    draw.rectangle([0, 0, 163, 311], fill=TEAL)
    draw.rectangle([0, 250, 163, 311], fill=TEAL_DARK)
    icon = logo.resize((112, 112), Image.Resampling.LANCZOS)
    dialog.paste(icon, (26, 60), icon)
    draw.text((82, 196), "Image", font=font(18), fill=WHITE, anchor="mm")
    draw.text((82, 220), "Resizer", font=font(18), fill=WHITE, anchor="mm")
    dialog.save(target / "dialog.bmp")

    # Top banner on the inner pages: text is drawn by Windows on the left, logo goes on the right.
    banner = Image.new("RGB", (493, 58), WHITE)
    draw = ImageDraw.Draw(banner)
    draw.rectangle([0, 55, 492, 57], fill=TEAL)
    small = logo.resize((42, 42), Image.Resampling.LANCZOS)
    banner.paste(small, (440, 6), small)
    banner.save(target / "banner.bmp")


def patch_wix_sources() -> None:
    wxs_path = APP_DIR / f"{APP}.wxs"
    wxs = wxs_path.read_text(encoding="utf-8")
    # Polish language + Central European code page (has Ł, ą, ę...).
    wxs = re.sub(r'Language="\d+"', 'Language="1045"\n        Codepage="1250"', wxs, count=1)
    # Display name with a space (Start menu, install folder, Apps & features). Briefcase
    # itself can't use a formal name with a space, the .exe would not be found.
    wxs = wxs.replace('Name="ImageResizer"', 'Name="Image Resizer"')
    wxs = wxs.replace('<Property Id="DIALOG_TITLE" Value="Installation" />',
                      '<Property Id="DIALOG_TITLE" Value="– instalacja" />')
    wxs = wxs.replace('Value="Uninstallation"', 'Value="– odinstalowywanie"')
    artwork = (
        '        <WixVariable Id="WixUIDialogBmp" Value="dialog.bmp" />\n'
        '        <WixVariable Id="WixUIBannerBmp" Value="banner.bmp" />\n'
    )
    if "WixUIDialogBmp" not in wxs:
        wxs = wxs.replace("    </Package>", artwork + "    </Package>")
    wxs_path.write_text(wxs, encoding="utf-8")

    wxl_path = APP_DIR / "unicode.wxl"
    wxl = wxl_path.read_text(encoding="utf-8")
    wxl = re.sub(r'<WixLocalization Culture="[^"]+"( Codepage="\d+")?',
                 '<WixLocalization Culture="pl-PL" Codepage="1250"', wxl)
    for string_id, text in POLISH_STRINGS.items():
        escaped = text.replace("&", "&amp;").replace('"', "&quot;")
        wxl = re.sub(rf'(Id="{string_id}"\s+Value=")[^"]*(")',
                     lambda m, text=escaped: m.group(1) + text + m.group(2), wxl)
    wxl_path.write_text(wxl, encoding="utf-8")


def find_wix() -> tuple[Path, list[Path]]:
    wix = next(iter(glob.glob(str(WIX_CACHE / "PFiles64" / "WiX Toolset *" / "bin" / "wix.exe"))), None)
    if not wix:
        sys.exit("WiX not found. Run `briefcase package windows` once so Briefcase downloads it.")
    extensions = [
        Path(next(iter(glob.glob(str(WIX_CACHE / "CFiles64" / "WixToolset" / "extensions" / name / "*" / "wixext*" / f"{name}.dll")))))
        for name in ("WixToolset.UI.wixext", "WixToolset.Netfx.wixext", "WixToolset.Util.wixext")
    ]
    return Path(wix), extensions


def main() -> None:
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["briefcase"]["version"]

    # Fresh build so no stale files end up in the package.
    shutil.rmtree(ROOT / "build" / APP / "windows", ignore_errors=True)
    briefcase("create", "windows")
    briefcase("build", "windows")

    # Portable ZIP straight from the built app.
    DIST.mkdir(exist_ok=True)
    briefcase("package", "windows", "--packaging-format", "zip", "--adhoc-sign")

    # Make sure WiX is installed in the Briefcase cache (first run only).
    if not WIX_CACHE.exists():
        try:
            briefcase("package", "windows", "--adhoc-sign")
        except subprocess.CalledProcessError:
            pass  # expected to fail on the code page; it only needs to download WiX

    patch_wix_sources()
    make_bitmaps(APP_DIR)
    wix, extensions = find_wix()
    msi = DIST / f"{APP}-{version}.msi"
    args: list[str | Path] = [wix, "build"]
    for ext in extensions:
        args += ["-ext", ext]
    args += ["-arch", "x64", "-culture", "pl-PL", f"{APP}.wxs", "-loc", "unicode.wxl",
             "-pdbtype", "none", "-o", msi]
    run(*args, cwd=APP_DIR)

    print(f"\nDone:\n  {msi}\n  {DIST / f'{APP}-{version}.zip'}")


if __name__ == "__main__":
    main()
