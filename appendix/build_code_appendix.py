"""Build a clean Python code appendix PDF from the assignment notebook.

Presentation-only elements (Markdown headings, soft wraps) are drawn outside
the executable source. Notebook code cells are not rewritten. The Word report
already supplies the appendix title, so this PDF does not repeat it.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from pygments import lex
from pygments.lexers import PythonLexer
from pygments.token import Comment, Keyword, Name, Number, Operator, String, Text, Token
from reportlab.lib.colors import Color, white
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "ida_25740123.ipynb"
OUTPUT_PDF = Path(__file__).resolve().parent / "ida_25740123_code_appendix.pdf"

PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT = 36
RIGHT = 36
TOP = 32
BOTTOM = 28
CODE_FONT_SIZE = 7.6
HEADING_FONT_SIZE = 9
LINE_GAP = 1.12
MAX_CODE_WIDTH = PAGE_WIDTH - LEFT - RIGHT

# Restrained syntax colours
COLOURS = {
    "default": Color(0.12, 0.12, 0.12),
    "keyword": Color(0.10, 0.20, 0.55),
    "builtin": Color(0.15, 0.35, 0.55),
    "string": Color(0.12, 0.45, 0.22),
    "comment": Color(0.45, 0.45, 0.45),
    "number": Color(0.55, 0.25, 0.10),
    "name": Color(0.12, 0.12, 0.12),
    "operator": Color(0.25, 0.25, 0.25),
    "wrap": Color(0.55, 0.55, 0.55),
}


def _register_fonts() -> tuple[str, str]:
    """Register readable mono and sans fonts available on macOS."""
    mono_candidates = [
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Supplemental/Courier New.ttf",
        "/Library/Fonts/Courier New.ttf",
    ]
    sans_candidates = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ]
    mono_name, sans_name = "AppendixMono", "AppendixSans"
    mono_path = next((p for p in mono_candidates if Path(p).exists()), None)
    sans_path = next((p for p in sans_candidates if Path(p).exists()), None)
    if mono_path:
        try:
            pdfmetrics.registerFont(TTFont(mono_name, mono_path, subfontIndex=0))
        except Exception:
            mono_name = "Courier"
    else:
        mono_name = "Courier"
    if sans_path:
        try:
            pdfmetrics.registerFont(TTFont(sans_name, sans_path, subfontIndex=0))
        except Exception:
            sans_name = "Helvetica"
    else:
        sans_name = "Helvetica"
    return mono_name, sans_name


def extract_notebook_blocks(notebook_path: Path) -> tuple[list[dict], list[str]]:
    """Return presentation blocks and ordered exact code-cell sources."""
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    blocks: list[dict] = []
    code_sources: list[str] = []
    pending_heading: str | None = None

    for cell in notebook["cells"]:
        source = "".join(cell.get("source", []))
        if cell.get("cell_type") == "markdown":
            for line in source.splitlines():
                if line.startswith("#"):
                    pending_heading = re.sub(r"^#+\s*", "", line).strip()
        elif cell.get("cell_type") == "code" and source.strip():
            if pending_heading:
                blocks.append({"kind": "heading", "text": pending_heading})
                pending_heading = None
            blocks.append({"kind": "code", "source": source})
            code_sources.append(source)
    return blocks, code_sources


def ordered_code_hash(sources: list[str]) -> str:
    """Deterministic SHA-256 over ordered code-cell sources."""
    payload = "\n\0\n".join(sources).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def token_colour(ttype) -> Color:
    if ttype in Token.Keyword or ttype in Keyword:
        return COLOURS["keyword"]
    if ttype in Name.Builtin:
        return COLOURS["builtin"]
    if ttype in String or ttype in Token.Literal.String:
        return COLOURS["string"]
    if ttype in Comment or ttype in Token.Comment:
        return COLOURS["comment"]
    if ttype in Number or ttype in Token.Literal.Number:
        return COLOURS["number"]
    if ttype in Operator:
        return COLOURS["operator"]
    if ttype in Name:
        return COLOURS["name"]
    if ttype in Text:
        return COLOURS["default"]
    return COLOURS["default"]


def _string_width(text: str, font_name: str, font_size: float) -> float:
    return pdfmetrics.stringWidth(text, font_name, font_size)


def soft_wrap_line(line: str, font_name: str, font_size: float, max_width: float) -> list[str]:
    """Visually wrap one source line without rewriting notebook source."""
    if _string_width(line, font_name, font_size) <= max_width:
        return [line]

    wrapped: list[str] = []
    remaining = line
    first = True
    while remaining:
        limit = max_width if first else max_width - _string_width("↳ ", font_name, font_size)
        if _string_width(remaining, font_name, font_size) <= limit:
            piece = remaining
            remaining = ""
        else:
            # Prefer a break near a space, otherwise hard-break by width.
            lo, hi = 1, len(remaining)
            fit = 1
            while lo <= hi:
                mid = (lo + hi) // 2
                chunk = remaining[:mid]
                if _string_width(chunk, font_name, font_size) <= limit:
                    fit = mid
                    lo = mid + 1
                else:
                    hi = mid - 1
            space = remaining.rfind(" ", 0, fit)
            if space >= max(8, fit // 4):
                fit = space + 1
            piece = remaining[:fit]
            remaining = remaining[fit:]
        if first:
            wrapped.append(piece)
            first = False
        else:
            wrapped.append("↳ " + piece)
    return wrapped


def highlight_source_lines(source: str, font_name: str, font_size: float) -> list[list[tuple[str, Color]]]:
    """Turn source into visually wrapped coloured runs. Soft wraps are presentation-only."""
    # Preserve exact line content; do not rewrite executable structure.
    raw_lines = source.splitlines()
    if source.endswith("\n"):
        # trailing newline does not create an extra blank display line
        pass
    display_rows: list[list[tuple[str, Color]]] = []

    # Lex whole source so multi-line strings stay coherent, then map by line.
    tokens = list(lex(source, PythonLexer()))
    line_tokens: list[list[tuple[str, Color]]] = [[]]
    for ttype, value in tokens:
        colour = token_colour(ttype)
        parts = value.split("\n")
        for i, part in enumerate(parts):
            if i > 0:
                line_tokens.append([])
            if part:
                line_tokens[-1].append((part, colour))

    # splitlines() drops a final empty line created by a trailing newline;
    # align token lines to raw_lines length.
    while len(line_tokens) < len(raw_lines):
        line_tokens.append([])
    if len(line_tokens) > len(raw_lines) and raw_lines:
        # trailing empty token line from final newline
        if not line_tokens[-1]:
            line_tokens.pop()
    if not raw_lines and source == "":
        return []

    for idx, raw in enumerate(raw_lines):
        runs = line_tokens[idx] if idx < len(line_tokens) else [(raw, COLOURS["default"])]
        # If lexing produced nothing for a blank line, keep an empty row.
        if not runs and raw == "":
            display_rows.append([])
            continue
        # Rebuild plain text to soft-wrap, then re-apply colours by slicing runs.
        plain = "".join(text for text, _ in runs) if runs else raw
        pieces = soft_wrap_line(plain, font_name, font_size, MAX_CODE_WIDTH)
        if len(pieces) == 1 and pieces[0] == plain:
            display_rows.append(runs if runs else [(plain, COLOURS["default"])])
            continue
        # Distribute original coloured runs across soft-wrapped pieces.
        flat = runs if runs else [(plain, COLOURS["default"])]
        cursor = 0
        run_i = 0
        run_pos = 0
        for p_i, piece in enumerate(pieces):
            visual = piece
            prefix_runs: list[tuple[str, Color]] = []
            content = visual
            if p_i > 0 and visual.startswith("↳ "):
                prefix_runs.append(("↳ ", COLOURS["wrap"]))
                content = visual[2:]
            out: list[tuple[str, Color]] = list(prefix_runs)
            need = len(content)
            taken = 0
            while taken < need and run_i < len(flat):
                text, colour = flat[run_i]
                avail = text[run_pos:]
                take = avail[: need - taken]
                if take:
                    out.append((take, colour))
                taken += len(take)
                run_pos += len(take)
                if run_pos >= len(text):
                    run_i += 1
                    run_pos = 0
            display_rows.append(out)
            cursor += len(content)
        _ = cursor  # presentation cursor only
    return display_rows


class AppendixBuilder:
    def __init__(self, output_path: Path):
        self.mono, self.sans = _register_fonts()
        self.output_path = output_path
        self.c = canvas.Canvas(str(output_path), pagesize=A4)
        self.y = PAGE_HEIGHT - TOP
        self.page_started = False
        self.line_height = CODE_FONT_SIZE * LINE_GAP

    def new_page(self) -> None:
        if self.page_started:
            self.c.showPage()
        self.page_started = True
        self.c.setFillColor(white)
        self.c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
        self.y = PAGE_HEIGHT - TOP

    def ensure_space(self, height: float) -> None:
        if not self.page_started:
            self.new_page()
        if self.y - height < BOTTOM:
            self.new_page()

    def draw_heading(self, text: str) -> None:
        needed = HEADING_FONT_SIZE + 6
        self.ensure_space(needed + self.line_height)
        # Small gap before a heading when not at top of page
        if self.y < PAGE_HEIGHT - TOP - 1:
            self.y -= 3
            self.ensure_space(needed + self.line_height)
        self.c.setFillColor(Color(0.15, 0.15, 0.15))
        self.c.setFont(self.sans, HEADING_FONT_SIZE)
        self.c.drawString(LEFT, self.y - HEADING_FONT_SIZE, text)
        self.y -= HEADING_FONT_SIZE + 3

    def draw_code(self, source: str) -> None:
        rows = highlight_source_lines(source, self.mono, CODE_FONT_SIZE)
        if not rows:
            return
        for row in rows:
            self.ensure_space(self.line_height)
            x = LEFT
            baseline = self.y - CODE_FONT_SIZE
            if not row:
                self.y -= self.line_height
                continue
            for text, colour in row:
                if not text:
                    continue
                self.c.setFillColor(colour)
                self.c.setFont(self.mono, CODE_FONT_SIZE)
                self.c.drawString(x, baseline, text)
                x += _string_width(text, self.mono, CODE_FONT_SIZE)
            self.y -= self.line_height
        # Compact gap after each code cell
        self.y -= 2

    def build(self, blocks: list[dict]) -> None:
        self.new_page()
        for block in blocks:
            if block["kind"] == "heading":
                self.draw_heading(block["text"])
            elif block["kind"] == "code":
                self.draw_code(block["source"])
        self.c.save()


def renderer_code_sources(blocks: list[dict]) -> list[str]:
    """Code sources passed to the renderer, excluding presentation headings."""
    return [b["source"] for b in blocks if b["kind"] == "code"]


def main() -> None:
    blocks, notebook_sources = extract_notebook_blocks(NOTEBOOK)
    renderer_sources = renderer_code_sources(blocks)

    nb_hash = ordered_code_hash(notebook_sources)
    rd_hash = ordered_code_hash(renderer_sources)
    if notebook_sources != renderer_sources or nb_hash != rd_hash:
        raise SystemExit(
            "Source integrity failure: renderer code does not match notebook code cells."
        )

    # Guard against accidental artificial content in renderer code input.
    joined = "\n".join(renderer_sources)
    forbidden = [
        "Appendix A, page",
        "# " + "=" * 20,
        "# " + "-" * 20,
        "# " + "*" * 20,
    ]
    for marker in forbidden:
        if marker in joined:
            raise SystemExit(f"Artificial content found in renderer code input: {marker!r}")

    OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    builder = AppendixBuilder(OUTPUT_PDF)
    builder.build(blocks)

    print(f"non_empty_code_cells: {len(notebook_sources)}")
    print(f"notebook_sha256: {nb_hash}")
    print(f"renderer_sha256: {rd_hash}")
    print(f"output: {OUTPUT_PDF}")


if __name__ == "__main__":
    main()
