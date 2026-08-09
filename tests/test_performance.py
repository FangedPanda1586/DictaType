from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dictatype.classroom import ClassroomServer
from dictatype.db import Database
from dictatype import performance


class PerformanceTests(unittest.TestCase):
    def test_auto_mode_uses_low_memory_profile_on_4gb_machine(self):
        with patch("dictatype.performance._physical_memory_gb", return_value=4.0), patch("dictatype.performance.os.cpu_count", return_value=4):
            profile = performance.resolve_performance_profile("auto")
        self.assertTrue(profile.low_memory)
        self.assertEqual(profile.effective_mode, "low")
        self.assertLessEqual(profile.audio_chunk_bytes, 32 * 1024)

    def test_standard_override_stays_standard(self):
        with patch("dictatype.performance._physical_memory_gb", return_value=4.0), patch("dictatype.performance.os.cpu_count", return_value=4):
            profile = performance.resolve_performance_profile("standard")
        self.assertFalse(profile.low_memory)
        self.assertEqual(profile.effective_mode, "standard")

    def test_exam_audio_is_cached_to_disk_and_reused(self):
        with tempfile.TemporaryDirectory() as tempdir:
            db = Database(Path(tempdir) / "dictatype.db")
            db.initialize()
            server = ClassroomServer(db)
            server.lessons = [{
                "id": 1,
                "title": "Passage français",
                "language": "fr",
                "text": "Bonjour à tous.",
                "voice_id": "",
                "rate": 160,
                "volume": 1.0,
                "sentence_mode": 0,
            }]
            server.session_id = "test-session"
            server.enhanced_audio = True
            server.builtin_french = True
            server._cache_dir = Path(tempdir) / "audio"

            def fake_render(_text, output_path, **_kwargs):
                Path(output_path).write_bytes(b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * 64)
                return True

            with patch("dictatype.classroom.render_speech_wav_file", side_effect=fake_render) as render, patch("dictatype.classroom.release_bundled_french_voice") as release:
                first = server._audio_path(0, 0)
                second = server._audio_path(0, 0)
                prepared, total = server.prepare_audio_cache()

            self.assertIsNotNone(first)
            self.assertEqual(first, second)
            self.assertTrue(first.exists())
            self.assertEqual(render.call_count, 1)
            self.assertEqual((prepared, total), (1, 1))
            release.assert_called_once()


if __name__ == "__main__":
    unittest.main()
