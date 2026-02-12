"""Indigo word list module - loads words from indigo.txt."""

import common

# Load words into a list
WORDS = common.load_words_from_file("indigo.txt")

__all__ = ["WORDS"]
