from pathlib import Path
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from app.documents import Chunk
from app.embeddings import vector_literal


class Repository:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def connect(self):
        return psycopg.connect(self.database_url, row_factory=dict_row, connect_timeout=5)

    def initialize(self):
        with self.connect() as connection:
            connection.execute(Path(__file__).with_name("schema.sql").read_text())

    def ping(self):
        with self.connect() as connection:
            connection.execute("SELECT 1")

    def list_documents(self, space: str):
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM documents WHERE embedding_space = %s ORDER BY created_at DESC",
                (space,),
            ).fetchall()

    def insert(self, filename: str, digest: str, space: str, byte_size: int,
               chunks: list[Chunk], vectors: list[list[float]]):
        with self.connect() as connection:
            document = connection.execute(
                """INSERT INTO documents (id, filename, checksum, embedding_space, byte_size, chunk_count)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (checksum, embedding_space) DO NOTHING RETURNING *""",
                (uuid4(), filename, digest, space, byte_size, len(chunks)),
            ).fetchone()
            if document is None:
                return connection.execute(
                    "SELECT * FROM documents WHERE checksum = %s AND embedding_space = %s",
                    (digest, space),
                ).fetchone(), False
            with connection.cursor() as cursor:
                cursor.executemany(
                    """INSERT INTO chunks (document_id, chunk_index, page, content, embedding)
                    VALUES (%s, %s, %s, %s, %s::vector)""",
                    [(document["id"], chunk.index, chunk.page, chunk.text, vector_literal(vector))
                     for chunk, vector in zip(chunks, vectors, strict=True)],
                )
            return document, True

    def delete(self, document_id: UUID) -> bool:
        with self.connect() as connection:
            result = connection.execute("DELETE FROM documents WHERE id = %s", (document_id,))
            return result.rowcount > 0

    def search(self, vector: list[float], space: str, document_ids: list[UUID], limit: int):
        literal = vector_literal(vector)
        with self.connect() as connection:
            return connection.execute(
                """SELECT c.id AS chunk_id, d.id AS document_id, d.filename, c.page,
                c.chunk_index, c.content, 1 - (c.embedding <=> %s::vector) AS score
                FROM chunks c JOIN documents d ON d.id = c.document_id
                WHERE d.embedding_space = %s
                AND (cardinality(%s::uuid[]) = 0 OR d.id = ANY(%s::uuid[]))
                ORDER BY c.embedding <=> %s::vector, c.id
                LIMIT %s""",
                (literal, space, document_ids, document_ids, literal, limit),
            ).fetchall()
