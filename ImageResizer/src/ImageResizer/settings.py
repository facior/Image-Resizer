"""Remembers the user's last settings between sessions."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from ImageResizer.core import ResizeSettings

FILE_NAME = "settings.json"

# Settings files written by 2.0.0 stored English labels instead of keys.
_LEGACY_VALUES = {
    "mode": {"Fit within": "fit", "Fill and crop": "fill", "Exact size": "exact", "Percentage": "percent"},
    "output_format": {"Same as original": "original"},
}


@dataclass
class Saved:
    settings: ResizeSettings = field(default_factory=ResizeSettings)
    preset: str = ""
    language: str = ""  # empty means "follow the system language"


def load(config_dir: Path) -> Saved:
    """Read saved settings. Falls back to defaults on any problem."""
    try:
        data = json.loads((config_dir / FILE_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Saved()
    if not isinstance(data, dict):
        return Saved()
    language = data.get("language") if isinstance(data.get("language"), str) else ""
    try:
        known = {f.name for f in fields(ResizeSettings)}
        values = {k: v for k, v in data.get("settings", {}).items() if k in known}
        for name, mapping in _LEGACY_VALUES.items():
            if values.get(name) in mapping:
                values[name] = mapping[values[name]]
        if values.get("output_dir"):
            values["output_dir"] = Path(values["output_dir"])
        settings = ResizeSettings(**values)
        settings.validate()
    except (AttributeError, ValueError, TypeError):
        return Saved(language=language)
    preset = data.get("preset") if isinstance(data.get("preset"), str) else ""
    return Saved(settings, preset, language)


def save(config_dir: Path, saved: Saved) -> None:
    data = asdict(saved.settings)
    data["output_dir"] = str(saved.settings.output_dir) if saved.settings.output_dir else None
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / FILE_NAME).write_text(
            json.dumps({"settings": data, "preset": saved.preset, "language": saved.language}, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass  # Losing remembered settings is not worth interrupting the user.
