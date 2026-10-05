from pathlib import Path

import pytest
from PIL import Image

from ImageResizer import settings as settings_store
from ImageResizer.core import (
    MODE_EXACT,
    MODE_FILL,
    MODE_FIT,
    MODE_PERCENT,
    ResizeSettings,
    collect_images,
    human_size,
    output_path,
    read_info,
    render_preview,
    resize_image,
    target_size,
)


def make_image(path: Path, size=(400, 200), mode="RGB", color=(200, 30, 30), **save_kwargs) -> Path:
    if mode == "RGBA":
        color = (*color, 128)
    Image.new(mode, size, color).save(path, **save_kwargs)
    return path


# ------------------------------------------------------------- target_size


@pytest.mark.parametrize(
    "mode, source, box, upscale, expected",
    [
        (MODE_FIT, (4000, 3000), (1920, 1080), False, (1440, 1080)),
        (MODE_FIT, (3000, 4000), (1920, 1080), False, (810, 1080)),
        (MODE_FIT, (800, 600), (1920, 1080), False, (800, 600)),  # no enlarging
        (MODE_FIT, (800, 600), (1920, 1080), True, (1440, 1080)),
        (MODE_FILL, (4000, 3000), (1080, 1080), False, (1080, 1080)),
        (MODE_FILL, (500, 400), (1080, 1080), False, (400, 400)),  # crop only, keeps box ratio
        (MODE_EXACT, (4000, 3000), (100, 900), False, (100, 900)),
    ],
)
def test_target_size(mode, source, box, upscale, expected):
    settings = ResizeSettings(mode=mode, width=box[0], height=box[1], allow_upscale=upscale)
    assert target_size(source, settings) == expected


def test_target_size_percent():
    assert target_size((1000, 500), ResizeSettings(mode=MODE_PERCENT, percent=25)) == (250, 125)
    assert target_size((1000, 500), ResizeSettings(mode=MODE_PERCENT, percent=150)) == (1000, 500)
    assert target_size(
        (1000, 500), ResizeSettings(mode=MODE_PERCENT, percent=150, allow_upscale=True)
    ) == (1500, 750)


def test_target_size_never_zero():
    settings = ResizeSettings(mode=MODE_PERCENT, percent=1)
    assert target_size((10, 10), settings) == (1, 1)


# -------------------------------------------------------------- validation


@pytest.mark.parametrize(
    "kwargs",
    [
        {"width": 0},
        {"height": -5},
        {"width": 50000},
        {"mode": MODE_PERCENT, "percent": 0},
        {"quality": 0},
        {"output_format": "PSD"},
        {"mode": "Stretch"},
    ],
)
def test_invalid_settings_rejected(kwargs):
    with pytest.raises(ValueError):
        ResizeSettings(**kwargs).validate()


# ------------------------------------------------------------ resize_image


def test_resize_uses_full_resolution_original(tmp_path):
    """Regression: v1 resized the 500 px preview thumbnail instead of the original."""
    src = make_image(tmp_path / "big.jpg", size=(3000, 2000))
    result = resize_image(src, ResizeSettings(mode=MODE_FIT, width=1500, height=1500))
    assert result.new_size == (1500, 1000)
    with Image.open(result.destination) as img:
        assert img.size == (1500, 1000)
    assert result.destination.name == "big_resized.jpg"


def test_fill_crops_to_exact_box(tmp_path):
    src = make_image(tmp_path / "wide.png", size=(1600, 900))
    result = resize_image(src, ResizeSettings(mode=MODE_FILL, width=500, height=500))
    assert result.new_size == (500, 500)


def test_rgba_to_jpeg_flattens_on_white(tmp_path):
    src = make_image(tmp_path / "alpha.png", mode="RGBA")
    result = resize_image(src, ResizeSettings(mode=MODE_PERCENT, percent=50, output_format="JPEG"))
    with Image.open(result.destination) as img:
        assert img.format == "JPEG"
        assert img.mode == "RGB"
        r, g, b = img.getpixel((10, 10))
        assert r > 200 and g > 100  # blended with white, not black


