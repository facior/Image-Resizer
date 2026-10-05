"""Image processing logic, independent of the UI so it can be tested directly."""

from __future__ import annotations

import io
import math
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageOps

from ImageResizer.i18n import format_decimal, tr

SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff")
MAX_DIMENSION = 20000

# Resize modes. These keys are stored in settings; labels come from i18n ("mode.<key>").
MODE_FIT = "fit"
MODE_FILL = "fill"
MODE_EXACT = "exact"
MODE_PERCENT = "percent"
MODES = [MODE_FIT, MODE_FILL, MODE_EXACT, MODE_PERCENT]

# Output formats: key -> (Pillow format, extension). None keeps the source format.
FORMAT_ORIGINAL = "original"
FORMATS: dict[str, tuple[str, str] | None] = {
    FORMAT_ORIGINAL: None,
    "JPEG": ("JPEG", ".jpg"),
    "PNG": ("PNG", ".png"),
    "WebP": ("WEBP", ".webp"),
    "BMP": ("BMP", ".bmp"),
    "GIF": ("GIF", ".gif"),
    "TIFF": ("TIFF", ".tiff"),
}
LOSSY_FORMATS = {"JPEG", "WEBP"}

GPS_IFD_TAG = 0x8825
BYTES_PER_MB = 1_000_000  # decimal MB: the result also fits limits that mean 1024 × 1024
MIN_LIMIT_MB = 0.01
MAX_LIMIT_MB = 100
MIN_AUTO_QUALITY = 40  # below this JPEG/WebP look bad; shrink the image instead
MIN_AUTO_SIDE = 64
_ALPHA_FORMATS = {"PNG", "WEBP", "GIF", "TIFF"}
_EXIF_FORMATS = {"JPEG", "PNG", "WEBP", "TIFF"}


@dataclass
class ResizeSettings:
    mode: str = MODE_FIT
    width: int = 1920
    height: int = 1080
    percent: float = 50.0
    allow_upscale: bool = False
    output_format: str = FORMAT_ORIGINAL
    quality: int = 85
    keep_metadata: bool = False
    strip_gps: bool = True  # applies when metadata is kept
    limit_file_size: bool = False
    max_file_mb: float = 2.0
    suffix: str = "_resized"
    output_dir: Path | None = None  # None saves next to the original
    overwrite: bool = False

    def validate(self) -> None:
        if self.mode not in MODES:
            raise ValueError(tr("err.mode", value=self.mode))
        if self.mode == MODE_PERCENT:
            if not 1 <= self.percent <= 1000:
                raise ValueError(tr("err.percent"))
        else:
            for field_key, value in (("field.width", self.width), ("field.height", self.height)):
                if not 1 <= value <= MAX_DIMENSION:
                    raise ValueError(tr("err.dimension", field=tr(field_key), max=MAX_DIMENSION))
        if self.output_format not in FORMATS:
            raise ValueError(tr("err.format", value=self.output_format))
        if not 1 <= self.quality <= 100:
            raise ValueError(tr("err.quality"))
        if self.limit_file_size and not MIN_LIMIT_MB <= self.max_file_mb <= MAX_LIMIT_MB:
            raise ValueError(tr("err.max_size", min=MIN_LIMIT_MB, max=MAX_LIMIT_MB))


@dataclass
class ResizeResult:
    source: Path
    destination: Path
    original_size: tuple[int, int]
    new_size: tuple[int, int]
    bytes_before: int
    bytes_after: int
    quality_used: int | None = None  # set for JPEG/WebP
    limit_met: bool | None = None  # None when no size limit was requested
    gps_removed: bool = False  # the source had GPS data and the output doesn't


@dataclass
class ImageInfo:
    path: Path
    size: tuple[int, int]
    file_bytes: int
    format: str = field(default="")


def read_info(path: Path) -> ImageInfo:
    """Read dimensions without decoding the pixel data. Honors EXIF rotation."""
    with Image.open(path) as img:
        width, height = img.size
        orientation = img.getexif().get(0x0112, 1)
        if orientation in (5, 6, 7, 8):
            width, height = height, width
        return ImageInfo(Path(path), (width, height), Path(path).stat().st_size, img.format or "")


