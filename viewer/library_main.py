"""GuidWire Library Viewer — entry point.

This script is used as the PyInstaller target when building the offline
library viewer executable.  The content folder
(``{CompanyName}_Content/``) must be placed next to the produced EXE;
its name is read from ``viewer_config.json`` in the same directory.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running from source (not just as a frozen bundle)
sys.path.insert(0, str(Path(__file__).parent.parent))

import customtkinter as ctk


def _read_content_folder_name() -> str:
    """Read the content folder name from ``viewer_config.json``."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        cfg_path = Path(sys._MEIPASS) / "assets" / "viewer_config.json"
    else:
        cfg_path = Path(__file__).parent / "assets" / "viewer_config.json"

    if cfg_path.exists():
        try:
            with cfg_path.open(encoding="utf-8") as fh:
                return json.load(fh).get("content_folder", "GuidWire_Content")
        except Exception:  # noqa: BLE001
            pass
    return "GuidWire_Content"


def main() -> None:
    content_folder_name = _read_content_folder_name()

    if getattr(sys, "frozen", False):
        content_dir = Path(sys.executable).parent / content_folder_name
    else:
        content_dir = Path(__file__).parent.parent / content_folder_name

    try:
        from viewer.library_engine import LibraryEngine
        from viewer.ui.library_viewer_ui import LibraryViewerUI
    except ImportError as exc:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        root = ctk.CTk()
        root.title("GuidWire Library Viewer — Error")
        root.geometry("520x200")
        ctk.CTkLabel(
            root,
            text=f"Missing dependency — cannot start GuidWire Library Viewer:\n{exc}",
            wraplength=480,
            text_color="#F44336",
            font=ctk.CTkFont(size=13),
        ).pack(expand=True, padx=20, pady=20)
        root.mainloop()
        return

    try:
        engine = LibraryEngine(content_dir)
    except FileNotFoundError as exc:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        root = ctk.CTk()
        root.title("GuidWire Library Viewer — Error")
        root.geometry("600x220")
        ctk.CTkLabel(
            root,
            text=(
                f"Content folder not found.\n\n"
                f"Expected: {content_dir}\n\n"
                f"Place the '{content_folder_name}' folder next to this executable."
            ),
            wraplength=560,
            text_color="#F44336",
            font=ctk.CTkFont(size=13),
        ).pack(expand=True, padx=20, pady=20)
        root.mainloop()
        return

    app = LibraryViewerUI(engine)
    app.mainloop()


if __name__ == "__main__":
    main()
