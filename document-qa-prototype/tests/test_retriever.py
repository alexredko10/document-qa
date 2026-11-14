
import pytest

from app.rag.embedder import embed_text
from app.rag.retriever import (
    cosine_similarity,
    search_chunks, search_vectors,
)


def test_identical_vectors():
    score = cosine_similarity(
        [1.0, 0.0],
        [1.0, 0.0],
    )

    assert score == pytest.approx(1.0)


def test_orthogonal_vectors():
    score = cosine_similarity(
        [1.0, 0.0],
        [0.0, 1.0],
    )

    assert score == pytest.approx(0.0)


def test_search_chunks():
    chunks = [
        "Cats are popular animals",
        "Dogs enjoy playing outside",
    ]

    results = search_chunks(
        query="Cats are popular animals",
        chunks=chunks,
        top_k=1,
    )

    assert len(results) == 1
    assert results[0].index == 0
    assert results[0].score == pytest.approx(1.0)


def test_invalid_dimensions():
    with pytest.raises(ValueError):
        cosine_similarity([1.0, 2.0], [1.0])


def test_empty_query():
    assert search_chunks("", ["Some document"]) == []


def test_zero_vector():
    score = cosine_similarity(
        [0.0, 0.0],
        [1.0, 0.0],
    )
    assert score == 0.0


def test_invalid_top_k():
    with pytest.raises(ValueError):
        search_chunks(
            "Cats are popular pets",
            ["Cats are popular pets"],
            top_k=0,
        )


def test_empty_chunks():
    results = search_chunks(
        "Cats are popular pets",
        [],
    )
    assert results == []

def test_search_precomputed_vectors():
    chunks = [
        "Cats are popular animals",
        "Dogs enjoy playing with water",
    ]

    vectors = [embed_text(chunk) for chunk in chunks]
    query_vector = embed_text("Cats are popular animals")

    results = search_vectors(
        query_vector=query_vector,
        chunks=chunks,
        vectors=vectors,
        top_k=1,
    )

    assert len(results) == 1
    assert results[0].index == 0
    assert results[0].score == pytest.approx(1.0)


def test_chunks_vectors_mismatch():
    with pytest.raises(ValueError):
        search_vectors(
            query_vector=[1.0, 0.0],
            chunks=["first", "second"],
            vectors=[[1.0, 0.0]],
        )
