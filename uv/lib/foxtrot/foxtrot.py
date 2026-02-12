"""Foxtrot word list module - loads words from foxtrot.txt."""

import common

# Load words into a list
WORDS = common.load_words_from_file("foxtrot.txt")

__all__ = ["WORDS"]
