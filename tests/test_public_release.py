from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PublicReleaseTests(unittest.TestCase):
    def test_preview_reads_complete_passage(self):
        text = (ROOT / "dictatype" / "ui.py").read_text(encoding="utf-8")
        match = re.search(r"    def preview\(self\):(?P<body>.*?)(?=\n    def save\(self\):)", text, re.S)
        self.assertIsNotNone(match)
        body = match.group("body")
        self.assertIn("preview_text = content", body)
        self.assertIn("self.app.speech.speak", body)
        self.assertNotIn("content[:300]", body)
        self.assertNotIn("split_sentences(content)[0]", body)

    def test_about_screen_is_publicly_accessible(self):
        text = (ROOT / "dictatype" / "ui.py").read_text(encoding="utf-8")
        self.assertIn("class AboutDialog", text)
        self.assertIn("About DictaType {APP_VERSION}", text)
        self.assertIn("THIRD-PARTY-NOTICES.md", text)

    def test_release_versions_are_consistent(self):
        ui = (ROOT / "dictatype" / "ui.py").read_text(encoding="utf-8")
        installer = (ROOT / "installer.iss").read_text(encoding="utf-8")
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('APP_VERSION = "1.0.0-rc.1"', ui)
        self.assertIn('#define MyAppVersion "1.0.0-rc.1"', installer)
        self.assertIn('version = "1.0.0rc1"', pyproject)

    def test_public_documents_and_release_workflow_are_present(self):
        for name in ["README.md", "FIRST_RUN.md", "LICENSE", "THIRD-PARTY-NOTICES.md", "CHANGELOG.md"]:
            self.assertTrue((ROOT / name).exists(), name)
        workflow = (ROOT / ".github" / "workflows" / "windows-build.yml").read_text(encoding="utf-8")
        self.assertIn("Stage public release documents", workflow)
        self.assertIn("public-rc1-onedir-native-runtime", workflow)
        self.assertIn("generate_release_notes: true", workflow)
        self.assertIn("prerelease: true", workflow)

    def test_french_voice_attribution_is_included(self):
        notices = (ROOT / "THIRD-PARTY-NOTICES.md").read_text(encoding="utf-8")
        self.assertIn("fr_FR-siwis-medium", notices)
        self.assertIn("CC BY 4.0", notices)
        self.assertIn("10.7488/ds/1705", notices)
        self.assertIn("GPL-3.0-or-later", notices)


if __name__ == "__main__":
    unittest.main()