def test_palette_gif_to_jpeg(tmp_path):
    """Regression: v1 crashed with 'cannot write mode P as JPEG'."""
    src = tmp_path / "anim.gif"
    Image.new("RGB", (300, 300), (0, 120, 255)).convert("P").save(src)
    result = resize_image(src, ResizeSettings(mode=MODE_FIT, width=100, height=100, output_format="JPEG"))
    assert result.destination.suffix == ".jpg"
    assert result.new_size == (100, 100)


def test_png_keeps_transparency(tmp_path):
    src = make_image(tmp_path / "alpha.png", mode="RGBA")
    result = resize_image(src, ResizeSettings(mode=MODE_PERCENT, percent=50))
    with Image.open(result.destination) as img:
        assert img.mode == "RGBA"
        assert img.getpixel((5, 5))[3] == 128


def test_webp_and_quality_affect_size(tmp_path):
    src = tmp_path / "noise.png"
    Image.effect_noise((800, 800), 64).convert("RGB").save(src)
    low = resize_image(src, ResizeSettings(mode=MODE_PERCENT, percent=100, output_format="WebP", quality=20,
                                           suffix="_low"))
    high = resize_image(src, ResizeSettings(mode=MODE_PERCENT, percent=100, output_format="WebP", quality=95,
                                            suffix="_high"))
    assert low.destination.suffix == ".webp"
    assert low.bytes_after < high.bytes_after


def test_exif_rotation_applied(tmp_path):
    src = tmp_path / "rotated.jpg"
    img = Image.new("RGB", (400, 200), "white")
    exif = img.getexif()
    exif[0x0112] = 6  # rotate 90° on display
    img.save(src, exif=exif.tobytes())

    assert read_info(src).size == (200, 400)
    result = resize_image(src, ResizeSettings(mode=MODE_PERCENT, percent=50, keep_metadata=True))
    assert result.new_size == (100, 200)
    with Image.open(result.destination) as out:
        assert out.getexif().get(0x0112, 1) == 1  # must not be rotated a second time


def test_metadata_stripped_by_default(tmp_path):
    src = tmp_path / "camera.jpg"
    img = Image.new("RGB", (200, 200), "white")
    exif = img.getexif()
    exif[0x010F] = "TestCam"  # Make
    img.save(src, exif=exif.tobytes())

    stripped = resize_image(src, ResizeSettings(mode=MODE_PERCENT, percent=50, suffix="_a"))
    kept = resize_image(src, ResizeSettings(mode=MODE_PERCENT, percent=50, suffix="_b", keep_metadata=True))
    with Image.open(stripped.destination) as a, Image.open(kept.destination) as b:
        assert 0x010F not in a.getexif()
        assert b.getexif()[0x010F] == "TestCam"


def test_custom_output_folder_is_created(tmp_path):
    src = make_image(tmp_path / "a.png")
    out_dir = tmp_path / "out" / "nested"
    result = resize_image(src, ResizeSettings(mode=MODE_PERCENT, percent=50, output_dir=out_dir, suffix=""))
    assert result.destination == out_dir / "a.png"


# ------------------------------------------------------------- output_path


def test_output_path_never_overwrites_without_permission(tmp_path):
    src = make_image(tmp_path / "photo.jpg")
    settings = ResizeSettings()
    (tmp_path / "photo_resized.jpg").write_bytes(b"x")
    assert output_path(src, settings).name == "photo_resized (2).jpg"

    settings.overwrite = True
    assert output_path(src, settings).name == "photo_resized.jpg"


def test_output_path_never_returns_source_without_overwrite(tmp_path):
    src = make_image(tmp_path / "photo.jpg")
    assert output_path(src, ResizeSettings(suffix="")) != src


