import unittest

from dictatype import tts


class FrenchReleaseFilenameTests(unittest.TestCase):
    def test_release_model_filename_has_no_underscore(self):
        self.assertEqual(tts.BUNDLED_FRENCH_MODEL, "french.onnx")
        self.assertNotIn("_", tts.BUNDLED_FRENCH_MODEL)


if __name__ == "__main__":
    unittest.main()
