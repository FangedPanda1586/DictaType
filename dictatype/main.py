from __future__ import annotations

import argparse
from pathlib import Path

from .ui import DictaTypeApp


def main() -> None:
    parser = argparse.ArgumentParser(description="DictaType bilingual dictation application")
    parser.add_argument("--database", type=Path, help="Use a custom SQLite database path")
    args = parser.parse_args()
    app = DictaTypeApp(args.database)
    app.mainloop()


if __name__ == "__main__":
    main()
