import pytest

from ImageResizer import i18n
from ImageResizer.core import MODES, ResizeSettings, human_size
from ImageResizer.presets import PRESET_KEYS, preset_label


@pytest.fixture(autouse=True)
def restore_language():
    yield
    i18n.set_language(i18n.DEFAULT_LANGUAGE)


def test_every_string_has_every_language():
    for key, entry in i18n.STRINGS.items():
        assert set(entry) == set(i18n.LANGUAGES), key
    for key, entry in i18n.PLURALS.items():
        assert set(entry) == set(i18n.LANGUAGES), key


def test_every_mode_and_preset_has_a_label():
    for code in i18n.LANGUAGES:
        i18n.set_language(code)
        for mode in MODES:
            assert i18n.tr(f"mode.{mode}") and i18n.tr(f"mode.{mode}.help")
        for key in PRESET_KEYS:
            assert preset_label(key)


@pytest.mark.parametrize(
    "n, expected",
    [(1, "1 obraz"), (2, "2 obrazy"), (4, "4 obrazy"), (5, "5 obrazów"), (12, "12 obrazów"),
     (14, "14 obrazów"), (22, "22 obrazy"), (25, "25 obrazów"), (0, "0 obrazów")],
)
def test_polish_plurals(n, expected):
    i18n.set_language("pl")
    assert i18n.plural("images", n) == expected


def test_english_plurals():
    assert i18n.plural("images", 1) == "1 image"
    assert i18n.plural("images", 3) == "3 images"


def test_polish_decimal_comma():
    i18n.set_language("pl")
    assert human_size(2048) == "2,0 KB"


def test_validation_messages_are_translated():
    i18n.set_language("pl")
    with pytest.raises(ValueError, match="Szerokość musi"):
        ResizeSettings(width=0).validate()


def test_unknown_language_falls_back_to_english():
    i18n.set_language("xx")
    assert i18n.current_language() == "en"
    assert i18n.tr("btn.remove") == "Remove"


def test_preset_labels_include_size():
    i18n.set_language("pl")
    assert preset_label("ig_story") == "Instagram – relacja (1080 × 1920)"
    assert preset_label("web") == "Strona WWW / blog (1200 px)"


@pytest.mark.parametrize("n, expected", [(1, "z 1 zdjęcia"), (3, "z 3 zdjęć"), (5, "z 5 zdjęć")])
def test_polish_genitive_after_z(n, expected):
    i18n.set_language("pl")
    assert i18n.tr("summary.gps", count=i18n.plural("photos_from", n)) == f"Usunięto lokalizację GPS {expected}."


def test_academic_presets_come_first():
    from ImageResizer.presets import PRESET_KEYS
    assert PRESET_KEYS[1:4] == ["slide_169", "slide_43", "thesis"]
