"""Document ingestion module for GuidWire Builder."""

from pathlib import Path


class DocumentIngestor:
    """Reads and extracts plain text from supported document formats."""

    def ingest(self, file_path: str | Path) -> str:
        """Extract plain text content from a document file.

        Args:
            file_path: Path to the document to ingest.

        Returns:
            Full extracted plain text as a single string.

        Raises:
            ValueError: If the file format is not supported.
            FileNotFoundError: If the file does not exist.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        suffix = path.suffix.lower()

        if suffix == ".txt":
            return self._read_txt(path)
        elif suffix == ".docx":
            return self._read_docx(path)
        elif suffix == ".pdf":
            return self._read_pdf(path)
        elif suffix in (".html", ".htm"):
            return self._read_html(path)
        else:
            raise ValueError(
                f"Unsupported file format: '{suffix}'. "
                "Supported formats are: .txt, .docx, .pdf, .html"
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _read_txt(self, path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="replace")

    def _read_docx(self, path: Path) -> str:
        import docx  # python-docx

        document = docx.Document(str(path))
        paragraphs = [para.text for para in document.paragraphs]
        return "\n".join(paragraphs)

    def _read_pdf(self, path: Path) -> str:
        import pdfplumber

        pages: list[str] = []
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
        return "\n".join(pages)

    def _read_html(self, path: Path) -> str:
        from bs4 import BeautifulSoup

        html = path.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(html, "lxml")

        # Remove script and style elements
        for tag in soup(["script", "style", "head", "meta", "link"]):
            tag.decompose()

        return soup.get_text(separator="\n", strip=True)
