import unittest
from pathlib import Path

from dictatype.tts import french_voice_diagnostics


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


if __name__ == "__main__":
    unittest.main()
