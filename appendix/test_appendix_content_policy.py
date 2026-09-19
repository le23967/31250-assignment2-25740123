"""QA: appendix PDF must contain code and section headings only, not Markdown prose.

This test deliberately extracts ordinary Markdown prose from the notebook and
checks that none of it appears in the generated appendix PDF text. It also
confirms that recognised section headings and code-cell content are present.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "ida_25740123.ipynb"
PDF_PATH = Path(__file__).resolve().parent / "ida_25740123_code_appendix.pdf"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_code_appendix import (  # noqa: E402
    extract_notebook_blocks,
    is_recognised_section_heading,
    renderer_code_sources,
)


def normalise_ws(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def strip_markdown_inline(text: str) -> str:
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text.strip()


def extract_ordinary_markdown_prose(notebook_path: Path) -> list[str]:
    """Collect ordinary Markdown prose and non-section headings from the notebook."""
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    fragments: list[str] = []

    for cell in notebook["cells"]:
        if cell.get("cell_type") != "markdown":
            continue
        source = "".join(cell.get("source", []))
        for raw_line in source.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("#"):
                heading = re.sub(r"^#+\s*", "", line).strip()
                if is_recognised_section_heading(heading):
                    continue
                # Subordinate or explanatory headings are ordinary prose for this QA.
                cleaned = strip_markdown_inline(heading)
                if len(normalise_ws(cleaned)) >= 12:
                    fragments.append(cleaned)
                continue
            if line.startswith("```"):
                continue
            cleaned = strip_markdown_inline(re.sub(r"^[-*+]\s+", "", line))
            cleaned = re.sub(r"^\d+\.\s+", "", cleaned)
            if len(normalise_ws(cleaned)) >= 24:
                fragments.append(cleaned)
    return fragments


def pdf_text(pdf_path: Path) -> str:
    """Extract PDF text with PyMuPDF for faithful code-line reconstruction."""
    doc = pymupdf.open(str(pdf_path))
    try:
        return "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()


def pdf_page_count(pdf_path: Path) -> int:
    doc = pymupdf.open(str(pdf_path))
    try:
        return doc.page_count
    finally:
        doc.close()


def distinctive_prose(fragments: list[str], code_blob: str) -> list[str]:
    """Keep prose long enough to be distinctive and not already present in code."""
    code_norm = normalise_ws(code_blob)
    out: list[str] = []
    seen: set[str] = set()
    for frag in fragments:
        norm = normalise_ws(frag)
        if len(norm) < 24:
            continue
        if norm.lower() in seen:
            continue
        if norm in code_norm:
            continue
        # Avoid very short token-like leftovers.
        if len(norm.split()) < 4:
            continue
        seen.add(norm.lower())
        out.append(norm)
    return out


def main() -> None:
    if not PDF_PATH.exists():
        raise SystemExit(f"Missing appendix PDF: {PDF_PATH}")

    blocks, notebook_sources = extract_notebook_blocks(NOTEBOOK)
    renderer_sources = renderer_code_sources(blocks)
    if notebook_sources != renderer_sources:
        raise SystemExit("FAIL: renderer code sources do not match notebook code cells.")

    expected_headings = [b["text"] for b in blocks if b["kind"] == "heading"]
    if not expected_headings:
        raise SystemExit("FAIL: no recognised section headings were selected.")
    if not notebook_sources:
        raise SystemExit("FAIL: no code cells were selected.")

    for heading in expected_headings:
        if not is_recognised_section_heading(heading):
            raise SystemExit(f"FAIL: non-recognised heading selected: {heading!r}")

    code_blob = "\n".join(notebook_sources)
    prose_fragments = extract_ordinary_markdown_prose(NOTEBOOK)
    distinctive = distinctive_prose(prose_fragments, code_blob)
    if len(distinctive) < 20:
        raise SystemExit(
            f"FAIL: expected many ordinary prose fragments for QA, found {len(distinctive)}."
        )

    raw_pdf = pdf_text(PDF_PATH)
    # Soft-wrap markers are presentation-only and must not affect code matching.
    pdf_for_code = raw_pdf.replace("↳ ", "")
    pdf_norm = normalise_ws(raw_pdf)
    pdf_code_norm = normalise_ws(pdf_for_code)
    if not pdf_norm:
        raise SystemExit("FAIL: appendix PDF text extraction returned empty content.")

    # 1. Ordinary Markdown prose must not appear in the PDF.
    prose_hits = [frag for frag in distinctive if frag in pdf_norm]
    if prose_hits:
        preview = "\n".join(f"  - {h[:100]}" for h in prose_hits[:10])
        raise SystemExit(
            f"FAIL: ordinary Markdown prose found in appendix PDF ({len(prose_hits)} hits):\n{preview}"
        )

    # 2. Recognised section headings must appear.
    missing_headings = [h for h in expected_headings if normalise_ws(h) not in pdf_norm]
    if missing_headings:
        preview = "\n".join(f"  - {h}" for h in missing_headings[:10])
        raise SystemExit(
            f"FAIL: expected section headings missing from PDF ({len(missing_headings)}):\n{preview}"
        )

    # 3. Code-cell content must appear (stable unique snippets from each cell).
    missing_code = []
    for idx, source in enumerate(notebook_sources):
        lines = [ln.strip() for ln in source.splitlines() if ln.strip()]
        if not lines:
            continue
        candidates = sorted(lines, key=lambda s: (abs(len(s) - 48), -len(s)))
        snippet = None
        for line in candidates:
            norm = normalise_ws(line)
            if 12 <= len(norm) <= 100:
                snippet = norm
                break
        if snippet is None:
            snippet = normalise_ws(candidates[0])
        if snippet and snippet not in pdf_code_norm:
            missing_code.append((idx, snippet[:100]))
    if missing_code:
        preview = "\n".join(f"  - cell {i}: {s}" for i, s in missing_code[:10])
        raise SystemExit(
            f"FAIL: code-cell content missing from PDF ({len(missing_code)} cells):\n{preview}"
        )

    # 4. Sanity: no appendix title or pagination footer.
    if "Appendix A. Python Code" in raw_pdf:
        raise SystemExit("FAIL: appendix title text should not appear in the PDF.")
    if "Appendix A, page" in raw_pdf:
        raise SystemExit("FAIL: appendix page footer text should not appear in the PDF.")

    print("PASS: ordinary Markdown prose absent from appendix PDF")
    print(f"PASS: recognised section headings present ({len(expected_headings)})")
    print(f"PASS: code-cell content present ({len(notebook_sources)} cells)")
    print(f"prose_fragments_checked: {len(distinctive)}")
    print(f"pdf_pages: {pdf_page_count(PDF_PATH)}")


if __name__ == "__main__":
    main()
