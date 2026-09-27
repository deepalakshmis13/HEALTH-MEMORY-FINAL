"""
Deterministic local embeddings.

The MVP must run with no API key and no model download, so retrieval uses a
hashed bag-of-words vector (the "hashing trick") with sub-word shingles for
robustness against OCR noise — `Amlodipme` still lands near `Amlodipine`.
Vectors are L2-normalised so cosine similarity is a dot product.

Swapping in a real embedding model means replacing `embed()` only; the
retriever depends on nothing else.
"""

import hashlib
import math
import re
from typing import Dict, List

from config import EMBEDDING_DIM

_TOKEN_RE = re.compile(r"[a-z0-9]+")

STOPWORDS = {
    "the", "and", "for", "with", "was", "are", "has", "had", "his", "her",
    "she", "him", "you", "your", "that", "this", "from", "have", "been",
    "were", "them", "they", "but", "not", "any", "all", "can", "will",
    "did", "does", "what", "when", "who", "how", "about", "into", "onto",
    "a", "an", "of", "on", "in", "to", "is", "it", "at", "as", "by", "or",
}

MEDICAL_BOOST = {
    "medication", "medicine", "dose", "dosage", "tablet", "prescription",
    "prescribed", "allergy", "allergic", "diagnosis", "symptom", "doctor",
    "consultation", "lab", "result", "blood", "pressure", "sugar", "verified",
    "verification", "reviewer", "shift", "handover", "observation",
    "administered", "missed", "emergency", "change", "changed",
}


def tokenize(text: str) -> List[str]:
    tokens = [t for t in _TOKEN_RE.findall((text or "").lower()) if len(t) > 1]
    return [t for t in tokens if t not in STOPWORDS]


def _shingles(token: str) -> List[str]:
    """Character 4-grams — makes matching resilient to OCR character noise."""
    if len(token) <= 4:
        return [token]
    return [token[i:i + 4] for i in range(len(token) - 3)]


def _bucket(feature: str) -> int:
    digest = hashlib.md5(feature.encode()).digest()
    return int.from_bytes(digest[:4], "big") % EMBEDDING_DIM


def embed(text: str) -> List[float]:
    vector = [0.0] * EMBEDDING_DIM
    tokens = tokenize(text)
    if not tokens:
        return vector

    for token in tokens:
        weight = 1.6 if token in MEDICAL_BOOST else 1.0
        vector[_bucket(token)] += weight
        for shingle in _shingles(token):
            vector[_bucket("#" + shingle)] += 0.45 * weight

    for first, second in zip(tokens, tokens[1:]):
        vector[_bucket(f"{first}_{second}")] += 0.6

    norm = math.sqrt(sum(value * value for value in vector))
    if norm:
        vector = [value / norm for value in vector]
    return [round(value, 6) for value in vector]


def cosine(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    length = min(len(a), len(b))
    return max(0.0, sum(a[i] * b[i] for i in range(length)))


def keyword_overlap(query: str, text: str) -> float:
    query_tokens = set(tokenize(query))
    if not query_tokens:
        return 0.0
    text_tokens = set(tokenize(text))
    if not text_tokens:
        return 0.0
    exact = len(query_tokens & text_tokens)
    fuzzy = 0
    for q in query_tokens - text_tokens:
        if any(q[:5] and t.startswith(q[:5]) for t in text_tokens):
            fuzzy += 1
    return min(1.0, (exact + 0.5 * fuzzy) / len(query_tokens))


def term_frequencies(text: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for token in tokenize(text):
        counts[token] = counts.get(token, 0) + 1
    return counts
