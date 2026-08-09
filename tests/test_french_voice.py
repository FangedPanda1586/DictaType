from __future__ import annotations

import unittest
from unittest.mock import patch

from dictatype import tts


class FrenchVoiceTests(unittest.TestCase):
    def test_french_dictation_clarity_uses_slower_neural_timing(self):
        normal = tts._piper_length_scale(175, False)
        clarity = tts._piper_length_scale(175, True)
        self.assertGreater(clarity, normal)

    def test_classroom_can_prefer_bundled_french_renderer(self):
        fake_wav = b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * 64
        with patch("dictatype.tts._render_piper_french_wav_bytes", return_value=fake_wav) as renderer:
            audio = tts.render_speech_wav_bytes(
                "Les élèves écoutent attentivement.",
                language="fr",
                rate=160,
                clarity_mode=True,
                prefer_builtin_french=True,
            )
        self.assertEqual(audio, fake_wav)
        renderer.assert_called_once()


if __name__ == "__main__":
    unittest.main()
