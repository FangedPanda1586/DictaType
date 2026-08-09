from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class FrenchOnedirReleaseTests(unittest.TestCase):
    def test_spec_uses_onedir_collect(self):
        text = (ROOT / "DictaType.spec").read_text(encoding="utf-8")
        self.assertIn("COLLECT(", text)
        self.assertIn("exclude_binaries=True", text)
        self.assertIn('upx=False', text)

    def test_installer_copies_complete_runtime_tree(self):
        text = (ROOT / "installer.iss").read_text(encoding="utf-8")
        self.assertIn('Source: "dist\\DictaType\\*"', text)
        self.assertIn("recursesubdirs", text)

    def test_tts_accepts_release_and_legacy_voice_names(self):
        text = (ROOT / "dictatype" / "tts.py").read_text(encoding="utf-8")
        self.assertIn('"french.onnx"', text)
        self.assertIn('"fr_FR-siwis-medium.onnx"', text)

    def test_workflow_verifies_normal_and_frozen_piper(self):
        text = (ROOT / ".github" / "workflows" / "windows-build.yml").read_text(encoding="utf-8")
        self.assertIn("Verify Piper with normal Python before frozen test", text)
        self.assertIn("Verify French neural voice inside finished EXE", text)
        self.assertIn("french-v7-onedir-native-runtime", text)
        self.assertNotIn("ConvertFrom-Json", text)


if __name__ == "__main__":
    unittest.main()
