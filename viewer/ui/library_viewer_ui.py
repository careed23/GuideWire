"""GuidWire Library Viewer — CustomTkinter GUI.

Provides:
  - Category sidebar for browsing ~60 categories
  - Search bar (title / description / symptoms — metadata only)
  - Tree list panel showing matching entries
  - Embedded tree navigator (reuses ViewerUI logic) for the selected entry
  - "Open Source Document" button on every tree navigation card
"""

from __future__ import annotations

import threading
from pathlib import Path
from tkinter import messagebox
from typing import Any

import customtkinter as ctk
from PIL import Image

# ---------------------------------------------------------------------------
# Appearance defaults (match builder / single-doc viewer)
# ---------------------------------------------------------------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

_ASSETS_DIR = Path(__file__).parent.parent / "assets"


def _load_logo() -> ctk.CTkImage | None:
    logo_path = _ASSETS_DIR / "logo.png"
    if not logo_path.exists():
        return None
    try:
        img = Image.open(str(logo_path)).convert("RGBA")
        w, h = img.size
        if h > 60:
            ratio = 60 / h
            img = img.resize((int(w * ratio), 60), Image.LANCZOS)
        return ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# Library Viewer main window
# ---------------------------------------------------------------------------


class LibraryViewerUI(ctk.CTk):
    """Main window for the GuidWire offline library viewer."""

    def __init__(self, engine: "LibraryEngine") -> None:  # type: ignore[name-defined]  # noqa: F821
        super().__init__()

        self._engine = engine
        self._dark_mode = True
        self._active_category: str | None = None
        self._active_entry: dict[str, Any] | None = None

        # Tree navigation state (None when no tree is open)
        self._tree_engine: Any = None

        self.title("GuidWire Library Viewer")
        self.geometry("1100x720")
        self.resizable(True, True)

        self._build_layout()
        self._populate_categories()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=0)   # category sidebar
        self.grid_columnconfigure(1, weight=1)   # list + detail
        self.grid_rowconfigure(0, weight=0)      # header
        self.grid_rowconfigure(1, weight=1)      # body

        # ---- HEADER ----
        header = ctk.CTkFrame(self, height=70, corner_radius=0)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_columnconfigure(2, weight=1)
        header.grid_propagate(False)

        logo_img = _load_logo()
        if logo_img:
            ctk.CTkLabel(header, image=logo_img, text="").grid(
                row=0, column=0, padx=14, pady=8
            )

        ctk.CTkLabel(
            header,
            text="GuidWire Library",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=1, padx=8, sticky="w")

        # Search bar
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", self._on_search_change)
        search_entry = ctk.CTkEntry(
            header,
            textvariable=self._search_var,
            placeholder_text="Search by title / description / symptoms…",
            width=340,
        )
        search_entry.grid(row=0, column=2, padx=20, pady=14, sticky="w")

        ctk.CTkLabel(
            header,
            text=f"{len(self._engine.entries)} trees",
            text_color="gray50",
            font=ctk.CTkFont(size=11),
        ).grid(row=0, column=3, padx=8)

        self._theme_btn = ctk.CTkButton(
            header, text="☀ Light Mode", width=120, command=self._toggle_theme
        )
        self._theme_btn.grid(row=0, column=4, padx=14, pady=14)

        # ---- CATEGORY SIDEBAR ----
        self._cat_sidebar = ctk.CTkScrollableFrame(self, width=200, corner_radius=0)
        self._cat_sidebar.grid(row=1, column=0, sticky="nsew")

        ctk.CTkLabel(
            self._cat_sidebar,
            text="Categories",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(12, 6))

        self._cat_buttons: dict[str, ctk.CTkButton] = {}

        # ---- BODY: entry list + tree panel side by side ----
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=1, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        # Entry list
        self._entry_list_frame = ctk.CTkScrollableFrame(body, width=300)
        self._entry_list_frame.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        self._entry_list_frame.grid_columnconfigure(0, weight=1)

        self._entry_count_label = ctk.CTkLabel(
            self._entry_list_frame,
            text="Select a category or search.",
            text_color="gray60",
            anchor="w",
        )
        self._entry_count_label.pack(fill="x", padx=8, pady=(0, 6))

        # Tree navigation panel
        self._tree_panel = ctk.CTkFrame(body, corner_radius=12)
        self._tree_panel.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        self._tree_panel.grid_columnconfigure(0, weight=1)
        self._tree_panel.grid_rowconfigure(1, weight=1)

        self._tree_placeholder = ctk.CTkLabel(
            self._tree_panel,
            text="Select a tree from the list to begin.",
            text_color="gray50",
            font=ctk.CTkFont(size=14),
        )
        self._tree_placeholder.grid(row=0, column=0, padx=20, pady=40)

    # ------------------------------------------------------------------
    # Category sidebar
    # ------------------------------------------------------------------

    def _populate_categories(self) -> None:
        categories = self._engine.get_categories()
        for cat in categories:
            count = len(self._engine.get_entries_for_category(cat))
            btn = ctk.CTkButton(
                self._cat_sidebar,
                text=f"{cat}  ({count})",
                anchor="w",
                fg_color="transparent",
                hover_color=("gray80", "gray25"),
                text_color=("gray10", "gray90"),
                font=ctk.CTkFont(size=12),
                command=lambda c=cat: self._select_category(c),
            )
            btn.pack(fill="x", padx=6, pady=2)
            self._cat_buttons[cat] = btn

    def _select_category(self, category: str) -> None:
        # Highlight selected
        for c, btn in self._cat_buttons.items():
            btn.configure(fg_color="#1565C0" if c == category else "transparent")

        self._active_category = category
        self._search_var.set("")  # clear search when browsing by category
        entries = self._engine.get_entries_for_category(category)
        self._show_entry_list(entries)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _on_search_change(self, *_: Any) -> None:
        query = self._search_var.get().strip()
        if not query:
            # Revert to active category view
            if self._active_category:
                self._show_entry_list(
                    self._engine.get_entries_for_category(self._active_category)
                )
            else:
                self._clear_entry_list()
            return

        # Deselect category buttons while searching
        for btn in self._cat_buttons.values():
            btn.configure(fg_color="transparent")

        results = self._engine.search(query)
        self._show_entry_list(results)

    # ------------------------------------------------------------------
    # Entry list
    # ------------------------------------------------------------------

    def _clear_entry_list(self) -> None:
        for w in self._entry_list_frame.winfo_children():
            if w is not self._entry_count_label:
                w.destroy()
        self._entry_count_label.configure(text="Select a category or search.")

    def _show_entry_list(self, entries: list[dict[str, Any]]) -> None:
        for w in self._entry_list_frame.winfo_children():
            if w is not self._entry_count_label:
                w.destroy()

        self._entry_count_label.configure(
            text=f"{len(entries)} tree{'s' if len(entries) != 1 else ''} found"
        )

        for entry in entries:
            row = ctk.CTkFrame(self._entry_list_frame, corner_radius=8)
            row.pack(fill="x", padx=4, pady=3)
            row.grid_columnconfigure(0, weight=1)

            title = entry.get("title", entry.get("source_doc", "Untitled"))
            desc = entry.get("description", "")

            ctk.CTkLabel(
                row,
                text=title[:60] + ("…" if len(title) > 60 else ""),
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w",
                wraplength=240,
                justify="left",
            ).pack(fill="x", padx=10, pady=(8, 2))

            if desc:
                ctk.CTkLabel(
                    row,
                    text=desc[:80] + ("…" if len(desc) > 80 else ""),
                    font=ctk.CTkFont(size=10),
                    text_color="gray60",
                    anchor="w",
                    wraplength=240,
                    justify="left",
                ).pack(fill="x", padx=10, pady=(0, 2))

            ctk.CTkLabel(
                row,
                text=entry.get("category", ""),
                font=ctk.CTkFont(size=10),
                text_color="#64B5F6",
                anchor="w",
            ).pack(fill="x", padx=10, pady=(0, 6))

            entry_ref = entry
            row.bind("<Button-1>", lambda e, ref=entry_ref: self._open_tree(ref))
            for child in row.winfo_children():
                child.bind("<Button-1>", lambda e, ref=entry_ref: self._open_tree(ref))

    # ------------------------------------------------------------------
    # Tree panel
    # ------------------------------------------------------------------

    def _open_tree(self, entry: dict[str, Any]) -> None:
        self._active_entry = entry
        try:
            tree_dict = self._engine.load_tree(entry)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Load Error", str(exc))
            return

        from viewer.tree_engine import TreeEngine  # local import

        self._tree_engine = TreeEngine(tree_dict=tree_dict, company_name="GuidWire")
        self._refresh_tree_panel()

    def _refresh_tree_panel(self) -> None:
        # Clear the panel
        for w in self._tree_panel.winfo_children():
            w.destroy()

        if self._tree_engine is None or self._active_entry is None:
            self._tree_placeholder = ctk.CTkLabel(
                self._tree_panel,
                text="Select a tree from the list to begin.",
                text_color="gray50",
                font=ctk.CTkFont(size=14),
            )
            self._tree_placeholder.grid(row=0, column=0, padx=20, pady=40)
            return

        engine = self._tree_engine
        entry = self._active_entry
        node = engine.get_current_node()
        node_type = node.get("type", "question")

        # ---- Title bar ----
        title_bar = ctk.CTkFrame(self._tree_panel, fg_color="transparent")
        title_bar.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 4))
        title_bar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            title_bar,
            text=entry.get("title", "Tree"),
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        # "Open Source Document" button
        ctk.CTkButton(
            title_bar,
            text="📄 Open Source Doc",
            width=160,
            fg_color="#37474F",
            hover_color="#546E7A",
            command=self._open_source_doc,
        ).grid(row=0, column=1, padx=(8, 0))

        # ---- Node type badge + text ----
        badge_colors = {
            "question": "#2196F3",
            "step": "#FF9800",
            "resolution": "#4CAF50",
        }
        card = ctk.CTkFrame(self._tree_panel, corner_radius=12)
        card.grid(row=1, column=0, sticky="nsew", padx=14, pady=6)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)
        self._tree_panel.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            card,
            text=node_type.upper(),
            width=100,
            corner_radius=8,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=badge_colors.get(node_type, "gray50"),
            text_color="white",
        ).grid(row=0, column=0, padx=16, pady=(12, 4), sticky="w")

        ctk.CTkLabel(
            card,
            text=node.get("text", ""),
            font=ctk.CTkFont(size=14),
            wraplength=520,
            justify="left",
            anchor="nw",
        ).grid(row=1, column=0, padx=16, pady=(4, 12), sticky="nsew")

        # ---- Navigation options ----
        nav_frame = ctk.CTkScrollableFrame(
            self._tree_panel, height=160, fg_color="transparent"
        )
        nav_frame.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 6))
        nav_frame.grid_columnconfigure(0, weight=1)

        self._build_nav_buttons(nav_frame, node, node_type)

        # ---- Footer (breadcrumb + back/reset) ----
        footer = ctk.CTkFrame(self._tree_panel, height=44, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 10))
        footer.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            footer,
            text="← Back",
            width=80,
            fg_color="gray40",
            command=self._tree_go_back,
        ).grid(row=0, column=0, padx=(0, 6))

        history = engine.get_history()
        step_text = (
            f"Step {engine.current_step_number()} "
            f"of ~{engine.approximate_total_steps()}"
        )
        ctk.CTkLabel(
            footer, text=step_text, text_color="gray60", font=ctk.CTkFont(size=11)
        ).grid(row=0, column=1)

        ctk.CTkButton(
            footer,
            text="Reset",
            width=80,
            fg_color="gray40",
            command=self._tree_reset,
        ).grid(row=0, column=2, padx=(6, 0))

    def _build_nav_buttons(
        self, nav_frame: ctk.CTkScrollableFrame, node: dict[str, Any], node_type: str
    ) -> None:
        if node_type == "question":
            for option in node.get("options", []):
                label = option["label"]
                ctk.CTkButton(
                    nav_frame,
                    text=label,
                    anchor="w",
                    height=38,
                    command=lambda lbl=label: self._tree_choose(lbl),
                ).pack(fill="x", pady=2)

        elif node_type == "step":
            ctk.CTkButton(
                nav_frame,
                text="Next Step →",
                height=42,
                font=ctk.CTkFont(size=13, weight="bold"),
                command=self._tree_advance,
            ).pack(fill="x", pady=4)

        elif node_type == "resolution":
            banner = ctk.CTkFrame(nav_frame, fg_color="#1B5E20", corner_radius=10)
            banner.pack(fill="x", pady=4)
            ctk.CTkLabel(
                banner,
                text="✓  Resolution",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#A5D6A7",
            ).pack(anchor="w", padx=14, pady=(8, 2))
            ctk.CTkLabel(
                banner,
                text=node.get("text", ""),
                font=ctk.CTkFont(size=11),
                text_color="#C8E6C9",
                wraplength=480,
                justify="left",
                anchor="w",
            ).pack(anchor="w", padx=14, pady=(0, 8))
            ctk.CTkButton(
                nav_frame,
                text="Start Over",
                fg_color="#4CAF50",
                hover_color="#388E3C",
                command=self._tree_reset,
            ).pack(pady=4)

    # ------------------------------------------------------------------
    # Tree navigation actions
    # ------------------------------------------------------------------

    def _tree_choose(self, label: str) -> None:
        if self._tree_engine:
            self._tree_engine.navigate(label)
            self._refresh_tree_panel()

    def _tree_advance(self) -> None:
        if self._tree_engine:
            self._tree_engine.advance()
            self._refresh_tree_panel()

    def _tree_go_back(self) -> None:
        if self._tree_engine:
            self._tree_engine.go_back()
            self._refresh_tree_panel()

    def _tree_reset(self) -> None:
        if self._tree_engine:
            self._tree_engine.reset()
            self._refresh_tree_panel()

    # ------------------------------------------------------------------
    # Source document
    # ------------------------------------------------------------------

    def _open_source_doc(self) -> None:
        if not self._active_entry:
            return
        try:
            self._engine.open_source_doc(self._active_entry)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Cannot Open Document", str(exc))

    # ------------------------------------------------------------------
    # Theme toggle
    # ------------------------------------------------------------------

    def _toggle_theme(self) -> None:
        if self._dark_mode:
            ctk.set_appearance_mode("light")
            self._theme_btn.configure(text="🌙 Dark Mode")
            self._dark_mode = False
        else:
            ctk.set_appearance_mode("dark")
            self._theme_btn.configure(text="☀ Light Mode")
            self._dark_mode = True
