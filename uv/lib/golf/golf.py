"""Golf word list module - loads words from golf.txt."""

import common

# Load words into a list
WORDS = common.load_words_from_file("golf.txt")

__all__ = ["WORDS"]
