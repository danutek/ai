-- PostgreSQL + pgvector schema for the Topological & RAG Lab
-- Stores structure-aware chunks of "The Species of the Non-Species"
-- as queryable points in a 384-dimensional synchronic manifold.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chunks (
    id              SERIAL PRIMARY KEY,
    source_file     TEXT NOT NULL,
    chapter_num     TEXT NOT NULL,
    chapter_title   TEXT NOT NULL,
    section_heading TEXT NOT NULL,
    chunk_index     INT NOT NULL,
    content         TEXT NOT NULL,
    word_count      INT NOT NULL,
    thinkers        TEXT[] NOT NULL DEFAULT '{}',
    themes          TEXT[] NOT NULL DEFAULT '{}',
    embed_backend   TEXT NOT NULL,
    embedding       vector(384) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source_file, chunk_index)
);

-- HNSW index for fast approximate nearest-neighbor cosine search
CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw_idx
    ON chunks USING hnsw (embedding vector_cosine_ops);

-- GIN indexes for hybrid Geometry A (symbolic) + Geometry B (vector) queries
CREATE INDEX IF NOT EXISTS chunks_thinkers_gin_idx ON chunks USING gin (thinkers);
CREATE INDEX IF NOT EXISTS chunks_themes_gin_idx   ON chunks USING gin (themes);

-- Optional diachronic audit trail ("The Courtroom of History")
CREATE TABLE IF NOT EXISTS query_log (
    id              SERIAL PRIMARY KEY,
    query_text      TEXT NOT NULL,
    filters         JSONB NOT NULL DEFAULT '{}',
    top_chunk_ids   INT[] NOT NULL,
    top_distances   DOUBLE PRECISION[] NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
