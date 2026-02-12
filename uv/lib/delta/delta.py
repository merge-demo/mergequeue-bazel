"""Delta word list module - loads words from delta.txt."""

import common

# Load words into a list
WORDS = common.load_words_from_file("delta.txt")

__all__ = ["WORDS"]
