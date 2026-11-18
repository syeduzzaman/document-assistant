import logging
from contextlib import asynccontextmanager
from uuid import UUID

import psycopg
from fastapi import FastAPI, HTTPException, Response, UploadFile
from fastapi.responses import JSONResponse
from openai import APIError, OpenAI

from app.answers import ProviderError
from app.config import Settings
from app.documents import DocumentError
from app.embeddings import DemoEmbedder, OpenAIEmbedder
from app.repair import RepairCase, RepairChecklist, generate_checklist, sample_checklist
from app.repository import Repository
from app.schemas import Answer, Document, Question, UploadResult
from app.service import Assistant

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    repository = Repository(settings.database_url)
    client = (
        OpenAI(api_key=settings.openai_api_key, timeout=30.0, max_retries=1)
        if settings.mode == "openai" else None
    )
    embedder = OpenAIEmbedder(client, settings.embedding_model) if client else DemoEmbedder()
    assistant = Assistant(repository, embedder, settings, client)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        repository.initialize()
        if settings.seed_samples:
            for path in sorted(settings.samples_dir.glob("*.md")):
                assistant.ingest(path.name, path.read_bytes())
        yield
        if client:
            client.close()

    app = FastAPI(
        title="Document Assistant", version="0.1.0",
        description="Document retrieval, source citations and optional OpenAI generation.",
        lifespan=lifespan,
    )

    @app.exception_handler(DocumentError)
    async def document_error_handler(request, exc):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(ProviderError)
    async def provider_error_handler(request, exc):
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.exception_handler(APIError)
    async def api_error_handler(request, exc):
        logger.warning("OpenAI request failed: %s", type(exc).__name__)
        return JSONResponse(status_code=502, content={"detail": "The AI provider is unavailable. Try again."})

    @app.exception_handler(psycopg.Error)
    async def database_error_handler(request, exc):
        logger.error("Database request failed: %s", type(exc).__name__)
        return JSONResponse(status_code=503, content={"detail": "The document database is unavailable."})

    @app.get("/api/health")
    def health():
        repository.ping()
        return {
            "status": "ok", "mode": settings.mode, "embedding_space": embedder.space,
            "supported_types": ["pdf", "txt", "md"], "max_upload_bytes": settings.max_upload_bytes,
        }

    @app.get("/api/documents", response_model=list[Document])
    def documents():
        return repository.list_documents(embedder.space)

    @app.post("/api/documents", response_model=UploadResult, status_code=201)
    def upload(file: UploadFile, response: Response):
        try:
            data = file.file.read(settings.max_upload_bytes + 1)
            if len(data) > settings.max_upload_bytes:
                raise HTTPException(status_code=413, detail="The file exceeds the 10 MiB upload limit.")
            document, created = assistant.ingest(file.filename or "document.txt", data)
            response.status_code = 201 if created else 200
            return UploadResult(document=Document(**document), created=created)
        finally:
            file.file.close()

    @app.delete("/api/documents/{document_id}", status_code=204)
    def delete_document(document_id: UUID):
        if not repository.delete(document_id):
            raise HTTPException(status_code=404, detail="Document not found.")
        return Response(status_code=204)

    @app.post("/api/ask", response_model=Answer)
    def ask(question: Question):
        return assistant.ask(question)

    @app.get("/api/repair-checklist/sample", response_model=RepairChecklist)
    def repair_sample():
        return sample_checklist(settings.samples_dir)

    @app.post("/api/repair-checklist", response_model=RepairChecklist)
    def repair_checklist(case: RepairCase):
        if client is None:
            raise HTTPException(status_code=409, detail="Enable OpenAI mode to generate a checklist from your files.")
        sources = assistant.retrieve(
            f"{case.scenario}\nRepair estimate submission photos, documents, and approvals.",
            case.document_ids,
            top_k=8,
        )
        return generate_checklist(client, settings.answer_model, case.scenario, sources)

    return app


app = create_app()
