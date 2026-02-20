"""Library navigation engine for the GuidWire offline library viewer.

Loads ``library.json`` from the content folder that sits adjacent to the
packaged executable (or the repository root when running from source),
and provides category browsing, keyword search, tree loading, and
source-document launching.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _locate_content_dir(content_folder_name: str) -> Path:
    """Return the content directory, supporting both frozen-exe and source runs.

    When running as a PyInstaller bundle the content folder lives next to
    ``sys.executable``; when running from source it lives next to the repo root.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / content_folder_name
    # Running from source — walk up to repo root
    return Path(__file__).parent.parent / content_folder_name


class LibraryEngine:
    """Loads and navigates a GuidWire tree library."""

    def __init__(self, content_dir: Path) -> None:
        """
        Args:
            content_dir: Path to the ``*_Content`` folder that contains
                         ``library.json``, ``trees/``, and ``docs/``.

        Raises:
            FileNotFoundError: If ``library.json`` is missing.
        """
        self._content_dir = content_dir
        library_path = content_dir / "library.json"

        if not library_path.exists():
            raise FileNotFoundError(
                f"library.json not found at {library_path}\n"
                "Make sure the content folder is placed next to the viewer executable."
            )

        with library_path.open(encoding="utf-8") as fh:
            data = json.load(fh)

        self._entries: list[dict[str, Any]] = data.get("entries", [])

    # ------------------------------------------------------------------
    # Public properties / helpers
    # ------------------------------------------------------------------

    @property
    def entries(self) -> list[dict[str, Any]]:
        """All library entries."""
        return self._entries

    @property
    def content_dir(self) -> Path:
        return self._content_dir

    def get_categories(self) -> list[str]:
        """Return a sorted list of unique category names."""
        return sorted({e.get("category", "Uncategorized") for e in self._entries})

    def get_entries_for_category(self, category: str) -> list[dict[str, Any]]:
        """Return all entries whose category matches *category*."""
        return [e for e in self._entries if e.get("category") == category]

    def search(self, query: str) -> list[dict[str, Any]]:
        """Search entries by title, description, or symptoms (case-insensitive).

        Args:
            query: Keyword(s) to search for.

        Returns:
            Matching entries; empty list when *query* is blank.
        """
        if not query.strip():
            return []
        q = query.lower()
        return [
            e
            for e in self._entries
            if q in e.get("title", "").lower()
            or q in e.get("description", "").lower()
            or any(q in s.lower() for s in e.get("symptoms", []))
        ]

    def load_tree(self, entry: dict[str, Any]) -> dict[str, Any]:
        """Load and return the decision-tree dict for *entry*.

        Raises:
            FileNotFoundError: If the tree JSON file is missing.
        """
        tree_path = self._content_dir / entry["tree_file"]
        if not tree_path.exists():
            raise FileNotFoundError(f"Tree file not found: {tree_path}")
        with tree_path.open(encoding="utf-8") as fh:
            return json.load(fh)

    def open_source_doc(self, entry: dict[str, Any]) -> None:
        """Open the source DOCX in the default system application (e.g. Word).

        Raises:
            FileNotFoundError: If the DOCX file is not present in the content
                               folder.
        """
        doc_path = self._content_dir / entry["source_doc"]
        if not doc_path.exists():
            raise FileNotFoundError(f"Source document not found: {doc_path}")

        if sys.platform == "win32":
            import os

            os.startfile(str(doc_path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(doc_path)])  # noqa: S603, S607
        else:
            subprocess.Popen(["xdg-open", str(doc_path)])  # noqa: S603, S607
