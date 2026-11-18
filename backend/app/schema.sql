CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id uuid PRIMARY KEY,
    filename text NOT NULL,
    checksum text NOT NULL,
    embedding_space text NOT NULL,
    byte_size integer NOT NULL,
    chunk_count integer NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (checksum, embedding_space)
);

CREATE TABLE IF NOT EXISTS chunks (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index integer NOT NULL,
    page integer NOT NULL,
    content text NOT NULL,
    embedding vector(384) NOT NULL,
    UNIQUE (document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS chunks_document_id_idx ON chunks(document_id);
