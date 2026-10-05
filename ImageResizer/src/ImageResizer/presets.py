"""Common target sizes. Each preset sets the resize mode and the box size."""

from ImageResizer.core import MODE_FILL, MODE_FIT
from ImageResizer.i18n import tr

CUSTOM = "custom"

# key -> (mode, width, height). Labels come from i18n ("preset.<key>").
PRESETS: dict[str, tuple[str, int, int]] = {
    # Academic use first: the app is mainly used at a university.
    "slide_169": (MODE_FIT, 1920, 1080),
    "slide_43": (MODE_FIT, 1024, 768),
    "thesis": (MODE_FIT, 2000, 2000),
    "poster": (MODE_FIT, 3500, 3500),
    "elearning": (MODE_FIT, 1280, 1280),
    "id_photo": (MODE_FILL, 413, 531),
    # General
    "uhd_4k": (MODE_FIT, 3840, 2160),
    "hd": (MODE_FIT, 1280, 720),
    "web": (MODE_FIT, 1200, 1200),
    "email": (MODE_FIT, 800, 800),
    "ig_post": (MODE_FILL, 1080, 1080),
    "ig_portrait": (MODE_FILL, 1080, 1350),
    "ig_story": (MODE_FILL, 1080, 1920),
    "fb_cover": (MODE_FILL, 851, 315),
    "yt_thumb": (MODE_FILL, 1280, 720),
    "x_post": (MODE_FILL, 1600, 900),
    "li_banner": (MODE_FILL, 1584, 396),
    "avatar": (MODE_FILL, 400, 400),
    "thumb": (MODE_FILL, 150, 150),
}

PRESET_KEYS = [CUSTOM, *PRESETS]

# Labels that already describe the size better than pixels do.
_NO_SIZE_IN_LABEL = {"id_photo"}


def preset_label(key: str) -> str:
    name = tr(f"preset.{key}")
    if key not in PRESETS:
        return name
    mode, width, height = PRESETS[key]
    if key in _NO_SIZE_IN_LABEL:
        return name
    if mode == MODE_FIT and width == height:
        return f"{name} ({width} px)"
    return f"{name} ({width} × {height})"
