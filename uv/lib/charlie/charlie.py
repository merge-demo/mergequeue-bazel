"""Charlie word list module - loads words from charlie.txt."""

import common

# Load words into a list
WORDS = common.load_words_from_file("charlie.txt")

__all__ = ["WORDS"]
