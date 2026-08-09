from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UI = (ROOT / "dictatype" / "ui.py").read_text(encoding="utf-8")


class FrenchLocalExerciseAndSettingsScrollTests(unittest.TestCase):
    def test_local_french_exercise_prefers_bundled_neural_voice(self):
        self.assertIn(
            'if self.current_lesson.get("language") == "fr" and builtin_french_available():',
            UI,
        )
        self.assertIn(
            '(voice for voice in self.app.voices if voice.id == BUNDLED_FRENCH_VOICE_ID)',
            UI,
        )
        self.assertIn('builtin_french_voice()', UI)

    def test_existing_french_editor_prefers_neural_voice(self):
        self.assertIn(
            'if self.lesson.get("language") == "fr" and builtin_french_available():',
            UI,
        )
        self.assertIn('self.voice_var.set(neural.display_name)', UI)

    def test_settings_page_has_vertical_scroll_container(self):
        self.assertIn('self.settings_canvas = tk.Canvas', UI)
        self.assertIn('self.settings_scrollbar = ttk.Scrollbar', UI)
        self.assertIn('orient="vertical"', UI)
        self.assertIn('yscrollcommand=self.settings_scrollbar.set', UI)
        self.assertIn('widget.bind("<MouseWheel>", wheel, add="+")', UI)
        self.assertIn('scrollregion=self.settings_canvas.bbox("all")', UI)


if __name__ == "__main__":
    unittest.main()
