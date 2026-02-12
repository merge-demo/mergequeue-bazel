"""Common utilities for word list packages."""

import inspect
import os


def load_words_from_file(txt_filename):
    """Load words from a text file into a list.

    Args:
        txt_filename: Name of the text file (e.g., 'alpha.txt')

    Returns:
        List of words from the file

    The function finds the text file in the same directory as the calling module.
    """
    words = []
    # Get the directory where the calling module is located
    # This assumes the txt file is in the same directory as the calling module
    caller_frame = inspect.stack()[1]
    caller_file = caller_frame.filename
    module_dir = os.path.dirname(caller_file)
    txt_file = os.path.join(module_dir, txt_filename)

    with open(txt_file, "r", encoding="utf-8") as f:
        for line in f:
            word = line.strip()
            if word:
                words.append(word)
    return words
