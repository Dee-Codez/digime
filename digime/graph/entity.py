import re

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "are", "was", "were",
    "how", "what", "why", "when", "where", "who", "will", "would", "could",
    "should", "can", "did", "does", "into", "about", "your", "you", "they",
    "have", "has", "had", "been", "not", "but", "all", "any", "some", "more",
    "most", "than", "then", "there", "their", "them", "its", "also", "just",
    "out", "off", "over", "under", "between", "after", "before", "while",
    "best", "2024", "2025", "2026", "tutorial", "scratch",
}


def extract_emails(text: str) -> set[str]:
    return {m.group(0).lower() for m in EMAIL_RE.finditer(text or "")}


def extract_topics(title: str, limit: int = 5) -> list[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", (title or "").lower())
    seen = []
    for t in tokens:
        if t in STOPWORDS or t in seen:
            continue
        seen.append(t)
        if len(seen) >= limit:
            break
    return seen
