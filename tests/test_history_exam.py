import tempfile
import unittest
from pathlib import Path

from dictatype.db import Database


class HistoryAndExamTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name) / "history.db")
        self.student = self.db.create_student_profile("Noah", "Grade 9")
        self.lesson1 = self.db.save_lesson({"title": "Passage A", "language": "en", "text": "First passage."})
        self.lesson2 = self.db.save_lesson({"title": "Passage B", "language": "en", "text": "Second passage."})

    def tearDown(self):
        self.temp.cleanup()

    def _attempt(self, lesson_id, title, score, item_index=0, item_count=0):
        return self.db.save_attempt({
            "student_id": self.student["id"],
            "student_name": self.student["name"],
            "class_name": self.student["class_name"],
            "lesson_id": lesson_id,
            "lesson_title": title,
            "answer": title,
            "score_word": score,
            "score_char": score,
            "overall_score": score,
            "wpm": 30,
            "duration_seconds": 60,
            "replay_count": 1,
            "details": {"changes": []},
            "source": "classroom-exam" if item_count else "desktop",
            "exam_session_id": "exam-001" if item_count else "",
            "exam_title": "Midterm Dictation" if item_count else "",
            "exam_item_index": item_index,
            "exam_item_count": item_count,
        })

    def test_history_contains_previous_work(self):
        self._attempt(self.lesson1, "Passage A", 70)
        self._attempt(self.lesson2, "Passage B", 90)
        history = self.db.list_student_attempts(self.student["id"])
        self.assertEqual(len(history), 2)
        summary = self.db.student_history_summary(self.student["id"])
        self.assertEqual(summary["attempt_count"], 2)
        self.assertAlmostEqual(summary["average_score"], 80.0)
        self.assertAlmostEqual(summary["best_score"], 90.0)

    def test_exam_metadata_is_saved_for_each_passage(self):
        attempt_id = self._attempt(self.lesson2, "Passage B", 88, item_index=2, item_count=3)
        attempt = self.db.get_attempt(attempt_id)
        self.assertEqual(attempt["exam_session_id"], "exam-001")
        self.assertEqual(attempt["exam_title"], "Midterm Dictation")
        self.assertEqual(attempt["exam_item_index"], 2)
        self.assertEqual(attempt["exam_item_count"], 3)


if __name__ == "__main__":
    unittest.main()
