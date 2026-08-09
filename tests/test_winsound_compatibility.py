import unittest
from types import SimpleNamespace
from unittest.mock import patch

from dictatype import tts


class WinsoundCompatibilityTests(unittest.TestCase):
    def test_python312_without_snd_sync_uses_filename_flag_only(self):
        fake_winsound = SimpleNamespace(SND_FILENAME=0x00020000)
        with patch.object(tts, "winsound", fake_winsound):
            self.assertEqual(
                tts._winsound_filename_sync_flags(),
                fake_winsound.SND_FILENAME,
            )

    def test_newer_python_can_include_snd_sync(self):
        fake_winsound = SimpleNamespace(SND_FILENAME=0x20, SND_SYNC=0x04)
        with patch.object(tts, "winsound", fake_winsound):
            self.assertEqual(tts._winsound_filename_sync_flags(), 0x24)

    def test_no_winsound_returns_zero(self):
        with patch.object(tts, "winsound", None):
            self.assertEqual(tts._winsound_filename_sync_flags(), 0)


if __name__ == "__main__":
    unittest.main()
