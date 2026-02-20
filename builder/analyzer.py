"""Gemini-powered document analysis module for GuidWire Builder."""

import json
import re
from typing import Any


_PROMPT_TEMPLATE = (
    "You are an expert IT support documentation analyst. Analyze the following "
    "support documentation and extract ALL troubleshooting workflows it contains.\n\n"
    "Return ONLY a valid JSON object with no markdown, no explanation, and no "
    "code blocks. The JSON must follow this exact schema:\n\n"
    "{{\n"
    '  "title": "string — the main issue or topic this document addresses",\n'
    '  "description": "string — one sentence summary of what this tree helps resolve",\n'
    '  "nodes": [\n'
    "    {{\n"
    '      "id": "string — unique node id, start with start for the first node",\n'
    '      "type": "string — either question, step, or resolution",\n'
    '      "text": "string — the question asked, instruction given, or resolution message",\n'
    '      "options": [\n'
    "        {{\n"
    '          "label": "string — the option label shown to the user",\n'
    '          "next": "string — the id of the next node this option leads to"\n'
    "        }}\n"
    "      ]\n"
    "    }}\n"
    "  ]\n"
    "}}\n\n"
    "Rules:\n"
    "- type question nodes must have an options array with at least 2 options\n"
    "- type step nodes have a single next field (string) pointing to the next node id, "
    "no options array\n"
    "- type resolution nodes have no next and no options — they are terminal nodes\n"
    "- Every non-terminal node must connect to another valid node id\n"
    "- The first node id must always be start\n"
    "- Extract every branch, every condition, and every resolution the document describes\n"
    "- Do not summarize or collapse steps — preserve full granularity\n\n"
    "Document to analyze:\n"
    "{document_text}"
)


class DocumentAnalyzer:
    """Sends extracted document text to Gemini and parses the structured response."""

    def __init__(self, api_key: str) -> None:
        """Initialize the analyzer with a Google Gemini API key.

        Args:
            api_key: A valid Google Gemini API key.
        """
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel("gemini-2.0-flash")

    def analyze(self, raw_text: str) -> dict[str, Any]:
        """Send document text to Gemini and return a parsed tree dict.

        Args:
            raw_text: The plain-text content of the ingested document.

        Returns:
            A Python dict following the GuidWire tree schema.

        Raises:
            ValueError: If Gemini's response cannot be parsed as valid JSON.
            google.api_core.exceptions.GoogleAPIError: For network or API-level
                errors (propagated).
        """
        prompt = _PROMPT_TEMPLATE.format(document_text=raw_text)

        response = self._model.generate_content(prompt)
        raw_response = response.text.strip()

        # Strip markdown code fences if Gemini included them despite instructions
        raw_response = re.sub(r"^```[a-zA-Z]*\n?", "", raw_response, flags=re.IGNORECASE)
        raw_response = re.sub(r"\n?```$", "", raw_response, flags=re.IGNORECASE).strip()

        try:
            return json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Gemini returned a response that could not be parsed as JSON: {exc}\n"
                f"Raw response (first 500 chars):\n{raw_response[:500]}"
            ) from exc
