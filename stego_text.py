"""Store each bit of a recipient ID in its own synonym pair."""

import re

PAIRS = [
    ("big", "large"),
    ("start", "begin"),
    ("help", "assist"),
    ("buy", "purchase"),
    ("show", "display"),
    ("need", "require"),
    ("end", "finish"),
    ("fast", "quick"),
]
LOOKUP = {}
for index, (zero_word, one_word) in enumerate(PAIRS):
    LOOKUP[zero_word] = (index, 0)
    LOOKUP[one_word] = (index, 1)
# r keeps regex backslashes literal. \b marks word boundaries and | separates alternatives.
# (?ai:...) groups the alternatives and scopes ASCII case-insensitive matching to them.
PATTERN = re.compile(r"\b(?ai:" + "|".join(LOOKUP) + r")\b")
MEMO = "We need to start the big launch fast. Please help the team buy the tools, show the plan, and end the review early."


def embed_id(text, recipient_id):
    if not 1 <= recipient_id <= 255:
        raise ValueError("Recipient ID must be between 1 and 255.")

    def swap(match):
        # match[0] is the whole match. The underscore is an unused unpacked value.
        word = match[0]
        index, _ = LOOKUP[word.lower()]
        # >> moves the chosen ID bit into the lowest position. & 1 isolates it.
        bit = (recipient_id >> (7 - index)) & 1
        replacement = PAIRS[index][bit]
        if word.isupper():
            return replacement.upper()
        if word[0].isupper():
            return replacement.capitalize()
        return replacement

    # sub calls swap for each regex match and inserts the string it returns.
    return PATTERN.sub(swap, text)


def votes_for(text):
    # Each iteration creates a separate pair of counters for 0 votes and 1 votes.
    votes = [[0, 0] for _ in PAIRS]
    for word in PATTERN.findall(text):
        index, bit = LOOKUP[word.lower()]
        votes[index][bit] += 1
    return votes


def decode_votes(votes):
    # int converts the comparison to 0 or 1. None represents a tied or missing bit.
    bits = [None if zero == one else int(one > zero) for zero, one in votes]
    if None in bits:
        return None, bits
    # map turns the bits into strings. int(..., 2) reads their joined digits in base two.
    return int("".join(map(str, bits)), 2), bits


def extract_id(text):
    return decode_votes(votes_for(text))


def coverage(text):
    # any checks whether either word was found. sum counts True as 1.
    return sum(any(counts) for counts in votes_for(text))
