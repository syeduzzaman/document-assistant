import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str = "postgresql://assistant:assistant@localhost:5432/assistant"
    mode: str = "demo"
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    answer_model: str = "gpt-4.1-mini"
    seed_samples: bool = True
    samples_dir: Path = Path(__file__).resolve().parents[2] / "sample-documents"
    max_upload_bytes: int = 10 * 1024 * 1024
    max_pages: int = 40
    max_characters: int = 300_000
    min_score: float = 0.16

    @classmethod
    def from_env(cls) -> "Settings":
        settings = cls(
            database_url=os.getenv("DATABASE_URL", cls.database_url),
            mode=os.getenv("RAG_MODE", "demo"),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            answer_model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4.1-mini"),
            seed_samples=os.getenv("SEED_SAMPLE_DOCS", "true").lower() == "true",
            samples_dir=Path(os.getenv("SAMPLES_DIR", str(cls.samples_dir))),
        )
        if settings.mode not in {"demo", "openai"}:
            raise ValueError("RAG_MODE must be demo or openai.")
        if settings.mode == "openai" and not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for openai mode.")
        return settings
