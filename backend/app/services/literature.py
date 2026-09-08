"""Deterministic, extractive evidence retrieval; no invented scientific claims."""
import math
import re
from collections import Counter


STOP_WORDS = set("a an the and or of to in is are was were with for on at by as it this that what how does do can about from be".split())


def tokens(text: str) -> list[str]:
    return [word for word in re.findall(r"[a-z0-9]+", text.lower()) if len(word) > 2 and word not in STOP_WORDS]


def passages(text: str) -> list[str]:
    # Stable passage numbers are reproducible from immutable source text.
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text.strip())
    result, current, size = [], [], 0
    for sentence in sentences:
        count = len(sentence.split())
        if current and size + count > 180:
            result.append(" ".join(current))
            # Retain a complete sentence for context; never cut away a negation.
            current = current[-1:] if len(current[-1].split()) <= 50 else []
            size = sum(len(item.split()) for item in current)
        current.append(sentence)
        size += count
    if current:
        result.append(" ".join(current))
    return result


def retrieve(question: str, documents: list, limit: int = 5) -> list[dict]:
    query = set(tokens(question))
    if not query:
        return []
    chunks = [(doc, index + 1, passage) for doc in documents for index, passage in enumerate(passages(doc.content))]
    frequencies = [Counter(tokens(passage)) for _, _, passage in chunks]
    df = Counter(word for frequency in frequencies for word in frequency)
    ranked = []
    for (doc, index, passage), frequency in zip(chunks, frequencies):
        score = sum((1 + math.log(frequency[word])) * math.log(1 + len(chunks) / (1 + df[word])) for word in query if frequency[word])
        score /= math.sqrt(max(1, sum(frequency.values())))
        if score > 0:
            ranked.append({"document_id": doc.document_id, "passage": index, "title": doc.title,
                           "authors": doc.authors, "year": doc.year, "source_url": doc.source_url,
                           "source_kind": doc.source_kind, "excerpt": passage, "score": round(score, 5)})
    ranked.sort(key=lambda hit: (-hit["score"], hit["document_id"], hit["passage"]))
    return ranked[:limit]
