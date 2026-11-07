
import pytest

from app.rag.embedder import embed_text


@pytest.mark.parametrize("dimensions", [16, 128])
def test_embedding_dimensions(dimensions):
    vector = embed_text("Lorem ipsum Lorem", dimensions=dimensions)
    assert len(vector) == dimensions


def test_embedding_deterministic():
    text = "Lorem ipsum dolor sit amet"
    assert embed_text(text) == embed_text(text)


def test_embedding_normalized():
    vector = embed_text("Lorem ipsum Lorem")
    norm_squared = sum(x * x for x in vector)
    assert norm_squared == pytest.approx(1.0)


def test_empty_embedding():
    vector = embed_text("")
    assert vector == [0.0] * 128


def test_case_insensitive():
    assert embed_text("LOREM IPSUM") == embed_text("lorem ipsum")


@pytest.mark.parametrize("dimensions", [0, -1])
def test_invalid_dimensions(dimensions):
    with pytest.raises(ValueError):
        embed_text("Lorem ipsum", dimensions=dimensions)
