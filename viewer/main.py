"""GuidWire Viewer — entry point."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running as a standalone script or packaged exe
sys.path.insert(0, str(Path(__file__).parent.parent))

import customtkinter as ctk


def main() -> None:
    try:
        from viewer.tree_engine import TreeEngine
        from viewer.ui.viewer_ui import ViewerUI
    except Exception as exc:
        # Fallback: show a simple error window
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        root = ctk.CTk()
        root.title("GuidWire Viewer — Error")
        root.geometry("500x200")
        ctk.CTkLabel(
            root,
            text=f"Failed to load GuidWire data:\n{exc}",
            wraplength=460,
            text_color="#F44336",
            font=ctk.CTkFont(size=13),
        ).pack(expand=True, padx=20, pady=20)
        root.mainloop()
        return

    engine = TreeEngine()
    app = ViewerUI(engine)
    app.mainloop()


if __name__ == "__main__":
    main()
