#!/usr/bin/env python3
"""Topological & RAG Explorer for PostgreSQL + pgvector.

Experiments:
  search     — Hybrid Geometry A (SQL filters) + Geometry B (cosine proximity) search
  collisions — 1D Projection Collision Detector across distinct chapters (Chapter VIII)
  bridges    — Hidden Homology Finder between any two chapters (e.g. Prologue '00' <-> '10')
  axis       — Concept Axis / Vector Arithmetic: centroid(A) - centroid(B) (e.g. derrida vs jameson)
  map        — Project the 384-dim monograph manifold to a 2D PCA SVG map
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import random
import sys

LAB_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(LAB_DIR))

from embeddings import LocalEmbedder, l2_normalize, vec_to_pg_literal

DEFAULT_DB = os.environ.get("DATABASE_URL", "postgresql://localhost:5432/danutek")


def snippet(text: str, limit: int = 210) -> str:
    clean = " ".join(text.split())
    return clean if len(clean) <= limit else clean[: limit - 1] + "…"


def parse_pg_vec(raw: str) -> list[float]:
    return [float(x) for x in raw.strip("[]").split(",")]


def detect_db_backend(conn) -> str:
    row = conn.execute("SELECT embed_backend FROM chunks LIMIT 1;").fetchone()
    if not row:
        raise SystemExit("No chunks found in database. Run `python3 lab/ingest.py` first.")
    return row[0]


def make_query_embedder(conn, backend_override: str | None = None) -> LocalEmbedder:
    backend = backend_override or detect_db_backend(conn)
    embedder = LocalEmbedder(backend=backend)
    if embedder.backend == "lsa":
        rows = conn.execute("SELECT chapter_title || ' — ' || section_heading || E'\n\n' || content FROM chunks;").fetchall()
        embedder.fit_corpus([r[0] for r in rows])
    return embedder


# ---------------------------------------------------------------------------
# Experiment 1: Hybrid Search (Geometry A + Geometry B)
# ---------------------------------------------------------------------------
def cmd_search(conn, args) -> None:
    embedder = make_query_embedder(conn)
    qvec = vec_to_pg_literal(embedder.embed_query(args.query))

    where = []
    params: list = [qvec]
    filters_meta = {}
    if args.chapter:
        where.append("chapter_num = %s")
        params.append(args.chapter)
        filters_meta["chapter"] = args.chapter
    if args.thinker:
        where.append("%s = ANY(thinkers)")
        params.append(args.thinker.lower())
        filters_meta["thinker"] = args.thinker.lower()
    if args.theme:
        where.append("%s = ANY(themes)")
        params.append(args.theme.lower())
        filters_meta["theme"] = args.theme.lower()

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    params.extend([qvec, args.top])

    rows = conn.execute(
        f"""
        SELECT id, chapter_num, section_heading, thinkers, themes, content,
               1 - (embedding <=> %s::vector) AS similarity,
               embedding <=> %s::vector AS distance
        FROM chunks
        {where_sql}
        ORDER BY distance ASC
        LIMIT %s;
        """,
        params,
    ).fetchall()

    if not rows:
        print("No matching chunks found for those filters.")
        return

    # Log to the Courtroom of History (diachronic audit trail)
    conn.execute(
        "INSERT INTO query_log (query_text, filters, top_chunk_ids, top_distances) VALUES (%s, %s::jsonb, %s, %s);",
        (args.query, json.dumps(filters_meta), [r[0] for r in rows], [float(r[7]) for r in rows]),
    )

    print(f"\nQuery: {args.query!r}  (backend={embedder.backend}, filters={filters_meta or 'none'})\n")
    for rank, (cid, ch, sec, thinkers, themes, content, sim, dist) in enumerate(rows, 1):
        print(f"  {rank}. [Ch {ch}] {sec}   (cos_sim={sim:.4f}, id={cid})")
        print(f"     tags: thinkers={thinkers}  themes={themes}")
        print(f"     {snippet(content)}\n")


# ---------------------------------------------------------------------------
# Experiment 2: 1D Projection Collision Detector (Chapter VIII)
# ---------------------------------------------------------------------------
def cmd_collisions(conn, args) -> None:
    embedder = make_query_embedder(conn)
    qvec = vec_to_pg_literal(embedder.embed_query(args.word))

    # Best chunk per distinct chapter near this single 1D signifier
    rows = conn.execute(
        """
        SELECT DISTINCT ON (chapter_num)
               chapter_num, chapter_title, section_heading, content,
               1 - (embedding <=> %s::vector) AS similarity
        FROM chunks
        ORDER BY chapter_num, embedding <=> %s::vector ASC;
        """,
        (qvec, qvec),
    ).fetchall()

    rows.sort(key=lambda r: r[4], reverse=True)
    top_rows = rows[: args.top]

    print(f"\n1D Signifier Collision Audit: {args.word!r}")
    print("Distinct chapters whose latent regions project near this single word:\n")
    for rank, (ch, title, sec, content, sim) in enumerate(top_rows, 1):
        print(f"  {rank}. [Ch {ch:>8}] cos_sim={sim:.4f} — {sec}")
        print(f"     {snippet(content, 175)}\n")


# ---------------------------------------------------------------------------
# Experiment 3: Cross-Chapter Hidden Homology Finder
# ---------------------------------------------------------------------------
def cmd_bridges(conn, args) -> None:
    rows = conn.execute(
        """
        SELECT a.section_heading, a.content,
               b.section_heading, b.content,
               1 - (a.embedding <=> b.embedding) AS similarity
        FROM chunks a
        JOIN chunks b ON a.chapter_num = %s AND b.chapter_num = %s
        ORDER BY a.embedding <=> b.embedding ASC
        LIMIT %s;
        """,
        (args.chapter_a, args.chapter_b, args.top),
    ).fetchall()

    if not rows:
        print(f"No chunks found for chapters {args.chapter_a!r} and {args.chapter_b!r}.")
        return

    print(f"\nClosest Semantic Bridges: Chapter {args.chapter_a}  ↔  Chapter {args.chapter_b}\n")
    for rank, (sa, ca, sb, cb, sim) in enumerate(rows, 1):
        print(f"  {rank}. cos_sim={sim:.4f}")
        print(f"     [Ch {args.chapter_a}] {sa}: {snippet(ca, 150)}")
        print(f"     [Ch {args.chapter_b}] {sb}: {snippet(cb, 150)}\n")


# ---------------------------------------------------------------------------
# Experiment 4: Concept Axis / Vector Arithmetic (centroid(A) - centroid(B))
# ---------------------------------------------------------------------------
def _centroid_for_tag(conn, tag: str) -> list[float]:
    t = tag.lower()
    row = conn.execute(
        """
        SELECT AVG(embedding)::text, COUNT(*)
        FROM chunks
        WHERE %s = ANY(thinkers) OR %s = ANY(themes) OR chapter_num = %s;
        """,
        (t, t, t),
    ).fetchone()
    if not row or not row[0] or row[1] == 0:
        raise SystemExit(f"No chunks matched tag/chapter {tag!r}.")
    print(f"  Centroid({tag!r}) computed from {row[1]} chunks.")
    return l2_normalize(parse_pg_vec(row[0]))


def cmd_axis(conn, args) -> None:
    print(f"\nComputing Philosophical Axis:  {args.pole_a}  ←————→  {args.pole_b}")
    va = _centroid_for_tag(conn, args.pole_a)
    vb = _centroid_for_tag(conn, args.pole_b)
    axis = l2_normalize([a - b for a, b in zip(va, vb)])

    rows = conn.execute(
        "SELECT chapter_num, section_heading, content, embedding::text FROM chunks;"
    ).fetchall()

    scored = []
    for ch, sec, content, emb_raw in rows:
        v = parse_pg_vec(emb_raw)
        proj = sum(x * y for x, y in zip(v, axis))
        scored.append((proj, ch, sec, content))

    scored.sort(key=lambda item: item[0], reverse=True)

    print(f"\n  ▲ Strongest toward [{args.pole_a.upper()}]:")
    for proj, ch, sec, content in scored[: args.top]:
        print(f"    +{proj:.4f}  [Ch {ch:>8}] {sec} — {snippet(content, 120)}")

    print(f"\n  ▼ Strongest toward [{args.pole_b.upper()}]:")
    for proj, ch, sec, content in scored[-args.top :][::-1]:
        print(f"    {proj:.4f}  [Ch {ch:>8}] {sec} — {snippet(content, 120)}")

    # Midpoint passages sitting closest to 0.0 (dialectical synthesis!)
    mid = sorted(scored, key=lambda item: abs(item[0]))[: args.top]
    print(f"\n  ◆ Dialectical Midpoint (nearest 0.0 between {args.pole_a} & {args.pole_b}):")
    for proj, ch, sec, content in mid:
        print(f"    {proj:+.4f}  [Ch {ch:>8}] {sec} — {snippet(content, 120)}")
    print()


# ---------------------------------------------------------------------------
# Experiment 5: Pure-Python 2D PCA Topology Map -> SVG
# ---------------------------------------------------------------------------
def _power_iteration(X: list[list[float]], iters: int = 40, seed: int = 42) -> list[float]:
    rng = random.Random(seed)
    d = len(X[0])
    v = l2_normalize([rng.gauss(0, 1) for _ in range(d)])
    for _ in range(iters):
        # Compute X^T (X v)
        xv = [sum(row[j] * v[j] for j in range(d)) for row in X]
        nxt = [0.0] * d
        for row, coeff in zip(X, xv):
            for j in range(d):
                nxt[j] += row[j] * coeff
        v = l2_normalize(nxt)
    return v


def pca_2d(vectors: list[list[float]]) -> list[tuple[float, float]]:
    n = len(vectors)
    d = len(vectors[0])
    mean = [sum(v[j] for v in vectors) / n for j in range(d)]
    centered = [[v[j] - mean[j] for j in range(d)] for v in vectors]

    pc1 = _power_iteration(centered, iters=45, seed=7)
    # Deflate along pc1
    deflated = []
    for row in centered:
        dot = sum(row[j] * pc1[j] for j in range(d))
        deflated.append([row[j] - dot * pc1[j] for j in range(d)])
    pc2 = _power_iteration(deflated, iters=45, seed=13)

    coords = []
    for row in centered:
        x = sum(row[j] * pc1[j] for j in range(d))
        y = sum(row[j] * pc2[j] for j in range(d))
        coords.append((x, y))
    return coords


CHAPTER_COLORS = {
    "00": "#fbbf24",        # Frogner Park Prologue (gold)
    "01": "#60a5fa",        # I. Derrida
    "02": "#38bdf8",        # II. Positive Geometries
    "03": "#f97316",        # III. Jameson's Real
    "04": "#a78bfa",        # IV. Metamorphosis
    "05": "#34d399",        # V. Riemann Proof
    "06": "#fb7185",        # VI. Desire
    "07": "#22d3ee",        # VII. Geometric Turn
    "08": "#e879f9",        # VIII. Synchronic/Diachronic
    "09": "#f43f5e",        # IX. Beyond 1D Aperture
    "10": "#4ade80",        # X. Topology of Sanity
    "protocol": "#94a3b8",  # Living Protocol
}

CHAPTER_SHORT = {
    "00": "Prologue (Frogner Park)",
    "01": "I. Derrida",
    "02": "II. Positive Geometries",
    "03": "III. Jameson's Real",
    "04": "IV. Metamorphosis",
    "05": "V. Riemann Proof",
    "06": "VI. Desire & Drive",
    "07": "VII. Geometric Turn",
    "08": "VIII. Synchronic/Diachronic",
    "09": "IX. Beyond 1D Aperture",
    "10": "X. Topology of Sanity",
    "protocol": "Living Protocol",
}


def render_topology_svg(rows: list[tuple[str, str, list[float]]], out_path: pathlib.Path, backend: str) -> None:
    vecs = [r[2] for r in rows]
    coords = pca_2d(vecs)

    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    W, H = 1120, 740
    pad_l, pad_r, pad_t, pad_b = 70, 270, 95, 65

    def to_px(x: float, y: float) -> tuple[float, float]:
        nx = (x - min_x) / (max_x - min_x + 1e-9)
        ny = (y - min_y) / (max_y - min_y + 1e-9)
        return pad_l + nx * (W - pad_l - pad_r), H - pad_b - ny * (H - pad_t - pad_b)

    # Group by chapter for centroids
    by_ch: dict[str, list[tuple[float, float]]] = {}
    dots_svg = []
    for (ch, sec, _), (x, y) in zip(rows, coords):
        px, py = to_px(x, y)
        col = CHAPTER_COLORS.get(ch, "#cbd5e1")
        by_ch.setdefault(ch, []).append((px, py))
        safe_title = f"[Ch {ch}] {sec}".replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        dots_svg.append(
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="5.2" fill="{col}" fill-opacity="0.72" '
            f'stroke="#0d1117" stroke-width="0.9"><title>{safe_title}</title></circle>'
        )

    centroids_svg = []
    legend_svg = []
    for idx, ch in enumerate(sorted(by_ch.keys())):
        pts = by_ch[ch]
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        col = CHAPTER_COLORS.get(ch, "#cbd5e1")
        label = CHAPTER_SHORT.get(ch, ch).replace("&", "&amp;")
        centroids_svg.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="11" fill="{col}" fill-opacity="0.18" stroke="{col}" stroke-width="1.6"/>'
            f'<text x="{cx:.1f}" y="{cy - 14:.1f}" text-anchor="middle" fill="{col}" font-size="11.5" font-weight="700">{ch}</text>'
        )
        ly = 128 + idx * 28
        legend_svg.append(
            f'<circle cx="888" cy="{ly - 4}" r="5.5" fill="{col}"/>'
            f'<text x="902" y="{ly}" fill="#c9d1d9" font-size="12">{label} ({len(pts)})</text>'
        )

    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}"
     style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;">
  <rect width="{W}" height="{H}" fill="#0d1117"/>
  <rect x="20" y="20" width="{W - 40}" height="{H - 40}" rx="14" fill="#161b22" stroke="#30363d"/>
  <text x="48" y="56" fill="#f0f6fc" font-size="20" font-weight="700">Monograph Latent Topology (2D PCA Projection of 384-dim pgvector Space)</text>
  <text x="48" y="78" fill="#8b949e" font-size="12.5">{len(rows)} chunks across {len(by_ch)} chapters · backend={backend} · ringed nodes show chapter centroids</text>

  <!-- Plot frame -->
  <rect x="{pad_l - 16}" y="{pad_t - 10}" width="{W - pad_l - pad_r + 32}" height="{H - pad_t - pad_b + 20}" rx="8" fill="#0d1117" stroke="#21262d"/>
  <text x="{(pad_l + W - pad_r) / 2:.1f}" y="{H - 30}" text-anchor="middle" fill="#6e7681" font-size="11">Principal Axis 1 (PC1)</text>
  <text x="38" y="{(pad_t + H - pad_b) / 2:.1f}" text-anchor="middle" fill="#6e7681" font-size="11" transform="rotate(-90 38 {(pad_t + H - pad_b) / 2:.1f})">Principal Axis 2 (PC2)</text>

  {''.join(dots_svg)}
  {''.join(centroids_svg)}

  <!-- Legend -->
  <text x="880" y="102" fill="#f0f6fc" font-size="13" font-weight="700">Chapters</text>
  {''.join(legend_svg)}
</svg>
"""
    out_path.write_text(svg, encoding="utf-8")
    print(f"Wrote 2D PCA topology map ({len(rows)} chunks) -> {out_path}")


