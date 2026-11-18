import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.repository import Repository


@pytest.fixture
def settings():
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to a dedicated PostgreSQL/pgvector test database.")
    return Settings(database_url=database_url, seed_samples=False)


@pytest.fixture
def client(settings):
    repository = Repository(settings.database_url)
    repository.initialize()
    # TEST_DATABASE_URL must point to a disposable database, never the development database.
    with repository.connect() as connection:
        connection.execute("TRUNCATE documents CASCADE")
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def sample_client(client):
    samples = Path(__file__).resolve().parents[2] / "sample-documents"
    for path in sorted(samples.glob("*.md")):
        response = client.post("/api/documents", files={"file": (path.name, path.read_bytes(), "text/markdown")})
        assert response.status_code == 201
    return client
