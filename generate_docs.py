#!/usr/bin/env python3
"""Generate TXT, PDF, and DOCX from ambar-proposal.md"""

from pathlib import Path
import re

BASE = Path(__file__).parent
MD_FILE = BASE / "ambar-proposal.md"

with open(MD_FILE, "r", encoding="utf-8") as f:
    md_text = f.read()

# ─── TXT ───────────────────────────────────────────────────────────
TXT_FILE = BASE / "ambar-proposal.txt"
with open(TXT_FILE, "w", encoding="utf-8") as f:
    f.write(md_text)

print(f"[OK] TXT: {TXT_FILE}")

# ─── Parse markdown into structured blocks ─────────────────────────
lines = md_text.split("\n")
blocks = []       # list of (type, list_of_lines)
current_type = None
current_lines = []

def flush():
    global current_type, current_lines
    if current_lines:
        blocks.append((current_type, current_lines))
    current_lines = []
    current_type = None

for line in lines:
    stripped = line.strip()

    # Determine type of this line
    if stripped.startswith("# ") and not stripped.startswith("## "):
        line_type = "h1"
    elif stripped.startswith("## "):
        line_type = "h2"
    elif stripped.startswith("### "):
        line_type = "h3"
    elif stripped.startswith("---"):
        line_type = "hr"
    elif stripped.startswith("> "):
        line_type = "quote"
    elif stripped.startswith("- ") or stripped.startswith("* "):
        line_type = "li"
    elif re.match(r"^\d+\.\s", stripped):
        line_type = "ol"
    elif "|" in stripped:
        line_type = "table"
    elif stripped == "":
        line_type = "blank"
    else:
        line_type = "p"

    if line_type == "blank":
        flush()
        continue

    if line_type == "hr":
        flush()
        blocks.append(("hr", []))
        continue

    if line_type != current_type:
        flush()
        current_type = line_type

    current_lines.append(line)

flush()

# ─── PDF via fpdf2 ─────────────────────────────────────────────────
from fpdf import FPDF

ARIAL = "/System/Library/Fonts/Supplemental/Arial.ttf"
ARIAL_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
ARIAL_ITALIC = "/System/Library/Fonts/Supplemental/Arial Italic.ttf"

pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=20)
pdf.add_page()

pdf.add_font("Arial", "", ARIAL)
pdf.add_font("Arial", "B", ARIAL_BOLD)
pdf.add_font("Arial", "I", ARIAL_ITALIC)

def write_mixed(pdf, text, size=10, default_bold=False):
    """Write text with **bold** markers to PDF."""
    parts = re.split(r"(\*\*.*?\*\*)", text)
    for part in parts:
        if part.startswith("**") and part.endswith("**"):
            pdf.set_font("Arial", "B", size)
            pdf.write(size * 0.5, part[2:-2])
        else:
            pdf.set_font("Arial", "B" if default_bold else "", size)
            pdf.write(size * 0.5, part)

def cell_mixed(pdf, w, h, text, size=10, bold=False):
    """Draw a cell with mixed bold/normal text."""
    parts = re.split(r"(\*\*.*?\*\*)", text)
    for part in parts:
        if part.startswith("**") and part.endswith("**"):
            pdf.set_font("Arial", "B", size)
            pdf.cell(w, h, part[2:-2])
        else:
            pdf.set_font("Arial", "B" if bold else "", size)
            pdf.cell(w, h, part)

def render_table(pdf, block_lines):
    """Render a markdown table in PDF."""
    # Filter out separator lines
    rows = []
    for l in block_lines:
        l = l.strip()
        if re.match(r"^\|[\s\-:|]+\|$", l):
            continue
        cells = [c.strip() for c in l.split("|")[1:-1]]
        rows.append(cells)

    if not rows:
        return

    num_cols = len(rows[0])
    col_width = (170) / num_cols  # 170mm usable width

    for ri, row in enumerate(rows):
        for ci in range(min(len(row), num_cols)):
            cell = row[ci]
            parts = re.split(r"(\*\*.*?\*\*)", cell)
            for part in parts:
                if part.startswith("**") and part.endswith("**"):
                    pdf.set_font("Arial", "B", 8)
                    pdf.cell(col_width, 5, part[2:-2])
                else:
                    pdf.set_font("Arial", "B" if ri == 0 else "", 8)
                    pdf.cell(col_width, 5, part)
        pdf.ln()

