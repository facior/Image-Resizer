"""Design tokens (flat style, teal + orange palette) and shared Pack styles."""

from toga.style import Pack
from toga.style.pack import BOLD

# Colors
PRIMARY = "#0D9488"
ON_PRIMARY = "#000000"
ACCENT = "#EA580C"
ON_ACCENT = "#000000"
BACKGROUND = "#F0FDFA"
FOREGROUND = "#134E4A"
CARD = "#FFFFFF"
MUTED = "#E8F1F4"
MUTED_FOREGROUND = "#475569"
DESTRUCTIVE = "#DC2626"
SUCCESS = "#0F766E"

# Spacing scale (px)
SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 12
SPACE_LG = 16
SPACE_XL = 24

FONT = ["Segoe UI", "system"]
FONT_SIZE = 10
CONTROL_HEIGHT = 32


def _style(defaults: dict, overrides: dict) -> Pack:
    return Pack(**{**defaults, **overrides})


def text(**kwargs) -> Pack:
    return _style(dict(font_family=FONT, font_size=FONT_SIZE, color=FOREGROUND), kwargs)


def muted(**kwargs) -> Pack:
    return _style(dict(font_family=FONT, font_size=FONT_SIZE - 1, color=MUTED_FOREGROUND), kwargs)


def heading(**kwargs) -> Pack:
    return _style(dict(font_family=FONT, font_size=FONT_SIZE + 2, font_weight=BOLD, color=FOREGROUND), kwargs)


def button(**kwargs) -> Pack:
    return _style(dict(font_family=FONT, font_size=FONT_SIZE, height=CONTROL_HEIGHT), kwargs)


def primary_button(**kwargs) -> Pack:
    return _style(
        dict(
            font_family=FONT,
            font_size=FONT_SIZE + 1,
            font_weight=BOLD,
            height=CONTROL_HEIGHT + 8,
            background_color=ACCENT,
            color=ON_ACCENT,
        ),
        kwargs,
    )


def secondary_button(**kwargs) -> Pack:
    return _style(
        dict(font_family=FONT, font_size=FONT_SIZE, height=CONTROL_HEIGHT, background_color=PRIMARY, color=ON_PRIMARY),
        kwargs,
    )


def field(**kwargs) -> Pack:
    return _style(dict(font_family=FONT, font_size=FONT_SIZE), kwargs)
