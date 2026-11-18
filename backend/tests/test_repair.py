import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.answers import ProviderError
from app.main import create_app
from app.repair import generate_checklist, sample_checklist
from app.schemas import Source

SCENARIO = "Replace the front bumper. The estimate increased by EUR 450 after teardown."
QUOTE = "Obtain written authorization when a supplement exceeds EUR 300."


def test_sample_uses_current_approval_revision_and_cites_original_text():
    samples_dir = Path(__file__).resolve().parents[2] / "sample-documents"
    result = sample_checklist(samples_dir)
    approvals = [item for item in result.requirements if item.category == "approvals"]
    assert len(approvals) == 1
    assert "EUR 300" in approvals[0].action
    assert "EUR 500" not in approvals[0].action
    assert approvals[0].citation.revision == "v2"
    assert approvals[0].citation.filename == "supplement-approval-v2.md"
    assert {item.category for item in result.requirements} == {"photos", "documents", "approvals"}
    assert any("VIN" in check for check in result.manual_checks)
    for item in result.requirements:
        original = (samples_dir / "repair" / item.citation.filename).read_text(encoding="utf-8")
        assert item.citation.quote in original


@pytest.mark.parametrize(("source_id", "quote"), [(99, QUOTE), (1, "Obtain authorization above EUR 900.")])
def test_generated_checklist_rejects_invented_passage_or_source(source_id, quote):
    source = Source(
        id=1, chunk_id=1, document_id=uuid4(), filename="approval.pdf", page=2,
        chunk_index=0, text=QUOTE, score=0.8,
    )
    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **_: SimpleNamespace(
        output_text=json.dumps({
            "requirements": [{"category": "approvals", "action": "Get written approval.",
                              "source_id": source_id, "quote": quote}],
            "manual_checks": [],
        }),
    )))
    with pytest.raises(ProviderError, match="unverified evidence"):
        generate_checklist(client, "test-model", SCENARIO, [source])


def test_no_matching_passages_returns_manual_checks_without_calling_model():
    result = generate_checklist(None, "test-model", SCENARIO, [])
    assert result.requirements == []
    assert len(result.manual_checks) == 4


@pytest.mark.usefixtures("client")
def test_custom_case_retrieves_only_selected_procedure_and_flags_missing_categories(settings, monkeypatch):
    seen_payloads = []

    def respond(**kwargs):
        payload = json.loads(kwargs["input"])
        seen_payloads.append(payload)
        source = payload["procedures"][0]
        return SimpleNamespace(output_text=json.dumps({
            "requirements": [{
                "category": "approvals", "action": "Obtain written authorization for this supplement.",
                "source_id": source["source_id"], "quote": QUOTE,
            }],
            "manual_checks": ["Does the insurer require a VIN photo?"],
        }))

    fake_client = SimpleNamespace(
        embeddings=SimpleNamespace(create=lambda **kwargs: SimpleNamespace(data=[
            SimpleNamespace(index=index, embedding=[0.1] * kwargs["dimensions"])
            for index in range(len(kwargs["input"]))
        ])),
        responses=SimpleNamespace(create=respond),
        close=lambda: None,
    )
    monkeypatch.setattr("app.main.OpenAI", lambda **_: fake_client)
    live_settings = replace(settings, mode="openai", openai_api_key="test-key")
    with TestClient(create_app(live_settings)) as app_client:
        for filename, content in [
            ("superseded.txt", b"Obtain approval above EUR 500."),
            ("active.txt", QUOTE.encode()),
        ]:
            upload = app_client.post("/api/documents", files={"file": (filename, content, "text/plain")})
            assert upload.status_code == 201
        result = app_client.post("/api/repair-checklist", json={
            "scenario": SCENARIO, "document_ids": [upload.json()["document"]["id"]],
        })
        assert result.status_code == 200
        assert app_client.post("/api/repair-checklist", json={"scenario": SCENARIO}).status_code == 422

    assert [item["filename"] for item in seen_payloads[0]["procedures"]] == ["active.txt"]
    response = result.json()
    assert response["requirements"][0]["citation"] == {
        "filename": "active.txt", "page": 1, "quote": QUOTE, "revision": None,
    }
    assert "Does the insurer require a VIN photo?" in response["manual_checks"]
    assert "Which documents are required for this case?" in response["manual_checks"]
