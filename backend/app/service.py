import time
from uuid import UUID

from app.answers import REFUSAL, extractive_answer, generated_answer
from app.config import Settings
from app.documents import checksum, chunk_pages, extract_pages, safe_filename
from app.embeddings import tokens
from app.schemas import Answer, Question, Source


class Assistant:
    def __init__(self, repository, embedder, settings: Settings, client=None):
        self.repository = repository
        self.embedder = embedder
        self.settings = settings
        self.client = client

    def ingest(self, filename: str, data: bytes):
        filename = safe_filename(filename)
        pages = extract_pages(filename, data, self.settings)
        chunks = chunk_pages(pages)
        vectors = self.embedder.embed([chunk.text for chunk in chunks])
        return self.repository.insert(
            filename, checksum(data), self.embedder.space, len(data), chunks, vectors,
        )

    def retrieve(self, text: str, document_ids: list[UUID], top_k: int) -> list[Source]:
        vector = self.embedder.embed([text])[0]
        # pgvector cosine distance is undefined for zero vectors.
        if not any(vector):
            return []
        hits = self.repository.search(
            vector, self.embedder.space, document_ids, top_k * 3,
        )
        query_tokens = set(tokens(text))
        hits = [
            hit for hit in hits
            if hit["score"] >= self.settings.min_score
            and (self.settings.mode != "demo" or query_tokens.intersection(tokens(hit["content"])))
        ][:top_k]
        return [
            Source(
                id=index, chunk_id=hit["chunk_id"], document_id=hit["document_id"],
                filename=hit["filename"], page=hit["page"], chunk_index=hit["chunk_index"],
                text=hit["content"], score=round(hit["score"], 4),
            )
            for index, hit in enumerate(hits, 1)
        ]

    def ask(self, question: Question) -> Answer:
        started = time.perf_counter()
        sources = self.retrieve(question.question, question.document_ids, question.top_k)
        if not sources:
            answer, sources, refused = REFUSAL, [], True
        elif self.settings.mode == "openai":
            answer, sources, refused = generated_answer(
                self.client, self.settings.answer_model, question.question, sources,
            )
        else:
            answer, sources, refused = extractive_answer(question.question, sources)
        return Answer(
            answer=answer, sources=sources, mode=self.settings.mode, refused=refused,
            elapsed_ms=round((time.perf_counter() - started) * 1000),
        )
