from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Document(BaseModel):
    id: UUID
    filename: str
    byte_size: int
    chunk_count: int
    created_at: datetime


class UploadResult(BaseModel):
    document: Document
    created: bool


class Question(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=3, max_length=2000)
    document_ids: list[UUID] = Field(default_factory=list, max_length=20)
    top_k: int = Field(default=3, ge=1, le=8)


class Source(BaseModel):
    id: int
    chunk_id: int
    document_id: UUID
    filename: str
    page: int
    chunk_index: int
    text: str
    score: float


class Answer(BaseModel):
    answer: str
    sources: list[Source]
    mode: Literal["demo", "openai"]
    refused: bool
    elapsed_ms: int
