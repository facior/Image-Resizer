"""Drag and drop of files from Explorer.

Toga has no cross-platform file-drop API yet, so on Windows this hooks the
native WinForms controls directly. On other platforms it is a no-op.
"""

from __future__ import annotations

import sys
from collections.abc import Callable


def enable_file_drop(window, on_files: Callable[[list[str]], None]) -> Callable[[object], None] | None:
    """Hook the whole window. Returns a function that hooks a newly created
    widget tree (call it after replacing the window content), or None when
    drag and drop is not available."""
    if sys.platform != "win32":
        return None
    try:
        from System.Windows.Forms import DataFormats, DragDropEffects

        form = window._impl.native
    except Exception:
        return None

    def drag_enter(sender, event):
        if event.Data.GetDataPresent(DataFormats.FileDrop):
            event.Effect = DragDropEffects.Copy

    def drag_drop(sender, event):
        files = event.Data.GetData(DataFormats.FileDrop)
        if files:
            on_files([str(f) for f in files])

    def hook(control):
        control.AllowDrop = True
        control.DragEnter += drag_enter
        control.DragDrop += drag_drop
        for child in control.Controls:
            hook(child)

    def hook_widget(widget) -> None:
        try:
            hook(widget._impl.native)
        except Exception:
            pass

    try:
        hook(form)
    except Exception:
        return None
    return hook_widget
