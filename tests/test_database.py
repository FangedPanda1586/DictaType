import tempfile
import unittest
from pathlib import Path

from dictatype.db import Database


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name) / "dictatype.db")

    def tearDown(self):
        self.temp.cleanup()

    def test_default_pin_and_samples(self):
        self.assertTrue(self.db.check_pin("1234"))
        self.assertGreaterEqual(len(self.db.list_lessons()), 2)

    def test_save_lesson_student_and_attempt(self):
        lesson_id = self.db.save_lesson({"title": "Test", "language": "en", "text": "A short test."})
        student_id = self.db.save_student("Amina", "ICT 1", "S001")
        attempt_id = self.db.save_attempt(
            {
                "student_id": student_id,
                "student_name": "Amina",
                "class_name": "ICT 1",
                "lesson_id": lesson_id,
                "lesson_title": "Test",
                "answer": "A short test.",
                "score_word": 100,
                "score_char": 100,
                "overall_score": 100,
                "wpm": 30,
                "duration_seconds": 10,
                "replay_count": 1,
                "details": {"changes": []},
            }
        )
        self.assertIsNotNone(self.db.get_attempt(attempt_id))

    def test_backup_and_restore(self):
        backup_path = Path(self.temp.name) / "backup.db"
        self.db.backup(backup_path)
        self.assertTrue(backup_path.exists())
        self.db.set_pin("5678")
        self.assertTrue(self.db.check_pin("5678"))
        self.db.restore(backup_path)
        self.assertTrue(self.db.check_pin("1234"))


if __name__ == "__main__":
    unittest.main()
