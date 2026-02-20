"""GuidWire Builder — CustomTkinter GUI."""

from __future__ import annotations

import json
import tempfile
import threading
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import customtkinter as ctk
from PIL import Image, ImageTk

from builder.analyzer import DocumentAnalyzer
from builder.bulk_ingestor import BulkIngestor
from builder.ingestor import DocumentIngestor
from builder.library_builder import LibraryBuilder
from builder.packager import Packager
from builder.tree_builder import TreeBuilder

_LOGO_THUMB_SIZE: tuple[int, int] = (80, 80)


# ---------------------------------------------------------------------------
# Appearance defaults
# ---------------------------------------------------------------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


# ---------------------------------------------------------------------------
# Helper widgets
# ---------------------------------------------------------------------------


class NodeEditDialog(ctk.CTkToplevel):
    """Small modal dialog for editing a node's text field."""

    def __init__(self, parent: ctk.CTk, node: dict[str, Any]) -> None:
        super().__init__(parent)
        self.title("Edit Node")
        self.geometry("500x250")
        self.resizable(False, False)
        self.grab_set()

        self._node = node
        self._result: str | None = None

        ctk.CTkLabel(self, text=f"Node ID: {node['id']}  |  Type: {node['type']}",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(20, 5), padx=20, anchor="w")

        self._text_box = ctk.CTkTextbox(self, height=100)
        self._text_box.insert("1.0", node.get("text", ""))
        self._text_box.pack(fill="x", padx=20, pady=5)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="Save", command=self._save).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", fg_color="gray40",
                      command=self.destroy).pack(side="left", padx=5)

    def _save(self) -> None:
        self._result = self._text_box.get("1.0", "end").strip()
        self.destroy()

    @property
    def result(self) -> str | None:
        return self._result


# ---------------------------------------------------------------------------
# Main Builder UI
# ---------------------------------------------------------------------------