def target_size(source: tuple[int, int], settings: ResizeSettings) -> tuple[int, int]:
    """Size of the final image (after any crop) for the given source size."""
    src_w, src_h = source
    if settings.mode == MODE_EXACT:
        return settings.width, settings.height
    if settings.mode == MODE_FILL:
        if not settings.allow_upscale and (src_w < settings.width or src_h < settings.height):
            # Can't fill without upscaling: crop to the box ratio at the largest possible size.
            scale = min(src_w / settings.width, src_h / settings.height, 1.0)
            return max(1, round(settings.width * scale)), max(1, round(settings.height * scale))
        return settings.width, settings.height
    if settings.mode == MODE_PERCENT:
        scale = settings.percent / 100
    else:  # MODE_FIT
        scale = min(settings.width / src_w, settings.height / src_h)
    if not settings.allow_upscale:
        scale = min(scale, 1.0)
    return max(1, round(src_w * scale)), max(1, round(src_h * scale))


def resolve_format(source: Path, settings: ResizeSettings) -> tuple[str, str]:
    """Return (Pillow format, extension) for the output file."""
    chosen = FORMATS[settings.output_format]
    if chosen is not None:
        return chosen
    ext = source.suffix.lower()
    for fmt, fmt_ext in (v for v in FORMATS.values() if v):
        if ext == fmt_ext or (fmt == "JPEG" and ext == ".jpeg") or (fmt == "TIFF" and ext == ".tif"):
            return fmt, ext
    return "PNG", ".png"


def output_path(source: Path, settings: ResizeSettings) -> Path:
    _, ext = resolve_format(source, settings)
    folder = settings.output_dir or source.parent
    candidate = folder / f"{source.stem}{settings.suffix}{ext}"
    if settings.overwrite:
        return candidate
    counter = 2
    while candidate.exists() or candidate == source:
        candidate = folder / f"{source.stem}{settings.suffix} ({counter}){ext}"
        counter += 1
    return candidate


def _prepare_mode(img: Image.Image, fmt: str) -> Image.Image:
    """Convert to a pixel mode the output format can store."""
    has_alpha = img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info)
    if fmt in _ALPHA_FORMATS and has_alpha:
        if img.mode == "RGBA" or fmt == "GIF" or (img.mode == "LA" and fmt in ("PNG", "TIFF")):
            return img
        return img.convert("RGBA")
    if has_alpha:
        # Flatten transparency onto white instead of letting it turn black.
        rgba = img.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    if img.mode in ("RGB", "L") or (fmt == "GIF" and img.mode == "P"):
        return img
    return img.convert("RGB")


def resize_image(source: Path, settings: ResizeSettings) -> ResizeResult:
    settings.validate()
    source = Path(source)
    fmt, _ = resolve_format(source, settings)
    destination = output_path(source, settings)

    with Image.open(source) as opened:
        icc_profile = opened.info.get("icc_profile")
        img = ImageOps.exif_transpose(opened)
        exif = img.getexif()
        original_size = img.size
        new_size = target_size(original_size, settings)

        # Palette and 1-bit images resize badly; work in full color.
        if img.mode in ("P", "1"):
            img = img.convert("RGBA" if "transparency" in img.info else "RGB")

        if settings.mode == MODE_FILL:
            resized = ImageOps.fit(img, new_size, Image.Resampling.LANCZOS)
        elif new_size != original_size:
            resized = img.resize(new_size, Image.Resampling.LANCZOS)
        else:
            resized = img.copy()

    resized = _prepare_mode(resized, fmt)

    has_gps = GPS_IFD_TAG in exif
    write_exif = settings.keep_metadata and fmt in _EXIF_FORMATS
    if write_exif and settings.strip_gps and has_gps:
        del exif[GPS_IFD_TAG]
    gps_kept = write_exif and has_gps and not settings.strip_gps

    save_kwargs: dict = {}
    if fmt == "JPEG":
        save_kwargs.update(quality=settings.quality, optimize=True, progressive=True)
    elif fmt == "WEBP":
        save_kwargs.update(quality=settings.quality, method=4)
    elif fmt == "PNG":
        save_kwargs.update(optimize=True)
    elif fmt == "TIFF":
        save_kwargs.update(compression="tiff_lzw")
    if icc_profile and fmt in ("JPEG", "PNG", "WEBP", "TIFF"):
        save_kwargs["icc_profile"] = icc_profile
    if write_exif and len(exif):
        save_kwargs["exif"] = exif.tobytes()

    limit = round(settings.max_file_mb * BYTES_PER_MB) if settings.limit_file_size else None
    data, final, quality_used = _encode_within_limit(resized, fmt, save_kwargs, limit)

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)

    return ResizeResult(
        source=source,
        destination=destination,
        original_size=original_size,
        new_size=final.size,
        bytes_before=source.stat().st_size,
        bytes_after=len(data),
        quality_used=quality_used,
        limit_met=None if limit is None else len(data) <= limit,
        gps_removed=has_gps and not gps_kept,
    )