def test_output_extension_follows_format(tmp_path):
    src = make_image(tmp_path / "photo.jpeg")
    assert output_path(src, ResizeSettings()).suffix == ".jpeg"
    assert output_path(src, ResizeSettings(output_format="PNG")).suffix == ".png"


# ------------------------------------------------------------------ helpers


def test_collect_images_filters_and_deduplicates(tmp_path):
    make_image(tmp_path / "a.jpg")
    make_image(tmp_path / "b.PNG")
    (tmp_path / "notes.txt").write_text("hi")
    sub = tmp_path / "sub"
    sub.mkdir()
    make_image(sub / "c.webp")

    found = collect_images([tmp_path, tmp_path / "a.jpg"])
    assert sorted(p.name for p in found) == ["a.jpg", "b.PNG", "c.webp"]


def test_render_preview_matches_fill_ratio(tmp_path):
    src = make_image(tmp_path / "wide.jpg", size=(2000, 1000))
    preview = render_preview(src, ResizeSettings(mode=MODE_FILL, width=1080, height=1920), (560, 300))
    assert preview.height == 300
    assert abs(preview.width / preview.height - 1080 / 1920) < 0.01


def test_human_size():
    assert human_size(500) == "500 B"
    assert human_size(2048) == "2.0 KB"
    assert human_size(5 * 1024 * 1024) == "5.0 MB"


def test_settings_roundtrip(tmp_path):
    original = ResizeSettings(mode=MODE_FILL, width=1080, height=1350, quality=70, output_dir=tmp_path / "out")
    settings_store.save(tmp_path, settings_store.Saved(original, "ig_portrait", "pl"))
    loaded = settings_store.load(tmp_path)
    assert loaded.settings == original
    assert loaded.preset == "ig_portrait"
    assert loaded.language == "pl"


def test_settings_load_survives_corrupt_file(tmp_path):
    (tmp_path / "settings.json").write_text("{not json", encoding="utf-8")
    assert settings_store.load(tmp_path) == settings_store.Saved()


def test_settings_from_v2_0_are_migrated(tmp_path):
    """2.0.0 stored English labels; they must still load after the switch to keys."""
    (tmp_path / "settings.json").write_text(
        '{"settings": {"mode": "Fill and crop", "width": 500, "height": 500, '
        '"output_format": "Same as original"}, "preset": "Avatar (400 × 400)"}',
        encoding="utf-8",
    )
    loaded = settings_store.load(tmp_path)
    assert loaded.settings.mode == MODE_FILL
    assert loaded.settings.output_format == "original"
    assert loaded.settings.width == 500


# ------------------------------------------------------- file size limit


def noisy_image(path: Path, size=(1600, 1200)) -> Path:
    """Random noise compresses badly, so it reliably exceeds small limits."""
    Image.effect_noise(size, 80).convert("RGB").save(path, quality=95)
    return path


@pytest.mark.parametrize("fmt", ["JPEG", "WebP"])
def test_size_limit_lowers_quality_first(tmp_path, fmt):
    src = noisy_image(tmp_path / "noise.jpg", size=(800, 600))
    unlimited = resize_image(src, ResizeSettings(mode=MODE_PERCENT, percent=100, output_format=fmt, quality=95,
                                                 suffix="_a"))
    limit_mb = unlimited.bytes_after * 0.6 / 1_000_000
    limited = resize_image(src, ResizeSettings(mode=MODE_PERCENT, percent=100, output_format=fmt, quality=95,
                                               limit_file_size=True, max_file_mb=limit_mb, suffix="_b"))
    assert limited.limit_met
    assert limited.bytes_after <= limit_mb * 1_000_000
    assert limited.destination.stat().st_size == limited.bytes_after
    assert limited.quality_used < 95
    assert limited.new_size == (800, 600)  # quality alone was enough


