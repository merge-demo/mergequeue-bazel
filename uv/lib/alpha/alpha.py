"""Alpha word list module - loads words from alpha.txt."""

import common

# Load words into a list
WORDS = common.load_words_from_file("alpha.txt")

__all__ = ["WORDS"]
