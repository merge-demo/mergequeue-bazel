"""Echo word list module - loads words from echo.txt."""

import common

# Load words into a list
WORDS = common.load_words_from_file("echo.txt")

__all__ = ["WORDS"]
