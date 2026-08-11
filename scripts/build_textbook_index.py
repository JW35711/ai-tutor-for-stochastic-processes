#!/usr/bin/env python3
"""Build a small, inspectable textbook index for the local RAG retriever.

The input PDF and generated JSON are deliberately ignored by Git.  This keeps
the repository light while making the exact ingestion step reproducible on a
machine that has the course notes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.curriculum import load_curriculum  # noqa: E402


HEADING = re.compile(r"(?im)^\s*(?:definition|theorem|example|remark|exercise)\b")
CONTENT_TYPE = re.compile(r"\b(definition|theorem|example|remark|exercise)\b", re.I)
WORDS = re.compile(r"[a-z][a-z0-9-]{2,}|[\u4e00-\u9fff]{2,}", re.I)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def split_blocks(text: str) -> list[str]:
    """Split at textbook landmarks before falling back to paragraph chunks."""

    lines = [normalize(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    blocks: list[str] = []
    current: list[str] = []
    for line in lines:
        if HEADING.match(line) and current:
            blocks.append(" ".join(current))
            current = []
        current.append(line)
    if current:
        blocks.append(" ".join(current))
    return blocks


def split_long_block(block: str, size: int = 1300, overlap: int = 220) -> list[str]:
    """Keep normal chunks near 800--1600 chars and preserve sentence edges."""

    if len(block) <= 1600:
        return [block]
    chunks: list[str] = []
    start = 0
    while start < len(block):
        end = min(len(block), start + size)
        if end < len(block):
            boundary = max(block.rfind(". ", start + 700, end), block.rfind(" ", start + 700, end))
            if boundary > start:
                end = boundary + 1
        chunk = block[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(block):
            break
        start = max(start + 1, end - overlap)
    return chunks


def chunk_page(text: str) -> list[str]:
    """Pack structural blocks without cutting a Definition/Theorem/Example."""

    chunks: list[str] = []
    current = ""
    for block in split_blocks(text):
        for piece in split_long_block(block):
            if current and len(current) + len(piece) + 1 > 1600:
                chunks.append(current)
                current = piece
            else:
                current = f"{current} {piece}".strip()
    if current:
        chunks.append(current)
    return chunks


def concept_vocabulary(curriculum: dict[str, Any]) -> list[dict[str, Any]]:
    concepts: list[dict[str, Any]] = []
    for module in curriculum["modules"]:
        for point in module["knowledge_points"]:
            raw = " ".join([point["title"], point["summary"]]).lower()
            terms = {word for word in WORDS.findall(raw) if len(word) >= 3}
            pages = {
                int(match.group(1))
                for ref in point.get("source_refs", [])
                if (match := re.search(r"#page-(\d+)$", ref))
            }
            concepts.append(
                {
                    "module_id": module["module_id"],
                    "concept_id": point["id"],
                    "title": point["title"],
                    "terms": terms,
                    "pages": pages,
                }
            )
    return concepts


def map_chunk(text: str, page: int, concepts: list[dict[str, Any]]) -> tuple[str | None, str | None, str]:
    text_terms = set(WORDS.findall(text.lower()))
    best: dict[str, Any] | None = None
    best_score = 0
    for concept in concepts:
        score = len(text_terms & concept["terms"])
        if concept["title"].lower() in text.lower():
            score += 8
        if score > best_score:
            best, best_score = concept, score
    match = CONTENT_TYPE.search(text[:250])
    content_type = match.group(1).lower() if match else "textbook_text"
    if best is None or best_score < 2:
        return None, None, content_type
    return best["module_id"], best["concept_id"], content_type


def first_title(text: str, page: int) -> str:
    first = normalize(text).split(". ", 1)[0]
    return (first[:110] or f"Textbook page {page}").strip()


def build_index(input_path: Path, output_path: Path) -> list[dict[str, Any]]:
    try:
        from pypdf import PdfReader
    except ImportError as error:  # pragma: no cover - environment dependent
        raise SystemExit("pypdf is required to build the textbook index") from error

    curriculum = load_curriculum()
    vocabulary = concept_vocabulary(curriculum)
    reader = PdfReader(str(input_path))
    chunks: list[dict[str, Any]] = []
    for page, pdf_page in enumerate(reader.pages, start=1):
        raw_text = pdf_page.extract_text() or ""
        for chunk_index, text in enumerate(chunk_page(raw_text)):
            module_id, concept_id, content_type = map_chunk(text, page, vocabulary)
            chunks.append(
                {
                    "text": text,
                    "title": first_title(text, page),
                    "source_type": "textbook",
                    "source": f"{input_path.name}#page-{page}",
                    "page": page,
                    "module_id": module_id,
                    "concept_id": concept_id,
                    "content_type": content_type,
                    "chunk_index": chunk_index,
                    "keywords": [],
                }
            )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(chunks, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "reference" / "lectnotes_technmath.pdf")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "textbook_chunks.json")
    args = parser.parse_args()
    if not args.input.is_file():
        raise SystemExit(f"textbook PDF not found: {args.input}")
    chunks = build_index(args.input, args.output)
    mapped = sum(chunk["concept_id"] is not None for chunk in chunks)
    print(f"wrote {len(chunks)} chunks to {args.output} ({mapped} mapped to concepts)")


if __name__ == "__main__":
    main()
