# Topological & RAG Lab (`PostgreSQL + pgvector`)

This lab turns *The Species of the Non-Species* (Prologue, Chapters I–X, and Living Protocol) into an **explicit, queryable 384-dimensional synchronic manifold** inside PostgreSQL + `pgvector`.

In the vocabulary of the monograph, this is **Microscope 1 (Macro-Topology of Traces)**: it lets you pair **Geometry A** (exact SQL symbolic predicates on chapters, thinkers, and themes) with **Geometry B** (continuous cosine proximity in $\mathbb{R}^{384}$), inspect 1D signifier collisions, measure concept axes via vector arithmetic, and visualize the monograph’s actual latent geometry.

---

## 1. Quickstart Setup

### Step 1: Database Connection
By default, the lab connects to `postgresql://localhost:5432/danutek` (with `pgvector` enabled). You can override it anytime via `DATABASE_URL` or `--db`:

```bash
export DATABASE_URL="postgresql://localhost:5432/danutek"
```

### Step 2: Install Dependencies
`psycopg[binary]` is required for Postgres. Installing **`fastembed`** (~50MB ONNX runtime, zero PyTorch bloat) gives you real local 384-dim neural embeddings (`BAAI/bge-small-en-v1.5`) running entirely on your Mac:

```bash
python3 -m pip install -r lab/requirements.txt
```

*(If you want to test the pipeline offline before installing `fastembed`, `ingest.py` automatically falls back to a deterministic zero-dependency `lsa` 384-dim backend—though `fastembed` produces far richer semantic topology.)*

### Step 3: Ingest the Monograph

```bash
python3 lab/ingest.py --reset
```

---

## 2. Five Topological Experiments

### 1. Hybrid Search (Geometry A + Geometry B)
Combine exact symbolic filters (`--thinker`, `--theme`, `--chapter`) with continuous cosine similarity:

```bash
python3 lab/explore.py search "mistaking the map for the cosmos"
python3 lab/explore.py search "material labor hidden under timeless form" --thinker jameson
python3 lab/explore.py search "thin walls around desire" --chapter 07
```

Every search is also recorded in the `query_log` table (*the Courtroom of History*).

### 2. 1D Projection Collision Detector ([Chapter VIII](../docs/08-synchronic-manifolds-and-diachronic-projections.md))
See which distinct chapters collide closest to a single overloaded 1D signifier:

```bash
python3 lab/explore.py collisions "trace"
python3 lab/explore.py collisions "refusal"
python3 lab/explore.py collisions "desire"
```

### 3. Hidden Homologies Across Chapters
Find the closest semantic bridges between any two chapters—for example, between the **Frogner Park Prologue (`00`)** and **Chapter X: The Topology of Sanity (`10`)**:

```bash
python3 lab/explore.py bridges 00 10
python3 lab/explore.py bridges 02 06
```

### 4. Concept Axes via Vector Arithmetic
Compute `centroid(A) - centroid(B)` directly via Postgres `AVG(embedding)`, then inspect which passages sit at the two extreme poles and which sit right at the **dialectical midpoint (`0.0`)**:

```bash
python3 lab/explore.py axis derrida jameson
python3 lab/explore.py axis geometry real
python3 lab/explore.py axis desire sanity
```

### 5. Visualize the Monograph’s Latent Topology (2D PCA Map)
Project all 384-dim chunks from `pgvector` down to a 2D PCA SVG scatter plot with chapter centroids:

```bash
python3 lab/explore.py map --out lab/monograph_topology.svg
```

---

## 3. Raw `pgvector` SQL Queries to Try in `psql`

You can also query the manifold directly in SQL:

```sql
-- 1. Check chunk counts per chapter and embedding backend
SELECT chapter_num, embed_backend, COUNT(*) AS chunks
FROM chunks
GROUP BY chapter_num, embed_backend
ORDER BY chapter_num;

-- 2. Find the two most geometrically distant chunks in the entire monograph
SELECT a.chapter_num AS ch_a, a.section_heading AS sec_a,
       b.chapter_num AS ch_b, b.section_heading AS sec_b,
       ROUND((a.embedding <=> b.embedding)::numeric, 4) AS cosine_distance
FROM chunks a
JOIN chunks b ON a.id < b.id
ORDER BY cosine_distance DESC
LIMIT 5;

-- 3. Compute the geometric centroid of the entire project and find the single most "central" passage
WITH center AS (SELECT AVG(embedding) AS c FROM chunks)
SELECT chapter_num, section_heading,
       ROUND((1 - (embedding <=> center.c))::numeric, 4) AS centrality
FROM chunks, center
ORDER BY embedding <=> center.c ASC
LIMIT 5;
```

---

[← Back to README](../README.md)
