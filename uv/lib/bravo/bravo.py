"""Bravo word list module - loads words from bravo.txt."""

import common

# Load words into a list
WORDS = common.load_words_from_file("bravo.txt")

__all__ = ["WORDS"]
