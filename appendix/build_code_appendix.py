import io
import json
import re

from PIL import Image, ImageDraw, ImageFont
from pygments import highlight
from pygments.formatters import ImageFormatter
from pygments.lexers import PythonLexer

NOTEBOOK = "ida_25740123.ipynb"
OUTPUT_PDF = "appendix/ida_25740123_code_appendix.pdf"
LINES_PER_PAGE = 110
PAGE = (1240, 1754)          # A4 at 150 dpi
MARGIN = 70


def collect_code(notebook_path):
    """Return the notebook code in order, with a comment line for each heading."""
    notebook = json.load(open(notebook_path, encoding="utf-8"))
    lines, heading = [], None
    for cell in notebook["cells"]:
        source = "".join(cell["source"])
        if cell["cell_type"] == "markdown":
            for line in source.splitlines():
                if line.startswith("#"):
                    heading = re.sub(r"^#+\s*", "", line).strip()
        elif source.strip():
            if heading:
                lines += ["", "# " + "=" * 70, f"# {heading}", "# " + "=" * 70, ""]
                heading = None
            for line in source.rstrip().splitlines():
                while len(line) > 118:                      # wrap rather than shrink the page
                    cut = line.rfind(" ", 0, 118)
                    cut = cut if cut > 40 else 118
                    lines.append(line[:cut])
                    line = "    " + line[cut:].lstrip()
                lines.append(line)
            lines.append("")
    return lines


def render_page(text, page_number, total_pages):
    """Draw one page of code onto an A4 canvas."""
    formatter = ImageFormatter(font_size=13, line_numbers=False, style="friendly",
                               image_pad=0, line_pad=1)
    code_image = Image.open(io.BytesIO(highlight(text, PythonLexer(), formatter)))
    usable = (PAGE[0] - 2 * MARGIN, PAGE[1] - 2 * MARGIN - 40)
    if code_image.width > usable[0] or code_image.height > usable[1]:
        scale = min(usable[0] / code_image.width, usable[1] / code_image.height)
        code_image = code_image.resize((int(code_image.width * scale), int(code_image.height * scale)))
    page = Image.new("RGB", PAGE, "white")
    page.paste(code_image, (MARGIN, MARGIN))
    draw = ImageDraw.Draw(page)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 18)
    except OSError:
        font = ImageFont.load_default()
    draw.text((MARGIN, PAGE[1] - MARGIN), f"Appendix A, page {page_number} of {total_pages}",
              fill=(110, 110, 110), font=font)
    return page


if __name__ == "__main__":
    import os
    os.makedirs("appendix", exist_ok=True)
    code_lines = collect_code(NOTEBOOK)
    chunks = [code_lines[i:i + LINES_PER_PAGE] for i in range(0, len(code_lines), LINES_PER_PAGE)]
    pages = [render_page("\n".join(chunk), i + 1, len(chunks)) for i, chunk in enumerate(chunks)]
    pages[0].save(OUTPUT_PDF, save_all=True, append_images=pages[1:], resolution=150)
    print(f"code lines: {len(code_lines)} | pages: {len(pages)}")
