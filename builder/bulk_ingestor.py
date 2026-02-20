"""Bulk document ingestion for GuidWire Builder.

Scans a folder tree for DOCX files, copies them (preserving folder structure),
extracts plain text, and maintains a hash-based manifest for incremental
re-processing on subsequent runs.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Callable


class BulkIngestor:
    """Scans a source folder tree for DOCX files, copies them into the output
    content directory (mirroring the source structure), extracts text, and
    maintains a manifest JSON for incremental processing."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan(self, root: Path) -> list[dict[str, Any]]:
        """Recursively find all .docx files under *root*.

        Args:
            root: The root folder to search.

        Returns:
            Sorted list of dicts, each containing:
              - ``path``     – absolute Path to the source file
              - ``rel_path`` – Path relative to *root*
              - ``size``     – file size in bytes
        """
        results: list[dict[str, Any]] = []
        for p in sorted(root.rglob("*.docx")):
            if p.is_file():
                results.append(
                    {
                        "path": p,
                        "rel_path": p.relative_to(root),
                        "size": p.stat().st_size,
                    }
                )
        return results

    def ingest(
        self,
        root: Path,
        output_base: Path,
        manifest_path: Path,
        progress_callback: Callable[[str, int, int], None] | None = None,
    ) -> dict[str, Any]:
        """Copy DOCX files preserving folder structure, extract text, and
        update the manifest (hash-based incremental).

        Args:
            root: Source root folder selected by the user.
            output_base: Base output folder (e.g. ``ForgedFiber37_Content``).
                         DOCX files are placed under ``output_base/docs/``.
            manifest_path: Path to the manifest JSON file.  Loaded if it
                           exists; created/updated after processing.
            progress_callback: Optional ``callback(message, current, total)``.

        Returns:
            The full manifest dictionary keyed by relative path string.
        """
        docs_dir = output_base / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)

        # Load existing manifest for incremental processing
        manifest: dict[str, Any] = {}
        if manifest_path.exists():
            try:
                with manifest_path.open(encoding="utf-8") as fh:
                    manifest = json.load(fh)
            except (json.JSONDecodeError, OSError):
                manifest = {}

        files = self.scan(root)
        total = len(files)

        from builder.ingestor import DocumentIngestor  # local import to avoid circular deps

        ingestor = DocumentIngestor()

        for idx, entry in enumerate(files, start=1):
            src_path: Path = entry["path"]
            rel_path: Path = entry["rel_path"]
            rel_str = str(rel_path)
            dest_path = docs_dir / rel_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            file_hash = self._hash_file(src_path)

            # Skip unchanged files
            if manifest.get(rel_str, {}).get("hash") == file_hash:
                if progress_callback:
                    progress_callback(f"Skipping (unchanged): {rel_path}", idx, total)
                continue

            if progress_callback:
                progress_callback(f"Copying: {rel_path}", idx, total)

            shutil.copy2(str(src_path), str(dest_path))

            # Extract text; capture errors without aborting the whole run
            text = ""
            extract_error = ""
            try:
                text = ingestor.ingest(src_path)
            except (FileNotFoundError, PermissionError) as exc:
                extract_error = f"File access error: {exc}"
            except ValueError as exc:
                extract_error = f"Unsupported format: {exc}"
            except Exception as exc:  # noqa: BLE001 — e.g. corrupt DOCX
                extract_error = f"Extraction error: {exc}"

            # Derive category from the top-level sub-folder name
            parts = rel_path.parts
            category = str(parts[0]) if len(parts) > 1 else "Uncategorized"

            manifest[rel_str] = {
                "hash": file_hash,
                "dest": str(dest_path),
                "category": category,
                "text": text,
                "size": src_path.stat().st_size,
                **({"extract_error": extract_error} if extract_error else {}),
            }

            if progress_callback:
                progress_callback(f"Indexed: {rel_path}", idx, total)

        # Persist manifest
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return manifest

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hash_file(path: Path) -> str:
        """Return the SHA-256 hex digest of a file."""
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(65_536), b""):
                h.update(chunk)
        return h.hexdigest()
