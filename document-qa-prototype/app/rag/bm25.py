import math
import re
from collections import Counter

from app.rag.retriever import ScoredChunk


def tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def bm25_search(
    query: str,
    chunks: list[str],
    top_k: int = 3,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[ScoredChunk]:

    if top_k <= 0:
        raise ValueError("top_k must be positive")

    if not query.strip() or not chunks:
        return []

    corpus = [tokenize(chunk) for chunk in chunks]
    query_tokens = set(tokenize(query))

    n = len(corpus)
    avgdl = sum(len(tokens) for tokens in corpus) / n

    # Document frequency for each term
    df = Counter()

    for tokens in corpus:
        df.update(set(tokens))

    results = []

    for index, tokens in enumerate(corpus):
        frequencies = Counter(tokens)
        score = 0.0

        for term in query_tokens:
            tf = frequencies[term]

            if tf == 0:
                continue

            idf = math.log(
                1 + (n - df[term] + 0.5) / (df[term] + 0.5)
            )

            length_norm = 1 - b + b * len(tokens) / avgdl

            score += idf * (
                tf * (k1 + 1)
                / (tf + k1 * length_norm)
            )

        if score > 0:
            results.append(
                ScoredChunk(
                    index=index,
                    text=chunks[index],
                    score=score,
                )
            )

    return sorted(
        results,
        key=lambda item: item.score,
        reverse=True,
    )[:top_k]