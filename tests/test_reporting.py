import tempfile
import unittest
from pathlib import Path

from dictatype.reporting import save_attempt_pdf


class ReportingTests(unittest.TestCase):
    def test_pdf_analysis_is_created(self):
        attempt = {
            "student_name": "Élodie Test",
            "class_name": "French A",
            "lesson_title": "Dictée française",
            "answer": "L'élève écoute et écrit le texte.",
            "overall_score": 92.5,
            "score_word": 95.0,
            "score_char": 97.0,
            "wpm": 31.4,
            "duration_seconds": 73,
            "replay_count": 2,
            "created_at": "2026-08-07T10:00:00+00:00",
            "source": "desktop",
            "details": {
                "mode": "balanced",
                "correct_words": 6,
                "substitutions": 1,
                "missing_words": 0,
                "extra_words": 0,
                "accent_mistakes": 1,
                "capitalization_mistakes": 0,
                "punctuation_mistakes": 1,
                "expected_word_count": 7,
                "actual_word_count": 7,
                "changes": [
                    {"kind": "replace", "expected": "écrit", "actual": "ecrit"}
                ],
            },
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "analysis.pdf"
            result = save_attempt_pdf(attempt, path, "Très bon travail.")
            self.assertEqual(result, path)
            self.assertTrue(path.exists())
            self.assertGreater(path.stat().st_size, 1000)
            self.assertEqual(path.read_bytes()[:4], b"%PDF")


if __name__ == "__main__":
    unittest.main()
