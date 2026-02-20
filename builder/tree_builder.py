"""Tree validation and persistence module for GuidWire Builder."""

import json
from pathlib import Path
from typing import Any


class TreeBuilder:
    """Validates and saves GuidWire decision-tree data structures."""

    def validate(self, tree_dict: dict[str, Any]) -> bool:
        """Validate the structure of a tree dictionary.

        Args:
            tree_dict: The tree dict produced by DocumentAnalyzer.

        Returns:
            True if the tree is structurally valid.

        Raises:
            ValueError: With a descriptive message if validation fails.
        """
        if "title" not in tree_dict:
            raise ValueError("Tree is missing required key: 'title'")
        if "nodes" not in tree_dict:
            raise ValueError("Tree is missing required key: 'nodes'")

        nodes: list[dict[str, Any]] = tree_dict["nodes"]
        if not isinstance(nodes, list) or len(nodes) == 0:
            raise ValueError("'nodes' must be a non-empty list")

        # Build a set of all known node ids for reference validation
        node_ids: set[str] = set()
        for node in nodes:
            for key in ("id", "type", "text"):
                if key not in node:
                    raise ValueError(f"Node is missing required key: '{key}'. Node: {node}")
            node_ids.add(node["id"])

        # Validate each node according to its type
        for node in nodes:
            node_type: str = node["type"]
            node_id: str = node["id"]

            if node_type == "question":
                options = node.get("options")
                if not isinstance(options, list) or len(options) < 2:
                    raise ValueError(
                        f"Question node '{node_id}' must have an 'options' list "
                        "with at least 2 entries"
                    )
                for opt in options:
                    if "label" not in opt or "next" not in opt:
                        raise ValueError(
                            f"Each option in question node '{node_id}' must have "
                            "'label' and 'next' keys"
                        )
                    if opt["next"] not in node_ids:
                        raise ValueError(
                            f"Option '{opt['label']}' in node '{node_id}' references "
                            f"unknown node id: '{opt['next']}'"
                        )

            elif node_type == "step":
                next_id = node.get("next")
                if not next_id:
                    raise ValueError(
                        f"Step node '{node_id}' must have a 'next' field"
                    )
                if next_id not in node_ids:
                    raise ValueError(
                        f"Step node '{node_id}' references unknown node id: '{next_id}'"
                    )

            elif node_type == "resolution":
                if node.get("next") or node.get("options"):
                    raise ValueError(
                        f"Resolution node '{node_id}' must be terminal "
                        "(no 'next' or 'options' fields)"
                    )
            else:
                raise ValueError(
                    f"Node '{node_id}' has unknown type: '{node_type}'. "
                    "Allowed types: question, step, resolution"
                )

        return True

    def save(self, tree_dict: dict[str, Any], output_path: str | Path) -> Path:
        """Write the tree dictionary to a JSON file.

        Args:
            tree_dict: The validated tree dictionary to persist.
            output_path: Destination file path (will be created/overwritten).

        Returns:
            The resolved Path of the written file.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(tree_dict, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path.resolve()
