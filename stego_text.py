"""Store each bit of a recipient ID in its own synonym pair."""

import re

PAIRS = [
    ("big", "large"), ("start", "begin"), ("help", "assist"), ("buy", "purchase"),
    ("show", "display"), ("need", "require"), ("end", "finish"), ("fast", "quick"),
]
LOOKUP = {word: (index, bit) for index, pair in enumerate(PAIRS) for bit, word in enumerate(pair)}
PATTERN = re.compile(r"\b(?:" + "|".join(LOOKUP) + r")\b", re.IGNORECASE | re.ASCII)
MEMO = "We need to start the big launch fast. Please help the team buy the tools, show the plan, and end the review early."


def embed_id(text, recipient_id):
    if not 1 <= recipient_id <= 255:
        raise ValueError("Recipient ID must be between 1 and 255.")

    def swap(match):
        word = match[0]
        index, _ = LOOKUP[word.lower()]
        bit = (recipient_id >> (7 - index)) & 1
        replacement = PAIRS[index][bit]
        if word.isupper():
            return replacement.upper()
        return replacement.capitalize() if word[0].isupper() else replacement

    return PATTERN.sub(swap, text)


def votes_for(text):
    votes = [[0, 0] for _ in PAIRS]
    for word in PATTERN.findall(text):
        index, bit = LOOKUP[word.lower()]
        votes[index][bit] += 1
    return votes


def extract_id(text):
    bits = [None if zero == one else int(one > zero) for zero, one in votes_for(text)]
    if None in bits:
        return None, bits
    return int("".join(map(str, bits)), 2), bits


def coverage(text):
    return sum(bool(zero or one) for zero, one in votes_for(text))
