"""Structure-aware Markdown chunker and metadata tagger for the monograph."""

from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass

DOCS_DIR = pathlib.Path(__file__).resolve().parent.parent / "docs"

THINKER_PATTERNS: dict[str, str] = {
    "husserl": r"\bhusserl\w*\b",
    "derrida": r"\bderrid\w*\b",
    "jameson": r"\bjameson\w*\b",
    "lacan": r"\blacan\w*\b",
    "saussure": r"\bsaussur\w*\b",
    "deleuze": r"\bdeleuz\w*\b|\bguattari\b",
    "hinton": r"\bhinton\b",
    "vigeland": r"\bvigeland\b|\bfrogner\b",
    "aristotle": r"\baristot\w*\b",
    "althusser": r"\balthusser\b",
}

THEME_PATTERNS: dict[str, str] = {
    "geometry": r"\bpolytop\w*\b|\bmanifold\w*\b|\bhyperplane\w*\b|\btopolog\w*\b|\bgeometr\w*\b|\binvariant\w*\b",
    "trace": r"\btrace\w*\b|\biterabilit\w*\b|\binscription\w*\b|\bdiff[eé]rance\b",
    "real": r"\bthe real\b|\babsent cause\b|\brefusal\b|\bthermodynamic\w*\b|\bsubstrate\b|\bmonolith\b|\bhistory is what hurts\b",
    "desire": r"\bdesire\w*\b|\bdrive\b|\bbasin\w*\b|\bprohibition\b|\bsuperego\b|\bgoodhart\b|\breward hack\w*\b",
    "projection": r"\bprojection\w*\b|\b1d\b|\bsynchronic\b|\bdiachronic\b|\bprison-house\b|\bideolog\w*\b|\bnarrative\b",
    "sanity": r"\bnarciss\w*\b|\bpsychos\w*\b|\bschizophren\w*\b|\bocd\b|\bdepression\b|\bsycophancy\b|\bsanity\b|\bhumility\b",
    "metamorphosis": r"\bdistillation\b|\bdark knowledge\b|\bcaterpillar\b|\bchrysalis\b|\bbutterfly\b|\bspock\b",
    "riemann": r"\briemann\b|\blean 4\b|\breactivation\b|\banisotropic\b|\balp[öo]ge\b|\b250,000\b",
}


@dataclass
class Chunk:
    source_file: str
    chapter_num: str
    chapter_title: str
    section_heading: str
    chunk_index: int
    content: str
    word_count: int
    thinkers: list[str]
    themes: list[str]


def infer_chapter_num(path: pathlib.Path) -> str:
    name = path.name
    if name == "frogner_park.md":
        return "00"
    if name == "metaphor-audit-and-methodology.md":
        return "protocol"
    m = re.match(r"^(\d{2})-", name)
    return m.group(1) if m else path.stem


def clean_markdown_text(text: str) -> str:
    """Strip image links, nav footers, and markdown punctuation noise while keeping concepts intact."""
    # Remove embedded image lines ![alt](path)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    # Replace markdown links [label](url) with label
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove blockquote prefixes and horizontal rules
    text = re.sub(r"^>\s*(\[![A-Z]+\])?\s*", "", text, flags=re.M)
    text = re.sub(r"^---+\s*$", "", text, flags=re.M)
    # Collapse excess whitespace
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def detect_tags(text: str, patterns: dict[str, str]) -> list[str]:
    lower = text.lower()
    return sorted(tag for tag, pat in patterns.items() if re.search(pat, lower))


def chunk_document(path: pathlib.Path, root: pathlib.Path, max_words: int = 180) -> list[Chunk]:
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()

    chapter_num = infer_chapter_num(path)
    chapter_title = path.stem
    for line in lines:
        if line.startswith("# "):
            chapter_title = line[2:].strip()
            break

    # Split into (section_heading, body_lines)
    sections: list[tuple[str, list[str]]] = []
    current_heading = "Introduction"
    current_lines: list[str] = []

    for line in lines:
        if line.startswith("# "):
            continue
        # Skip footer navigation bars
        if line.startswith("[← ") or line.startswith("[Back to README]"):
            continue
        if re.match(r"^#{2,3}\s+", line):
            if current_lines:
                sections.append((current_heading, current_lines))
            current_heading = re.sub(r"^#{2,3}\s+", "", line).strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_heading, current_lines))

    chunks: list[Chunk] = []
    chunk_idx = 0
    rel_source = str(path.relative_to(root))

    for heading, body_lines in sections:
        body = clean_markdown_text("\n".join(body_lines))
        if not body:
            continue

        # Split by blank lines into coherent paragraphs / tables / lists
        blocks = [b.strip() for b in re.split(r"\n\s*\n", body) if b.strip()]
        buf: list[str] = []
        buf_words = 0

        def flush() -> None:
            nonlocal chunk_idx, buf, buf_words
            if not buf:
                return
            combined = "\n\n".join(buf).strip()
            wc = len(combined.split())
            if wc < 15:
                buf = []
                buf_words = 0
                return
            full_for_tags = f"{chapter_title} {heading} {combined}"
            chunks.append(
                Chunk(
                    source_file=rel_source,
                    chapter_num=chapter_num,
                    chapter_title=chapter_title,
                    section_heading=heading,
                    chunk_index=chunk_idx,
                    content=combined,
                    word_count=wc,
                    thinkers=detect_tags(full_for_tags, THINKER_PATTERNS),
                    themes=detect_tags(full_for_tags, THEME_PATTERNS),
                )
            )
            chunk_idx += 1
            buf = []
            buf_words = 0

        for block in blocks:
            # Skip bare code/template fences or tiny metadata lines
            if block.startswith("```markdown"):
                continue
            bw = len(block.split())
            if buf and buf_words + bw > max_words:
                flush()
            buf.append(block)
            buf_words += bw
        flush()

    return chunks


def load_all_chunks(docs_dir: pathlib.Path = DOCS_DIR) -> list[Chunk]:
    root = docs_dir.parent
    md_files = sorted(docs_dir.glob("*.md"))
    all_chunks: list[Chunk] = []
    for md in md_files:
        all_chunks.extend(chunk_document(md, root=root))
    return all_chunks


if __name__ == "__main__":
    chunks = load_all_chunks()
    print(f"Total chunks: {len(chunks)}")
    by_ch: dict[str, int] = {}
    for c in chunks:
        by_ch[c.chapter_num] = by_ch.get(c.chapter_num, 0) + 1
    for ch, count in sorted(by_ch.items()):
        print(f"  Chapter {ch:>8}: {count} chunks")
