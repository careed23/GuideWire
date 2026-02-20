"""GuidWire Builder — CustomTkinter GUI."""

from __future__ import annotations

import threading
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import customtkinter as ctk
from PIL import Image, ImageTk


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
        self.geometry("900x650")
        self.resizable(True, True)

        self._file_path: Path | None = None
        self._logo_path: Path | None = None
        self._output_dir: Path | None = None
        self._tree_dict: dict[str, Any] | None = None
        self._current_step: int = 1

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
        ).pack(pady=(0, 30), padx=20)

        # Step indicators
        self._step_labels: list[ctk.CTkLabel] = []
        steps = [
            "Step 1: Upload Document",
            "Step 2: Analyze",
            "Step 3: Preview Tree",
            "Step 4: Brand & Export",
        ]
        for i, label_text in enumerate(steps, start=1):
            lbl = ctk.CTkLabel(
                self._sidebar,
                text=label_text,
                font=ctk.CTkFont(size=13),
                anchor="w",
                text_color="gray60",
            )
            lbl.pack(pady=6, padx=20, anchor="w")
            self._step_labels.append(lbl)

        self._update_step_indicators()

        # ---- MAIN CONTENT ----
        self._content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self._content.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)

        # Build all step frames but show only the active one
        self._frames: dict[int, ctk.CTkScrollableFrame] = {}
        self._build_step1()
        self._build_step2()
        self._build_step3()
        self._build_step4()
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
    # Navigation helpers
    # ------------------------------------------------------------------

    def _make_step_frame(self) -> ctk.CTkScrollableFrame:
        f = ctk.CTkScrollableFrame(self._content, fg_color="transparent")
        f.grid_columnconfigure(0, weight=1)
        return f

    def _show_step(self, step: int) -> None:
        for s, frame in self._frames.items():
            if s == step:
                frame.grid(row=0, column=0, sticky="nsew")
            else:
                frame.grid_remove()
        self._current_step = step
        self._update_step_indicators()

    def _goto_step(self, step: int) -> None:
        self._show_step(step)

    def _update_step_indicators(self) -> None:
        for i, lbl in enumerate(self._step_labels, start=1):
            if i == self._current_step:
                lbl.configure(text_color="white",
                               font=ctk.CTkFont(size=13, weight="bold"))
            elif i < self._current_step:
                lbl.configure(text_color="#4CAF50",
                               font=ctk.CTkFont(size=13))
            else:
                lbl.configure(text_color="gray60",
                               font=ctk.CTkFont(size=13))

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
                from builder.ingestor import DocumentIngestor
                from builder.analyzer import DocumentAnalyzer
                from builder.tree_builder import TreeBuilder

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
            img.thumbnail((80, 80))
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(80, 80))
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
                import tempfile
                from builder.tree_builder import TreeBuilder
                from builder.packager import Packager

                # Save tree to a temp file
                with tempfile.NamedTemporaryFile(
                    suffix=".json", delete=False, mode="w", encoding="utf-8"
                ) as tmp_f:
                    import json
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
