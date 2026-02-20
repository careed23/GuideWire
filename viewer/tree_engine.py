"""Decision-tree navigation engine for GuidWire Viewer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_ASSETS_DIR = Path(__file__).parent / "assets"


class TreeEngine:
    """Loads and navigates a GuidWire decision tree."""

    def __init__(self) -> None:
        tree_path = _ASSETS_DIR / "tree.json"
        config_path = _ASSETS_DIR / "config.json"

        if not tree_path.exists():
            raise FileNotFoundError(f"tree.json not found at {tree_path}")
        if not config_path.exists():
            raise FileNotFoundError(f"config.json not found at {config_path}")

        with tree_path.open(encoding="utf-8") as f:
            self._tree: dict[str, Any] = json.load(f)

        with config_path.open(encoding="utf-8") as f:
            self._config: dict[str, Any] = json.load(f)

        # Index nodes by id for O(1) lookup
        self._nodes: dict[str, dict[str, Any]] = {
            node["id"]: node for node in self._tree.get("nodes", [])
        }

        self._current_id: str = "start"
        self._history: list[str] = []

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def company_name(self) -> str:
        return self._config.get("company_name", "GuidWire")

    @property
    def title(self) -> str:
        return self._tree.get("title", "")

    @property
    def description(self) -> str:
        return self._tree.get("description", "")

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def get_current_node(self) -> dict[str, Any]:
        """Return the current node dict."""
        return self._nodes[self._current_id]

    def navigate(self, option_label: str) -> None:
        """For question nodes: advance to the node referenced by option_label.

        Args:
            option_label: The label of the chosen option.

        Raises:
            ValueError: If the current node is not a question node or the label
                        is not found.
        """
        node = self.get_current_node()
        if node["type"] != "question":
            raise ValueError(
                f"navigate() called on non-question node '{self._current_id}'"
            )

        for option in node.get("options", []):
            if option["label"] == option_label:
                self._history.append(node["text"])
                self._current_id = option["next"]
                return

        raise ValueError(
            f"Option '{option_label}' not found in node '{self._current_id}'"
        )

    def advance(self) -> None:
        """For step nodes: advance to the next node.

        Raises:
            ValueError: If the current node is not a step node.
        """
        node = self.get_current_node()
        if node["type"] != "step":
            raise ValueError(
                f"advance() called on non-step node '{self._current_id}'"
            )
        self._history.append(node["text"])
        self._current_id = node["next"]

    def reset(self) -> None:
        """Reset navigation back to the start node."""
        self._current_id = "start"
        self._history.clear()

    def get_history(self) -> list[str]:
        """Return list of visited node texts for breadcrumb display."""
        return list(self._history)

    def is_complete(self) -> bool:
        """Return True if the current node is a resolution (terminal) node."""
        return self.get_current_node().get("type") == "resolution"

    def go_back(self) -> bool:
        """Navigate to the previous node if history allows.

        Returns:
            True if navigation succeeded, False if already at the start.
        """
        if not self._history:
            return False

        # We need to find which node had the text that is last in history
        target_text = self._history[-1]
        for node_id, node in self._nodes.items():
            if node["text"] == target_text:
                self._history.pop()
                self._current_id = node_id
                return True

        # Fallback: just pop history and reset to start
        self._history.pop()
        self._current_id = "start"
        return True

    def approximate_total_steps(self) -> int:
        """Return a rough count of nodes for the step counter."""
        return len(self._nodes)

    def current_step_number(self) -> int:
        """Return the number of steps taken so far (1-indexed)."""
        return len(self._history) + 1
