import math
from types import SimpleNamespace

import pytest

from app.embeddings import DIMENSIONS, DemoEmbedder, OpenAIEmbedder, vector_literal


def test_demo_embedding_is_stable_and_normalized():
    embedder = DemoEmbedder()
    first, second = embedder.embed(["annual leave employee", "employee annual leave"])
    assert first == second == DemoEmbedder().embed(["annual leave employee"])[0]
    assert len(first) == DIMENSIONS
    assert math.isclose(sum(value * value for value in first), 1)


def test_stopword_query_has_zero_vector():
    assert not any(DemoEmbedder().embed(["what is the"])[0])


def test_similar_text_has_higher_cosine_score():
    query, relevant, unrelated = DemoEmbedder().embed([
        "annual leave", "annual leave is thirty days", "database encryption backups",
    ])
    assert sum(a * b for a, b in zip(query, relevant)) > sum(a * b for a, b in zip(query, unrelated))


def test_invalid_vectors_are_rejected():
    with pytest.raises(ValueError):
        vector_literal([1.0])
    with pytest.raises(ValueError):
        vector_literal([float("nan")] * DIMENSIONS)


def test_openai_embedding_dimensions_and_space():
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(data=[SimpleNamespace(index=0, embedding=[0.1] * DIMENSIONS)])

    embedder = OpenAIEmbedder(SimpleNamespace(embeddings=SimpleNamespace(create=create)), "model-name")
    assert len(embedder.embed(["sample"])[0]) == DIMENSIONS
    assert calls[0]["dimensions"] == DIMENSIONS
    assert embedder.space == "openai:model-name:384"
