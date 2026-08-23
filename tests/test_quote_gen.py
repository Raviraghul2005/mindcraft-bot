import unittest

from services.quote_gen import _fallback_quotes, _is_usable_quote


class QuoteGenerationTests(unittest.TestCase):
    def test_fallback_quotes_match_their_style(self):
        self.assertTrue(all(_is_usable_quote(q, style="calm") for q in _fallback_quotes("calm")))
        self.assertTrue(all(_is_usable_quote(q, style="vivid") for q in _fallback_quotes("vivid")))

    def test_vivid_vocabulary_is_rejected_only_for_calm_style(self):
        vivid_line = "The wolf hunts alone under a dying moon."
        self.assertTrue(_is_usable_quote(vivid_line, style="vivid"))
        self.assertFalse(_is_usable_quote(vivid_line, style="calm"))

    def test_dead_stock_phrases_are_rejected_regardless_of_style(self):
        stock_line = "The storm doesn't ask permission. Neither should you."
        self.assertFalse(_is_usable_quote(stock_line, style="vivid"))
        self.assertFalse(_is_usable_quote(stock_line, style="calm"))

    def test_concise_observations_are_accepted_for_calm_style(self):
        self.assertTrue(_is_usable_quote("Some progress is quiet enough to be mistaken for nothing.", style="calm"))
        self.assertTrue(_is_usable_quote("You can be uncertain and still be consistent.", style="calm"))


if __name__ == "__main__":
    unittest.main()