def _encode(img: Image.Image, fmt: str, save_kwargs: dict) -> bytes:
    buffer = io.BytesIO()
    img.save(buffer, format=fmt, **save_kwargs)
    return buffer.getvalue()


def _encode_within_limit(
    img: Image.Image, fmt: str, save_kwargs: dict, limit: int | None
) -> tuple[bytes, Image.Image, int | None]:
    """Encode the image, lowering quality and then resolution until it fits `limit` bytes.

    Returns (data, the image that was encoded, JPEG/WebP quality used). If the
    limit can't be met, returns the smallest attempt.
    """
    lossy = fmt in LOSSY_FORMATS
    quality = save_kwargs.get("quality") if lossy else None
    data = _encode(img, fmt, save_kwargs)
    if limit is None or len(data) <= limit:
        return data, img, quality

    best = (data, img, quality)
    current = img
    scale = 1.0
    for _ in range(15):
        if lossy:
            # Binary search for the highest quality that fits at this resolution.
            low, high = MIN_AUTO_QUALITY, save_kwargs["quality"]
            smallest = None
            while low <= high:
                q = (low + high) // 2
                attempt = _encode(current, fmt, {**save_kwargs, "quality": q})
                if len(attempt) <= limit:
                    return attempt, current, q
                smallest = (attempt, current, q)
                high = q - 1
            if smallest and len(smallest[0]) < len(best[0]):
                best = smallest
        # Still too big: shrink, estimating from how far over the limit we are.
        over = len(best[0]) / limit
        scale *= min(0.9, max(0.5, 0.95 / math.sqrt(over)))
        size = (round(img.width * scale), round(img.height * scale))
        if min(size) < MIN_AUTO_SIDE:
            break
        current = img.resize(size, Image.Resampling.LANCZOS)  # always from the full image
        if not lossy:
            attempt = _encode(current, fmt, save_kwargs)
            if len(attempt) <= limit:
                return attempt, current, None
            if len(attempt) < len(best[0]):
                best = (attempt, current, None)
    return best


def render_preview(source: Path, settings: ResizeSettings, box: tuple[int, int]) -> Image.Image:
    """Small image showing what the output will look like (crop and distortion included)."""
    with Image.open(source) as opened:
        opened.draft("RGB", (box[0] * 2, box[1] * 2))  # fast JPEG decode at reduced scale
        img = ImageOps.exif_transpose(opened).convert("RGBA")
    if settings.mode in (MODE_FILL, MODE_EXACT):
        # The decoded image may be reduced by draft(), so only the box ratio matters here.
        out_w, out_h = settings.width, settings.height
        scale = min(box[0] / out_w, box[1] / out_h)
        size = (max(1, round(out_w * scale)), max(1, round(out_h * scale)))
        if settings.mode == MODE_FILL:
            return ImageOps.fit(img, size, Image.Resampling.LANCZOS)
        return img.resize(size, Image.Resampling.LANCZOS)
    img.thumbnail(box, Image.Resampling.LANCZOS)
    return img


def collect_images(paths, recursive: bool = True) -> list[Path]:
    """Expand files and folders into a sorted, de-duplicated list of image files."""
    found: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            pattern = path.rglob("*") if recursive else path.glob("*")
            found.extend(sorted(p for p in pattern if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS))
        elif path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            found.append(path)
    seen: set[Path] = set()
    unique = []
    for p in found:
        key = p.resolve()
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def human_size(num_bytes: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(num_bytes) < 1024 or unit == "GB":
            return f"{num_bytes:.0f} {unit}" if unit == "B" else f"{format_decimal(num_bytes)} {unit}"
        num_bytes /= 1024
    return f"{format_decimal(num_bytes)} GB"
