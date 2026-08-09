from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ClassroomAsyncRoomTests(unittest.TestCase):
    def test_exam_audio_preparation_runs_on_background_worker(self):
        text = (ROOT / "dictatype" / "classroom.py").read_text(encoding="utf-8")
        self.assertIn("DictaTypeExamAudioPrep", text)
        self.assertIn("should_prepare_audio", text)
        self.assertIn("self.audio_preparing = should_prepare_audio", text)
        self.assertIn("self.audio_ready = not should_prepare_audio", text)
        self.assertIn("self.thread.start()", text)
        self.assertLess(text.index("self.thread.start()"), text.index("DictaTypeExamAudioPrep"))

    def test_students_wait_until_exam_audio_is_ready(self):
        text = (ROOT / "dictatype" / "classroom.py").read_text(encoding="utf-8")
        self.assertIn("if server.audio_preparing:", text)
        self.assertIn("The exam room is preparing audio", text)
        self.assertIn("HTTPStatus.SERVICE_UNAVAILABLE", text)
        self.assertIn('"audio_ready": server.audio_ready', text)

    def test_classroom_page_scrolls_and_keeps_room_details_visible(self):
        text = (ROOT / "dictatype" / "ui.py").read_text(encoding="utf-8")
        self.assertIn("self.classroom_canvas = tk.Canvas", text)
        self.assertIn("self.classroom_scrollbar = ttk.Scrollbar", text)
        self.assertIn("ROOM DETAILS", text)
        self.assertIn("self.room_banner_var", text)
        self.assertIn("self.classroom_canvas.yview_moveto(0.0)", text)

    def test_teacher_ui_polls_background_audio_progress(self):
        text = (ROOT / "dictatype" / "ui.py").read_text(encoding="utf-8")
        self.assertIn("self._room_progress_queue", text)
        self.assertIn("def _poll_room_preparation", text)
        self.assertIn("Preparing audio in background", text)
        self.assertIn("room stays responsive", text)


if __name__ == "__main__":
    unittest.main()
