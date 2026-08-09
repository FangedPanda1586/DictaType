import os
import tempfile
import unittest
from pathlib import Path

from dictatype.tts import BUNDLED_FRENCH_MODEL, bundled_french_model_path, builtin_french_available, french_voice_diagnostics


class FrenchPackagingTests(unittest.TestCase):
    def test_diagnostics_returns_actionable_fields(self):
        diag = french_voice_diagnostics(synthesize=False)
        for key in (
            "ready",
            "model_path",
            "config_path",
            "model_exists",
            "config_exists",
            "piper_importable",
            "synthesis_ok",
            "reason",
        ):
            self.assertIn(key, diag)
        self.assertIsInstance(diag["reason"], str)

    def test_external_voice_directory_override(self):
        previous = os.environ.get("DICTATYPE_FRENCH_VOICE_DIR")
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                voice_dir = Path(temp_dir)
                (voice_dir / BUNDLED_FRENCH_MODEL).write_bytes(b"model")
                (voice_dir / f"{BUNDLED_FRENCH_MODEL}.json").write_text("{}", encoding="utf-8")
                os.environ["DICTATYPE_FRENCH_VOICE_DIR"] = str(voice_dir)
                self.assertEqual(bundled_french_model_path(), voice_dir / BUNDLED_FRENCH_MODEL)
                self.assertTrue(builtin_french_available())
        finally:
            if previous is None:
                os.environ.pop("DICTATYPE_FRENCH_VOICE_DIR", None)
            else:
                os.environ["DICTATYPE_FRENCH_VOICE_DIR"] = previous


if __name__ == "__main__":
    unittest.main()
