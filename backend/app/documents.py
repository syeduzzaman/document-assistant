import hashlib
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from app.config import Settings

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


class DocumentError(ValueError):
    pass


@dataclass(frozen=True)
class Chunk:
    text: str
    page: int
    index: int


def extract_pages(filename: str, data: bytes, settings: Settings) -> list[tuple[int, str]]:
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise DocumentError("Upload a PDF, TXT or Markdown file.")
    if not data:
        raise DocumentError("The file is empty.")
    if len(data) > settings.max_upload_bytes:
        raise DocumentError("The file exceeds the 10 MiB upload limit.")
    if extension == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise DocumentError("This file does not contain a valid PDF header.")
        try:
            reader = PdfReader(BytesIO(data))
            if reader.is_encrypted:
                raise DocumentError("Encrypted PDFs are not supported.")
            if len(reader.pages) > settings.max_pages:
                raise DocumentError("PDFs may contain at most 40 pages.")
            pages = []
            total = 0
            for number, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ""
                total += len(text)
                if total > settings.max_characters:
                    raise DocumentError("The extracted document is too large.")
                pages.append((number, text))
        except DocumentError:
            raise
        except Exception as exc:
            raise DocumentError("The PDF could not be read.") from exc
    else:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise DocumentError("Text documents must use UTF-8 encoding.") from exc
        if "\x00" in text:
            raise DocumentError("Binary content is not supported.")
        pages = [(1, text)]
    if sum(len(text) for _, text in pages) > settings.max_characters:
        raise DocumentError("The extracted document is too large.")
    if not any(text.strip() for _, text in pages):
        raise DocumentError("No readable text found. Scanned PDFs require OCR, which is not included.")
    return pages


def chunk_pages(pages: list[tuple[int, str]], size: int = 150, overlap: int = 25) -> list[Chunk]:
    if size < 1 or not 0 <= overlap < size:
        raise ValueError("Chunk size must be positive and overlap smaller than size.")
    chunks = []
    for page, text in pages:
        # Whitespace normalization retains text and page provenance without HTML rendering.
        words = re.sub(r"\s+", " ", text).strip().split()
        for start in range(0, len(words), size - overlap):
            chunks.append(Chunk(" ".join(words[start:start + size]), page, len(chunks)))
            if start + size >= len(words):
                break
    if len(chunks) > 500:
        raise DocumentError("The document produces too many chunks.")
    return chunks


def checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_filename(filename: str) -> str:
    name = filename.replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(character for character in name if character.isprintable()).strip()
    return name[:200] or "document.txt"
