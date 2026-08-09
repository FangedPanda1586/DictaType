from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="DictaType bilingual dictation application")
    parser.add_argument("--database", type=Path, help="Use a custom SQLite database path")
    parser.add_argument(
        "--verify-french-voice",
        action="store_true",
        help="Verify the bundled French neural voice and exit",
    )
    parser.add_argument(
        "--verification-output",
        type=Path,
        help="Write French voice verification details to this JSON file",
    )
    args = parser.parse_args()

    if args.verify_french_voice:
        from .tts import french_voice_diagnostics

        result = french_voice_diagnostics(synthesize=True)
        payload = json.dumps(result, ensure_ascii=False, indent=2)
        if args.verification_output:
            args.verification_output.write_text(payload, encoding="utf-8")
        else:
            print(payload)
        raise SystemExit(0 if result.get("ready") else 3)

    # Import the full Tk interface only for a normal application session. This
    # keeps the build-time voice verification small and deterministic.
    from .ui import DictaTypeApp

    app = DictaTypeApp(args.database)
    app.mainloop()


if __name__ == "__main__":
    main()
