import pytest

from app.rag.chunker import split_text


def test_empty_text():
    assert split_text("") == []


def test_chunking_with_overlap():
    chunks = split_text(
        "abcdefghij",
        chunk_size=4,
        overlap=1,
    )

    assert chunks == [
        "abcd",
        "defg",
        "ghij",
    ]


def test_invalid_overlap():
    with pytest.raises(ValueError):
        split_text("hello", chunk_size=4, overlap=4)


def test_text_shorter_than_chunk_size():
    chunks = split_text("hello", chunk_size=10, overlap=2)
    assert chunks == ["hello"]


def test_chunking_without_overlap():
    chunks = split_text(
        "abcdefghij",
        chunk_size=4,
        overlap=0,
    )
    assert chunks == ["abcd", "efgh", "ij"]


def test_negative_overlap():
    with pytest.raises(ValueError):
        split_text("hello", chunk_size=4, overlap=-1)
