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

    # Scale first to avoid overflow for valid, finite provider vectors.
    scale_a = max((abs(x) for x in a), default=0.0)
    scale_b = max((abs(x) for x in b), default=0.0)
    if scale_a == 0 or scale_b == 0:
        return 0.0
    scaled_a = [x / scale_a for x in a]
    scaled_b = [x / scale_b for x in b]
    norm_a = math.sqrt(sum(x * x for x in scaled_a))
    norm_b = math.sqrt(sum(x * x for x in scaled_b))
    return sum((x / norm_a) * (y / norm_b) for x, y in zip(scaled_a, scaled_b))


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
    positive_only: bool = True,
) -> list[ScoredChunk]:

    if top_k <= 0:
        raise ValueError("top_k must be positive")

    if len(chunks) != len(vectors):
        raise ValueError("Chunks and vectors count mismatch")

    results = []

    for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
        score = cosine_similarity(query_vector, vector)

        if not positive_only or score > 0:
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