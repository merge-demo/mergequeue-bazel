"""Juliet word list module - loads words from juliet.txt."""

import common

# Load words into a list
WORDS = common.load_words_from_file("juliet.txt")

__all__ = ["WORDS"]