class BuilderUI(ctk.CTk):
    """Main window for the GuidWire Builder application."""

    def __init__(self) -> None:
        super().__init__()

        self.title("GuidWire Builder")
        self.geometry("900x700")
        self.resizable(True, True)

        # --- Single-document mode state ---
        self._file_path: Path | None = None
        self._logo_path: Path | None = None
        self._output_dir: Path | None = None
        self._tree_dict: dict[str, Any] | None = None
        self._current_step: int = 1

        # --- Bulk-library mode state ---
        self._bulk_source_root: Path | None = None
        self._bulk_output_base: Path | None = None
        self._bulk_manifest: dict[str, Any] | None = None
        self._bulk_library_path: Path | None = None
        self._bulk_current_step: int = 1
        self._bulk_exe_output_dir: Path | None = None

        self._mode: str = "single"  # "single" | "bulk"

        self._build_layout()

    # ------------------------------------------------------------------
    # Layout construction
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ---- LEFT SIDEBAR ----
        self._sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self._sidebar.grid(row=0, column=0, sticky="nsew")
        self._sidebar.grid_propagate(False)

        ctk.CTkLabel(
            self._sidebar,
            text="GuidWire",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="white",
        ).pack(pady=(30, 2), padx=20)

        ctk.CTkLabel(
            self._sidebar,
            text="Follow the wire.\nResolve the issue.",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="gray60",
            justify="center",
        ).pack(pady=(0, 16), padx=20)

        # Mode toggle
        mode_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        mode_frame.pack(fill="x", padx=10, pady=(0, 16))
        self._single_mode_btn = ctk.CTkButton(
            mode_frame,
            text="Single Doc",
            width=90,
            command=self._switch_to_single,
        )
        self._single_mode_btn.pack(side="left", padx=2)
        self._bulk_mode_btn = ctk.CTkButton(
            mode_frame,
            text="Bulk Library",
            width=90,
            fg_color="gray40",
            command=self._switch_to_bulk,
        )
        self._bulk_mode_btn.pack(side="left", padx=2)

        # Step indicators — single mode
        self._step_labels: list[ctk.CTkLabel] = []
        single_steps = [
            "Step 1: Upload Document",
            "Step 2: Analyze",
            "Step 3: Preview Tree",
            "Step 4: Brand & Export",
        ]
        self._single_step_labels: list[ctk.CTkLabel] = []
        self._single_steps_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        self._single_steps_frame.pack(fill="x")
        for i, label_text in enumerate(single_steps, start=1):
            lbl = ctk.CTkLabel(
                self._single_steps_frame,
                text=label_text,
                font=ctk.CTkFont(size=13),
                anchor="w",
                text_color="gray60",
            )
            lbl.pack(pady=6, padx=20, anchor="w")
            self._single_step_labels.append(lbl)

        # Step indicators — bulk mode
        bulk_steps = [
            "Step 1: Select Folder",
            "Step 2: Ingest & Index",
            "Step 3: Generate Trees",
            "Step 4: Export Package",
        ]
        self._bulk_step_labels: list[ctk.CTkLabel] = []
        self._bulk_steps_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        for i, label_text in enumerate(bulk_steps, start=1):
            lbl = ctk.CTkLabel(
                self._bulk_steps_frame,
                text=label_text,
                font=ctk.CTkFont(size=13),
                anchor="w",
                text_color="gray60",
            )
            lbl.pack(pady=6, padx=20, anchor="w")
            self._bulk_step_labels.append(lbl)

        # Keep backward compat: _step_labels points to currently active set
        self._step_labels = self._single_step_labels

        self._update_step_indicators()

        # ---- MAIN CONTENT ----
        self._content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self._content.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)

        # Build all step frames
        self._frames: dict[int, ctk.CTkScrollableFrame] = {}
        self._build_step1()
        self._build_step2()
        self._build_step3()
        self._build_step4()

        self._bulk_frames: dict[int, ctk.CTkScrollableFrame] = {}
        self._build_bulk_step1()
        self._build_bulk_step2()
        self._build_bulk_step3()
        self._build_bulk_step4()

        self._show_step(1)

    # ------------------------------------------------------------------
    # Step 1 — Upload Document
    # ------------------------------------------------------------------

    def _build_step1(self) -> None:
        frame = self._make_step_frame()
        self._frames[1] = frame

        ctk.CTkLabel(frame, text="Upload Document",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(10, 4), anchor="w")
        ctk.CTkLabel(frame, text="Select the support document you want to convert into a decision tree.",
                     text_color="gray60", wraplength=600, justify="left").pack(anchor="w", pady=(0, 20))

        # Drop zone / browse button
        drop_frame = ctk.CTkFrame(frame, height=160, corner_radius=12,
                                  border_width=2, border_color="gray40")
        drop_frame.pack(fill="x", pady=10)
        drop_frame.pack_propagate(False)

        ctk.CTkLabel(drop_frame, text="Drag & drop a file here or click Browse",
                     text_color="gray60").pack(expand=True)
        ctk.CTkLabel(drop_frame, text="Accepted: .pdf  .docx  .html  .txt",
                     font=ctk.CTkFont(size=11), text_color="gray50").pack(pady=(0, 10))

        ctk.CTkButton(frame, text="Browse File", command=self._browse_file).pack(pady=10)

        self._file_label = ctk.CTkLabel(frame, text="No file selected", text_color="gray50",
                                        font=ctk.CTkFont(size=12))
        self._file_label.pack(pady=4)

        ctk.CTkButton(frame, text="Next →", command=lambda: self._goto_step(2)).pack(pady=(20, 0))

    # ------------------------------------------------------------------
    # Step 2 — Analyze
    # ------------------------------------------------------------------

    def _build_step2(self) -> None:
        frame = self._make_step_frame()
        self._frames[2] = frame

        ctk.CTkLabel(frame, text="Analyze Document",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(10, 4), anchor="w")
        ctk.CTkLabel(frame, text="Enter your Anthropic API key and let Claude extract the troubleshooting tree.",
                     text_color="gray60", wraplength=600, justify="left").pack(anchor="w", pady=(0, 20))

        api_row = ctk.CTkFrame(frame, fg_color="transparent")
        api_row.pack(fill="x", pady=5)
        ctk.CTkLabel(api_row, text="API Key:", width=80).pack(side="left")
        self._api_key_entry = ctk.CTkEntry(api_row, show="•", width=360,
                                           placeholder_text="sk-ant-…")
        self._api_key_entry.pack(side="left", padx=5)
        self._show_key_btn = ctk.CTkButton(api_row, text="Show", width=60,
                                           command=self._toggle_api_key_visibility)
        self._show_key_btn.pack(side="left")

        self._analyze_btn = ctk.CTkButton(frame, text="Analyze Document",
                                          command=self._run_analysis)
        self._analyze_btn.pack(pady=15)

        self._analysis_progress = ctk.CTkProgressBar(frame, mode="indeterminate")

        self._analysis_status = ctk.CTkLabel(frame, text="", wraplength=600,
                                             justify="left")
        self._analysis_status.pack(pady=5)

        nav_row = ctk.CTkFrame(frame, fg_color="transparent")
        nav_row.pack(pady=(20, 0))
        ctk.CTkButton(nav_row, text="← Back", fg_color="gray40",
                      command=lambda: self._goto_step(1)).pack(side="left", padx=5)
        ctk.CTkButton(nav_row, text="Next →",
                      command=lambda: self._goto_step(3)).pack(side="left", padx=5)

    # ------------------------------------------------------------------
    # Step 3 — Preview Tree
    # ------------------------------------------------------------------

    def _build_step3(self) -> None:
        frame = self._make_step_frame()
        self._frames[3] = frame

        ctk.CTkLabel(frame, text="Preview Tree",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(10, 4), anchor="w")

        self._node_count_label = ctk.CTkLabel(frame, text="No tree loaded.",
                                              text_color="gray60")
        self._node_count_label.pack(anchor="w", pady=(0, 10))

        self._node_list_frame = ctk.CTkScrollableFrame(frame, height=360)
        self._node_list_frame.pack(fill="both", expand=True)
        self._node_list_frame.grid_columnconfigure(0, weight=1)

        nav_row = ctk.CTkFrame(frame, fg_color="transparent")
        nav_row.pack(pady=(10, 0))
        ctk.CTkButton(nav_row, text="← Back", fg_color="gray40",
                      command=lambda: self._goto_step(2)).pack(side="left", padx=5)
        ctk.CTkButton(nav_row, text="Next →",
                      command=lambda: self._goto_step(4)).pack(side="left", padx=5)

    # ------------------------------------------------------------------
    # Step 4 — Brand & Export
    # ------------------------------------------------------------------

    def _build_step4(self) -> None:
        frame = self._make_step_frame()
        self._frames[4] = frame

        ctk.CTkLabel(frame, text="Brand & Export",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(10, 4), anchor="w")
        ctk.CTkLabel(frame, text="Configure branding and build the standalone viewer .exe.",
                     text_color="gray60", wraplength=600, justify="left").pack(anchor="w", pady=(0, 20))

        # Company name
        name_row = ctk.CTkFrame(frame, fg_color="transparent")
        name_row.pack(fill="x", pady=5)
        ctk.CTkLabel(name_row, text="Company Name:", width=130).pack(side="left")
        self._company_name_entry = ctk.CTkEntry(name_row, width=300,
                                                placeholder_text="Acme Corp")
        self._company_name_entry.pack(side="left", padx=5)

        # Logo
        logo_row = ctk.CTkFrame(frame, fg_color="transparent")
        logo_row.pack(fill="x", pady=5)
        ctk.CTkButton(logo_row, text="Upload Logo", command=self._browse_logo,
                      width=130).pack(side="left")
        self._logo_label = ctk.CTkLabel(logo_row, text="No logo selected",
                                        text_color="gray50")
        self._logo_label.pack(side="left", padx=10)
        self._logo_preview_label: ctk.CTkLabel | None = None

        # Output directory
        out_row = ctk.CTkFrame(frame, fg_color="transparent")
        out_row.pack(fill="x", pady=5)
        ctk.CTkButton(out_row, text="Output Directory", command=self._browse_output,
                      width=130).pack(side="left")
        self._output_label = ctk.CTkLabel(out_row, text="No directory selected",
                                          text_color="gray50")
        self._output_label.pack(side="left", padx=10)

        # Logo thumbnail area
        self._logo_thumb_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self._logo_thumb_frame.pack(fill="x", pady=5)

        # Build button
        self._build_btn = ctk.CTkButton(frame, text="Build .exe",
                                        command=self._run_build, height=40,
                                        font=ctk.CTkFont(size=15, weight="bold"))
        self._build_btn.pack(pady=15)

        self._build_progress = ctk.CTkProgressBar(frame)
        self._build_status = ctk.CTkLabel(frame, text="", wraplength=600, justify="left")
        self._build_status.pack(pady=5)

        ctk.CTkButton(frame, text="← Back", fg_color="gray40",
                      command=lambda: self._goto_step(3)).pack(pady=(10, 0))

    # ------------------------------------------------------------------
    # Mode switching
    # ------------------------------------------------------------------

    def _switch_to_single(self) -> None:
        if self._mode == "single":
            return
        self._mode = "single"
        self._single_mode_btn.configure(fg_color=["#3B8ED0", "#1F6AA5"])
        self._bulk_mode_btn.configure(fg_color="gray40")
        self._bulk_steps_frame.pack_forget()
        self._single_steps_frame.pack(fill="x")
        self._step_labels = self._single_step_labels
        self._current_step = 1
        self._update_step_indicators()
        self._show_step(1)

    def _switch_to_bulk(self) -> None:
        if self._mode == "bulk":
            return
        self._mode = "bulk"
        self._bulk_mode_btn.configure(fg_color=["#3B8ED0", "#1F6AA5"])
        self._single_mode_btn.configure(fg_color="gray40")
        self._single_steps_frame.pack_forget()
        self._bulk_steps_frame.pack(fill="x")
        self._step_labels = self._bulk_step_labels
        self._bulk_current_step = 1
        self._update_step_indicators()
        self._show_bulk_step(1)

    # ------------------------------------------------------------------
    # Navigation helpers
    # ------------------------------------------------------------------

    def _make_step_frame(self) -> ctk.CTkScrollableFrame:
        f = ctk.CTkScrollableFrame(self._content, fg_color="transparent")
        f.grid_columnconfigure(0, weight=1)
        return f

    def _show_step(self, step: int) -> None:
        all_frames = list(self._frames.values()) + list(self._bulk_frames.values())
        for frame in all_frames:
            frame.grid_remove()
        self._frames[step].grid(row=0, column=0, sticky="nsew")
        self._current_step = step
        self._update_step_indicators()

    def _show_bulk_step(self, step: int) -> None:
        all_frames = list(self._frames.values()) + list(self._bulk_frames.values())
        for frame in all_frames:
            frame.grid_remove()
        self._bulk_frames[step].grid(row=0, column=0, sticky="nsew")
        self._bulk_current_step = step
        self._update_step_indicators()

    def _goto_step(self, step: int) -> None:
        self._show_step(step)

    def _goto_bulk_step(self, step: int) -> None:
        self._show_bulk_step(step)

    def _update_step_indicators(self) -> None:
        active = (
            self._current_step if self._mode == "single" else self._bulk_current_step
        )
        for i, lbl in enumerate(self._step_labels, start=1):
            if i == active:
                lbl.configure(text_color="white", font=ctk.CTkFont(size=13, weight="bold"))
            elif i < active:
                lbl.configure(text_color="#4CAF50", font=ctk.CTkFont(size=13))
            else:
                lbl.configure(text_color="gray60", font=ctk.CTkFont(size=13))

    # ------------------------------------------------------------------
    # Actions — Step 1
    # ------------------------------------------------------------------

    def _browse_file(self) -> None:
        path_str = filedialog.askopenfilename(
            title="Select Support Document",
            filetypes=[
                ("Supported Documents", "*.pdf *.docx *.html *.htm *.txt"),
                ("PDF files", "*.pdf"),
                ("Word documents", "*.docx"),
                ("HTML files", "*.html *.htm"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
        )
        if path_str:
            self._file_path = Path(path_str)
            self._file_label.configure(text=self._file_path.name, text_color="white")

    # ------------------------------------------------------------------
    # Actions — Step 2
    # ------------------------------------------------------------------

    def _toggle_api_key_visibility(self) -> None:
        current = self._api_key_entry.cget("show")
        if current == "•":
            self._api_key_entry.configure(show="")
            self._show_key_btn.configure(text="Hide")
        else:
            self._api_key_entry.configure(show="•")
            self._show_key_btn.configure(text="Show")

    def _run_analysis(self) -> None:
        if not self._file_path:
            messagebox.showwarning("No File", "Please select a document in Step 1 first.")
            return

        api_key = self._api_key_entry.get().strip()
        if not api_key:
            messagebox.showwarning("No API Key", "Please enter your Anthropic API key.")
            return

        self._analyze_btn.configure(state="disabled")
        self._analysis_status.configure(text="Extracting document text…", text_color="gray60")
        self._analysis_progress.pack(pady=5)
        self._analysis_progress.start()

        def _worker() -> None:
            try:
                ingestor = DocumentIngestor()
                raw_text = ingestor.ingest(self._file_path)

                self.after(0, lambda: self._analysis_status.configure(
                    text="Sending to Claude for analysis…", text_color="gray60"))

                analyzer = DocumentAnalyzer(api_key)
                tree_dict = analyzer.analyze(raw_text)

                validator = TreeBuilder()
                validator.validate(tree_dict)

                self._tree_dict = tree_dict

                self.after(0, self._on_analysis_success)
            except Exception as exc:
                self.after(0, lambda: self._on_analysis_error(str(exc)))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_analysis_success(self) -> None:
        self._analysis_progress.stop()
        self._analysis_progress.pack_forget()
        node_count = len(self._tree_dict.get("nodes", []))
        self._analysis_status.configure(
            text=f"✓ Analysis complete! Extracted {node_count} nodes. "
                 f"Title: {self._tree_dict.get('title', 'N/A')}",
            text_color="#4CAF50",
        )
        self._analyze_btn.configure(state="normal")
        self._populate_node_list()

    def _on_analysis_error(self, error_msg: str) -> None:
        self._analysis_progress.stop()
        self._analysis_progress.pack_forget()
        self._analysis_status.configure(
            text=f"✗ Error: {error_msg}", text_color="#F44336")
        self._analyze_btn.configure(state="normal")

    # ------------------------------------------------------------------
    # Actions — Step 3
    # ------------------------------------------------------------------

    def _populate_node_list(self) -> None:
        if not self._tree_dict:
            return

        # Clear existing widgets
        for widget in self._node_list_frame.winfo_children():
            widget.destroy()

        nodes = self._tree_dict.get("nodes", [])
        self._node_count_label.configure(
            text=f"{len(nodes)} nodes extracted  |  Title: {self._tree_dict.get('title', 'N/A')}",
            text_color="white",
        )

        type_colors = {"question": "#2196F3", "step": "#FF9800", "resolution": "#4CAF50"}

        for idx, node in enumerate(nodes):
            row = ctk.CTkFrame(self._node_list_frame, corner_radius=8)
            row.grid(row=idx, column=0, sticky="ew", pady=3, padx=2)
            row.grid_columnconfigure(1, weight=1)

            color = type_colors.get(node.get("type", ""), "gray50")
            ctk.CTkLabel(row, text=node.get("type", "?").upper(),
                         width=90, fg_color=color, corner_radius=6,
                         font=ctk.CTkFont(size=10, weight="bold"),
                         text_color="white").grid(row=0, column=0, padx=6, pady=6)

            text_preview = node.get("text", "")[:80] + ("…" if len(node.get("text", "")) > 80 else "")
            ctk.CTkLabel(row, text=f"[{node.get('id', '?')}] {text_preview}",
                         anchor="w", justify="left", wraplength=440).grid(
                row=0, column=1, padx=6, pady=6, sticky="ew")

            # Capture loop variable for lambda
            node_ref = node
            ctk.CTkButton(row, text="Edit", width=55,
                          command=lambda n=node_ref: self._edit_node(n)).grid(
                row=0, column=2, padx=6, pady=6)

    def _edit_node(self, node: dict[str, Any]) -> None:
        dialog = NodeEditDialog(self, node)
        self.wait_window(dialog)
        if dialog.result is not None:
            node["text"] = dialog.result
            self._populate_node_list()

    # ------------------------------------------------------------------
    # Actions — Step 4
    # ------------------------------------------------------------------

    def _browse_logo(self) -> None:
        path_str = filedialog.askopenfilename(
            title="Select Company Logo",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.ico *.tiff"),
                ("All files", "*.*"),
            ],
        )
        if path_str:
            self._logo_path = Path(path_str)
            self._logo_label.configure(text=self._logo_path.name, text_color="white")
            self._show_logo_thumbnail()

    def _show_logo_thumbnail(self) -> None:
        if not self._logo_path:
            return
        try:
            img = Image.open(str(self._logo_path)).convert("RGBA")
            img.thumbnail(_LOGO_THUMB_SIZE)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=_LOGO_THUMB_SIZE)
            if self._logo_preview_label is None:
                self._logo_preview_label = ctk.CTkLabel(
                    self._logo_thumb_frame, image=ctk_img, text="")
                self._logo_preview_label.pack(anchor="w", padx=5)
            else:
                self._logo_preview_label.configure(image=ctk_img)
        except Exception:
            pass

    def _browse_output(self) -> None:
        dir_str = filedialog.askdirectory(title="Select Output Directory")
        if dir_str:
            self._output_dir = Path(dir_str)
            self._output_label.configure(text=str(self._output_dir), text_color="white")

    def _run_build(self) -> None:
        if not self._tree_dict:
            messagebox.showwarning("No Tree", "Please analyze a document first (Step 2).")
            return

        company_name = self._company_name_entry.get().strip()
        if not company_name:
            messagebox.showwarning("No Company Name", "Please enter a company name.")
            return

        if not self._logo_path:
            messagebox.showwarning("No Logo", "Please upload a company logo.")
            return

        if not self._output_dir:
            messagebox.showwarning("No Output Directory", "Please select an output directory.")
            return

        self._build_btn.configure(state="disabled")
        self._build_progress.pack(pady=5)
        self._build_progress.configure(mode="indeterminate")
        self._build_progress.start()
        self._build_status.configure(text="Building…", text_color="gray60")

        def _worker() -> None:
            try:
                # Save tree to a temp file
                with tempfile.NamedTemporaryFile(
                    suffix=".json", delete=False, mode="w", encoding="utf-8"
                ) as tmp_f:
                    json.dump(self._tree_dict, tmp_f, indent=2)
                    tmp_tree_path = Path(tmp_f.name)

                def _progress(msg: str) -> None:
                    self.after(0, lambda m=msg: self._build_status.configure(
                        text=m, text_color="gray60"))

                packager = Packager()
                exe_path = packager.build(
                    tree_json_path=tmp_tree_path,
                    logo_path=self._logo_path,
                    company_name=company_name,
                    output_dir=self._output_dir,
                    progress_callback=_progress,
                )

                tmp_tree_path.unlink(missing_ok=True)
                self.after(0, lambda: self._on_build_success(exe_path))
            except Exception as exc:
                self.after(0, lambda: self._on_build_error(str(exc)))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_build_success(self, exe_path: Path) -> None:
        self._build_progress.stop()
        self._build_progress.pack_forget()
        self._build_status.configure(
            text=f"✓ Build complete!\n{exe_path}", text_color="#4CAF50")
        self._build_btn.configure(state="normal")

    def _on_build_error(self, error_msg: str) -> None:
        self._build_progress.stop()
        self._build_progress.pack_forget()
        self._build_status.configure(
            text=f"✗ Build failed: {error_msg}", text_color="#F44336")
        self._build_btn.configure(state="normal")

    # ==================================================================
    # BULK LIBRARY MODE — Step builders
    # ==================================================================

    # ------------------------------------------------------------------
    # Bulk Step 1 — Select Knowledge Base Folder
    # ------------------------------------------------------------------

    def _build_bulk_step1(self) -> None:
        frame = self._make_step_frame()
        self._bulk_frames[1] = frame

        ctk.CTkLabel(frame, text="Select Knowledge Base Folder",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(10, 4), anchor="w")
        ctk.CTkLabel(
            frame,
            text=(
                "Choose the root folder containing your DOCX documentation.\n"
                "GuidWire will recursively scan all sub-folders and preserve the"
                " folder structure in the output content package."
            ),
            text_color="gray60", wraplength=620, justify="left",
        ).pack(anchor="w", pady=(0, 16))

        ctk.CTkButton(frame, text="Browse Folder…",
                      command=self._bulk_browse_folder).pack(anchor="w", pady=4)

        self._bulk_folder_label = ctk.CTkLabel(
            frame, text="No folder selected", text_color="gray50",
            font=ctk.CTkFont(size=12),
        )
        self._bulk_folder_label.pack(anchor="w", pady=4)

        # Scan result
        self._bulk_scan_label = ctk.CTkLabel(frame, text="", text_color="gray60",
                                             font=ctk.CTkFont(size=12))
        self._bulk_scan_label.pack(anchor="w", pady=4)

        # Output base folder
        out_row = ctk.CTkFrame(frame, fg_color="transparent")
        out_row.pack(fill="x", pady=8)
        ctk.CTkButton(out_row, text="Output Base Folder…",
                      command=self._bulk_browse_output_base,
                      width=160).pack(side="left")
        self._bulk_output_label = ctk.CTkLabel(out_row, text="No folder selected",
                                               text_color="gray50")
        self._bulk_output_label.pack(side="left", padx=10)

        ctk.CTkButton(frame, text="Next →",
                      command=lambda: self._goto_bulk_step(2)).pack(pady=(20, 0))

    # ------------------------------------------------------------------
    # Bulk Step 2 — Ingest & Index
    # ------------------------------------------------------------------

    def _build_bulk_step2(self) -> None:
        frame = self._make_step_frame()
        self._bulk_frames[2] = frame

        ctk.CTkLabel(frame, text="Ingest & Index",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(10, 4), anchor="w")
        ctk.CTkLabel(
            frame,
            text=(
                "GuidWire will copy each DOCX file into the content folder (preserving"
                " the source folder tree), extract its text, and build a manifest.\n"
                "Unchanged files are skipped on subsequent runs."
            ),
            text_color="gray60", wraplength=620, justify="left",
        ).pack(anchor="w", pady=(0, 16))

        self._bulk_ingest_btn = ctk.CTkButton(
            frame, text="Start Ingest", command=self._run_bulk_ingest,
        )
        self._bulk_ingest_btn.pack(pady=8)

        self._bulk_ingest_progress = ctk.CTkProgressBar(frame)
        self._bulk_ingest_status = ctk.CTkLabel(frame, text="", wraplength=620,
                                                justify="left")
        self._bulk_ingest_status.pack(pady=4)

        # Scrollable log
        self._bulk_ingest_log = ctk.CTkTextbox(frame, height=200, state="disabled")
        self._bulk_ingest_log.pack(fill="x", pady=8)

        nav_row = ctk.CTkFrame(frame, fg_color="transparent")
        nav_row.pack(pady=(10, 0))
        ctk.CTkButton(nav_row, text="← Back", fg_color="gray40",
                      command=lambda: self._goto_bulk_step(1)).pack(side="left", padx=5)
        ctk.CTkButton(nav_row, text="Next →",
                      command=lambda: self._goto_bulk_step(3)).pack(side="left", padx=5)

    # ------------------------------------------------------------------
    # Bulk Step 3 — Generate Tree Library
    # ------------------------------------------------------------------

    def _build_bulk_step3(self) -> None:
        frame = self._make_step_frame()
        self._bulk_frames[3] = frame

        ctk.CTkLabel(frame, text="Generate Tree Library",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(10, 4), anchor="w")
        ctk.CTkLabel(
            frame,
            text=(
                "Enter your Anthropic API key.  GuidWire will group documents by"
                " top-level folder (category), generate a decision tree per document,"
                " and write library.json."
            ),
            text_color="gray60", wraplength=620, justify="left",
        ).pack(anchor="w", pady=(0, 16))

        api_row = ctk.CTkFrame(frame, fg_color="transparent")
        api_row.pack(fill="x", pady=5)
        ctk.CTkLabel(api_row, text="API Key:", width=80).pack(side="left")
        self._bulk_api_key_entry = ctk.CTkEntry(api_row, show="•", width=340,
                                                placeholder_text="sk-ant-…")
        self._bulk_api_key_entry.pack(side="left", padx=5)
        self._bulk_show_key_btn = ctk.CTkButton(
            api_row, text="Show", width=60,
            command=self._bulk_toggle_api_key,
        )
        self._bulk_show_key_btn.pack(side="left")

        self._bulk_gen_btn = ctk.CTkButton(
            frame, text="Generate Trees", command=self._run_bulk_generate,
        )
        self._bulk_gen_btn.pack(pady=10)

        self._bulk_gen_progress = ctk.CTkProgressBar(frame)
        self._bulk_gen_status = ctk.CTkLabel(frame, text="", wraplength=620,
                                             justify="left")
        self._bulk_gen_status.pack(pady=4)

        self._bulk_gen_log = ctk.CTkTextbox(frame, height=200, state="disabled")
        self._bulk_gen_log.pack(fill="x", pady=8)

        nav_row = ctk.CTkFrame(frame, fg_color="transparent")
        nav_row.pack(pady=(10, 0))
        ctk.CTkButton(nav_row, text="← Back", fg_color="gray40",
                      command=lambda: self._goto_bulk_step(2)).pack(side="left", padx=5)
        ctk.CTkButton(nav_row, text="Next →",
                      command=lambda: self._goto_bulk_step(4)).pack(side="left", padx=5)

    # ------------------------------------------------------------------
    # Bulk Step 4 — Export Offline Package
    # ------------------------------------------------------------------

    def _build_bulk_step4(self) -> None:
        frame = self._make_step_frame()
        self._bulk_frames[4] = frame

        ctk.CTkLabel(frame, text="Export Offline Package",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(10, 4), anchor="w")
        ctk.CTkLabel(
            frame,
            text=(
                "Build the standalone offline library viewer executable.\n"
                "Place the generated EXE together with the content folder"
                " (created in Step 2) on the analyst's machine — no Python required."
            ),
            text_color="gray60", wraplength=620, justify="left",
        ).pack(anchor="w", pady=(0, 16))

        # Company name
        name_row = ctk.CTkFrame(frame, fg_color="transparent")
        name_row.pack(fill="x", pady=5)
        ctk.CTkLabel(name_row, text="Company Name:", width=130).pack(side="left")
        self._bulk_company_entry = ctk.CTkEntry(name_row, width=300,
                                                placeholder_text="ForgedFiber37")
        self._bulk_company_entry.pack(side="left", padx=5)

        # Output directory
        out_row = ctk.CTkFrame(frame, fg_color="transparent")
        out_row.pack(fill="x", pady=5)
        ctk.CTkButton(out_row, text="Output Directory", width=130,
                      command=self._bulk_browse_exe_output).pack(side="left")
        self._bulk_exe_output_label = ctk.CTkLabel(out_row, text="No directory selected",
                                                   text_color="gray50")
        self._bulk_exe_output_label.pack(side="left", padx=10)

        self._bulk_build_btn = ctk.CTkButton(
            frame, text="Build Library Viewer .exe",
            command=self._run_bulk_build, height=40,
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        self._bulk_build_btn.pack(pady=15)

        self._bulk_build_progress = ctk.CTkProgressBar(frame)
        self._bulk_build_status = ctk.CTkLabel(frame, text="", wraplength=620,
                                               justify="left")
        self._bulk_build_status.pack(pady=5)

        ctk.CTkButton(frame, text="← Back", fg_color="gray40",
                      command=lambda: self._goto_bulk_step(3)).pack(pady=(10, 0))

    # ==================================================================
    # BULK LIBRARY MODE — Actions
    # ==================================================================

    # ------------------------------------------------------------------
    # Bulk Step 1 actions
    # ------------------------------------------------------------------

    def _bulk_browse_folder(self) -> None:
        dir_str = filedialog.askdirectory(title="Select Knowledge Base Root Folder")
        if not dir_str:
            return
        self._bulk_source_root = Path(dir_str)
        self._bulk_folder_label.configure(
            text=str(self._bulk_source_root), text_color="white"
        )
        # Scan immediately to show file count / size
        ingestor = BulkIngestor()
        files = ingestor.scan(self._bulk_source_root)
        total_size = sum(f["size"] for f in files)
        size_mb = total_size / (1024 * 1024)
        self._bulk_scan_label.configure(
            text=f"Found {len(files)} DOCX file(s)  |  Total size: {size_mb:.1f} MB",
            text_color="#4CAF50" if files else "orange",
        )

    def _bulk_browse_output_base(self) -> None:
        dir_str = filedialog.askdirectory(title="Select Output Base Folder")
        if dir_str:
            self._bulk_output_base = Path(dir_str)
            self._bulk_output_label.configure(
                text=str(self._bulk_output_base), text_color="white"
            )

    # ------------------------------------------------------------------
    # Bulk Step 2 actions
    # ------------------------------------------------------------------

    def _bulk_log(self, textbox: ctk.CTkTextbox, msg: str) -> None:
        textbox.configure(state="normal")
        textbox.insert("end", msg + "\n")
        textbox.see("end")
        textbox.configure(state="disabled")

    def _run_bulk_ingest(self) -> None:
        if not self._bulk_source_root:
            messagebox.showwarning("No Folder", "Please select a source folder in Step 1.")
            return
        if not self._bulk_output_base:
            messagebox.showwarning("No Output Folder",
                                   "Please select an output base folder in Step 1.")
            return

        self._bulk_ingest_btn.configure(state="disabled")
        self._bulk_ingest_progress.pack(pady=5)
        self._bulk_ingest_progress.configure(mode="indeterminate")
        self._bulk_ingest_progress.start()
        self._bulk_ingest_status.configure(text="Ingesting…", text_color="gray60")

        # Derive content folder name from output_base name
        content_dir = self._bulk_output_base
        manifest_path = content_dir / "manifest.json"

        def _cb(msg: str, current: int, total: int) -> None:
            self.after(0, lambda m=msg, c=current, t=total: (
                self._bulk_ingest_status.configure(text=f"[{c}/{t}] {m}"),
                self._bulk_log(self._bulk_ingest_log, f"[{c}/{t}] {m}"),
            ))

        def _worker() -> None:
            try:
                ingestor = BulkIngestor()
                manifest = ingestor.ingest(
                    root=self._bulk_source_root,
                    output_base=content_dir,
                    manifest_path=manifest_path,
                    progress_callback=_cb,
                )
                self._bulk_manifest = manifest
                self.after(0, self._on_bulk_ingest_success)
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda e=str(exc): self._on_bulk_ingest_error(e))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_bulk_ingest_success(self) -> None:
        self._bulk_ingest_progress.stop()
        self._bulk_ingest_progress.pack_forget()
        count = len(self._bulk_manifest or {})
        self._bulk_ingest_status.configure(
            text=f"✓ Ingest complete — {count} file(s) indexed.", text_color="#4CAF50"
        )
        self._bulk_ingest_btn.configure(state="normal")

    def _on_bulk_ingest_error(self, error_msg: str) -> None:
        self._bulk_ingest_progress.stop()
        self._bulk_ingest_progress.pack_forget()
        self._bulk_ingest_status.configure(
            text=f"✗ Error: {error_msg}", text_color="#F44336"
        )
        self._bulk_ingest_btn.configure(state="normal")

    # ------------------------------------------------------------------
    # Bulk Step 3 actions
    # ------------------------------------------------------------------

    def _bulk_toggle_api_key(self) -> None:
        current = self._bulk_api_key_entry.cget("show")
        if current == "•":
            self._bulk_api_key_entry.configure(show="")
            self._bulk_show_key_btn.configure(text="Hide")
        else:
            self._bulk_api_key_entry.configure(show="•")
            self._bulk_show_key_btn.configure(text="Show")

    def _run_bulk_generate(self) -> None:
        if not self._bulk_manifest:
            messagebox.showwarning("No Manifest",
                                   "Please run Ingest & Index (Step 2) first.")
            return
        api_key = self._bulk_api_key_entry.get().strip()
        if not api_key:
            messagebox.showwarning("No API Key", "Please enter your Anthropic API key.")
            return
        if not self._bulk_output_base:
            messagebox.showwarning("No Output Folder",
                                   "Please select an output base folder in Step 1.")
            return

        self._bulk_gen_btn.configure(state="disabled")
        self._bulk_gen_progress.pack(pady=5)
        self._bulk_gen_progress.configure(mode="indeterminate")
        self._bulk_gen_progress.start()
        self._bulk_gen_status.configure(text="Generating…", text_color="gray60")

        content_dir = self._bulk_output_base

        def _cb(msg: str, current: int, total: int) -> None:
            self.after(0, lambda m=msg, c=current, t=total: (
                self._bulk_gen_status.configure(text=f"[{c}/{t}] {m}"),
                self._bulk_log(self._bulk_gen_log, f"[{c}/{t}] {m}"),
            ))

        def _worker() -> None:
            try:
                builder = LibraryBuilder()
                library_path = builder.build(
                    manifest=self._bulk_manifest,
                    output_base=content_dir,
                    api_key=api_key,
                    progress_callback=_cb,
                )
                self._bulk_library_path = library_path
                self.after(0, self._on_bulk_generate_success)
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda e=str(exc): self._on_bulk_generate_error(e))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_bulk_generate_success(self) -> None:
        self._bulk_gen_progress.stop()
        self._bulk_gen_progress.pack_forget()
        self._bulk_gen_status.configure(
            text=f"✓ Library generated → {self._bulk_library_path}",
            text_color="#4CAF50",
        )
        self._bulk_gen_btn.configure(state="normal")

    def _on_bulk_generate_error(self, error_msg: str) -> None:
        self._bulk_gen_progress.stop()
        self._bulk_gen_progress.pack_forget()
        self._bulk_gen_status.configure(
            text=f"✗ Error: {error_msg}", text_color="#F44336"
        )
        self._bulk_gen_btn.configure(state="normal")

    # ------------------------------------------------------------------
    # Bulk Step 4 actions
    # ------------------------------------------------------------------

    def _bulk_browse_exe_output(self) -> None:
        dir_str = filedialog.askdirectory(title="Select EXE Output Directory")
        if dir_str:
            self._bulk_exe_output_dir = Path(dir_str)
            self._bulk_exe_output_label.configure(
                text=str(self._bulk_exe_output_dir), text_color="white"
            )

    def _run_bulk_build(self) -> None:
        if not self._bulk_library_path:
            messagebox.showwarning("No Library",
                                   "Please generate the tree library (Step 3) first.")
            return
        company_name = self._bulk_company_entry.get().strip()
        if not company_name:
            messagebox.showwarning("No Company Name", "Please enter a company name.")
            return
        if not hasattr(self, "_bulk_exe_output_dir") or not self._bulk_exe_output_dir:
            messagebox.showwarning("No Output Directory",
                                   "Please select an output directory.")
            return
        if not self._bulk_output_base:
            messagebox.showwarning("No Content Folder",
                                   "Please select an output base folder in Step 1.")
            return

        self._bulk_build_btn.configure(state="disabled")
        self._bulk_build_progress.pack(pady=5)
        self._bulk_build_progress.configure(mode="indeterminate")
        self._bulk_build_progress.start()
        self._bulk_build_status.configure(text="Building…", text_color="gray60")

        content_dir = self._bulk_output_base
        exe_out = self._bulk_exe_output_dir

        def _progress(msg: str) -> None:
            self.after(0, lambda m=msg: self._bulk_build_status.configure(
                text=m, text_color="gray60"
            ))

        def _worker() -> None:
            try:
                packager = Packager()
                exe_path = packager.build_library_viewer(
                    content_dir=content_dir,
                    company_name=company_name,
                    output_dir=exe_out,
                    progress_callback=_progress,
                )
                self.after(0, lambda: self._on_bulk_build_success(exe_path))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda e=str(exc): self._on_bulk_build_error(e))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_bulk_build_success(self, exe_path: Path) -> None:
        self._bulk_build_progress.stop()
        self._bulk_build_progress.pack_forget()
        content_folder = self._bulk_output_base.name if self._bulk_output_base else "Content"
        self._bulk_build_status.configure(
            text=(
                f"✓ Build complete!\n{exe_path}\n\n"
                f"Place the '{content_folder}' folder next to the EXE for offline use."
            ),
            text_color="#4CAF50",
        )
        self._bulk_build_btn.configure(state="normal")

    def _on_bulk_build_error(self, error_msg: str) -> None:
        self._bulk_build_progress.stop()
        self._bulk_build_progress.pack_forget()
        self._bulk_build_status.configure(
            text=f"✗ Build failed: {error_msg}", text_color="#F44336"
        )
        self._bulk_build_btn.configure(state="normal")
