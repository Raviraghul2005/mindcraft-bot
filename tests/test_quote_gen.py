import unittest

from services.quote_gen import _fallback_quotes, _is_usable_quote


class QuoteGenerationTests(unittest.TestCase):
    def test_fallback_quotes_match_the_new_editorial_standard(self):
        self.assertTrue(all(_is_usable_quote(quote) for quote in _fallback_quotes()))

    def test_cliche_language_is_rejected(self):
        self.assertFalse(_is_usable_quote("Wolves don't lose sleep over the opinions of sheep."))
        self.assertFalse(_is_usable_quote("The storm doesn't ask permission. Neither should you."))

    def test_concise_observations_are_accepted(self):
        self.assertTrue(_is_usable_quote("Some progress is quiet enough to be mistaken for nothing."))
        self.assertTrue(_is_usable_quote("You can be uncertain and still be consistent."))


if __name__ == "__main__":
    unittest.main()
