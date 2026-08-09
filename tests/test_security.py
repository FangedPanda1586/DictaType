import tempfile
import unittest
from pathlib import Path

from dictatype.db import Database


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name) / "security.db")

    def tearDown(self):
        self.temp.cleanup()

    def test_student_profile_has_no_pin_and_can_be_opened(self):
        student = self.db.create_student_profile("Alice", "Form 2")
        self.assertTrue(student["identifier"].startswith("ST"))
        opened = self.db.authenticate_student(student["identifier"])
        self.assertIsNotNone(opened)
        self.assertEqual(opened["id"], student["id"])

    def test_disabled_profile_cannot_be_opened_or_recreated(self):
        student = self.db.create_student_profile("Alice", "Form 2")
        self.db.save_student("Alice", "Form 2", student["identifier"], student["id"], active=False)
        self.assertIsNone(self.db.authenticate_student(student["identifier"]))
        with self.assertRaises(ValueError):
            self.db.create_student_profile("Alice", "Form 2")

    def test_duplicate_student_id_is_rejected(self):
        self.db.save_student("Alice", "A", "S100")
        with self.assertRaises(ValueError):
            self.db.save_student("Bob", "B", "s100")


if __name__ == "__main__":
    unittest.main()
