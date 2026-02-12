"""Kilo word list module - loads words from kilo.txt."""

import common

# Load words into a list
WORDS = common.load_words_from_file("kilo.txt")

__all__ = ["WORDS"]
