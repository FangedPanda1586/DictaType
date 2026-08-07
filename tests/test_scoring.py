import unittest

from dictatype.scoring import calculate_wpm, score_text, split_sentences


class ScoringTests(unittest.TestCase):
    def test_exact_answer_scores_100(self):
        result = score_text("The class begins at nine.", "The class begins at nine.", "strict")
        self.assertEqual(result.overall_score, 100.0)
        self.assertEqual(result.word_accuracy, 100.0)
        self.assertEqual(result.punctuation_mistakes, 0)

    def test_flexible_mode_ignores_accents_and_case(self):
        result = score_text("L'école est déjà ouverte.", "L'ECOLE EST DEJA OUVERTE", "flexible")
        self.assertEqual(result.word_accuracy, 100.0)

    def test_balanced_mode_reports_french_accents(self):
        result = score_text("Les étudiants sont arrivés à huit heures.", "Les etudiants sont arrives a huit heures.", "balanced")
        self.assertEqual(result.accent_mistakes, 3)
        self.assertLess(result.overall_score, 100)

    def test_missing_and_extra_words(self):
        result = score_text("one two three", "one extra two", "balanced")
        self.assertGreaterEqual(result.extra_words, 1)
        self.assertGreaterEqual(result.missing_words, 1)

    def test_sentence_splitting(self):
        self.assertEqual(split_sentences("First sentence. Second sentence!\nThird?"), ["First sentence.", "Second sentence!", "Third?"])

    def test_wpm(self):
        self.assertEqual(calculate_wpm("a" * 250, 60), 50.0)


if __name__ == "__main__":
    unittest.main()
