"""Draws the Image Resizer logo in the app palette (teal + orange).

Concept: a photo card (mountain + sun) with an orange "expand" arrow leaving
its corner - resizing an image. Drawn at 4x and downsampled for smooth edges.
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

TEAL = (13, 148, 136)
TEAL_DARK = (15, 118, 110)
WHITE = (255, 255, 255)
ORANGE = (234, 88, 12)
MINT = (204, 251, 241)

SS = 4  # supersampling


def draw_logo(size: int, simple: bool = False) -> Image.Image:
    S = size * SS
    u = S / 100  # work in a 100-unit grid
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def box(x0, y0, x1, y1):
        return [round(x0 * u), round(y0 * u), round(x1 * u), round(y1 * u)]

    def pts(*xy):
        return [(round(x * u), round(y * u)) for x, y in xy]

    # Background tile
    d.rounded_rectangle(box(2, 2, 98, 98), radius=round(22 * u), fill=TEAL)

    # Photo card (bottom-left)
    card = (14, 34, 66, 86)
    d.rounded_rectangle(box(*card), radius=round(7 * u), fill=WHITE)
    # Picture area inside the card
    inner = (20, 40, 60, 80)
    d.rounded_rectangle(box(*inner), radius=round(3.5 * u), fill=MINT)
    # Mountains
    d.polygon(pts((20, 80), (33, 59), (42, 72), (49, 63), (60, 80)), fill=TEAL)
    # Sun (top-left of the picture, away from the arrow)
    d.ellipse(box(24, 44, 33, 53), fill=ORANGE)

    # Expand arrow: shaft from the card's top-right corner, triangular head at the tile corner

    tail, tip = (52, 48), (86, 14)
    dx, dy = tip[0] - tail[0], tip[1] - tail[1]
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length  # along the arrow
    nx, ny = -uy, ux  # normal
    shaft_w = 8 if not simple else 10
    head_len = 20 if not simple else 24
    head_w = 26 if not simple else 30
    base = (tip[0] - ux * head_len, tip[1] - uy * head_len)
    hw, sw = head_w / 2, shaft_w / 2
    # White outline first so the arrow reads where it crosses the card edge
    outline = 3 if not simple else 0
    for grow, color in (((outline, WHITE) if outline else (0, None)), (0, ORANGE)):
        if color is None:
            continue
        g = grow
        shaft = [
            (tail[0] + nx * (sw + g) - ux * g, tail[1] + ny * (sw + g) - uy * g),
            (base[0] + nx * (sw + g), base[1] + ny * (sw + g)),
            (base[0] + nx * (hw + g * 1.6), base[1] + ny * (hw + g * 1.6)),
            (tip[0] + ux * g * 1.8, tip[1] + uy * g * 1.8),
            (base[0] - nx * (hw + g * 1.6), base[1] - ny * (hw + g * 1.6)),
            (base[0] - nx * (sw + g), base[1] - ny * (sw + g)),
            (tail[0] - nx * (sw + g) - ux * g, tail[1] - ny * (sw + g) - uy * g),
        ]
        d.polygon(pts(*shaft), fill=color)

    return img.resize((size, size), Image.Resampling.LANCZOS)


def main(out_dirs):
    big = draw_logo(1024)
    sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    frames = [draw_logo(s, simple=s <= 32) for s in sizes]
    for out in out_dirs:
        out = Path(out)
        out.mkdir(parents=True, exist_ok=True)
        big.resize((512, 512), Image.Resampling.LANCZOS).save(out / "logo.png")
        frames[-1].save(out / "logo.ico", format="ICO", sizes=[(s, s) for s in sizes], append_images=frames[:-1])
    big.save(Path(out_dirs[0]).parent / "logo-1024.png") if len(out_dirs) > 1 else None
    # Preview sheet for checking small sizes
    sheet = Image.new("RGBA", (sum(sizes) + 20 * len(sizes) + 532, 532), (240, 253, 250, 255))
    x = 10
    sheet.paste(big.resize((512, 512)), (x, 10), big.resize((512, 512)))
    x += 532
    for f in frames:
        sheet.paste(f, (x, 266 - f.height // 2), f)
        x += f.width + 20
    return sheet


if __name__ == "__main__":
    sheet = main(sys.argv[2:])
    sheet.save(sys.argv[1])

# Usage (from the ImageResizer folder):
#   python tools/make_logo.py preview.png src/ImageResizer/resources
