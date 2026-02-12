"""Hotel word list module - loads words from hotel.txt."""

import common

# Load words into a list
WORDS = common.load_words_from_file("hotel.txt")

__all__ = ["WORDS"]
