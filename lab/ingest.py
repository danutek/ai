#!/usr/bin/env python3
"""Ingest the monograph markdown chapters into PostgreSQL + pgvector."""

from __future__ import annotations

import argparse
import os
import pathlib
import sys

LAB_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(LAB_DIR))

from chunker import load_all_chunks
from embeddings import LocalEmbedder, vec_to_pg_literal

DEFAULT_DB = os.environ.get("DATABASE_URL", "postgresql://localhost:5432/danutek")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest monograph docs into PostgreSQL + pgvector.")
    parser.add_argument("--db", default=DEFAULT_DB, help=f"PostgreSQL connection URL (default: {DEFAULT_DB})")
    parser.add_argument(
        "--backend",
        choices=["auto", "fastembed", "lsa"],
        default="auto",
        help="Embedding backend ('auto' uses fastembed if installed, else zero-dep 'lsa').",
    )
    parser.add_argument("--dry-run", action="store_true", help="Chunk and embed without connecting to Postgres.")
    parser.add_argument("--reset", action="store_true", help="Truncate chunks table before inserting.")
    args = parser.parse_args()

    chunks = load_all_chunks()
    embedder = LocalEmbedder(backend=args.backend)

    # Include chapter & section context in the text we embed so vectors carry structural grounding
    embed_inputs = [
        f"{c.chapter_title} — {c.section_heading}\n\n{c.content}" for c in chunks
    ]
    print(f"Loaded {len(chunks)} chunks across {len({c.source_file for c in chunks})} documents.")
    print(f"Computing 384-dim embeddings using backend: {embedder.backend}...")
    vectors = embedder.embed_documents(embed_inputs)

    if args.dry_run:
        print("Dry-run complete! Sample chunks:")
        for c in chunks[:5]:
            print(f"  [{c.chapter_num}] {c.section_heading} ({c.word_count}w) thinkers={c.thinkers} themes={c.themes}")
        return

    import psycopg

    schema_sql = (LAB_DIR / "schema.sql").read_text(encoding="utf-8")
    with psycopg.connect(args.db, autocommit=True) as conn:
        conn.execute(schema_sql)
        if args.reset:
            conn.execute("TRUNCATE TABLE chunks RESTART IDENTITY;")

        with conn.cursor() as cur:
            for c, vec in zip(chunks, vectors):
                cur.execute(
                    """
                    INSERT INTO chunks (
                        source_file, chapter_num, chapter_title, section_heading,
                        chunk_index, content, word_count, thinkers, themes,
                        embed_backend, embedding
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
                    ON CONFLICT (source_file, chunk_index) DO UPDATE SET
                        chapter_title   = EXCLUDED.chapter_title,
                        section_heading = EXCLUDED.section_heading,
                        content         = EXCLUDED.content,
                        word_count      = EXCLUDED.word_count,
                        thinkers        = EXCLUDED.thinkers,
                        themes          = EXCLUDED.themes,
                        embed_backend   = EXCLUDED.embed_backend,
                        embedding       = EXCLUDED.embedding,
                        created_at      = NOW();
                    """,
                    (
                        c.source_file,
                        c.chapter_num,
                        c.chapter_title,
                        c.section_heading,
                        c.chunk_index,
                        c.content,
                        c.word_count,
                        c.thinkers,
                        c.themes,
                        embedder.backend,
                        vec_to_pg_literal(vec),
                    ),
                )

        total = conn.execute("SELECT COUNT(*) FROM chunks;").fetchone()[0]
        print(f"Ingested {len(chunks)} chunks into Postgres ({total} total rows in 'chunks').")


if __name__ == "__main__":
    main()
