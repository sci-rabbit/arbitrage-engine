import re

STOPWORDS = {
    "will", "be", "the", "a", "an", "for", "to",
    "win", "wins", "nominee", "election",
    "presidential", "president", "senate",
    "democratic", "republican", "party",
}


def extract_entities(text: str) -> set[str]:
    text = text.lower()

    words = re.findall(r"\b[a-z]{3,}\b", text)

    return {
        w for w in words
        if w not in STOPWORDS
    }


def extract_tickers(text: str) -> set[str]:
    return set(re.findall(r"\b[A-Z]{3}/[A-Z]{3}\b", text.upper()))


def extract_persons(text: str) -> set[str]:
    text = text.lower()
    candidates = re.findall(
        r'\b[a-z]+(?:\s+[a-z]+){1,2}\b',
        text
    )
    return {
        c.strip()
        for c in candidates
        if c.split()[0] not in {"will", "the", "if", "when"}
    }
