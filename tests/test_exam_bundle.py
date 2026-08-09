from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dictatype.classroom import ClassroomServer
from dictatype.db import Database
from dictatype.reporting import save_exam_pdf
from dictatype.scoring import score_text


class ExamBundleTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.db = Database(self.root / "dictatype.db")
        self.db.initialize()
        self.student = self.db.create_student_profile("Élodie Martin", "Form 4")

    def tearDown(self):
        self.tempdir.cleanup()

    def _save_passage(self, index: int, expected: str, answer: str) -> int:
        result = score_text(expected, answer, "balanced")
        return self.db.save_attempt(
            {
                "student_id": self.student["id"],
                "student_name": self.student["name"],
                "class_name": self.student["class_name"],
                "lesson_title": f"Passage {index}",
                "expected_text": expected,
                "answer": answer,
                "score_word": result.word_accuracy,
                "score_char": result.character_accuracy,
                "overall_score": result.overall_score,
                "wpm": 31 + index,
                "duration_seconds": 75 + index,
                "replay_count": 1,
                "details": result.to_dict(),
                "source": "classroom-exam",
                "exam_session_id": "exam-abc",
                "exam_title": "Examen de français",
                "exam_item_index": index,
                "exam_item_count": 2,
            }
        )

    def test_exam_attempts_are_grouped_and_pdf_is_single_file(self):
        self._save_passage(2, "Les élèves écoutent attentivement.", "Les élèves écoutent attentivement.")
        self._save_passage(1, "Aujourd'hui, le soleil brille.", "Aujourd'hui le soleil brille.")
        attempts = self.db.list_exam_attempts("exam-abc", self.student["id"])
        self.assertEqual([item["exam_item_index"] for item in attempts], [1, 2])
        self.assertEqual(attempts[0]["expected_text"], "Aujourd'hui, le soleil brille.")

        output = self.root / "complete_exam.pdf"
        save_exam_pdf(attempts, output)
        self.assertTrue(output.exists())
        self.assertGreater(output.stat().st_size, 2000)
        self.assertEqual(output.read_bytes()[:4], b"%PDF")

    def test_classroom_audio_uses_server_renderer_and_cache(self):
        server = ClassroomServer(self.db)
        server.lessons = [
            {
                "id": 1,
                "title": "Français",
                "language": "fr",
                "text": "Bonjour à tous.",
                "voice_id": "french-voice",
                "rate": 175,
                "volume": 1.0,
                "sentence_mode": 0,
            }
        ]
        server.enhanced_audio = True
        server.french_clarity = True
        fake_wav = b"RIFF" + b"\x00" * 48
        with patch("dictatype.classroom.render_speech_wav_bytes", return_value=fake_wav) as render:
            self.assertEqual(server._audio_bytes(0, 0), fake_wav)
            self.assertEqual(server._audio_bytes(0, 0), fake_wav)
            render.assert_called_once()
            self.assertTrue(render.call_args.kwargs["clarity_mode"])
            self.assertEqual(render.call_args.kwargs["language"], "fr")


if __name__ == "__main__":
    unittest.main()