def test_size_limit_reduces_resolution_when_quality_is_not_enough(tmp_path):
    src = noisy_image(tmp_path / "noise.jpg")
    result = resize_image(src, ResizeSettings(mode=MODE_PERCENT, percent=100, output_format="JPEG",
                                              limit_file_size=True, max_file_mb=0.05))
    assert result.limit_met
    assert result.bytes_after <= 50_000
    assert result.new_size[0] < 1600
    assert abs(result.new_size[0] / result.new_size[1] - 4 / 3) < 0.01  # proportions kept


def test_size_limit_for_lossless_png_shrinks_resolution(tmp_path):
    src = noisy_image(tmp_path / "noise.jpg", size=(1000, 1000))
    result = resize_image(src, ResizeSettings(mode=MODE_PERCENT, percent=100, output_format="PNG",
                                              limit_file_size=True, max_file_mb=0.3))
    assert result.limit_met
    assert result.bytes_after <= 300_000
    assert result.quality_used is None


def test_size_limit_not_applied_when_off(tmp_path):
    src = noisy_image(tmp_path / "noise.jpg", size=(400, 300))
    result = resize_image(src, ResizeSettings(mode=MODE_PERCENT, percent=100, output_format="JPEG", quality=90))
    assert result.limit_met is None
    assert result.quality_used == 90


def test_impossible_limit_reports_failure(tmp_path):
    src = noisy_image(tmp_path / "noise.jpg", size=(800, 600))
    result = resize_image(src, ResizeSettings(mode=MODE_PERCENT, percent=100, output_format="BMP",
                                              limit_file_size=True, max_file_mb=0.01))
    assert result.limit_met is False
    assert result.destination.exists()


def test_invalid_limit_rejected():
    with pytest.raises(ValueError):
        ResizeSettings(limit_file_size=True, max_file_mb=0).validate()
    ResizeSettings(limit_file_size=False, max_file_mb=0).validate()  # ignored when off


# ------------------------------------------------------------------- GPS


def photo_with_gps(path: Path) -> Path:
    img = Image.new("RGB", (300, 200), "white")
    exif = img.getexif()
    exif[0x010F] = "TestCam"
    gps = exif.get_ifd(0x8825)
    gps[1] = "N"
    gps[2] = (52.0, 13.0, 0.0)
    img.save(path, exif=exif.tobytes())
    with Image.open(path) as check:
        assert 0x8825 in check.getexif()
    return path


def test_gps_removed_when_metadata_is_kept(tmp_path):
    src = photo_with_gps(tmp_path / "gps.jpg")
    result = resize_image(src, ResizeSettings(mode=MODE_PERCENT, percent=50, keep_metadata=True))
    assert result.gps_removed
    with Image.open(result.destination) as out:
        exif = out.getexif()
        assert exif[0x010F] == "TestCam"  # other metadata stays
        assert 0x8825 not in exif
        assert not exif.get_ifd(0x8825)


def test_gps_kept_only_when_explicitly_allowed(tmp_path):
    src = photo_with_gps(tmp_path / "gps.jpg")
    result = resize_image(src, ResizeSettings(mode=MODE_PERCENT, percent=50, keep_metadata=True, strip_gps=False))
    assert not result.gps_removed
    with Image.open(result.destination) as out:
        assert out.getexif().get_ifd(0x8825)[1] == "N"


def test_gps_removed_with_all_metadata_by_default(tmp_path):
    src = photo_with_gps(tmp_path / "gps.jpg")
    result = resize_image(src, ResizeSettings(mode=MODE_PERCENT, percent=50))
    assert result.gps_removed
    with Image.open(result.destination) as out:
        assert 0x8825 not in out.getexif()


def test_gps_not_reported_for_photos_without_it(tmp_path):
    src = make_image(tmp_path / "plain.jpg")
    assert not resize_image(src, ResizeSettings(mode=MODE_PERCENT, percent=50)).gps_removed
