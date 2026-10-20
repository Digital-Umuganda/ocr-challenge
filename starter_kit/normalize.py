"""Text normalization applied to BOTH predictions and ground truth before scoring.

This file is identical for applicants and evaluators. Do not modify it: the
official score always uses this exact version.

Steps:
  1. Unicode NFKC normalization (curly quotes, ligatures, full-width chars -> plain)
  2. Lowercase
  3. Remove punctuation: apostrophes are deleted ("it's" -> "its"),
     every other Unicode punctuation character (category P*) becomes a space
  4. Collapse all whitespace, including line breaks, into single spaces
"""

import unicodedata


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = text.lower()
    # Apostrophes are dropped so "it's" -> "its" (one word, not two).
    text = text.replace("'", "").replace("’", "")
    # Other punctuation becomes a space so "word,word" becomes two words.
    text = "".join(" " if unicodedata.category(ch).startswith("P") else ch for ch in text)
    return " ".join(text.split())


if __name__ == "__main__":
    sample = "Hello,  “World”!\nIt's   ﬁne—really."
    print(repr(normalize(sample)))