def cmd_map(conn, args) -> None:
    backend = detect_db_backend(conn)
    db_rows = conn.execute(
        "SELECT chapter_num, section_heading, embedding::text FROM chunks ORDER BY chapter_num, chunk_index;"
    ).fetchall()
    parsed = [(ch, sec, parse_pg_vec(emb)) for ch, sec, emb in db_rows]
    render_topology_svg(parsed, pathlib.Path(args.out), backend=backend)


def main() -> None:
    parser = argparse.ArgumentParser(description="Explore the monograph's latent topology in PostgreSQL + pgvector.")
    parser.add_argument("--db", default=DEFAULT_DB, help=f"PostgreSQL connection URL (default: {DEFAULT_DB})")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_search = sub.add_parser("search", help="Hybrid SQL + cosine vector search")
    p_search.add_argument("query", help="Natural-language query")
    p_search.add_argument("--chapter", help="Filter by chapter_num (e.g., 00, 03, 10, protocol)")
    p_search.add_argument("--thinker", help="Filter by thinker tag (e.g., derrida, jameson, lacan)")
    p_search.add_argument("--theme", help="Filter by theme tag (e.g., geometry, desire, real, sanity)")
    p_search.add_argument("--top", type=int, default=5)

    p_col = sub.add_parser("collisions", help="Find distinct chapters colliding near a 1D signifier")
    p_col.add_argument("word", help="Single word or concept (e.g., trace, desire, refusal, center)")
    p_col.add_argument("--top", type=int, default=6)

    p_br = sub.add_parser("bridges", help="Find closest cross-chapter semantic homologies")
    p_br.add_argument("chapter_a", help="First chapter_num (e.g., 00)")
    p_br.add_argument("chapter_b", help="Second chapter_num (e.g., 10)")
    p_br.add_argument("--top", type=int, default=5)

    p_ax = sub.add_parser("axis", help="Compute vector axis centroid(A) - centroid(B)")
    p_ax.add_argument("pole_a", help="First thinker/theme/chapter (e.g., derrida)")
    p_ax.add_argument("pole_b", help="Second thinker/theme/chapter (e.g., jameson)")
    p_ax.add_argument("--top", type=int, default=3)

    p_map = sub.add_parser("map", help="Project 384-dim pgvector space into a 2D PCA SVG map")
    p_map.add_argument("--out", default=str(LAB_DIR / "monograph_topology.svg"))

    args = parser.parse_args()

    import psycopg

    with psycopg.connect(args.db, autocommit=True) as conn:
        if args.cmd == "search":
            cmd_search(conn, args)
        elif args.cmd == "collisions":
            cmd_collisions(conn, args)
        elif args.cmd == "bridges":
            cmd_bridges(conn, args)
        elif args.cmd == "axis":
            cmd_axis(conn, args)
        elif args.cmd == "map":
            cmd_map(conn, args)


if __name__ == "__main__":
    main()
