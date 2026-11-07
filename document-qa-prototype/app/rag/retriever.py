import math
from dataclasses import dataclass
from app.rag.embedder import embed_text


@dataclass
class ScoredChunk:
    index: int
    text: str
    score: float


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError("Vector dimensions must match")

    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def search_chunks(query: str, chunks: list[str], top_k: int = 3) -> list[ScoredChunk]:
    if top_k <= 0:
        raise ValueError("top_k must be positive")
    if not query.strip():
        return []
    query_vector = embed_text(query)
    results = []
    for index, chunk in enumerate(chunks):
        chunk_vector = embed_text(chunk)
        score = cosine_similarity(
            query_vector,
            chunk_vector,
        )

        if score > 0:
            results.append(ScoredChunk(index=index, text=chunk, score=score))
    results.sort(key=lambda item: item.score, reverse=True)
    return results[:top_k]


def search_vectors(
    query_vector: list[float],
    chunks: list[str],
    vectors: list[list[float]],
    top_k: int = 3,
) -> list[ScoredChunk]:

    if top_k <= 0:
        raise ValueError("top_k must be positive")

    if len(chunks) != len(vectors):
        raise ValueError("Chunks and vectors count mismatch")

    results = []

    for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
        score = cosine_similarity(query_vector, vector)

        if score > 0:
            results.append(
                ScoredChunk(
                    index=index,
                    text=chunk,
                    score=score,
                )
            )

    results.sort(
        key=lambda item: item.score,
        reverse=True,
    )

    return results[:top_k]