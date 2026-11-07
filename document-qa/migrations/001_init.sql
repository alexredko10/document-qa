-- Schema: documents, chunks (pgvector), sessions, messages.
-- Applied by app.store.postgres.run_migrations under an advisory lock,
-- so concurrent replicas starting at once do not race.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documents (
    id           uuid PRIMARY KEY,
    title        text,
    status       text        NOT NULL CHECK (status IN ('pending', 'approved')),
    size_bytes   integer     NOT NULL CHECK (size_bytes > 0),
    chunk_count  integer     NOT NULL CHECK (chunk_count >= 0),
    created_at   timestamptz NOT NULL DEFAULT now(),
    approved_at  timestamptz
);

CREATE INDEX documents_status_idx ON documents (status, created_at DESC);

CREATE TABLE chunks (
    document_id  uuid    NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    chunk_index  integer NOT NULL,
    text         text    NOT NULL,
    embedding    vector(1024) NOT NULL,
    PRIMARY KEY (document_id, chunk_index)
);

-- Approximate nearest-neighbour index for corpus-wide search.
-- Note: HNSW applies WHERE filters after the index scan; with very selective
-- filters (one small document) pgvector >= 0.8 needs hnsw.iterative_scan to
-- guarantee top_k results. For small corpora the planner uses an exact scan.
CREATE INDEX chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops);

CREATE TABLE sessions (
    id          uuid PRIMARY KEY,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE messages (
    id              bigserial PRIMARY KEY,
    session_id      uuid  NOT NULL REFERENCES sessions (id) ON DELETE CASCADE,
    role            text  NOT NULL CHECK (role IN ('user', 'assistant')),
    content         text  NOT NULL,
    sources         jsonb NOT NULL DEFAULT '[]'::jsonb,
    model_id        text,
    prompt_version  text,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX messages_session_idx ON messages (session_id, id);
