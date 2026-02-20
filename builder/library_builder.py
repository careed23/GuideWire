"""Library building module for GuidWire Builder.

Groups ingested documents by top-level-folder category, generates a
decision-tree JSON per document via Gemini, and writes a ``library.json``
catalog that the offline viewer can browse and search.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable


class LibraryBuilder:
    """Generates a library of troubleshooting trees from an ingested manifest."""

    def build(
        self,
        manifest: dict[str, Any],
        output_base: Path,
        api_key: str,
        progress_callback: Callable[[str, int, int], None] | None = None,
    ) -> Path:
        """Generate decision trees for every document in *manifest* and write
        ``library.json``.

        Args:
            manifest: The manifest dict produced by :class:`BulkIngestor`.
            output_base: Base content folder (``*_Content``).  Trees are
                         written to ``output_base/trees/``.
            api_key: Google Gemini API key passed to :class:`DocumentAnalyzer`.
            progress_callback: Optional ``callback(message, current, total)``.

        Returns:
            Path to the generated ``library.json``.
        """
        from builder.analyzer import DocumentAnalyzer
        from builder.tree_builder import TreeBuilder

        trees_dir = output_base / "trees"
        trees_dir.mkdir(parents=True, exist_ok=True)

        analyzer = DocumentAnalyzer(api_key)
        validator = TreeBuilder()

        # Group entries by category for ordered processing
        categories: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        for rel_str, entry in manifest.items():
            cat = entry.get("category", "Uncategorized")
            categories.setdefault(cat, []).append((rel_str, entry))

        total = sum(len(v) for v in categories.values())
        current = 0
        library_entries: list[dict[str, Any]] = []

        for category in sorted(categories.keys()):
            for rel_str, entry in categories[category]:
                current += 1
                text: str = entry.get("text", "")
                if not text.strip():
                    if progress_callback:
                        progress_callback(
                            f"[{category}] Skipping (no text): {rel_str}",
                            current,
                            total,
                        )
                    continue

                if progress_callback:
                    progress_callback(
                        f"[{category}] Analyzing: {rel_str}", current, total
                    )

                try:
                    tree_dict = analyzer.analyze(text)
                    validator.validate(tree_dict)
                except ValueError as exc:
                    if progress_callback:
                        progress_callback(
                            f"  ✗ Validation error ({exc})", current, total
                        )
                    continue
                except Exception as exc:  # noqa: BLE001 — API/network errors
                    if progress_callback:
                        progress_callback(
                            f"  ✗ Analysis error ({exc})", current, total
                        )
                    continue

                # Build a filesystem-safe filename from the relative path
                safe_stem = re.sub(r"[^\w\-]", "_", rel_str.replace(".docx", ""))
                tree_filename = f"{safe_stem}.json"
                tree_path = trees_dir / tree_filename
                validator.save(tree_dict, tree_path)

                library_entries.append(
                    {
                        "title": tree_dict.get("title", rel_str),
                        "description": tree_dict.get("description", ""),
                        "category": category,
                        "tree_file": f"trees/{tree_filename}",
                        "source_doc": f"docs/{rel_str}",
                        "symptoms": [],
                    }
                )

                if progress_callback:
                    progress_callback(f"  ✓ Tree saved: {tree_filename}", current, total)

        # Write library catalog
        library_path = output_base / "library.json"
        library_path.write_text(
            json.dumps({"entries": library_entries}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return library_path
