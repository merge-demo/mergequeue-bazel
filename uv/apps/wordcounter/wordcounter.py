"""Word counter application - displays word dictionary statistics."""

# Import from workspace packages in lib (uv-alpha, uv-bravo, etc.)
# Each package exposes its module directly
import alpha
import bravo
import charlie
import delta
import echo
import foxtrot
import golf
import hotel
import indigo
import juliet
import kilo

# Dictionary mapping folder names to their word lists
WORD_DICT = {
    "alpha": alpha.WORDS,
    "bravo": bravo.WORDS,
    "charlie": charlie.WORDS,
    "delta": delta.WORDS,
    "echo": echo.WORDS,
    "foxtrot": foxtrot.WORDS,
    "golf": golf.WORDS,
    "hotel": hotel.WORDS,
    "indigo": indigo.WORDS,
    "juliet": juliet.WORDS,
    "kilo": kilo.WORDS,
}

__all__ = ["WORD_DICT", "main"]


def main():
    """Main entry point - displays word dictionary statistics."""
    print("UV Word Dictionary")
    print("=" * 50)

    for folder, words in WORD_DICT.items():
        print(f"{folder}: {len(words)} words")

    print("\nTotal words:", sum(len(words) for words in WORD_DICT.values()))


if __name__ == "__main__":
    main()
