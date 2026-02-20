"""GuidWire Builder — entry point."""

import sys
from pathlib import Path

# Ensure project root is on the path so `builder.*` imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from builder.ui.builder_ui import BuilderUI


def main() -> None:
    app = BuilderUI()
    app.mainloop()


if __name__ == "__main__":
    main()
