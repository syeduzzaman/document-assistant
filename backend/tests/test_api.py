from app.embeddings import DemoEmbedder
from app.repository import Repository


def upload(client, name="policy.txt", content=b"Employees receive 30 days of annual leave."):
    return client.post("/api/documents", files={"file": (name, content, "text/plain")})


def test_upload_retrieve_and_delete(client):
    response = upload(client)
    assert response.status_code == 201
    document = response.json()["document"]
    answer = client.post("/api/ask", json={"question": "How many days of annual leave do employees receive?"}).json()
    assert not answer["refused"] and "30 days" in answer["answer"]
    assert answer["sources"][0]["document_id"] == document["id"]
    assert answer["sources"][0]["page"] == 1
    assert "30 days" in answer["sources"][0]["text"]
    assert client.delete("/api/documents/" + document["id"]).status_code == 204
    assert client.get("/api/documents").json() == []
    assert client.post("/api/ask", json={"question": "Annual leave days?"}).json()["refused"]


def test_duplicate_upload_is_idempotent(client):
    first = upload(client).json()
    second = upload(client)
    assert second.status_code == 200 and not second.json()["created"]
    assert first["document"]["id"] == second.json()["document"]["id"]
    assert len(client.get("/api/documents").json()) == 1


def test_question_filter_cannot_retrieve_other_documents(client):
    leave = upload(client).json()["document"]
    upload(client, "backups.txt", b"Database backups run every night at 02:00 UTC.")
    response = client.post("/api/ask", json={
        "question": "Database backups?", "document_ids": [leave["id"]],
    }).json()
    assert response["refused"] and not response["sources"]


def test_embedding_spaces_are_isolated(client, settings):
    upload(client)
    repository = Repository(settings.database_url)
    assert repository.list_documents("different-model") == []
    assert repository.search(DemoEmbedder().embed(["annual leave"])[0], "different-model", [], 3) == []


def test_unknown_question_is_refused(sample_client):
    result = sample_client.post("/api/ask", json={"question": "Which astronauts visited Jupiter?"}).json()
    assert result["refused"] and not result["sources"]


def test_request_validation(client):
    assert client.post("/api/ask", json={"question": "  "}).status_code == 422
    assert client.post("/api/ask", json={"question": "Annual leave", "top_k": 100}).status_code == 422
    assert client.delete("/api/documents/not-a-uuid").status_code == 422
    assert upload(client, "malware.exe").status_code == 422


def test_health_reports_active_mode(client):
    health = client.get("/api/health").json()
    assert health["status"] == "ok" and health["mode"] == "demo"