for btype, blines in blocks:
    if btype == "h1":
        pdf.set_font("Arial", "B", 16)
        pdf.set_x(pdf.l_margin)
        text = blines[0][2:]  # remove "# "
        pdf.multi_cell(170, 8, text)
        pdf.ln(3)

    elif btype == "h2":
        pdf.set_font("Arial", "B", 13)
        pdf.set_x(pdf.l_margin)
        text = blines[0][3:]  # remove "## "
        pdf.multi_cell(170, 7, text)
        pdf.ln(2)

    elif btype == "h3":
        pdf.set_font("Arial", "B", 11)
        pdf.set_x(pdf.l_margin)
        text = blines[0][4:]  # remove "### "
        pdf.multi_cell(170, 6, text)
        pdf.ln(2)

    elif btype == "hr":
        y = pdf.get_y()
        pdf.set_draw_color(180, 180, 180)
        pdf.set_line_width(0.3)
        pdf.line(20, y, 190, y)
        pdf.ln(4)

    elif btype == "quote":
        pdf.set_text_color(80, 80, 80)
        for l in blines:
            pdf.set_font("Arial", "I", 10)
            pdf.set_x(25)
            pdf.multi_cell(165, 5, l[2:])
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

    elif btype == "li":
        for l in blines:
            pdf.set_x(22)
            pdf.set_font("Arial", "", 10)
            pdf.cell(5, 5, "\u2022")
            write_mixed(pdf, l[2:], size=10)
            pdf.ln(5)

    elif btype == "ol":
        for l in blines:
            m = re.match(r"^\d+\.\s", l)
            if m:
                pdf.set_x(22)
                pdf.set_font("Arial", "", 10)
                pdf.cell(8, 5, m.group())
                write_mixed(pdf, l[m.end():], size=10)
                pdf.ln(5)

    elif btype == "table":
        render_table(pdf, blines)
        pdf.ln(3)

    elif btype == "p":
        for l in blines:
            if l.strip().startswith("**") and l.strip().endswith("**"):
                pdf.set_font("Arial", "B", 10)
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(170, 5, l.strip()[2:-2])
            else:
                pdf.set_x(pdf.l_margin)
                write_mixed(pdf, l, size=10)
                pdf.ln(5)

PDF_FILE = BASE / "ambar-proposal.pdf"
pdf.output(str(PDF_FILE))
print(f"[OK] PDF: {PDF_FILE}")

# ─── DOCX via python-docx ──────────────────────────────────────────
from docx import Document
from docx.shared import Pt, RGBColor, Inches

doc = Document()

style = doc.styles["Normal"]
font = style.font
font.name = "Arial"
font.size = Pt(11)

def add_formatted_paragraph(doc, text, size=11, bold=False, italic=False, color=None, space_after=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    parts = re.split(r"(\*\*.*?\*\*)", text)
    for part in parts:
        run = p.add_run()
        if part.startswith("**") and part.endswith("**"):
            run.text = part[2:-2]
            run.bold = True
        else:
            run.text = part
        run.font.name = "Arial"
        run.font.size = Pt(size)
        if bold:
            run.bold = True
        if italic:
            run.italic = True
        if color:
            run.font.color.rgb = color
    return p

def render_table_docx(doc, block_lines):
    rows_data = []
    for l in block_lines:
        l = l.strip()
        if re.match(r"^\|[\s\-:|]+\|$", l):
            continue
        cells = [c.strip() for c in l.split("|")[1:-1]]
        rows_data.append(cells)

    if not rows_data:
        return

    num_cols = len(rows_data[0])
    table = doc.add_table(rows=len(rows_data), cols=num_cols)
    table.style = "Light Grid Accent 1"

    for ri, row in enumerate(rows_data):
        for ci in range(min(len(row), num_cols)):
            cell = table.cell(ri, ci)

            # Parse bold markers within cell text
            parts = re.split(r"(\*\*.*?\*\*)", row[ci])
            p = cell.paragraphs[0]
            p.clear()
            for part in parts:
                run = p.add_run()
                if part.startswith("**") and part.endswith("**"):
                    run.text = part[2:-2]
                    run.bold = True
                else:
                    run.text = part
                run.font.name = "Arial"
                run.font.size = Pt(9)
                if ri == 0:
                    run.bold = True

    doc.add_paragraph()

for btype, blines in blocks:
    if btype == "h1":
        add_formatted_paragraph(doc, blines[0][2:], size=18, bold=True, space_after=12)

    elif btype == "h2":
        add_formatted_paragraph(doc, blines[0][3:], size=14, bold=True, space_after=8)

    elif btype == "h3":
        add_formatted_paragraph(doc, blines[0][4:], size=12, bold=True, space_after=6)

    elif btype == "hr":
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run("─" * 60)
        run.font.size = Pt(8)
        run.font.color.rgb = RGBColor(180, 180, 180)

    elif btype == "quote":
        for l in blines:
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.3)
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run(l[2:])
            run.font.name = "Arial"
            run.font.size = Pt(10)
            run.italic = True
            run.font.color.rgb = RGBColor(100, 100, 100)

    elif btype == "li":
        for l in blines:
            add_formatted_paragraph(doc, "\u2022 " + l[2:], size=10, space_after=2)

    elif btype == "ol":
        for l in blines:
            add_formatted_paragraph(doc, l, size=10, space_after=2)

    elif btype == "table":
        render_table_docx(doc, blines)

    elif btype == "p":
        for l in blines:
            # Clean text for bold-only lines
            if l.strip().startswith("**") and l.strip().endswith("**"):
                add_formatted_paragraph(doc, l.strip(), size=11, bold=True, space_after=4)
            else:
                add_formatted_paragraph(doc, l, size=10, space_after=4)

DOCX_FILE = BASE / "ambar-proposal.docx"
doc.save(str(DOCX_FILE))
print(f"[OK] DOCX: {DOCX_FILE}")

print("\n✅ All files generated successfully.")
