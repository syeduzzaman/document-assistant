import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.answers import ProviderError, generated_answer
from app.config import Settings
from app.schemas import Source


@pytest.fixture
def source():
    return Source(id=1, chunk_id=1, document_id=uuid4(), filename="leave.md", page=2,
                  chunk_index=0, text="Employees have 30 days annual leave.", score=0.8)


def client_for(payload):
    return SimpleNamespace(responses=SimpleNamespace(
        create=lambda **kwargs: SimpleNamespace(output_text=json.dumps(payload)),
    ))


def test_openai_answer_uses_retrieved_sources(source):
    answer, sources, refused = generated_answer(client_for({
        "answer": "Employees have 30 days leave. [1]", "source_ids": [1], "insufficient_context": False,
    }), "test-model", "Annual leave?", [source])
    assert "30 days" in answer and sources == [source] and not refused


@pytest.mark.parametrize("answer,ids", [
    ("Thirty days. [99]", [99]), ("Thirty days.", [1]), ("Thirty days. [2]", [1]),
])
def test_fabricated_or_missing_citations_are_rejected(source, answer, ids):
    with pytest.raises(ProviderError):
        generated_answer(client_for({
            "answer": answer, "source_ids": ids, "insufficient_context": False,
        }), "test-model", "Annual leave?", [source])


def test_model_can_decline_insufficient_evidence(source):
    _, sources, refused = generated_answer(client_for({
        "answer": "", "source_ids": [], "insufficient_context": True,
    }), "test-model", "Unknown question?", [source])
    assert refused and not sources


def test_openai_mode_requires_explicit_key(monkeypatch):
    monkeypatch.setenv("RAG_MODE", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        Settings.from_env()
