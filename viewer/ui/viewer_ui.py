"""GuidWire Viewer — CustomTkinter GUI."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import customtkinter as ctk
from PIL import Image


# ---------------------------------------------------------------------------
# Attempt to import TreeEngine; provide a fallback for development runs that
# lack the assets directory.
# ---------------------------------------------------------------------------
try:
    from viewer.tree_engine import TreeEngine
except Exception:
    TreeEngine = None  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Appearance defaults
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
        # Constrain height to 60px while preserving aspect ratio
        w, h = img.size
        if h > 60:
            ratio = 60 / h
            img = img.resize((int(w * ratio), 60), Image.LANCZOS)
        return ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Main Viewer UI
# ---------------------------------------------------------------------------


class ViewerUI(ctk.CTk):
    """Main window for the GuidWire Viewer application."""

    def __init__(self, engine: "TreeEngine") -> None:
        super().__init__()

        self._engine = engine
        self._dark_mode = True

        self.title(f"{engine.company_name} — GuidWire")
        self.geometry("800x600")
        self.resizable(True, True)

        self._build_layout()
        self._refresh()

    # ------------------------------------------------------------------
    # Layout construction
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ---- HEADER ----
        header = ctk.CTkFrame(self, height=80, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        header.grid_propagate(False)

        logo_img = _load_logo()
        if logo_img:
            logo_lbl = ctk.CTkLabel(header, image=logo_img, text="")
            logo_lbl.grid(row=0, column=0, padx=16, pady=10)

        self._company_label = ctk.CTkLabel(
            header,
            text=self._engine.company_name,
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self._company_label.grid(row=0, column=1, padx=10, sticky="w")

        self._theme_btn = ctk.CTkButton(
            header, text="☀ Light Mode", width=120, command=self._toggle_theme
        )
        self._theme_btn.grid(row=0, column=2, padx=16, pady=10)

        # ---- BREADCRUMB BAR ----
        breadcrumb_outer = ctk.CTkFrame(self, height=36, corner_radius=0,
                                        fg_color=("gray85", "gray20"))
        breadcrumb_outer.grid(row=1, column=0, sticky="ew")
        breadcrumb_outer.grid_columnconfigure(0, weight=1)
        breadcrumb_outer.grid_propagate(False)

        self._breadcrumb_scroll = ctk.CTkScrollableFrame(
            breadcrumb_outer, height=30, orientation="horizontal",
            fg_color="transparent",
        )
        self._breadcrumb_scroll.grid(row=0, column=0, sticky="ew", padx=4)

        # ---- MAIN CARD AREA ----
        card_outer = ctk.CTkFrame(self, fg_color="transparent")
        card_outer.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        card_outer.grid_columnconfigure(0, weight=1)
        card_outer.grid_rowconfigure(0, weight=1)

        self._main_card = ctk.CTkFrame(card_outer, corner_radius=16)
        self._main_card.grid(row=0, column=0, sticky="nsew")
        self._main_card.grid_columnconfigure(0, weight=1)
        self._main_card.grid_rowconfigure(1, weight=1)

        # Node type badge
        self._type_badge = ctk.CTkLabel(
            self._main_card, text="QUESTION", width=100, corner_radius=8,
            font=ctk.CTkFont(size=11, weight="bold"), fg_color="#2196F3",
            text_color="white",
        )
        self._type_badge.grid(row=0, column=0, padx=20, pady=(16, 4), sticky="w")

        # Node text
        self._node_text = ctk.CTkLabel(
            self._main_card, text="",
            font=ctk.CTkFont(size=16),
            wraplength=650, justify="left", anchor="nw",
        )
        self._node_text.grid(row=1, column=0, padx=20, pady=(8, 16), sticky="nsew")

        # ---- NAVIGATION AREA ----
        self._nav_frame = ctk.CTkScrollableFrame(self, height=180, fg_color="transparent")
        self._nav_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 5))
        self._nav_frame.grid_columnconfigure(0, weight=1)

        # ---- FOOTER ----
        footer = ctk.CTkFrame(self, height=50, corner_radius=0)
        footer.grid(row=4, column=0, sticky="ew")
        footer.grid_columnconfigure(1, weight=1)
        footer.grid_propagate(False)

        self._back_btn = ctk.CTkButton(footer, text="← Back", width=90,
                                       fg_color="gray40", command=self._go_back)
        self._back_btn.grid(row=0, column=0, padx=12, pady=8)

        self._step_counter = ctk.CTkLabel(footer, text="Step 1 of ~1",
                                          text_color="gray60")
        self._step_counter.grid(row=0, column=1, pady=8)

        ctk.CTkButton(footer, text="Reset", width=90,
                      fg_color="gray40", command=self._reset).grid(
            row=0, column=2, padx=12, pady=8)

    # ------------------------------------------------------------------
    # Refresh UI to match current engine state
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        node = self._engine.get_current_node()
        node_type: str = node.get("type", "question")
        node_text: str = node.get("text", "")

        # Update badge
        badge_colors = {
            "question": "#2196F3",
            "step": "#FF9800",
            "resolution": "#4CAF50",
        }
        self._type_badge.configure(
            text=node_type.upper(),
            fg_color=badge_colors.get(node_type, "gray50"),
        )

        # Update node text
        self._node_text.configure(text=node_text)

        # Update breadcrumb
        self._update_breadcrumb()

        # Update navigation area
        self._update_nav(node)

        # Update step counter
        self._step_counter.configure(
            text=f"Step {self._engine.current_step_number()} "
                 f"of ~{self._engine.approximate_total_steps()}"
        )

        # Back button enabled only if there is history
        self._back_btn.configure(
            state="normal" if self._engine.get_history() else "disabled"
        )

    def _update_breadcrumb(self) -> None:
        for w in self._breadcrumb_scroll.winfo_children():
            w.destroy()

        history = self._engine.get_history()
        for i, text in enumerate(history):
            short = text[:30] + ("…" if len(text) > 30 else "")
            ctk.CTkLabel(
                self._breadcrumb_scroll,
                text=short,
                font=ctk.CTkFont(size=10),
                text_color="gray60",
            ).pack(side="left", padx=2)
            if i < len(history) - 1:
                ctk.CTkLabel(self._breadcrumb_scroll, text="›",
                             text_color="gray50",
                             font=ctk.CTkFont(size=10)).pack(side="left")

    def _update_nav(self, node: dict[str, Any]) -> None:
        for w in self._nav_frame.winfo_children():
            w.destroy()

        node_type = node.get("type", "question")

        if node_type == "question":
            for option in node.get("options", []):
                label = option["label"]
                btn = ctk.CTkButton(
                    self._nav_frame,
                    text=label,
                    anchor="w",
                    height=40,
                    command=lambda lbl=label: self._choose_option(lbl),
                )
                btn.pack(fill="x", pady=3)

        elif node_type == "step":
            ctk.CTkButton(
                self._nav_frame,
                text="Next Step →",
                height=44,
                font=ctk.CTkFont(size=14, weight="bold"),
                command=self._advance,
            ).pack(fill="x", pady=6)

        elif node_type == "resolution":
            banner = ctk.CTkFrame(self._nav_frame, fg_color="#1B5E20", corner_radius=10)
            banner.pack(fill="x", pady=4)
            ctk.CTkLabel(
                banner,
                text="✓  Resolution",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#A5D6A7",
            ).pack(anchor="w", padx=16, pady=(10, 2))
            ctk.CTkLabel(
                banner,
                text=node.get("text", ""),
                font=ctk.CTkFont(size=12),
                text_color="#C8E6C9",
                wraplength=660,
                justify="left",
                anchor="w",
            ).pack(anchor="w", padx=16, pady=(0, 10))

            ctk.CTkButton(
                self._nav_frame,
                text="Start Over",
                fg_color="#4CAF50",
                hover_color="#388E3C",
                command=self._reset,
            ).pack(pady=6)

    # ------------------------------------------------------------------
    # Navigation actions
    # ------------------------------------------------------------------

    def _choose_option(self, label: str) -> None:
        self._engine.navigate(label)
        self._refresh()

    def _advance(self) -> None:
        self._engine.advance()
        self._refresh()

    def _go_back(self) -> None:
        self._engine.go_back()
        self._refresh()

    def _reset(self) -> None:
        self._engine.reset()
        self._refresh()

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
