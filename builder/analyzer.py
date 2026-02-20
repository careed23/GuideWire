"""Claude-powered document analysis module for GuidWire Builder."""

import json
from typing import Any


_PROMPT_TEMPLATE = (
    "You are an expert IT support documentation analyst. Analyze the following "
    "support documentation and extract ALL troubleshooting workflows it contains.\n\n"
    "Return ONLY a valid JSON object with no markdown, no explanation, and no "
    "code blocks. The JSON must follow this exact schema:\n\n"
    "{\n"
    '  "title": "string — the main issue or topic this document addresses",\n'
    '  "description": "string — one sentence summary of what this tree helps resolve",\n'
    '  "nodes": [\n'
    "    {\n"
    '      "id": "string — unique node id, start with start for the first node",\n'
    '      "type": "string — either question, step, or resolution",\n'
    '      "text": "string — the question asked, instruction given, or resolution message",\n'
    '      "options": [\n'
    "        {\n"
    '          "label": "string — the option label shown to the user",\n'
    '          "next": "string — the id of the next node this option leads to"\n'
    "        }\n"
    "      ]\n"
    "    }\n"
    "  ]\n"
    "}\n\n"
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
    """Sends extracted document text to Claude and parses the structured response."""

    def __init__(self, api_key: str) -> None:
        """Initialize the analyzer with an Anthropic API key.

        Args:
            api_key: A valid Anthropic API key.
        """
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)

    def analyze(self, raw_text: str) -> dict[str, Any]:
        """Send document text to Claude and return a parsed tree dict.

        Args:
            raw_text: The plain-text content of the ingested document.

        Returns:
            A Python dict following the GuidWire tree schema.

        Raises:
            ValueError: If Claude's response cannot be parsed as valid JSON.
            anthropic.APIError: For network or API-level errors (propagated).
        """
        prompt = _PROMPT_TEMPLATE.format(document_text=raw_text)

        message = self._client.messages.create(
            model="claude-opus-4-5",
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}],
        )

        raw_response = message.content[0].text.strip()

        # Strip markdown code fences if Claude included them despite instructions
        if raw_response.startswith("```"):
            lines = raw_response.splitlines()
            # Remove opening fence (```json or ```)
            lines = lines[1:]
            # Remove closing fence
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            raw_response = "\n".join(lines).strip()

        try:
            return json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Claude returned a response that could not be parsed as JSON: {exc}\n"
                f"Raw response (first 500 chars):\n{raw_response[:500]}"
            ) from exc
