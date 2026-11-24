"""
Build the complete M.Sc. IT project report for RainVision.

The report follows the institute-supplied 14-chapter format, uses Times New
Roman (12 pt body, 14 pt headings, 1.5 line spacing), and embeds the verified
figures and benchmark results produced by build_report_assets.py.

Run:
    python scripts/build_report_docx.py
"""
from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from PIL import Image

ROOT = Path(r"D:\sem=1\Project")
FIG = ROOT / "outputs" / "report_figures"
DATA = ROOT / "outputs" / "report_data"
OUT = ROOT / "outputs" / "RainVision_Project_Report.docx"

NAVY = "1F3864"
BLUE = "2E5597"
LIGHT_BLUE = "D9E2F3"
LIGHT_GREY = "F2F2F2"
MID_GREY = "BFBFBF"
DARK_GREY = "404040"
WHITE = "FFFFFF"

PAGE_W = 8.27
PAGE_H = 11.69
MARGIN = 1.0
CONTENT_W = PAGE_W - 2 * MARGIN  # 6.27 in

STUDENTS = [
    ("Makvana Mukeshbhai Mohanbhai", "26TMSCIT22030"),
    ("Heet Ashokkumar Velani", "26TMSCIT22045"),
]
GUIDE = "Mr. Jignesh Senjaliya"
TITLE = (
    "RAINVISION: AN INTELLIGENT RAINFALL FORECASTING, PREDICTION "
    "AND CLIMATE ANALYTICS PLATFORM"
)
INSTITUTE = "Shri Maneklal M. Patel Institute of Sciences & Research"
INSTITUTE_SUB = "M.Sc. IT and B.Sc. CS, Gandhinagar"
ACADEMIC_YEAR = "2026\u20132027"


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------
def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)
    shd.set(qn("w:val"), "clear")


def set_cell_margins(cell, top=40, start=70, bottom=40, end=70) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for m, v in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(v))
        node.set(qn("w:type"), "dxa")


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def prevent_row_split(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    cant_split.set(qn("w:val"), "true")
    tr_pr.append(cant_split)


def set_table_borders(table, color=MID_GREY, size="4") -> None:
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = borders.find(qn(f"w:{edge}"))
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), size)
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)


def add_page_field(paragraph) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instr)
    run._r.append(separate)
    run._r.append(text)
    run._r.append(end)


def add_page_number_format(section, fmt: str, start: int | None = None) -> None:
    sect_pr = section._sectPr
    pg_num_type = sect_pr.find(qn("w:pgNumType"))
    if pg_num_type is None:
        pg_num_type = OxmlElement("w:pgNumType")
        sect_pr.append(pg_num_type)
    pg_num_type.set(qn("w:fmt"), fmt)
    if start is not None:
        pg_num_type.set(qn("w:start"), str(start))


def add_page_border(section) -> None:
    sect_pr = section._sectPr
    borders = OxmlElement("w:pgBorders")
    borders.set(qn("w:offsetFrom"), "page")
    for edge in ("top", "left", "bottom", "right"):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), "double")
        element.set(qn("w:sz"), "12")
        element.set(qn("w:space"), "24")
        element.set(qn("w:color"), NAVY)
        borders.append(element)
    sect_pr.append(borders)


def configure_section(section) -> None:
    section.page_width = Inches(PAGE_W)
    section.page_height = Inches(PAGE_H)
    section.top_margin = Inches(MARGIN)
    section.bottom_margin = Inches(MARGIN)
    section.left_margin = Inches(MARGIN)
    section.right_margin = Inches(MARGIN)
    section.header_distance = Inches(0.45)
    section.footer_distance = Inches(0.45)


def set_paragraph_bottom_border(paragraph, color=NAVY, size="8") -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), size)
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), color)
    p_bdr.append(bottom)
    p_pr.append(p_bdr)


def set_run_font(run, name="Times New Roman", size=None, bold=None,
                 italic=None, color=None) -> None:
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color is not None:
        run.font.color.rgb = RGBColor.from_string(color)


# ---------------------------------------------------------------------------
# Document and styles
# ---------------------------------------------------------------------------
doc = Document()
configure_section(doc.sections[0])
add_page_border(doc.sections[0])

styles = doc.styles
normal = styles["Normal"]
normal.font.name = "Times New Roman"
normal.font.size = Pt(12)
normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
normal.paragraph_format.line_spacing = 1.5
normal.paragraph_format.space_after = Pt(6)
normal.paragraph_format.space_before = Pt(0)
normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
normal.paragraph_format.widow_control = True

for style_name, size, bold, italic in (
    ("Heading 1", 14, True, False),
    ("Heading 2", 12, True, False),
    ("Heading 3", 12, True, True),
):
    style = styles[style_name]
    style.font.name = "Times New Roman"
    style.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.italic = italic
    style.font.color.rgb = RGBColor(0, 0, 0)
    style.paragraph_format.keep_with_next = True
    style.paragraph_format.keep_together = True
    style.paragraph_format.line_spacing = 1.5
    style.paragraph_format.space_before = Pt(12 if style_name == "Heading 1" else 10)
    style.paragraph_format.space_after = Pt(8 if style_name == "Heading 1" else 4)
    style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

style = styles["Heading 1"]
style.paragraph_format.space_before = Pt(0)
style.paragraph_format.space_after = Pt(12)

# Caption style
caption = styles["Caption"]
caption.font.name = "Times New Roman"
caption.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
caption.font.size = Pt(10)
caption.font.italic = True
caption.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
caption.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
caption.paragraph_format.line_spacing = 1.0
caption.paragraph_format.space_before = Pt(4)
caption.paragraph_format.space_after = Pt(10)

# Code style
code_style = styles.add_style("Code Block", 1)
code_style.font.name = "Consolas"
code_style.element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
code_style.font.size = Pt(8)
code_style.paragraph_format.line_spacing = 1.0
code_style.paragraph_format.space_before = Pt(0)
code_style.paragraph_format.space_after = Pt(0)
code_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
code_style.paragraph_format.left_indent = Inches(0.08)
code_style.paragraph_format.right_indent = Inches(0.05)

# List styles
for list_style_name in ("List Bullet", "List Number"):
    ls = styles[list_style_name]
    ls.font.name = "Times New Roman"
    ls.font.size = Pt(12)
    ls.paragraph_format.line_spacing = 1.5
    ls.paragraph_format.space_after = Pt(3)
    ls.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

doc.core_properties.title = "RainVision: An Intelligent Rainfall Forecasting, Prediction and Climate Analytics Platform"
doc.core_properties.subject = "M.Sc. IT Foundational Project I (VAC441-1C) Project Report"
doc.core_properties.author = "Makvana Mukeshbhai Mohanbhai; Heet Ashokkumar Velani"
doc.core_properties.keywords = "rainfall prediction, machine learning, climate analytics, Flask, scikit-learn"
doc.core_properties.comments = "Final M.Sc. IT semester I project report"


# ---------------------------------------------------------------------------
# Content helpers
# ---------------------------------------------------------------------------
def p(text="", bold=False, italic=False, size=12, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
      space_after=6, space_before=0, keep_with_next=False, line_spacing=1.5,
      color=None):
    paragraph = doc.add_paragraph()
    run = paragraph.add_run(text)
    set_run_font(run, size=size, bold=bold, italic=italic, color=color)
    paragraph.alignment = align
    paragraph.paragraph_format.space_after = Pt(space_after)
    paragraph.paragraph_format.space_before = Pt(space_before)
    paragraph.paragraph_format.keep_with_next = keep_with_next
    paragraph.paragraph_format.line_spacing = line_spacing
    return paragraph


def lead_para(lead: str, body: str) -> None:
    paragraph = doc.add_paragraph()
    r1 = paragraph.add_run(lead)
    set_run_font(r1, bold=True)
    r2 = paragraph.add_run(body)
    set_run_font(r2)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph.paragraph_format.line_spacing = 1.5
    paragraph.paragraph_format.space_after = Pt(6)


def bullets(items, style="List Bullet") -> None:
    for item in items:
        paragraph = doc.add_paragraph(style=style)
        run = paragraph.add_run(item)
        set_run_font(run)
        paragraph.paragraph_format.line_spacing = 1.5
        paragraph.paragraph_format.space_after = Pt(3)
        paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        paragraph.paragraph_format.left_indent = Inches(0.3)
        paragraph.paragraph_format.first_line_indent = Inches(-0.2)


def numbered(items) -> None:
    for i, item in enumerate(items, 1):
        paragraph = doc.add_paragraph()
        r1 = paragraph.add_run(f"{i}.  ")
        set_run_font(r1, bold=True)
        r2 = paragraph.add_run(item)
        set_run_font(r2)
        paragraph.paragraph_format.left_indent = Inches(0.35)
        paragraph.paragraph_format.first_line_indent = Inches(-0.25)
        paragraph.paragraph_format.line_spacing = 1.5
        paragraph.paragraph_format.space_after = Pt(4)
        paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY


def h1(text: str, page_break=True) -> None:
    if page_break:
        doc.add_page_break()
    heading = doc.add_heading(text, level=1)
    for run in heading.runs:
        set_run_font(run, size=14, bold=True, color="000000")
    heading.paragraph_format.space_before = Pt(0)
    heading.paragraph_format.space_after = Pt(12)


def h2(text: str) -> None:
    heading = doc.add_heading(text, level=2)
    for run in heading.runs:
        set_run_font(run, size=12, bold=True, color="000000")


def h3(text: str) -> None:
    heading = doc.add_heading(text, level=3)
    for run in heading.runs:
        set_run_font(run, size=12, bold=True, italic=True, color="000000")


def caption_para(text: str, table=False) -> None:
    paragraph = doc.add_paragraph(style="Caption")
    run = paragraph.add_run(text)
    set_run_font(run, size=10, italic=True, color="333333")
    paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.line_spacing = 1.0
    paragraph.paragraph_format.space_before = Pt(6 if table else 4)
    paragraph.paragraph_format.space_after = Pt(6 if table else 10)
    paragraph.paragraph_format.keep_with_next = table


def add_table(headers, rows, widths, caption=None, font_size=9.0,
              header_fill=NAVY, center_cols=None, bold_first_col=False,
              row_height=None):
    if caption:
        caption_para(caption, table=True)

    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.style = "Table Grid"
    set_table_borders(table)

    header = table.rows[0]
    set_repeat_table_header(header)
    prevent_row_split(header)
    for i, text in enumerate(headers):
        cell = header.cells[i]
        cell.width = Inches(widths[i])
        set_cell_shading(cell, header_fill)
        set_cell_margins(cell)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        paragraph = cell.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.line_spacing = 1.0
        paragraph.paragraph_format.space_after = Pt(0)
        run = paragraph.add_run(str(text))
        set_run_font(run, size=font_size, bold=True, color=WHITE)

    for r_idx, row_data in enumerate(rows):
        row = table.add_row()
        prevent_row_split(row)
        if row_height:
            row.height = Inches(row_height)
        for c_idx, value in enumerate(row_data):
            cell = row.cells[c_idx]
            cell.width = Inches(widths[c_idx])
            set_cell_margins(cell)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            if r_idx % 2 == 1:
                set_cell_shading(cell, LIGHT_GREY)
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.line_spacing = 1.0
            paragraph.paragraph_format.space_after = Pt(0)
            if center_cols and c_idx in center_cols:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
            run = paragraph.add_run(str(value))
            set_run_font(run, size=font_size,
                         bold=(bold_first_col and c_idx == 0))

    p("", space_after=4, line_spacing=1.0)
    return table


def add_figure(filename: str, caption: str, width=CONTENT_W):
    path = FIG / filename
    with Image.open(path) as img:
        w, h = img.size
    max_height = 7.7  # leaves room for caption inside A4 text area
    if width * h / w > max_height:
        width = max_height * w / h
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(4)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.keep_with_next = True
    run = paragraph.add_run()
    run.add_picture(str(path), width=Inches(width))
    caption_para(caption)


def code_block(code: str, caption=None) -> None:
    if caption:
        caption_para(caption, table=True)
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.style = "Table Grid"
    set_table_borders(table, color="D0D0D0", size="4")
    cell = table.cell(0, 0)
    cell.width = Inches(CONTENT_W)
    set_cell_shading(cell, "F7F7F7")
    set_cell_margins(cell, top=80, start=100, bottom=80, end=100)
    paragraph = cell.paragraphs[0]
    paragraph.paragraph_format.line_spacing = 1.0
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    lines = code.strip("\n").split("\n")
    for idx, line in enumerate(lines):
        run = paragraph.add_run(line)
        set_run_font(run, name="Consolas", size=8)
        if idx < len(lines) - 1:
            run.add_break()
    p("", space_after=4, line_spacing=1.0)


def prelim_title(text: str, subtitle: str | None = None) -> None:
    paragraph = p(text, bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER,
                  space_before=0, space_after=4)
    set_paragraph_bottom_border(paragraph, color=NAVY, size="6")
    if subtitle:
        p(subtitle, italic=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER,
          space_before=4, space_after=14)
    else:
        p("", space_after=8)


def cover_line(text, size=12, bold=False, italic=False, space_after=2, space_before=0):
    return p(text, size=size, bold=bold, italic=italic,
             align=WD_ALIGN_PARAGRAPH.CENTER, space_after=space_after,
             space_before=space_before, line_spacing=1.0)


def add_signature_table(entries, widths):
    table = doc.add_table(rows=2, cols=len(entries))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for i, (label, name) in enumerate(entries):
        top = table.cell(0, i)
        bottom = table.cell(1, i)
        top.width = Inches(widths[i])
        bottom.width = Inches(widths[i])
        for c in (top, bottom):
            set_cell_margins(c, top=30, start=40, bottom=30, end=40)
        p1 = top.paragraphs[0]
        p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p1.paragraph_format.space_after = Pt(0)
        r1 = p1.add_run("__________________________")
        set_run_font(r1, size=11)
        p2 = bottom.paragraphs[0]
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p2.paragraph_format.space_after = Pt(0)
        r2 = p2.add_run(label)
        set_run_font(r2, size=10.5, bold=True)
        if name:
            r3 = p2.add_run("\n" + name)
            set_run_font(r3, size=9.5, italic=True)


# ---------------------------------------------------------------------------
# Preliminary pages
# ---------------------------------------------------------------------------
# Title page
cover_line("A PROJECT REPORT ON", size=11, bold=True, space_before=8, space_after=10)
cover_line("RAINVISION", size=24, bold=True, space_after=2)
cover_line(
    "AN INTELLIGENT RAINFALL FORECASTING, PREDICTION\nAND CLIMATE ANALYTICS PLATFORM",
    size=15, bold=True, space_after=12,
)
line = cover_line("", size=2, space_after=0)
set_paragraph_bottom_border(line, color=NAVY, size="12")
cover_line("FOUNDATIONAL PROJECT \u2013 I  (VAC441-1C)", size=13, bold=True,
           space_before=10, space_after=4)
cover_line("Semester \u2013 I", size=12, bold=True, space_after=2)
cover_line(f"Academic Year {ACADEMIC_YEAR}", size=12, space_after=18)
cover_line("Submitted as partial fulfillment of the requirement for", size=10.5,
           italic=True, space_after=4)
cover_line("M.Sc. (IT) with Major (Data Science and Artificial Intelligence) \u2013 Semester I",
           size=11.5, bold=True, space_after=4)
cover_line("Prepared for Subject: Foundational Project \u2013 I (VAC441-1C)",
           size=10.5, italic=True, space_after=20)
cover_line("SUBMITTED BY", size=11, bold=True, space_after=8)

table = doc.add_table(rows=3, cols=3)
table.alignment = WD_TABLE_ALIGNMENT.CENTER
table.autofit = False
widths = [2.75, 1.9, 1.25]
headers = ["Name of Student", "Enrollment No.", "Exam No."]
for c_idx, text in enumerate(headers):
    cell = table.cell(0, c_idx)
    cell.width = Inches(widths[c_idx])
    set_cell_shading(cell, NAVY)
    set_cell_margins(cell, top=50, start=50, bottom=50, end=50)
    para = cell.paragraphs[0]
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.space_after = Pt(0)
    run = para.add_run(text)
    set_run_font(run, size=9, bold=True, color=WHITE)

for r_idx, (name, enroll) in enumerate(STUDENTS, 1):
    values = [name, enroll, ""]
    for c_idx, value in enumerate(values):
        cell = table.cell(r_idx, c_idx)
        cell.width = Inches(widths[c_idx])
        set_cell_margins(cell, top=55, start=50, bottom=55, end=50)
        para = cell.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER if c_idx > 0 else WD_ALIGN_PARAGRAPH.LEFT
        para.paragraph_format.space_after = Pt(0)
        run = para.add_run(value)
        set_run_font(run, size=10)

p("", space_after=16, line_spacing=1.0)
cover_line(INSTITUTE, size=13, bold=True, space_after=2)
cover_line(INSTITUTE_SUB, size=10.5, space_after=2)
cover_line("Gandhinagar, Gujarat", size=10.5, space_after=10)
cover_line("NOVEMBER 2026", size=11, bold=True, space_after=0)


# Section 2: certificate and acknowledgement
section2 = doc.add_section(WD_SECTION.NEW_PAGE)
configure_section(section2)
section2.different_first_page_header_footer = True
add_page_number_format(section2, "lowerRoman", 1)
footer = section2.footer
footer.is_linked_to_previous = False
fp = footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
fp.paragraph_format.space_after = Pt(0)
add_page_field(fp)
for run in fp.runs:
    set_run_font(run, size=9, color="555555")

# Certificate
p("", space_after=10, line_spacing=1.0)
p(INSTITUTE.upper(), bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER,
  space_after=2, line_spacing=1.0)
p(INSTITUTE_SUB, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2,
  line_spacing=1.0)
p("Gandhinagar, Gujarat", size=10.5, align=WD_ALIGN_PARAGRAPH.CENTER,
  space_after=22, line_spacing=1.0)
cert = p("PROJECT CERTIFICATE", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER,
         space_after=18, line_spacing=1.0)
for run in cert.runs:
    run.underline = True

p(
    "This is to certify that the project report submitted by "
    "Makvana Mukeshbhai Mohanbhai (Enrollment No. 26TMSCIT22030) and "
    "Heet Ashokkumar Velani (Enrollment No. 26TMSCIT22045), students of "
    "M.Sc. (IT) with Major (Data Science and Artificial Intelligence), "
    "Semester-I, have completed their project titled "
    "\u201cRainVision: An Intelligent Rainfall Forecasting, Prediction and "
    "Climate Analytics Platform\u201d satisfactorily during the academic year "
    f"{ACADEMIC_YEAR}.",
    space_after=12,
)
p(
    f"The project work has been carried out under the supervision of {GUIDE}, "
    "and the report has been examined and found satisfactory in partial "
    "fulfillment of the requirements for the Foundational Project \u2013 I "
    "(VAC441-1C).",
    space_after=12,
)
p(
    "We appreciate the enthusiasm, technical effort and dedication shown by the "
    "students towards the design, implementation and documentation of this work.",
    space_after=28,
)
p("Date: ____________", size=11, align=WD_ALIGN_PARAGRAPH.LEFT, space_after=2,
  line_spacing=1.0)
p("Place: Gandhinagar", size=11, align=WD_ALIGN_PARAGRAPH.LEFT, space_after=50,
  line_spacing=1.0)
add_signature_table(
    [("Project Guide", GUIDE), ("Head of Department", "M.Sc. IT Department"),
     ("External Examiner", "")],
    [2.2, 2.2, 1.87],
)

# Acknowledgement
doc.add_page_break()
p("", space_after=6, line_spacing=1.0)
ack = p("ACKNOWLEDGEMENT", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER,
        space_after=8, line_spacing=1.0)
set_paragraph_bottom_border(ack, color=NAVY, size="6")
p("", space_after=8)

p(
    "We would like to express our sincere gratitude to all those who supported "
    "and guided us throughout the completion of this project titled "
    "\u201cRainVision: An Intelligent Rainfall Forecasting, Prediction and "
    "Climate Analytics Platform\u201d."
)
p(
    f"First and foremost, we are deeply thankful to {GUIDE}, our project "
    "supervisor, for his valuable guidance, continuous encouragement and "
    "constructive feedback. His suggestions regarding temporal validation, "
    "zero-inflated regression and the practical presentation of machine "
    "learning results helped us improve both the technical quality and the "
    "clarity of this work."
)
p(
    "We are also grateful to the M.Sc. IT Department of Shri Maneklal M. Patel "
    "Institute of Sciences & Research, Gandhinagar, and to all faculty members "
    "for providing the necessary laboratory facilities, software resources and "
    "a supportive academic environment. The departmental workshops on Python, "
    "data analytics and project documentation were particularly helpful during "
    "the implementation of this project."
)
p(
    "We sincerely acknowledge the open-source scientific community behind "
    "Python, NumPy, pandas, scikit-learn, matplotlib, seaborn, Flask and "
    "related libraries. Their tools made it possible to build, evaluate and "
    "deploy a reproducible end-to-end machine learning system within the "
    "scope of a semester project."
)
p(
    "Finally, we thank our families and friends for their patience, motivation "
    "and constant support during the project. Their encouragement helped us "
    "complete the work on time and present it with confidence."
)
p("", space_after=14)
p("Name of Students:", bold=True, size=11, align=WD_ALIGN_PARAGRAPH.LEFT,
  space_after=6)
for name, enroll in STUDENTS:
    p(f"{name}    \u2013    Enrollment No. {enroll}", size=11,
      align=WD_ALIGN_PARAGRAPH.LEFT, space_after=2, line_spacing=1.15)
p("", space_after=18)
p("Signature: ______________________", size=11, align=WD_ALIGN_PARAGRAPH.LEFT,
  space_after=2, line_spacing=1.0)


# Section 3: index / table of contents
section3 = doc.add_section(WD_SECTION.NEW_PAGE)
configure_section(section3)
footer = section3.footer
footer.is_linked_to_previous = False
fp = footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
fp.paragraph_format.space_after = Pt(0)
add_page_field(fp)
for run in fp.runs:
    set_run_font(run, size=9, color="555555")
add_page_number_format(section3, "lowerRoman")

prelim_title("INDEX", "Table of Contents")
toc_para = doc.add_paragraph()
toc_para.paragraph_format.line_spacing = 1.15
toc_para.paragraph_format.space_after = Pt(8)
run = toc_para.add_run()
begin = OxmlElement("w:fldChar")
begin.set(qn("w:fldCharType"), "begin")
instr = OxmlElement("w:instrText")
instr.set(qn("xml:space"), "preserve")
instr.text = ' TOC \\o "1-2" \\h \\z \\u '
separate = OxmlElement("w:fldChar")
separate.set(qn("w:fldCharType"), "separate")
text = OxmlElement("w:t")
text.text = "Table of contents will be generated when the document fields are updated."
end = OxmlElement("w:fldChar")
end.set(qn("w:fldCharType"), "end")
run._r.append(begin)
run._r.append(instr)
run._r.append(separate)
run._r.append(text)
run._r.append(end)
for r in toc_para.runs:
    set_run_font(r, size=11)

p(
    "Note: Chapter and section page numbers are generated automatically by "
    "Microsoft Word. If the document is edited after submission, place the "
    "cursor anywhere in the index and press F9 to refresh the field.",
    size=9.5, italic=True, align=WD_ALIGN_PARAGRAPH.LEFT, space_before=14,
    line_spacing=1.15,
)


# Section 4: main body
section4 = doc.add_section(WD_SECTION.NEW_PAGE)
configure_section(section4)
add_page_number_format(section4, "decimal", 1)
footer = section4.footer
footer.is_linked_to_previous = False
fp = footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
fp.paragraph_format.space_after = Pt(0)
add_page_field(fp)
for run in fp.runs:
    set_run_font(run, size=9, color="555555")

header = section4.header
header.is_linked_to_previous = False
hp = header.paragraphs[0]
hp.paragraph_format.space_after = Pt(0)
hp.paragraph_format.tab_stops.add_tab_stop(Inches(CONTENT_W), WD_TAB_ALIGNMENT.RIGHT)
r1 = hp.add_run("RainVision Project Report")
set_run_font(r1, size=9, color="595959")
r2 = hp.add_run("\tM.Sc. IT (DS & AI) \u2013 Semester I")
set_run_font(r2, size=9, color="595959")
set_paragraph_bottom_border(hp, color=MID_GREY, size="4")


# ===========================================================================
# CHAPTER 1
# ===========================================================================
h1("CHAPTER 1: INTRODUCTION", page_break=False)

h2("1.1 Project Overview")
p(
    "Rainfall is one of the most consequential and least predictable variables "
    "in the daily operation of agriculture, water supply, transport and disaster "
    "management systems. In Gujarat and the wider western-Indian monsoon "
    "corridor, more than nine-tenths of annual precipitation is delivered in a "
    "compressed June-to-September window. A delay of even a few days in the "
    "onset of the monsoon can affect sowing decisions, reservoir planning and "
    "the scheduling of municipal water releases, while a single intense "
    "cloudburst can overwhelm drainage infrastructure that was sized for a much "
    "more moderate rainfall regime."
)
p(
    "RainVision is an end-to-end machine learning platform that converts a "
    "42-year daily meteorological record into three practical outputs: a "
    "quantitative 24-hour rainfall-depth forecast in millimetres, a "
    "meteorological intensity class, and a set of climate analytics and "
    "operational advisories. The system combines careful data preparation, "
    "leakage-safe feature engineering, regression and classification models, "
    "chronological validation, and a Flask-based web interface. It is designed "
    "as a reproducible academic prototype rather than as a replacement for an "
    "official numerical weather prediction service."
)
p(
    "The project began from a simple observation: a conventional regression "
    "model trained on raw weather variables can appear reasonable on average "
    "while still failing on the two cases that matter most\u2014dry days, where "
    "it invents rainfall, and extreme days, where it smooths away the peak. "
    "RainVision therefore treats zero-inflation, temporal leakage, class "
    "imbalance and physical consistency as first-class design problems. The "
    "result is a system whose evaluation is deliberately disaggregated: overall "
    "error, wet-day error, dry-day behaviour, per-class recall and "
    "expanding-window cross-validation are reported separately."
)
p(
    "The historical dataset used in this study contains 15,279 daily "
    "observations from 1 January 1985 to 31 October 2026 for the Metropolis "
    "Central Station (approximately 23.025\u00b0 N, 72.5714\u00b0 E; 55 m above "
    "mean sea level). It includes temperature, relative humidity, barometric "
    "pressure, wind speed, previous-day rainfall and the target 24-hour rainfall "
    "depth. The final benchmark uses a strict 80/20 chronological split: the "
    "first 12,223 observations, ending on 19 June 2018, are used for training, "
    "and the remaining 3,056 observations, from 20 June 2018 to 31 October "
    "2026, are held out as an unseen future test set."
)

h2("1.2 Problem Statement")
p(
    "The central problem is to estimate daily rainfall depth and intensity from "
    "routine surface meteorological observations without allowing future "
    "information to leak into model training. Although this sounds like a "
    "standard supervised-learning task, the rainfall series violates several "
    "assumptions that ordinary regression and random cross-validation rely on."
)
bullets([
    "Zero-inflation: 11,214 of 15,279 days (73.39%) record 0.05 mm or less. A "
    "model that predicts almost zero everywhere can obtain a low mean absolute "
    "error while being useless for wet-day and flood-risk decisions.",
    "Heavy-tailed extremes: the maximum daily rainfall is 339.9 mm, while the "
    "95th percentile is only 10.5 mm and the 99th percentile is 42.94 mm. A "
    "small number of extreme days therefore dominates squared-error metrics.",
    "Temporal dependence: rainfall is autocorrelated and strongly seasonal. "
    "Randomly shuffling observations during training creates look-ahead bias "
    "and produces optimistic validation scores that do not survive a real "
    "forecast setting.",
    "Class imbalance: Dry/Trace days account for 73.39% of the data, whereas "
    "Torrential days account for only 0.79%. An unweighted classifier can "
    "achieve high accuracy by never predicting the rare but operationally "
    "important classes.",
    "Physical plausibility: unconstrained linear models can output negative "
    "rainfall. Predictions must be clipped at zero, and intensity labels must "
    "remain consistent with the predicted depth.",
    "Fragmented analytics: dataset inspection, model comparison, live "
    "prediction and climate summaries are often spread across notebooks and "
    "spreadsheets. A single interface is needed for reproducible exploration "
    "and demonstration.",
])
p(
    "Existing notebook prototypes in the project addressed parts of this "
    "problem, but the results were distributed across several metric "
    "generations and were not presented through one consistent evaluation "
    "protocol. The need addressed by this report is therefore both technical "
    "and methodological: build a leakage-safe rainfall pipeline, evaluate it "
    "honestly on a future hold-out period, and expose the trained models through "
    "a usable application whose behaviour can be demonstrated and audited."
)

h2("1.3 Scope of the Project")
p(
    "The scope is deliberately bounded so that the project remains a complete, "
    "defensible semester artefact rather than an open-ended meteorological "
    "research programme. Table 1.1 summarises what the system covers and what "
    "it intentionally leaves outside its current boundary."
)
add_table(
    ["Dimension", "Included in RainVision", "Not included in the current version"],
    [
        ["Geographic scope", "One station representative of the Gujarat / western-India semi-arid monsoon climate (Metropolis Central Station).",
         "District-level or statewide spatial interpolation; gridded IMD or AWS ingestion."],
        ["Temporal scope", "Daily observations from 1985-01-01 to 2026-10-31; 24-hour accumulated rainfall.",
         "Sub-daily nowcasting, hourly radar reflectivity and cloudburst-scale forecasting."],
        ["Prediction targets", "Continuous rainfall depth (mm), five-tier intensity class and operational advisory.",
         "Exact timing of rainfall within the day; probabilistic ensemble forecasts from a numerical weather model."],
        ["Models", "Baselines, OLS, Ridge, Decision Tree, Random Forest, Gradient Boosting and a two-stage Hurdle model.",
         "Deep sequence models (LSTM/Transformer), graph neural networks and operational numerical weather prediction."],
        ["Interface", "Flask web application with dashboard, prediction studio, model comparison, dataset explorer and batch inference.",
         "Native mobile application, multi-user authentication, role-based access control and cloud auto-scaling."],
        ["Users", "Students, researchers, demonstration evaluators and prototype-level decision support users.",
         "Mission-critical public warning systems or regulated utility operations without human review."],
    ],
    [1.15, 2.65, 2.47],
    caption="Table 1.1: Scope of the RainVision project.",
    font_size=8.8,
)

h2("1.4 Objectives of the Project")
p("The project pursues the following primary and specific objectives:")
numbered([
    "To assemble and validate a long-run daily meteorological dataset suitable "
    "for supervised rainfall prediction, and to document its provenance, "
    "quality and limitations.",
    "To design a leakage-safe pre-processing and feature-engineering pipeline "
    "that represents seasonality, antecedent moisture and atmospheric change "
    "without using future observations.",
    "To train and compare a family of regression models for 24-hour rainfall "
    "depth, including simple baselines, linear models, tree ensembles and a "
    "two-stage Hurdle formulation.",
    "To train and compare multi-class classifiers for meteorological rainfall "
    "intensity, with explicit attention to rare heavy and torrential events.",
    "To evaluate models on a strictly chronological future hold-out set and "
    "with expanding-window time-series cross-validation, reporting overall and "
    "wet-day/dry-day behaviour separately.",
    "To identify the meteorological features that drive model decisions and to "
    "interpret them in terms of known monsoon physics.",
    "To integrate the trained models into a Flask application that supports "
    "live prediction, model comparison, dataset exploration and downloadable "
    "reports.",
    "To document the complete system, its results, limitations and future "
    "enhancements in a reproducible academic report.",
])

h2("1.5 Functional Requirements")
p(
    "Functional requirements describe what the system must do from the point of "
    "view of a user or an integrating client. The requirements below were "
    "derived from the implemented application and are numbered for traceability "
    "to the design and testing chapters."
)
add_table(
    ["ID", "Functional requirement", "Description", "Priority"],
    [
        ["FR-01", "Load historical dataset", "Read the multi-sheet Excel workbook and expose the daily rainfall table without manual conversion.", "High"],
        ["FR-02", "Validate input data", "Check required columns, date ordering, numeric ranges and duplicate dates before analysis.", "High"],
        ["FR-03", "Generate features", "Create cyclical calendar, lag, rolling-window and pressure-change features in a leakage-safe order.", "High"],
        ["FR-04", "Train regression models", "Fit baselines, OLS, Ridge, Decision Tree, Random Forest, Gradient Boosting and Hurdle models.", "High"],
        ["FR-05", "Train classification models", "Fit majority baseline, logistic regression, decision tree, random forest and gradient boosting classifiers.", "High"],
        ["FR-06", "Evaluate and compare", "Compute MAE, RMSE, R\u00b2, accuracy, precision, recall, F1, confusion matrices and wet-day errors.", "High"],
        ["FR-07", "Predict rainfall depth", "Accept temperature, humidity, pressure, wind speed, previous rainfall and date, then return a non-negative depth in mm.", "High"],
        ["FR-08", "Predict intensity class", "Return Dry/Trace, Light, Moderate, Heavy or Torrential with a confidence indicator.", "High"],
        ["FR-09", "Generate advisory", "Map the predicted depth and class to an operational urban-flood and agricultural advisory.", "Medium"],
        ["FR-10", "Explore dataset", "Search, filter, sort and paginate the historical observations in the browser.", "Medium"],
        ["FR-11", "Compare models", "Run compatible models on the same input and display their outputs side by side.", "Medium"],
        ["FR-12", "Export reports", "Download prediction history, evaluation metrics or batch results as CSV, and the dataset as Excel.", "Medium"],
        ["FR-13", "Batch inference", "Accept an uploaded CSV of weather observations and return annotated predictions for every row.", "Low"],
        ["FR-14", "Explain prediction", "Display a feature-attribution summary and a short natural-language interpretation of the result.", "Low"],
    ],
    [0.55, 1.35, 3.55, 0.82],
    caption="Table 1.2: Functional requirements of RainVision.",
    font_size=8.8,
    center_cols={0, 3},
)

h2("1.6 Significance of the Project")
p(
    "The significance of RainVision lies in the combination of a real "
    "climatological question, a defensible machine learning methodology and a "
    "working user interface. The project is not limited to fitting a model in a "
    "notebook; it demonstrates how a rainfall model can be validated, "
    "interpreted and operated."
)
bullets([
    "Agricultural relevance: sowing, irrigation and harvest decisions depend on "
    "the timing and intensity of monsoon rainfall. A calibrated daily estimate "
    "supports scenario analysis even when an official forecast is unavailable.",
    "Urban water management: municipal drainage, low-lying-area warnings and "
    "storm-water pump scheduling can use intensity-class predictions as an "
    "additional screening signal.",
    "Methodological value: the project shows why random shuffling is "
    "inappropriate for weather time series and how a chronological split, "
    "expanding-window validation and dry-day diagnostics change the "
    "interpretation of model quality.",
    "Educational value: the code and report provide a complete reference "
    "pipeline covering ingestion, EDA, feature engineering, model comparison, "
    "serialization and Flask deployment.",
    "Reproducibility: every number in the results chapter is generated from a "
    "scripted pipeline with fixed random seeds and saved artefacts, rather than "
    "being copied manually from an interactive session.",
    "Responsible communication: the interface separates a statistical estimate "
    "from an official warning and includes a visible advisory caveat, reducing "
    "the risk that a prototype output is treated as an authoritative alert.",
])

h2("1.7 Organization of the Report")
p(
    "The report follows the fourteen-chapter format prescribed by the "
    "department. Table 1.3 provides a reading guide."
)
add_table(
    ["Chapter", "Title", "Main content"],
    [
        ["1", "Introduction", "Background, problem statement, scope, objectives, requirements, significance and report structure."],
        ["2", "System Architecture, Tools & Technology", "Layered architecture, technology stack, hardware/software requirements and non-functional requirements."],
        ["3", "System Design", "Workflow, use cases, logical data model, data dictionary, sample records and interface design."],
        ["4", "Dataset", "Provenance, size, schema, target definition, quality summary, temporal split and workbook contents."],
        ["5", "Data Pre-processing", "Cleaning, outlier policy, encoding, scaling, feature engineering and leakage controls."],
        ["6", "Exploratory Data Analysis", "Descriptive statistics, seasonality, distributions, correlations, bivariate analysis and key observations."],
        ["7", "Machine Learning Methodology", "Problem formulation, algorithm selection, split strategy, Hurdle model, cross-validation and tuning."],
        ["8", "Model Evaluation & Comparison", "Metric definitions, regression and classification benchmarks, per-class analysis and cross-validation results."],
        ["9", "Implementation & Coding", "Repository structure, major code excerpts, model integration, inference and serialization."],
        ["10", "System Interface / Screen Layouts", "Dashboard, prediction studio, dataset explorer, API endpoints and generated reports."],
        ["11", "Results & Discussion", "Interpretation of results, feature importance, dry-day behaviour, operational performance and objective-wise assessment."],
        ["12", "Conclusion", "Summary of achievements, contributions and final remarks."],
        ["13", "Limitations & Future Enhancements", "Current constraints, improvement opportunities and a phased roadmap."],
        ["14", "References / Bibliography", "Research papers, standards, datasets, books and official documentation."],
    ],
    [0.58, 1.72, 3.97],
    caption="Table 1.3: Organization of the report.",
    font_size=8.8,
    center_cols={0},
)


# ===========================================================================
# CHAPTER 2
# ===========================================================================
h1("CHAPTER 2: SYSTEM ARCHITECTURE, TOOLS & TECHNOLOGY")

h2("2.1 Architectural Overview")
p(
    "RainVision uses a layered architecture that separates the user interface, "
    "the web/API service, the machine learning intelligence, the feature and "
    "pre-processing logic, and the underlying data artefacts. The separation is "
    "intentional: a change to the presentation layer should not require "
    "retraining a model, and a change to a feature definition should be "
    "traceable through a single feature module rather than being duplicated in "
    "several notebooks."
)
add_figure(
    "fig_architecture.png",
    "Figure 2.1: Layered system architecture of RainVision.",
)
p(
    "The presentation layer is a responsive single-page interface built with "
    "HTML5, CSS3 and vanilla JavaScript. It communicates with the service layer "
    "through JSON endpoints. The service layer validates requests, invokes the "
    "appropriate model and returns a structured prediction together with an "
    "advisory and an explanation. The intelligence layer contains the "
    "regression suite, the classification suite and the two-stage Hurdle model. "
    "The feature layer converts raw observations into the exact 17-feature "
    "vector expected by the trained artefacts. The data layer stores the "
    "historical workbook, serialized joblib models, metadata and generated "
    "reports."
)

h2("2.2 Layer Responsibilities")
add_table(
    ["Layer", "Main components", "Responsibility"],
    [
        ["Presentation", "Dashboard, Prediction Studio, Model Comparison, Dataset Explorer, Historical Analytics, About page.",
         "Collect user inputs, display results, charts and tables, and provide accessible navigation across the application."],
        ["Service / API", "Flask routes, request validation, response formatting, advisory engine, CSV/Excel export.",
         "Expose a stable JSON contract, reject invalid meteorological inputs, coordinate model calls and record prediction history."],
        ["Intelligence", "OLS, Ridge, Decision Tree, Random Forest, Gradient Boosting, Hurdle regressor, classifier suite.",
         "Fit and serve the predictive models; support side-by-side comparison and probability/feature attribution."],
        ["Feature & pre-processing", "Cleaning rules, calendar encodings, lag features, rolling windows, pressure tendency, scaling.",
         "Transform raw weather values into a leakage-safe numeric matrix and preserve a consistent feature order."],
        ["Data", "Excel workbook, processed CSV files, joblib model artefacts, JSON metadata, report figures.",
         "Provide durable inputs and outputs so that experiments and application behaviour can be reproduced."],
    ],
    [1.12, 2.65, 2.50],
    caption="Table 2.1: Responsibilities of the architectural layers.",
    font_size=8.8,
)

h2("2.3 Technology Stack")
p(
    "The implementation deliberately uses a compact, widely available open-source "
    "stack. This keeps the project portable across Windows, Linux and Google "
    "Colab while remaining close to the tools used in professional data science "
    "practice. The versions listed below are the versions used for the final "
    "benchmark and report generation."
)
add_table(
    ["Category", "Technology", "Version", "Role in RainVision"],
    [
        ["Programming language", "Python", "3.13.17", "Data processing, model training, evaluation, application logic and report automation."],
        ["Data manipulation", "pandas", "2.2.3", "Excel/CSV ingestion, date handling, grouping, pivoting and tabular transformations."],
        ["Numerical computing", "NumPy", "2.2.5", "Vectorised arithmetic, trigonometric encodings, clipping and metric calculations."],
        ["Machine learning", "scikit-learn", "1.9.1", "Estimators, pipelines, scaling, TimeSeriesSplit, GridSearchCV and metrics."],
        ["Visualisation", "matplotlib / seaborn", "3.10.1 / 0.13.2", "Publication-quality EDA, diagnostic and comparison figures."],
        ["Web framework", "Flask", "3.1.3", "Routing, JSON API, template rendering and file download responses."],
        ["Model persistence", "joblib", "1.6.0", "Serialization and reloading of trained regressors and classifiers."],
        ["Spreadsheet I/O", "openpyxl", "3.1.5", "Reading and writing multi-sheet Excel workbooks."],
        ["Front end", "HTML5, CSS3, JavaScript", "Browser-native", "Responsive single-page interface, charts and interactive forms."],
        ["Documentation", "python-docx / Microsoft Word", "1.2.0 / Office", "Programmatic report generation and final field/page-number update."],
        ["Version control", "Git / GitHub", "Git 2.x", "Source history, experiment tracking and reproducible collaboration."],
    ],
    [1.25, 1.38, 0.95, 2.69],
    caption="Table 2.2: Technology stack used in the project.",
    font_size=8.7,
    center_cols={1, 2},
)

h2("2.4 Hardware Requirements")
p(
    "The system is CPU-first. The full benchmark can be reproduced on a "
    "moderate laptop; the random forests and gradient-boosting models are small "
    "enough that a GPU is not required. The recommended configuration is "
    "intended for comfortable exploratory work and for running the web "
    "application while a notebook kernel is open."
)
add_table(
    ["Component", "Minimum requirement", "Recommended configuration"],
    [
        ["Processor", "Intel Core i3 (8th generation) or AMD Ryzen 3 equivalent", "Intel Core i5 / i7 (10th generation or newer) or AMD Ryzen 5 / 7"],
        ["Memory", "8 GB RAM", "16 GB RAM or more"],
        ["Storage", "5 GB free disk space", "10 GB free SSD space for datasets, models, notebooks and reports"],
        ["Display", "1366 \u00d7 768", "1920 \u00d7 1080 or higher"],
        ["Network", "Required only for initial package installation", "Broadband connection for package installation and optional live-weather sync"],
        ["GPU", "Not required", "Optional CUDA-capable GPU for future deep-learning extensions"],
    ],
    [1.25, 2.40, 2.62],
    caption="Table 2.3: Minimum and recommended hardware requirements.",
    font_size=8.8,
)

h2("2.5 Software Requirements")
add_table(
    ["Software", "Requirement", "Purpose"],
    [
        ["Operating system", "Windows 10/11, Ubuntu 20.04+ or macOS 12+", "Cross-platform execution of the Python stack and Flask server."],
        ["Python", "3.10 or newer (3.13 used)", "Runtime for data processing, modelling and the web application."],
        ["Web browser", "Chrome, Edge, Firefox or Safari (current version)", "Access to the RainVision interface and browser developer tools."],
        ["Jupyter", "JupyterLab or Jupyter Notebook", "Exploratory analysis and notebook-based demonstration."],
        ["Microsoft Word", "Word 2016 or newer (optional)", "Final field update, PDF export and manual layout review of this report."],
        ["PDF reader", "Any standards-compliant reader", "Review of the exported report and figures."],
        ["Optional", "Google Colab account", "Cloud execution of the self-contained master notebook."],
    ],
    [1.25, 2.60, 2.42],
    caption="Table 2.4: Software requirements.",
    font_size=8.8,
)

h2("2.6 Non-Functional Requirements")
add_table(
    ["Quality attribute", "Requirement", "How it is addressed"],
    [
        ["Performance", "A single live prediction should normally return within a few hundred milliseconds on a laptop CPU.",
         "Small tree ensembles, pre-loaded joblib artefacts and a lightweight Flask endpoint; the demonstrated prediction reported about 85 ms inference time."],
        ["Scalability", "The pipeline should handle at least the full 15,279-row dataset and batch uploads without redesign.",
         "Vectorised pandas operations, configurable batch inference and a data cache in the Flask application."],
        ["Usability", "A first-time user should be able to generate a prediction without reading code.",
         "Preset weather scenarios, labelled sliders, inline validation and plain-language advisories."],
        ["Reliability", "Invalid inputs must be rejected with a clear message rather than crashing the server.",
         "Central validation bounds, try/except handling and JSON error responses with HTTP 400/500 status codes."],
        ["Maintainability", "Model, feature and API logic should be separable and testable.",
         "Modular `src/` and `Website/ml/` packages, named constants, docstrings and a single canonical feature list."],
        ["Reproducibility", "The reported benchmark should be regenerable from the dataset and scripts.",
         "Fixed random seeds, a scripted asset builder, saved metrics JSON/CSV and versioned requirements."],
        ["Security", "The prototype should avoid exposing arbitrary filesystem paths or executing uploaded code.",
         "Uploaded files are parsed as data only; downloads are generated by the server; no shell execution from user input."],
        ["Portability", "The application should run on a standard laptop without cloud services.",
         "Pure-Python dependencies, relative project paths and no mandatory external database."],
    ],
    [1.24, 2.38, 2.65],
    caption="Table 2.5: Non-functional requirements and design response.",
    font_size=8.7,
)

h2("2.7 Design Principles")
bullets([
    "Temporal integrity first: every transformation that uses rainfall history is "
    "shifted so that only information available before the prediction date is used.",
    "Single source of truth: the 17 model features are defined once and reused by "
    "training, evaluation and inference code.",
    "Baselines are mandatory: a mean predictor and a lag-1 persistence predictor are "
    "reported alongside learned models so that improvements are measurable.",
    "Separate the two questions: rainfall amount is treated as a regression problem, "
    "while intensity is treated as a multi-class classification problem with its own "
    "metrics.",
    "Explain before deploying: feature importance, dry-day diagnostics and per-class "
    "recall are reviewed before a model is exposed in the interface.",
    "Fail visibly: out-of-range temperature, humidity, pressure or wind values produce "
    "a helpful validation error rather than a silent, physically impossible prediction.",
])

h2("2.8 Deployment View")
p(
    "In the demonstration environment, the Flask development server runs on "
    "localhost port 5000 and serves both the interface and the API. The trained "
    "models are loaded from the `models/` directory, while the dataset is read "
    "from the project workbook. For a production deployment, the same application "
    "could be placed behind a WSGI server such as Waitress or Gunicorn, with the "
    "model artefacts stored in a versioned object store and the dataset replaced "
    "by a scheduled meteorological feed. The current project intentionally keeps "
    "the deployment simple so that the complete system can be reproduced on a "
    "student laptop."
)


# ===========================================================================
# CHAPTER 3
# ===========================================================================
h1("CHAPTER 3: SYSTEM DESIGN")

h2("3.1 Design Approach")
p(
    "The design follows a data-centric pipeline rather than a conventional "
    "transaction-processing architecture. Raw observations enter through an "
    "ingestion and validation stage, are transformed into a feature matrix, and "
    "are then used to train and evaluate models. The same feature contract is "
    "reused at inference time so that a value entered in the browser is "
    "transformed in exactly the same way as a value seen during training."
)
p(
    "The system has two logical views. The offline view is concerned with "
    "reproducible experimentation: cleaning, EDA, feature engineering, training, "
    "cross-validation, tuning and artefact generation. The online view is "
    "concerned with interaction: input validation, model selection, prediction, "
    "advisory generation, explanation and export. Separating these views avoids "
    "the common failure mode in which exploratory code is quietly reused as "
    "production inference code with different assumptions."
)

h2("3.2 End-to-End Workflow")
add_figure(
    "fig_workflow.png",
    "Figure 3.1: End-to-end process workflow from data acquisition to the web interface.",
)
p(
    "The workflow begins with the multi-sheet Excel workbook and ends with a "
    "serialized model registry and an interactive interface. The chronological "
    "split is placed after feature engineering but before model fitting. This "
    "ordering is important: the split is defined on dates, not on randomly "
    "selected rows, and no statistic from the test period is used to scale or "
    "impute the training data."
)

h2("3.3 Use Case View")
add_figure(
    "fig_usecase.png",
    "Figure 3.2: Use case diagram for the RainVision platform.",
    width=5.7,
)
add_table(
    ["Actor", "Goal", "Main use cases"],
    [
        ["Meteorologist / domain expert", "Inspect historical climate behaviour and test model sensitivity.",
         "Upload or inspect the historical dataset; view dashboard and analytics; select a model; enter weather parameters; interpret feature attribution."],
        ["Citizen / decision maker", "Obtain a quick rainfall estimate and a plain-language advisory.",
         "Enter or select weather conditions; view predicted depth and intensity; read the urban-flood or agricultural advisory."],
        ["Student / researcher", "Reproduce experiments and compare models.",
         "Review evaluation metrics; compare regression and classification models; export prediction or metrics reports."],
        ["System administrator (prototype)", "Keep the application and model artefacts available.",
         "Start the Flask service; verify model health; replace serialized artefacts after retraining."],
    ],
    [1.42, 2.05, 2.80],
    caption="Table 3.1: Actors and their goals.",
    font_size=8.8,
)
p(
    "The primary use-case flow is: select a model, enter or load a weather "
    "scenario, validate the values, generate a prediction, inspect the intensity "
    "class and advisory, and optionally compare the output with another model. "
    "A secondary flow supports dataset exploration and batch prediction. The "
    "interface intentionally keeps the model choice visible so that a user does "
    "not mistake one algorithm's output for a universal forecast."
)

h2("3.4 Logical Data Model")
p(
    "The current implementation is file-based: the historical dataset is stored "
    "in an Excel workbook, processed tables are stored as CSV, and model "
    "metadata is stored as JSON. However, the entities and relationships are "
    "designed so that the same structure could be implemented in a relational "
    "database without changing the application logic. Figure 3.3 presents this "
    "logical entity-relationship model."
)
add_figure(
    "fig_erd.png",
    "Figure 3.3: Logical entity-relationship diagram for RainVision.",
)
p(
    "OBSERVATION is the master table of daily weather measurements. "
    "FEATURE_VECTOR is derived one-to-one from an observation and stores the "
    "engineered predictors. MODEL_REGISTRY records the trained algorithm and its "
    "evaluation metrics. PREDICTION stores the output produced by a model for a "
    "feature vector. CLIMATE_SUMMARY stores aggregated annual statistics used by "
    "the dashboard. In the prototype, these tables are represented by the "
    "workbook sheets, CSV exports and JSON metadata described in Chapter 4."
)

h2("3.5 Data Dictionary")
p(
    "Table 3.2 documents the logical fields, data types, constraints and "
    "descriptions. The sizes shown are storage-oriented suggestions for a future "
    "relational implementation; the Python implementation uses pandas dtypes "
    "and JSON serialization."
)
add_table(
    ["Sr.", "Table / field", "Data type & size", "Constraints", "Description"],
    [
        ["1", "OBSERVATION.observation_id", "BIGINT (20)", "PK, NOT NULL, AUTO", "Surrogate key for one daily station observation."],
        ["2", "OBSERVATION.obs_date", "DATE", "NOT NULL, UNIQUE", "Calendar date of the 24-hour observation."],
        ["3", "OBSERVATION.location", "VARCHAR(80)", "NOT NULL", "Station name (Metropolis Central Station)."],
        ["4", "OBSERVATION.temperature", "DECIMAL(5,2)", "CHECK (-10 to 60)", "Ambient dry-bulb temperature in \u00b0C."],
        ["5", "OBSERVATION.humidity", "DECIMAL(5,2)", "CHECK (0 to 100)", "Near-surface relative humidity in percent."],
        ["6", "OBSERVATION.pressure", "DECIMAL(7,2)", "CHECK (850 to 1100)", "Sea-level barometric pressure in hPa."],
        ["7", "OBSERVATION.wind_speed", "DECIMAL(6,2)", "CHECK (0 to 180)", "10-metre horizontal wind speed in km/h."],
        ["8", "OBSERVATION.previous_rainfall", "DECIMAL(7,2)", "CHECK (>= 0)", "Lag-1 daily rainfall in mm."],
        ["9", "OBSERVATION.rainfall", "DECIMAL(7,2)", "CHECK (>= 0)", "Target 24-hour accumulated rainfall in mm."],
        ["10", "OBSERVATION.rainfall_category", "VARCHAR(20)", "NOT NULL", "Intensity class derived from rainfall depth."],
        ["11", "OBSERVATION.is_monsoon", "TINYINT(1)", "CHECK (0 or 1)", "Flag for June\u2013September monsoon season."],
        ["12", "FEATURE_VECTOR.feature_id", "BIGINT (20)", "PK, NOT NULL", "Surrogate key for an engineered feature row."],
        ["13", "FEATURE_VECTOR.observation_id", "BIGINT (20)", "FK, UNIQUE, NOT NULL", "One-to-one link to OBSERVATION."],
        ["14", "FEATURE_VECTOR.rain_lag_1_to_3", "DECIMAL(7,2) \u00d7 3", "CHECK (>= 0)", "Rainfall on the previous three days."],
        ["15", "FEATURE_VECTOR.rolling_stats", "DECIMAL(9,3) \u00d7 4", "CHECK (>= 0)", "7-day mean/sum/max and 14-day mean of prior rainfall."],
        ["16", "FEATURE_VECTOR.calendar_terms", "DECIMAL(9,6) \u00d7 2", "CHECK (-1 to 1)", "Sine and cosine of day-of-year."],
        ["17", "FEATURE_VECTOR.pressure_diff_1", "DECIMAL(6,2)", "CHECK (-50 to 50)", "One-day pressure tendency in hPa."],
        ["18", "MODEL_REGISTRY.model_id", "BIGINT (20)", "PK, NOT NULL", "Surrogate key for a trained model."],
        ["19", "MODEL_REGISTRY.model_name", "VARCHAR(80)", "NOT NULL", "Human-readable model name."],
        ["20", "MODEL_REGISTRY.algorithm", "VARCHAR(80)", "NOT NULL", "Estimator family or ensemble definition."],
        ["21", "MODEL_REGISTRY.r2_score", "DECIMAL(6,4)", "CHECK (-1 to 1)", "Hold-out coefficient of determination."],
        ["22", "MODEL_REGISTRY.mae_mm", "DECIMAL(7,3)", "CHECK (>= 0)", "Hold-out mean absolute error in mm."],
        ["23", "MODEL_REGISTRY.artifact_path", "VARCHAR(255)", "NOT NULL", "Relative path to the serialized joblib artefact."],
        ["24", "PREDICTION.prediction_id", "BIGINT (20)", "PK, NOT NULL", "Surrogate key for one prediction event."],
        ["25", "PREDICTION.feature_id", "BIGINT (20)", "FK, NOT NULL", "Feature vector used for the prediction."],
        ["26", "PREDICTION.predicted_mm", "DECIMAL(7,2)", "CHECK (>= 0)", "Non-negative predicted rainfall depth."],
        ["27", "PREDICTION.intensity_class", "VARCHAR(20)", "NOT NULL", "Predicted intensity class."],
        ["28", "PREDICTION.advisory", "TEXT", "NOT NULL", "Generated public-safety or agricultural advisory."],
        ["29", "CLIMATE_SUMMARY.summary_id", "BIGINT (20)", "PK, NOT NULL", "Surrogate key for an annual summary."],
        ["30", "CLIMATE_SUMMARY.year", "SMALLINT (4)", "UNIQUE, NOT NULL", "Calendar year of the summary."],
        ["31", "CLIMATE_SUMMARY.total_rainfall_mm", "DECIMAL(9,2)", "CHECK (>= 0)", "Annual cumulative rainfall."],
        ["32", "CLIMATE_SUMMARY.rainy_days", "SMALLINT (3)", "CHECK (0 to 366)", "Number of days with rainfall above 0.05 mm."],
    ],
    [0.38, 2.28, 1.24, 1.10, 1.27],
    caption="Table 3.2: Logical data dictionary.",
    font_size=7.6,
    center_cols={0},
)

h2("3.6 Sample Records")
p(
    "The following sample rows illustrate the logical structure. They are "
    "representative records derived from the project dataset and model outputs; "
    "the exact values are not intended to reconstruct the full table."
)
add_table(
    ["observation_id", "obs_date", "location", "temp", "humidity", "pressure", "wind", "rainfall"],
    [
        ["1", "2026-10-31", "Metropolis Central", "28.1", "58", "1009.6", "11.2", "0.00"],
        ["2", "2026-10-30", "Metropolis Central", "28.4", "56", "1007.3", "13.8", "0.80"],
        ["3", "2026-10-29", "Metropolis Central", "28.5", "40", "1005.1", "13.2", "0.60"],
        ["4", "2026-10-28", "Metropolis Central", "29.7", "28", "1006.4", "14.3", "0.00"],
        ["5", "2026-10-27", "Metropolis Central", "30.7", "31", "1007.6", "13.5", "0.00"],
    ],
    [0.85, 0.82, 1.22, 0.55, 0.62, 0.68, 0.55, 0.68],
    caption="Table 3.3: Sample OBSERVATION records.",
    font_size=7.8,
    center_cols={0, 1, 3, 4, 5, 6, 7},
)

add_table(
    ["feature_id", "observation_id", "rain_lag_1", "roll_mean_7", "roll_sum_7", "sin_doy", "cos_doy", "monsoon"],
    [
        ["1", "1", "0.00", "0.11", "0.80", "-0.71", "0.70", "0"],
        ["2", "2", "0.80", "0.09", "0.60", "-0.69", "0.73", "0"],
        ["3", "3", "0.60", "0.00", "0.00", "-0.66", "0.75", "0"],
        ["4", "4", "0.00", "0.00", "0.00", "-0.63", "0.77", "0"],
        ["5", "5", "0.00", "0.00", "0.00", "-0.61", "0.79", "0"],
    ],
    [0.65, 0.90, 0.72, 0.90, 0.88, 0.72, 0.72, 0.72],
    caption="Table 3.4: Sample FEATURE_VECTOR records.",
    font_size=7.8,
    center_cols=set(range(8)),
)

add_table(
    ["prediction_id", "feature_id", "model_name", "predicted_mm", "intensity_class", "created_at"],
    [
        ["P-1001", "1", "Random Forest", "0.00", "Dry / Trace", "2026-10-31 18:20"],
        ["P-1002", "2", "Random Forest", "0.80", "Light", "2026-10-30 18:22"],
        ["P-1003", "3", "Random Forest", "0.60", "Light", "2026-10-29 18:25"],
        ["P-1004", "4", "Hurdle", "0.00", "Dry / Trace", "2026-10-28 18:27"],
        ["P-1005", "5", "Hurdle", "0.00", "Dry / Trace", "2026-10-27 18:30"],
    ],
    [0.88, 0.72, 1.12, 0.92, 1.05, 1.58],
    caption="Table 3.5: Sample PREDICTION records.",
    font_size=7.8,
    center_cols={0, 1, 3, 4, 5},
)

add_table(
    ["model_id", "model_name", "algorithm", "r2_score", "mae_mm", "artifact_path"],
    [
        ["M-01", "Hurdle Regressor", "RF occurrence + RF severity", "0.6465", "1.775", "models/hurdle_model.joblib"],
        ["M-02", "Random Forest", "100-tree ensemble", "0.6035", "1.835", "models/random_forest_model.joblib"],
        ["M-03", "Gradient Boosting", "Sequential boosted trees", "0.5732", "1.848", "models/gradient_boosting_model.joblib"],
        ["M-04", "Ridge Regression", "L2-regularised linear model", "0.3860", "2.931", "models/regression_model.joblib"],
        ["M-05", "Decision Tree", "Single CART regressor", "0.0551", "2.232", "models/regression_model.joblib"],
    ],
    [0.58, 1.18, 1.70, 0.78, 0.72, 1.31],
    caption="Table 3.6: Sample MODEL_REGISTRY records.",
    font_size=7.8,
    center_cols={0, 3, 4},
)

add_table(
    ["summary_id", "year", "total_rainfall_mm", "rainy_days", "avg_temp_c"],
    [
        ["S-01", "2022", "1014.7", "112", "27.4"],
        ["S-02", "2023", "1035.9", "125", "27.4"],
        ["S-03", "2024", "1335.1", "118", "27.8"],
        ["S-04", "2025", "945.6", "137", "28.4"],
        ["S-05", "2026", "747.7", "118", "29.9"],
    ],
    [0.90, 0.62, 1.35, 0.98, 1.05],
    caption="Table 3.7: Sample CLIMATE_SUMMARY records.",
    font_size=7.8,
    center_cols={0, 1, 2, 3, 4},
)
p(
    "The rainy-day counts and average temperatures in the sample climate table "
    "are illustrative values for the schema; the rainfall totals match the "
    "verified annual sums used in Chapter 6. In the actual workbook, the "
    "Annual_Climate_Summary sheet contains the complete computed values.",
    size=10, italic=True,
)

h2("3.7 Interface Design")
p(
    "The interface uses a persistent top navigation bar and a card-based content "
    "layout. Each page answers one primary question, and the visual hierarchy "
    "keeps the numerical result above supporting charts."
)
add_table(
    ["Page", "Primary purpose", "Key components"],
    [
        ["Dashboard", "Provide an immediate climate and dataset overview.", "KPI cards, latest prediction, recent 30-day trend, rainfall distribution, monthly and annual charts."],
        ["Rainfall Prediction", "Collect weather inputs and generate a live forecast.", "Preset scenarios, range sliders, model selector, predicted depth, intensity gauge, advisory and attribution."],
        ["Model Comparison", "Show how compatible models differ on the same observation.", "Model cards, side-by-side predictions, metric table and comparison chart."],
        ["Dataset Explorer", "Inspect the raw historical record.", "Search, year filter, rainfall filter, sortable table and pagination."],
        ["Historical Analytics", "Explore long-run climate behaviour.", "Annual anomalies, seasonal profiles and trend charts."],
        ["About Project", "Explain scope, methodology and limitations.", "Project narrative, technology summary and responsible-use note."],
    ],
    [1.35, 2.20, 2.72],
    caption="Table 3.8: Interface pages and their design purpose.",
    font_size=8.8,
)

h2("3.8 Prediction Sequence")
p(
    "A prediction request follows a deterministic sequence that is repeated in "
    "the Flask service and in the standalone inference module:"
)
numbered([
    "The browser collects temperature, humidity, pressure, wind speed, previous "
    "rainfall and an optional date.",
    "The API validates presence, numeric type and physical bounds for each field.",
    "The feature builder derives cyclical calendar terms and fills the lag and "
    "rolling features from the supplied antecedent rainfall.",
    "The selected regressor returns a continuous depth, which is clipped to a "
    "non-negative value.",
    "The classifier returns an intensity class; if the class is Dry/Trace and the "
    "depth is below 15 mm, the consistency gate sets the depth to zero.",
    "The advisory engine maps the class and depth to a public-safety or "
    "agricultural message.",
    "The API returns the prediction, class, advisory, input summary and a "
    "prediction identifier, and the interface renders the gauge and cards.",
])
p(
    "The consistency gate is a pragmatic design choice. It prevents a regression "
    "model from reporting a small positive depth on a day that the classifier has "
    "already classified as dry, while preserving a large predicted depth if the "
    "two models disagree strongly. This behaviour is documented so that it is not "
    "mistaken for an additional learned model."
)

h2("3.9 Implementation Note on Persistence")
p(
    "Because the project is a single-user academic prototype, a full relational "
    "database would add deployment overhead without improving the demonstrated "
    "machine learning outcomes. The workbook and CSV files are therefore the "
    "system of record, while JSON metadata records model version, feature order "
    "and evaluation metrics. The logical schema in this chapter is still useful: "
    "it documents the intended relationships and provides a straightforward "
    "migration path to PostgreSQL or SQLite if the application is extended to "
    "multiple stations, users or scheduled feeds."
)


# ===========================================================================
# CHAPTER 4
# ===========================================================================
h1("CHAPTER 4: DATASET")

h2("4.1 Dataset Source and Provenance")
p(
    "The project uses a daily historical weather workbook named "
    "`RainVision_Historical_1985_to_Today.xlsx`. The observations are attributed "
    "to the Metropolis Central Station at approximately 23.025\u00b0 N, "
    "72.5714\u00b0 E, at an elevation of 55 m above mean sea level. This station "
    "is treated as representative of the semi-arid, monsoon-dominated climate of "
    "the Gujarat corridor. The dataset was compiled from ECMWF ERA5 reanalysis "
    "records and packaged with the project so that the experiments do not depend "
    "on a live network connection."
)
p(
    "The workbook is deliberately more than a single flat table. It contains the "
    "daily observations, pre-computed annual and monthly summaries, dataset "
    "metadata, the held-out evaluation period, regression and classification "
    "results, feature importances and demonstration scenarios. For modelling, "
    "only the `Rainfall_Data_1985_to_Today` sheet is used; the other sheets serve "
    "as documentation, cross-checks and presentation assets."
)
p(
    "The record begins on 1 January 1985 and ends on 31 October 2026, covering "
    "15,279 daily rows and 42 calendar years. The final year is partial because "
    "the extract ends in October 2026; this is stated explicitly so that the "
    "annual total for 2026 (747.7 mm) is not compared naively with a complete "
    "year. The mean daily rainfall is 2.09 mm, the median is 0.0 mm and the "
    "standard deviation is 10.33 mm."
)

h2("4.2 Dataset Structure")
p(
    "The raw workbook has 13 columns. Seven fields identify or describe the "
    "observation, five are meteorological measurements, and one is the target "
    "rainfall depth. The `previous_rainfall`, `rainfall_category` and "
    "`is_monsoon` fields are convenience fields; the pipeline recomputes the "
    "category and monsoon flag from the date and target so that the modelling "
    "logic does not depend on a possibly inconsistent stored label."
)
add_table(
    ["No.", "Field", "Data type", "Unit / values", "Description"],
    [
        ["1", "date", "datetime64", "YYYY-MM-DD", "Calendar date of the daily observation."],
        ["2", "year", "int64", "1985\u20132026", "Calendar year, retained for grouping and audit."],
        ["3", "month", "int64", "1\u201312", "Calendar month, retained for seasonality checks."],
        ["4", "day", "int64", "1\u201331", "Day of month."],
        ["5", "location", "object", "Station name", "Metropolis Central Station."],
        ["6", "temperature", "float64", "\u00b0C", "Ambient dry-bulb temperature."],
        ["7", "humidity", "int64", "%", "Near-surface relative humidity."],
        ["8", "pressure", "float64", "hPa", "Sea-level barometric pressure."],
        ["9", "wind_speed", "float64", "km/h", "10-metre horizontal wind speed."],
        ["10", "previous_rainfall", "float64", "mm", "Lag-1 daily rainfall supplied in the workbook."],
        ["11", "rainfall", "float64", "mm", "Target: 24-hour accumulated rainfall."],
        ["12", "rainfall_category", "object", "5 classes", "Stored intensity label; recomputed during feature engineering."],
        ["13", "is_monsoon", "int64", "0 / 1", "Stored monsoon flag; recomputed from the month."],
    ],
    [0.42, 1.36, 0.93, 1.12, 2.44],
    caption="Table 4.1: Dataset schema and field descriptions.",
    font_size=8.5,
    center_cols={0, 2, 3},
)
p(
    "The seven meteorological inputs used by the production inference module are "
    "temperature, humidity, pressure, wind speed, previous-day rainfall and the "
    "date-derived calendar terms. The model does not use the stored year, month "
    "or day fields directly; those are replaced by sine and cosine encodings of "
    "day-of-year, which preserve the cyclical nature of the annual cycle."
)

h2("4.3 Target Variable and Intensity Classes")
p(
    "The continuous target is `rainfall`, measured in millimetres over a 24-hour "
    "period. Because the distribution is strongly zero-inflated, the project "
    "also evaluates a five-class intensity target. The thresholds follow common "
    "operational practice and separate ordinary monsoon showers from "
    "high-impact torrential events."
)
add_table(
    ["Class", "Definition (mm)", "Count", "Share"],
    [
        ["Dry / Trace", "rainfall \u2264 0.05", "11,214", "73.39%"],
        ["Light", "0.05 < rainfall \u2264 2.5", "2,410", "15.77%"],
        ["Moderate", "2.5 < rainfall \u2264 15.0", "1,113", "7.28%"],
        ["Heavy", "15.0 < rainfall \u2264 50.0", "422", "2.76%"],
        ["Torrential", "rainfall > 50.0", "120", "0.79%"],
        ["Total", "\u2014", "15,279", "100.00%"],
    ],
    [1.55, 2.35, 1.10, 1.12],
    caption="Table 4.2: Rainfall intensity classes and their frequency.",
    font_size=9,
    center_cols={1, 2, 3},
    bold_first_col=False,
)
p(
    "The five-tier scheme is a deliberate extension of the simpler four-tier "
    "labels used in some earlier notebooks. Separating Heavy (15\u201350 mm) from "
    "Torrential (>50 mm) makes the rare extreme cases visible in the confusion "
    "matrix and prevents a model from being credited with a good Heavy-class "
    "score simply because it predicts the lower end of the range."
)

h2("4.4 Data Quality Assessment")
p(
    "A formal quality check was performed before modelling. The raw sheet "
    "contains no missing values and no duplicate dates. The date sequence is "
    "continuous for the covered period, and all meteorological values fall "
    "within physically plausible bounds. The maximum rainfall of 339.9 mm is "
    "large but not impossible for a monsoon station; it is retained as a genuine "
    "extreme rather than being treated as a data-entry error."
)
add_table(
    ["Check", "Result", "Action taken"],
    [
        ["Total rows", "15,279", "All rows retained after validation."],
        ["Columns", "13", "Twelve descriptive/measurement fields plus the date key."],
        ["Missing values", "0", "No imputation required for the raw sheet."],
        ["Duplicate dates", "0", "Sorted chronologically and reset to a clean index."],
        ["Date range", "1985-01-01 to 2026-10-31", "Chronological order enforced before feature engineering."],
        ["Temperature range", "13.6\u201338.6 \u00b0C", "Within the configured physical bounds of \u221210 to 60 \u00b0C."],
        ["Humidity range", "8\u201398%", "Within 0\u2013100%; no clipping required."],
        ["Pressure range", "980.7\u20131015.4 hPa", "Within 850\u20131100 hPa; plausible for the station."],
        ["Wind range", "5.4\u201357.5 km/h", "Within 0\u2013180 km/h; extreme but physically possible."],
        ["Rainfall range", "0.0\u2013339.9 mm", "Extremes retained; target is not clipped during training."],
        ["Dry days", "11,214 (73.39%)", "Reported separately through dry-day diagnostics."],
        ["Wet days", "4,065 (26.61%)", "Wet-day MAE used as a secondary regression metric."],
    ],
    [1.55, 2.15, 2.57],
    caption="Table 4.3: Data quality checks and actions.",
    font_size=8.6,
)

h2("4.5 Temporal Split")
p(
    "The benchmark uses a strict forward-in-time split. The first 80% of the "
    "chronologically sorted rows form the training set; the last 20% form the "
    "test set. The split point is 19 June 2018. No test observation is used for "
    "fitting, scaling, imputation or feature selection. This is a more demanding "
    "and more realistic evaluation than a random 80/20 split because the test "
    "period includes seasons and years that the model has never seen."
)
add_table(
    ["Partition", "Rows", "Date range", "Share", "Purpose"],
    [
        ["Training", "12,223", "1985-01-01 to 2018-06-19", "80.0%", "Fit all candidate models and learn preprocessing statistics."],
        ["Test (hold-out)", "3,056", "2018-06-20 to 2026-10-31", "20.0%", "Final comparison on unseen future observations."],
        ["Total", "15,279", "1985-01-01 to 2026-10-31", "100.0%", "\u2014"],
    ],
    [1.18, 0.75, 2.45, 0.70, 1.19],
    caption="Table 4.4: Chronological train\u2013test partition.",
    font_size=8.8,
    center_cols={1, 2, 3},
)
p(
    "The final 20% is not a random sample of years: it contains the 2018 "
    "post-monsoon period, the 2019\u20132025 monsoon seasons and the partial 2026 "
    "season. This makes the evaluation sensitive to interannual variability, "
    "including the very wet 2019, 2024 and 2025 seasons and the comparatively dry "
    "2025\u20132026 transition. A model that only memorises the training-era "
    "distribution will therefore be penalised."
)

h2("4.6 Annual Climatology")
p(
    "The 42 annual totals have a mean of 759.4 mm and a standard deviation of "
    "354.9 mm. The minimum is 140.0 mm (1987) and the maximum is 1,617.0 mm "
    "(2006). The monsoon months dominate the water budget: June, July, August "
    "and September together account for 95.27% of the total recorded rainfall. "
    "July alone contributes 40.34% of the monthly total, followed by August at "
    "30.57% and September at 15.27%."
)
add_table(
    ["Statistic", "Value", "Interpretation"],
    [
        ["Annual mean", "759.4 mm", "Long-run average annual accumulation."],
        ["Annual standard deviation", "354.9 mm", "Large interannual variability."],
        ["Minimum annual total", "140.0 mm (1987)", "Severe drought-like year in the record."],
        ["Maximum annual total", "1,617.0 mm (2006)", "Exceptionally wet monsoon year."],
        ["Monsoon share", "95.27%", "June\u2013September dominates the annual water budget."],
        ["Wettest month (total)", "July, 12,865.5 mm", "Peak monsoon month across the full record."],
        ["Driest month (total)", "February, 39.0 mm", "Winter dryness; mostly trace events."],
        ["Maximum daily rainfall", "339.9 mm", "Extreme event retained for model stress testing."],
    ],
    [1.80, 2.13, 2.34],
    caption="Table 4.5: Key climatological statistics.",
    font_size=8.8,
)

h2("4.7 Workbook Sheets")
add_table(
    ["Sheet", "Rows / role", "Contents"],
    [
        ["Rainfall_Data_1985_to_Today", "15,279 daily rows", "Primary modelling table with date, weather, previous rainfall and target."],
        ["Annual_Climate_Summary", "42 annual rows", "Annual totals, rainy days, mean temperature and anomaly indicators."],
        ["Monthly_Seasonality", "12 monthly rows", "Long-run monthly totals and averages."],
        ["Dataset_Metadata", "Key\u2013value", "Station details, date range, source and column descriptions."],
        ["Heldout_Test_Data", "3,056 rows", "The chronological test partition used for final evaluation."],
        ["Regression_Results", "8 model rows", "Stored regression benchmark metrics."],
        ["Classification_Results", "5 model rows", "Stored classification benchmark metrics."],
        ["Feature_Importances", "17 feature rows", "Tree-based importance values for the final models."],
        ["Scenario_Predictions", "4 scenarios", "Illustrative dry, pre-monsoon, monsoon and cyclonic cases."],
    ],
    [2.30, 1.23, 2.74],
    caption="Table 4.6: Contents of the project workbook.",
    font_size=8.7,
)

h2("4.8 Dataset Limitations")
bullets([
    "Single-station coverage: the data describe one location and cannot capture "
    "spatial gradients across a district or state.",
    "Daily aggregation: sub-daily cloudbursts are summed into a 24-hour value, "
    "so the timing and short-duration intensity of rainfall are lost.",
    "Reanalysis provenance: ERA5 is a modelled reanalysis product, not a direct "
    "rain-gauge measurement at every grid point. It is suitable for a "
    "methodological study but should not be treated as a gauge record.",
    "Partial final year: 2026 ends on 31 October, so the 2026 annual total is not "
    "directly comparable with complete years.",
    "No explicit station-quality flags: the workbook does not include instrument "
    "maintenance or quality-control codes, so the quality statement is limited "
    "to the checks that can be performed on the tabular values.",
])


# ===========================================================================
# CHAPTER 5
# ===========================================================================
h1("CHAPTER 5: DATA PRE-PROCESSING")

h2("5.1 Pre-processing Pipeline")
p(
    "Pre-processing is organised as a deterministic sequence: ingest, validate, "
    "sort, clean, derive calendar features, derive antecedent features, create "
    "the classification target, and split chronologically. The order matters. "
    "If rolling features were computed after a random split, or if scaling were "
    "fitted on the full dataset, the test score would be contaminated by future "
    "information. The pipeline therefore treats the split boundary as a hard "
    "barrier."
)
p(
    "The final modelling matrix contains 17 predictors. Seven are direct "
    "meteorological inputs or lagged versions of them; four summarise "
    "antecedent rainfall over 7 and 14 days; two encode the annual cycle; one "
    "captures pressure tendency; and one is a monsoon-season indicator. The "
    "target is retained separately for regression, and a five-class label is "
    "derived for classification."
)

h2("5.2 Ingestion and Cleaning")
p(
    "The raw sheet is read with pandas and the date column is converted to a "
    "datetime type. Records are sorted by date, duplicate dates are removed if "
    "present, and the index is reset. Numeric columns are coerced to numeric "
    "types so that a stray text value becomes a missing value rather than "
    "silently corrupting a calculation. The pipeline then checks the physical "
    "domains: temperature between \u221210 and 60 \u00b0C, humidity between 0 "
    "and 100%, pressure between 850 and 1100 hPa, wind between 0 and 180 km/h, "
    "and rainfall non-negative."
)
p(
    "In the supplied workbook, all 15,279 rows pass these checks and no "
    "imputation is required. The cleaning stage is nevertheless retained because "
    "the same code will be used when a new station extract or a user-uploaded "
    "CSV is introduced. A future version can replace the hard failure with a "
    "quarantine table that records rejected rows and the reason for rejection."
)
add_table(
    ["Step", "Operation", "Result on the project dataset"],
    [
        ["1", "Read the `Rainfall_Data_1985_to_Today` sheet.", "15,279 rows \u00d7 13 columns loaded."],
        ["2", "Parse `date` and sort ascending.", "Continuous 1985-01-01 to 2026-10-31 sequence."],
        ["3", "Drop duplicate dates, keeping the first occurrence.", "0 duplicates found; no rows removed."],
        ["4", "Coerce numeric weather fields and count missing values.", "0 missing values in the modelling columns."],
        ["5", "Validate physical ranges.", "All values within configured bounds."],
        ["6", "Recompute monsoon flag and intensity category.", "Consistent labels derived from date and rainfall."],
        ["7", "Reset the index and preserve the date column.", "Clean, ordered modelling table."],
    ],
    [0.45, 3.12, 2.70],
    caption="Table 5.1: Cleaning and validation steps.",
    font_size=8.8,
    center_cols={0},
)

h2("5.3 Missing-Value Treatment")
p(
    "No missing values were found in the raw data, so no statistical imputation "
    "was applied to the observed weather fields. The engineered lag and rolling "
    "features create missing values at the beginning of the series because there "
    "is no prior observation for the first few days. The final benchmark uses a "
    "zero-fill policy for those warm-up rows: a missing lag is interpreted as "
    "\u201cno recorded antecedent rainfall\u201d rather than as an unknown value. "
    "This is conservative for a dry-start series and avoids dropping the first "
    "days of 1985."
)
p(
    "An alternative implementation drops the first 14 rows, once the longest "
    "rolling window is available. Both approaches are leakage-safe; the zero-fill "
    "approach is used in the reported benchmark because it preserves the full "
    "42-year record and keeps the train/test row counts aligned with the "
    "reproducible asset builder. The choice is documented here because the "
    "difference in row count can otherwise look like an inconsistency between "
    "notebooks."
)

h2("5.4 Outlier Policy")
p(
    "Rainfall extremes are the most important events in the dataset and are "
    "therefore not removed. The 99th percentile is 42.94 mm and the maximum is "
    "339.9 mm; the gap confirms a heavy right tail. Clipping or winsorising the "
    "target would make the regression metrics look better while removing exactly "
    "the events that a flood-warning application needs to detect. Instead, the "
    "evaluation reports wet-day MAE and a dedicated dry-day diagnostic, and the "
    "residual plots expose the under-prediction of large events."
)
p(
    "Input variables are also left unscaled for tree models, because decision "
    "trees are invariant to monotonic transformations. Linear models and logistic "
    "regression are wrapped in a scikit-learn pipeline with `StandardScaler`, "
    "which is fitted only on the training partition. This keeps the comparison "
    "fair while avoiding leakage from the test set."
)

h2("5.5 Feature Engineering")
p(
    "The feature set is designed around three meteorological ideas. First, the "
    "annual cycle controls the monsoon and is represented cyclically so that "
    "31 December and 1 January are adjacent rather than far apart. Second, "
    "antecedent moisture matters: rainfall yesterday and over the previous week "
    "changes soil saturation and the likelihood of runoff. Third, atmospheric "
    "change matters: a falling barometer often precedes a depression or storm "
    "front. Table 5.2 documents all 17 features."
)
add_table(
    ["No.", "Feature", "Type", "Definition / formula", "Purpose"],
    [
        ["1", "temperature", "Input", "Observed dry-bulb temperature (\u00b0C).", "Thermodynamic state and seasonal context."],
        ["2", "humidity", "Input", "Observed relative humidity (%).", "Proximity to saturation; strongest univariate signal."],
        ["3", "pressure", "Input", "Sea-level pressure (hPa).", "Synoptic setting; low pressure favours convection."],
        ["4", "wind_speed", "Input", "10-m wind speed (km/h).", "Moisture advection and convective mixing."],
        ["5", "rain_lag_1", "Lag", "rainfall(t\u22121)", "Persistence and immediate antecedent moisture."],
        ["6", "rain_lag_2", "Lag", "rainfall(t\u22122)", "Short-memory rainfall history."],
        ["7", "rain_lag_3", "Lag", "rainfall(t\u22123)", "Additional persistence information."],
        ["8", "rain_roll_mean_7", "Rolling", "mean(rainfall(t\u22127)\u2026rainfall(t\u22121))", "Average wetness of the previous week."],
        ["9", "rain_roll_sum_7", "Rolling", "sum(rainfall(t\u22127)\u2026rainfall(t\u22121))", "Cumulative water input over seven days."],
        ["10", "rain_roll_max_7", "Rolling", "max(rainfall(t\u22127)\u2026rainfall(t\u22121))", "Recent peak intensity."],
        ["11", "rain_roll_mean_14", "Rolling", "mean(rainfall(t\u221214)\u2026rainfall(t\u22121))", "Longer soil-moisture memory."],
        ["12", "temp_lag_1", "Lag", "temperature(t\u22121)", "Short-term thermal inertia."],
        ["13", "humidity_lag_1", "Lag", "humidity(t\u22121)", "Moisture persistence."],
        ["14", "pressure_diff_1", "Difference", "pressure(t) \u2212 pressure(t\u22121)", "Barometric tendency; negative values signal approaching unsettled weather."],
        ["15", "sin_day_of_year", "Cyclical", "sin(2\u03c0 \u00b7 DOY / 365.25)", "Smooth annual seasonality."],
        ["16", "cos_day_of_year", "Cyclical", "cos(2\u03c0 \u00b7 DOY / 365.25)", "Smooth annual seasonality, phase-shifted."],
        ["17", "is_monsoon", "Binary", "1 if month \u2208 {6,7,8,9}, else 0", "Explicit monsoon-season indicator."],
    ],
    [0.40, 1.43, 0.77, 2.35, 1.32],
    caption="Table 5.2: Engineered model features.",
    font_size=7.9,
    center_cols={0, 2},
)

h2("5.6 Encoding and Scaling")
p(
    "Cyclical encoding is used for day-of-year rather than a raw integer. A raw "
    "day number would make 31 December (365) and 1 January (1) appear maximally "
    "far apart even though they are adjacent in the seasonal cycle. The sine and "
    "cosine pair maps the year onto a unit circle, preserving continuity. The "
    "monsoon flag is retained in addition to the cyclical terms because the "
    "monsoon onset is a discrete regime change rather than a purely smooth "
    "sinusoid."
)
p(
    "Categorical text fields are not fed directly to the models. The target "
    "category is used only for classification, and the location field is constant "
    "for this single-station study. Linear and logistic models use standardised "
    "numeric inputs; tree-based models use the raw numeric values. The scaler is "
    "fitted inside a pipeline on the training fold only, so cross-validation "
    "does not leak test-fold means or variances."
)

h2("5.7 Leakage Controls")
add_table(
    ["Potential leakage", "Control implemented", "Why it matters"],
    [
        ["Random train/test split", "Chronological 80/20 split by date.", "Prevents the model from learning from future years."],
        ["Random cross-validation", "Expanding-window `TimeSeriesSplit` with five folds.", "Validation always follows training in time."],
        ["Future rainfall in lags", "All lags and rolling windows use `shift(1)` or earlier.", "The model only sees antecedent rainfall."],
        ["Scaling on full data", "Scaler fitted inside the training pipeline.", "Test-period means and variances remain unseen."],
        ["Target-derived category", "Category is derived from the target only for classification labels.", "The regression features never include the current target."],
        ["Duplicate dates", "Explicit duplicate check before sorting.", "Prevents the same day appearing in both partitions."],
        ["Tuning on test data", "Hyperparameters selected with time-series CV on training data only.", "The hold-out set remains an unbiased final check."],
    ],
    [1.65, 2.55, 2.07],
    caption="Table 5.3: Leakage risks and controls.",
    font_size=8.7,
)

h2("5.8 Final Modelling Matrix")
add_table(
    ["Property", "Value"],
    [
        ["Rows", "15,279 daily observations"],
        ["Raw columns", "13"],
        ["Engineered predictors", "17"],
        ["Regression target", "rainfall (mm), clipped at zero only for predictions, never for observed values"],
        ["Classification target", "Dry / Trace, Light, Moderate, Heavy, Torrential"],
        ["Training rows", "12,223 (1985-01-01 to 2018-06-19)"],
        ["Test rows", "3,056 (2018-06-20 to 2026-10-31)"],
        ["Random seed", "42 for all stochastic estimators"],
        ["Missing values in final matrix", "0 after warm-up handling"],
    ],
    [2.15, 4.12],
    caption="Table 5.4: Final modelling matrix.",
    font_size=9,
)

h2("5.9 Pre-processing Quality Checks")
p(
    "Before model fitting, the pipeline verifies that the feature matrix contains "
    "only numeric values, that the row count matches the number of dates, that "
    "the training and test date ranges do not overlap, and that the target is "
    "non-negative. It also checks that the feature order used for training is "
    "identical to the order saved in the metadata. This last check is important "
    "at inference time: scikit-learn estimators accept a DataFrame and silently "
    "use column order, so a mismatch would produce plausible but wrong "
    "predictions."
)


# ===========================================================================
# CHAPTER 6
# ===========================================================================
h1("CHAPTER 6: EXPLORATORY DATA ANALYSIS")

h2("6.1 Objectives of the Analysis")
p(
    "Exploratory data analysis (EDA) was used to understand the distribution of "
    "the target, the seasonal structure of the record, the relationships between "
    "meteorological variables, and the extent of the zero-inflation and extreme "
    "value problems. The findings directly shaped the modelling choices: they "
    "motivated the Hurdle model, the wet-day error metric, the class-weighted "
    "classifiers and the decision to retain rather than clip extreme rainfall."
)

h2("6.2 Descriptive Statistics")
add_table(
    ["Statistic", "Rainfall (mm)", "Temperature (\u00b0C)", "Humidity (%)", "Pressure (hPa)", "Wind (km/h)"],
    [
        ["Count", "15,279", "15,279", "15,279", "15,279", "15,279"],
        ["Mean", "2.09", "27.20", "53.79", "1002.18", "14.07"],
        ["Median", "0.00", "27.50", "51.00", "1002.40", "13.40"],
        ["Standard deviation", "10.33", "4.35", "18.77", "5.40", "4.20"],
        ["Minimum", "0.00", "13.6", "8.0", "980.7", "5.4"],
        ["95th percentile", "10.50", "33.80", "87.00", "1010.20", "21.70"],
        ["Maximum", "339.90", "38.6", "98.0", "1015.4", "57.5"],
    ],
    [1.30, 1.02, 1.02, 0.93, 1.06, 0.94],
    caption="Table 6.1: Descriptive statistics of the main meteorological variables.",
    font_size=8.6,
    center_cols=set(range(1, 6)),
)
p(
    "The contrast between the mean (2.09 mm) and the median (0.00 mm) is the "
    "clearest summary of the modelling challenge. More than half of all days are "
    "completely dry, yet the upper tail reaches 339.9 mm. The 95th percentile is "
    "10.5 mm and the 99th percentile is 42.94 mm, which means that a small number "
    "of days carry a disproportionate share of the annual total."
)

h2("6.3 Long-Run Rainfall Behaviour")
add_figure(
    "fig1_timeseries_annual.png",
    "Figure 6.1: Daily rainfall time series and annual totals, 1985\u20132026.",
)
p(
    "The daily series is dominated by isolated spikes rather than a stable "
    "background level. The 365-day moving average is deliberately included to "
    "make the low-frequency behaviour visible; it remains close to zero on the "
    "daily scale because dry days dominate. The annual bar chart shows strong "
    "interannual variability, with a notable cluster of wet years after 2019 and "
    "a much drier 2025\u20132026 period. The dashed line marks the 42-year mean of "
    "759 mm."
)
add_figure(
    "fig12_anomalies.png",
    "Figure 6.2: Annual rainfall anomaly relative to the 42-year mean.",
)
p(
    "The anomaly view makes the same information easier to compare across years. "
    "The 1986\u20131987 drought, the very wet 2006 and 2019 seasons, and the "
    "positive anomalies of 2020\u20132024 stand out. The presence of both "
    "multi-year wet spells and isolated dry years is a warning against assuming "
    "a stationary climate: a model trained on one decade may not transfer "
    "perfectly to the next."
)

h2("6.4 Distribution and Seasonality")
add_figure(
    "fig2_distribution_seasonality.png",
    "Figure 6.3: Wet-day distribution, intensity-class frequency and mean daily rainfall by month.",
)
p(
    "The wet-day histogram uses a logarithmic frequency axis because the "
    "distribution is extremely skewed: many light events and relatively few "
    "large events. The class bar chart shows the dominance of Dry/Trace days "
    "(73.4%), followed by Light (15.8%), Moderate (7.3%), Heavy (2.8%) and "
    "Torrential (0.8%). The monthly profile has a sharp monsoon peak in July, "
    "with August and September still substantially wetter than the winter and "
    "pre-monsoon months."
)
add_table(
    ["Month", "Total rainfall (mm)", "Share of annual total", "Mean daily rainfall (mm)"],
    [
        ["January", "58.6", "0.18%", "0.05"],
        ["February", "39.0", "0.12%", "0.03"],
        ["March", "81.8", "0.26%", "0.06"],
        ["April", "53.2", "0.17%", "0.04"],
        ["May", "184.4", "0.58%", "0.14"],
        ["June", "2,900.6", "9.09%", "2.30"],
        ["July", "12,865.5", "40.34%", "9.88"],
        ["August", "9,750.7", "30.57%", "7.49"],
        ["September", "4,869.7", "15.27%", "3.86"],
        ["October", "888.1", "2.78%", "0.68"],
        ["November", "149.4", "0.47%", "0.12"],
        ["December", "55.5", "0.17%", "0.04"],
    ],
    [1.30, 1.65, 1.55, 1.77],
    caption="Table 6.2: Monthly rainfall profile across the full record.",
    font_size=8.8,
    center_cols={1, 2, 3},
)
p(
    "June\u2013September accounts for 95.27% of recorded rainfall. This is the "
    "single most important seasonal fact in the dataset. It explains why the "
    "monsoon flag and the day-of-year encodings are useful, and why a model "
    "evaluated only on annual averages can hide large errors within the monsoon "
    "window."
)

h2("6.5 Correlation Analysis")
add_figure(
    "fig3_correlation.png",
    "Figure 6.4: Correlation matrix of rainfall and meteorological variables.",
    width=5.7,
)
p(
    "Among the continuous weather variables, humidity has the strongest positive "
    "linear correlation with rainfall (r = 0.37), followed by wind speed "
    "(r = 0.18). Pressure has a negative correlation (r = \u22120.28), consistent "
    "with the association between low-pressure systems and unsettled weather. "
    "Temperature has almost no overall linear correlation (r = \u22120.02) because "
    "its relationship with rainfall is non-monotonic and strongly seasonal. "
    "Previous-day rainfall (r = 0.41) and the monsoon flag (r = 0.26) are the "
    "strongest single predictors in the correlation matrix."
)
p(
    "Correlation is only a first look. A low linear correlation does not mean a "
    "variable is unimportant to a tree model, because trees can capture "
    "thresholds and interactions. Conversely, a moderate correlation can be "
    "driven by a shared seasonal trend rather than a causal mechanism. The "
    "feature-importance analysis in Chapter 11 is therefore used alongside these "
    "coefficients."
)

h2("6.6 Bivariate Relationships")
add_figure(
    "fig4_bivariate.png",
    "Figure 6.5: Rainfall versus humidity, pressure, temperature and wind speed with binned means.",
)
p(
    "The bivariate plots show why simple linear regression is insufficient. "
    "Rainfall remains near zero across most of the humidity range and then rises "
    "sharply above roughly 80% relative humidity. The pressure relationship is "
    "weaker but visibly negative at the low-pressure end. Temperature shows a "
    "broad monsoon-window bump rather than a monotonic trend. Wind speed has a "
    "long right tail and a weak positive association with rainfall. These "
    "non-linear and threshold-like patterns favour tree-based models and motivate "
    "the Hurdle formulation."
)

h2("6.7 Zero-Inflation Diagnostics")
p(
    "The dry-day share (73.39%) is not merely a descriptive curiosity; it changes "
    "the meaning of the standard metrics. A mean predictor can achieve a "
    "relatively low MAE because most observations are zero, yet it has a "
    "negative R\u00b2 on the held-out period. The project therefore reports MAE, "
    "RMSE, R\u00b2, wet-day MAE, dry-day MAE and bias together. The dry-day plot in "
    "Chapter 8 makes the distinction visible: a model that predicts a small "
    "positive amount on every dry day may look acceptable in aggregate but is "
    "operationally wrong."
)

h2("6.8 Key Observations")
bullets([
    "The target is zero-inflated and heavy-tailed; ordinary least squares alone "
    "is not an adequate model for the full distribution.",
    "The monsoon is the dominant seasonal signal, with 95.27% of rainfall "
    "occurring in June\u2013September.",
    "Humidity and antecedent rainfall are the strongest simple correlates of "
    "rainfall, while pressure is negatively associated with wet conditions.",
    "Annual totals vary by more than a factor of ten between the driest and "
    "wettest years, so a single global mean is a weak baseline.",
    "Class imbalance is severe: Torrential days are less than 1% of the record, "
    "so accuracy alone is misleading.",
    "Extreme values should be retained because they are the events of greatest "
    "operational interest, even though they make squared-error metrics noisy.",
    "The test period contains both very wet and relatively dry years, which is "
    "useful for assessing whether a model generalises beyond the training era.",
])


# ===========================================================================
# CHAPTER 7
# ===========================================================================
h1("CHAPTER 7: MACHINE LEARNING METHODOLOGY")

h2("7.1 Problem Formulation")
p(
    "Let an observation on day t be represented by a 17-dimensional feature "
    "vector x\u209c containing current weather, antecedent rainfall, pressure "
    "tendency and calendar encodings. The regression task is to learn a function "
    "f that estimates the 24-hour rainfall depth y\u209c \u2265 0:"
)
p("\u0177\u209c = f(x\u209c),   \u0177\u209c \u2265 0", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER,
  space_before=4, space_after=8)
p(
    "The classification task is to learn a function g that maps the same feature "
    "vector to one of five intensity classes c\u209c \u2208 {Dry/Trace, Light, "
    "Moderate, Heavy, Torrential}. The two tasks are related but not identical: "
    "a model can estimate a reasonable depth while assigning the wrong intensity "
    "label, especially near a class boundary. The project therefore evaluates "
    "both tasks and uses the classifier as a consistency gate in the application."
)
p(
    "The Hurdle formulation decomposes the regression problem into an occurrence "
    "stage and a severity stage. Let p\u209c = P(y\u209c > 0.05 | x\u209c) be the "
    "probability of a wet day from a binary classifier, and let s\u209c be the "
    "conditional severity predicted by a regressor trained only on wet days. The "
    "expected depth is:"
)
p("E[y\u209c | x\u209c] = p\u209c \u00b7 s\u209c", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER,
  space_before=4, space_after=4)
p(
    "The implementation supports two decision modes. The hard-threshold mode "
    "uses the binary class decision and sets the depth to zero when the gate "
    "predicts a dry day. The probability-weighted mode multiplies the probability "
    "by the severity estimate and is reported as a sensitivity analysis. The "
    "hard-threshold version is used for the primary benchmark because it has a "
    "clear interpretation and avoids multiplying a noisy probability by a large "
    "severity estimate on marginal days."
)

h2("7.2 Algorithm Selection")
p(
    "The model suite was chosen to span different inductive biases rather than to "
    "maximise the number of algorithms. Linear models provide an interpretable "
    "lower bound; a single tree exposes over-fitting; random forests reduce "
    "variance through bagging; gradient boosting reduces bias through sequential "
    "correction; and the Hurdle model directly addresses zero-inflation."
)
add_table(
    ["Model", "Family", "Why it was included"],
    [
        ["Baseline Mean", "Dummy regressor", "Establishes the score of predicting the training mean for every day."],
        ["Baseline Persistence", "Lag-1 rule", "Tests whether yesterday's rainfall is a stronger predictor than a learned model."],
        ["Linear Regression (OLS)", "Linear", "Provides an interpretable linear reference and reveals the limits of additive effects."],
        ["Ridge Regression", "Regularised linear", "Controls coefficient instability when correlated weather variables are present."],
        ["Decision Tree", "Single CART tree", "Captures thresholds and interactions but is prone to high variance."],
        ["Random Forest", "Bagged trees", "Reduces variance and handles non-linearity without extensive feature scaling."],
        ["Gradient Boosting", "Boosted trees", "Models subtle non-linear structure through sequential residual fitting."],
        ["Two-Stage Hurdle", "Occurrence + severity", "Separates the dry/wet decision from the conditional rainfall amount, directly addressing zero-inflation."],
        ["Majority Baseline", "Dummy classifier", "Shows the accuracy that can be obtained by always predicting Dry/Trace."],
        ["Logistic Regression", "Linear classifier", "Provides a balanced, interpretable multi-class reference."],
        ["Decision Tree Classifier", "Single tree", "Captures non-linear class boundaries but over-fits rare classes."],
        ["Random Forest Classifier", "Bagged trees", "Combines balanced class weights with non-linear decision boundaries."],
        ["Gradient Boosting Classifier", "Boosted trees", "Provides a strong sequential ensemble for intensity classification."],
    ],
    [1.55, 1.15, 3.57],
    caption="Table 7.1: Candidate models and rationale.",
    font_size=8.6,
)

h2("7.3 Baselines")
p(
    "Two regression baselines and one classification baseline are mandatory. The "
    "mean baseline predicts the training-set mean for every test day. The "
    "persistence baseline predicts yesterday's rainfall (`rain_lag_1`) and is a "
    "strong test in a monsoon climate because wet spells cluster. The majority "
    "classifier always predicts Dry/Trace. A learned model is only useful if it "
    "beats these references on the metrics that matter, not merely because it has "
    "a recognisable algorithm name."
)
p(
    "The persistence baseline is particularly informative for a zero-inflated "
    "series. It has a low dry-day error because yesterday is usually dry when "
    "today is dry, but it fails badly at the onset of a wet spell. The Hurdle "
    "model improves on persistence by combining antecedent rainfall with humidity "
    "and pressure tendency rather than relying on the previous value alone."
)

h2("7.4 Train\u2013Test Split and Validation Strategy")
p(
    "The final evaluation uses the chronological 80/20 split described in "
    "Chapter 4. The training period ends on 19 June 2018 and the test period "
    "starts on 20 June 2018. Hyperparameters are selected only within the "
    "training period using five-fold expanding-window `TimeSeriesSplit`. In each "
    "fold, the training window contains all earlier data and the validation "
    "window is the next contiguous block. The test set is touched once, after "
    "model selection, for the final comparison."
)
p(
    "This design answers a harder question than random cross-validation: can the "
    "model generalise forward in time? The trade-off is that the test period is a "
    "single contiguous era, so the result is sensitive to the particular climate "
    "of 2018\u20132026. The fold-level results are therefore reported alongside the "
    "hold-out result to show variability."
)
add_table(
    ["Design choice", "Setting", "Reason"],
    [
        ["Training share", "80% (12,223 rows)", "Large enough to fit tree ensembles while retaining a multi-year future test period."],
        ["Test share", "20% (3,056 rows)", "Covers 2018\u20132026 and includes several monsoon seasons."],
        ["Split direction", "Forward in time", "Prevents look-ahead leakage."],
        ["Cross-validation", "5-fold expanding window", "Uses all available history in each fold and validates on the future."],
        ["Tuning search", "4-fold time-series grid search", "Selects hyperparameters without touching the final test set."],
        ["Random seed", "42", "Makes the stochastic tree ensembles reproducible."],
        ["Prediction clipping", "max(0, prediction)", "Enforces the physical lower bound of rainfall."],
    ],
    [1.55, 1.95, 2.77],
    caption="Table 7.2: Validation design.",
    font_size=8.7,
)

h2("7.5 Training Configuration")
add_table(
    ["Model", "Key hyperparameters / configuration"],
    [
        ["Baseline Mean", "`DummyRegressor(strategy='mean')`."],
        ["Baseline Persistence", "Prediction = `rain_lag_1`; no fitting."],
        ["OLS", "Default `LinearRegression()` with intercept."],
        ["Ridge", "`StandardScaler` followed by `Ridge(alpha=10.0)`."],
        ["Decision Tree", "`max_depth=6`, `min_samples_split=10`, `random_state=42`."],
        ["Random Forest", "`n_estimators=100`, `max_depth=10`, `min_samples_split=5`, `random_state=42`."],
        ["Gradient Boosting", "`n_estimators=100`, `learning_rate=0.05`, `max_depth=4`, `random_state=42`."],
        ["Hurdle gate", "`RandomForestClassifier(n_estimators=100, max_depth=8, class_weight='balanced')`."],
        ["Hurdle severity", "`RandomForestRegressor(n_estimators=100, max_depth=10, min_samples_split=5)` trained on wet days only."],
        ["Logistic Regression", "`StandardScaler` + `LogisticRegression(max_iter=1000, class_weight='balanced')`."],
        ["Decision Tree Classifier", "`max_depth=6`, `min_samples_split=10`, `class_weight='balanced'`."],
        ["Random Forest Classifier", "`n_estimators=100`, `max_depth=8`, `min_samples_split=5`, `class_weight='balanced'`."],
        ["Gradient Boosting Classifier", "`n_estimators=100`, `learning_rate=0.05`, `max_depth=3`."],
    ],
    [1.62, 4.65],
    caption="Table 7.3: Training configuration of the candidate models.",
    font_size=8.4,
)

h2("7.6 Two-Stage Hurdle Model")
p(
    "The Hurdle model is the methodological centrepiece of the project. It is "
    "motivated by a simple fact: the process that decides whether it rains is not "
    "the same as the process that decides how much it rains. A single regressor "
    "trained on all days sees more than eleven thousand zeros and learns to shrink "
    "most predictions toward zero. A model trained only on wet days, by contrast, "
    "learns the conditional severity distribution but has no mechanism for "
    "deciding whether a day is wet."
)
numbered([
    "Stage 1 fits a balanced random-forest classifier to the binary target "
    "`rainfall > 0.05 mm`.",
    "Stage 2 fits a random-forest regressor on the subset of training days with "
    "`rainfall > 0.05 mm` only.",
    "At prediction time, the gate returns a wet/dry decision and the severity "
    "model returns a non-negative depth.",
    "The final hard-threshold prediction is the severity value on predicted-wet "
    "days and zero on predicted-dry days.",
    "A probability-weighted variant multiplies the gate probability by the "
    "severity estimate and is reported as a sensitivity check.",
])
p(
    "This decomposition has two practical benefits. First, it prevents the "
    "regressor from being dominated by the zero mass: the severity model is not "
    "trained on thousands of identical zeros. Second, it produces an explicit "
    "occurrence probability that can be shown to the user. The cost is additional "
    "complexity and the risk that stage-1 and stage-2 errors compound. The "
    "evaluation in Chapter 8 reports both overall and dry-day behaviour so that "
    "this trade-off is visible."
)

h2("7.7 Cross-Validation and Hyperparameter Tuning")
p(
    "The expanding-window cross-validation uses five folds. Fold 1 trains on the "
    "earliest 2,549 rows and validates on the next 2,546; each subsequent fold "
    "expands the training window by one validation block. The reported mean "
    "R\u00b2 is 0.6048 with a standard deviation of 0.086, and the mean RMSE is "
    "6.605 mm. The variability across folds is substantial, which is expected for "
    "a rainfall series with strong interannual differences."
)
p(
    "Random-forest regression was tuned with a time-series grid search over "
    "`n_estimators` \u2208 {50, 100, 150}, `max_depth` \u2208 {6, 10, 14} and "
    "`min_samples_split` \u2208 {2, 5, 10}. The best configuration was 50 trees, "
    "maximum depth 10 and minimum split size 2, with a cross-validated RMSE of "
    "7.191 mm. On the hold-out set this tuned forest achieved R\u00b2 = 0.6249, "
    "MAE = 1.811 mm and RMSE = 6.453 mm. It improved on the default forest but did "
    "not surpass the Hurdle model."
)
p(
    "The classifier tuning grid used the same tree counts and split values with "
    "depths {6, 8, 12} and macro-F1 as the scoring metric. The balanced, "
    "depth-limited forest remained the preferred classifier because it offered a "
    "better balance between Dry/Trace recall and rare-class recall than deeper "
    "alternatives."
)

h2("7.8 Evaluation Protocol")
p(
    "Every regression model is evaluated with MAE, RMSE, R\u00b2, wet-day MAE, "
    "dry-day MAE and mean bias. Every classifier is evaluated with accuracy, "
    "macro precision, macro recall, macro F1, weighted F1 and a confusion matrix. "
    "The macro metrics give each class equal weight, which is appropriate when "
    "the rare classes are operationally important. Weighted F1 is also reported "
    "because it reflects the experience of a randomly chosen day."
)
p(
    "The Hurdle model is compared with the single-stage regressors on exactly the "
    "same test rows. No model receives additional features or a different "
    "pre-processing pipeline. This controlled comparison is essential: a "
    "difference in score should be attributable to the model, not to a change in "
    "the feature set or the evaluation period."
)

h2("7.9 Reproducibility Controls")
bullets([
    "All random operations use seed 42, including random forests, gradient "
    "boosting, decision trees and the train/test split.",
    "The benchmark is regenerated by a single script (`build_report_assets.py`) "
    "that writes the metrics JSON/CSV and every report figure.",
    "The 17-feature order is stored in model metadata and checked at inference "
    "time.",
    "The final report tables are generated from the saved metrics rather than "
    "typed from memory.",
    "The notebook and web application share the same column definitions, which "
    "reduces the risk of a silent train/serve mismatch.",
])


# ===========================================================================
# CHAPTER 8
# ===========================================================================
h1("CHAPTER 8: MODEL EVALUATION & COMPARISON")

h2("8.1 Evaluation Metrics")
p(
    "No single metric is sufficient for a zero-inflated, heavy-tailed target. The "
    "project therefore uses a compact but complementary set of regression and "
    "classification metrics. Table 8.1 defines each one and explains how it should "
    "be read in this domain."
)
add_table(
    ["Metric", "Definition", "Interpretation in RainVision"],
    [
        ["MAE", "Mean absolute error: average |y \u2212 \u0177| in mm.", "Easy to interpret; dominated by the large number of dry and light-rain days."],
        ["RMSE", "Root mean squared error in mm.", "Penalises large errors; sensitive to extreme under-prediction."],
        ["R\u00b2", "Coefficient of determination on the test set.", "Can be negative when a model is worse than predicting the test mean."],
        ["Wet-day MAE", "MAE on days with observed rainfall > 0.05 mm.", "Measures performance where a rainfall forecast is actually needed."],
        ["Dry-day MAE", "MAE on days with observed rainfall \u2264 0.05 mm.", "Detects false-rain behaviour and unnecessary alerts."],
        ["Bias", "Mean(\u0177 \u2212 y) in mm.", "Positive values indicate over-prediction; negative values indicate under-prediction."],
        ["Accuracy", "Fraction of correctly classified intensity tiers.", "Useful for overall summary but misleading under class imbalance."],
        ["Macro F1", "Unweighted mean of per-class F1 scores.", "Gives rare Heavy and Torrential classes equal importance."],
        ["Weighted F1", "F1 weighted by class support.", "Reflects typical daily performance."],
        ["Confusion matrix", "Counts of actual versus predicted classes.", "Shows which intensity tiers are confused with which neighbours."],
    ],
    [1.13, 2.58, 2.56],
    caption="Table 8.1: Evaluation metrics and their interpretation.",
    font_size=8.6,
)

h2("8.2 Regression Results")
p(
    "Table 8.2 reports the hold-out performance of all eight regression "
    "approaches. The rows are ordered by R\u00b2. The Hurdle model is the best "
    "overall model, with R\u00b2 = 0.6465, MAE = 1.775 mm and RMSE = 6.264 mm. "
    "The random forest is second (R\u00b2 = 0.6035) and gradient boosting is third "
    "(R\u00b2 = 0.5732). The linear models explain about 39% of the variance, while "
    "the single decision tree and both baselines are poor."
)
add_table(
    ["Rank", "Model", "MAE (mm)", "RMSE (mm)", "R\u00b2", "Wet-day MAE", "Dry-day MAE", "Bias"],
    [
        ["1", "Two-Stage Hurdle", "1.775", "6.264", "0.6465", "4.924", "0.062", "0.038"],
        ["2", "Random Forest", "1.835", "6.635", "0.6035", "5.069", "0.075", "0.135"],
        ["3", "Gradient Boosting", "1.848", "6.883", "0.5732", "5.010", "0.127", "\u22120.006"],
        ["4", "Linear Regression (OLS)", "2.936", "8.247", "0.3874", "6.693", "0.891", "0.235"],
        ["5", "Ridge Regression", "2.931", "8.256", "0.3860", "6.701", "0.878", "0.221"],
        ["6", "Decision Tree", "2.232", "10.242", "0.0551", "6.178", "0.084", "0.118"],
        ["7", "Baseline Mean", "3.937", "10.596", "\u22120.0114", "7.747", "1.863", "\u22121.124"],
        ["8", "Baseline Persistence (Lag-1)", "3.076", "11.060", "\u22120.1020", "8.553", "0.095", "0.000"],
    ],
    [0.42, 1.65, 0.72, 0.76, 0.67, 0.76, 0.76, 0.53],
    caption="Table 8.2: Regression benchmark on the 3,056-row chronological hold-out set.",
    font_size=7.9,
    center_cols={0, 2, 3, 4, 5, 6, 7},
)
p(
    "The gap between MAE and RMSE is large for every model, which is a direct "
    "consequence of the heavy tail. The Hurdle model's MAE is 1.775 mm, but its "
    "RMSE is 6.264 mm; the difference is produced by a relatively small number of "
    "large residuals on extreme days. This is not a reason to reject the model, "
    "but it is a reason to report both metrics and to inspect the residual plots."
)
p(
    "The dry-day behaviour is especially revealing. The Hurdle model has a "
    "dry-day MAE of only 0.062 mm, compared with 0.891 mm for OLS and 1.863 mm for "
    "the mean baseline. In other words, the Hurdle model rarely invents rainfall "
    "on dry days, while a linear model distributes a small positive amount across "
    "many dry days. The persistence baseline also has a low dry-day MAE (0.095 mm) "
    "for the same reason, but it performs poorly on wet days (8.553 mm)."
)

h2("8.3 Visual Comparison of Regression Models")
add_figure(
    "fig5_regression_comparison.png",
    "Figure 8.1: R\u00b2 and MAE comparison of the regression models.",
)
p(
    "Figure 8.1 makes the ranking visible. The Hurdle, random forest and gradient "
    "boosting models form a clear top group. The OLS and Ridge bars are nearly "
    "identical, which is expected because the ridge penalty mainly stabilises "
    "coefficients rather than changing the fitted function substantially. The "
    "decision tree has a small positive R\u00b2 but a very large RMSE, indicating "
    "that it captures some non-linear structure while remaining unstable on "
    "extremes. The mean and persistence baselines have negative R\u00b2, confirming "
    "that a simple reference is not adequate for this test period."
)

h2("8.4 Actual-versus-Predicted and Residual Diagnostics")
add_figure(
    "fig6_actual_vs_predicted_residuals.png",
    "Figure 8.2: Actual-versus-predicted and residual plots for the random forest and Hurdle models.",
)
p(
    "Both models concentrate their predictions near the lower-left corner because "
    "most days are dry or light-rain. The ideal 1:1 line is shown for reference. "
    "The Hurdle model is noticeably better at keeping dry-day predictions at "
    "zero, while the random forest produces a small positive cloud on the y-axis. "
    "At high actual rainfall, both models under-predict the peak; the Hurdle "
    "residual plot therefore has a longer negative tail at large predicted values. "
    "This is the expected behaviour of a variance-reducing ensemble and is one of "
    "the main limitations discussed in Chapter 13."
)
p(
    "Residual heteroscedasticity is also visible: errors are small near zero and "
    "grow with the predicted amount. A single global error bar would therefore be "
    "misleading. The application communicates this limitation by presenting the "
    "prediction as a statistical estimate and by pairing it with an advisory "
    "rather than a precise confidence interval."
)

h2("8.5 Dry-Day Behaviour")
add_figure(
    "fig7_dry_day_check.png",
    "Figure 8.3: False-rain diagnostic on observed dry days.",
)
p(
    "The left panel shows the mean predicted rainfall on days that were actually "
    "dry. The ideal value is zero. The Hurdle model averages 0.062 mm, the random "
    "forest 0.075 mm and OLS 0.891 mm. The right panel shows the full distribution: "
    "the Hurdle and random-forest predictions are concentrated at zero, whereas "
    "OLS spreads mass across small positive values. This diagnostic is arguably "
    "more useful to an operational user than a small change in overall R\u00b2, "
    "because a false-rain alert has a real cost in irrigation scheduling and "
    "public messaging."
)

h2("8.6 Classification Results")
p(
    "Table 8.3 reports the multi-class intensity results. The random forest is "
    "the best model by accuracy (0.8253), macro F1 (0.6780) and weighted F1 "
    "(0.8296). Logistic regression has a slightly lower accuracy (0.8024) but a "
    "higher macro recall (0.6911) than the random forest (0.6689), indicating that "
    "it finds more of the rare events at the cost of more false positives. "
    "Gradient boosting is close to the random forest on accuracy but has a lower "
    "macro F1 because its recall on rare classes is weaker."
)
add_table(
    ["Rank", "Model", "Accuracy", "Macro precision", "Macro recall", "Macro F1", "Weighted F1"],
    [
        ["1", "Random Forest", "0.8253", "0.6974", "0.6689", "0.6780", "0.8296"],
        ["2", "Logistic Regression", "0.8024", "0.6064", "0.6911", "0.6372", "0.8093"],
        ["3", "Decision Tree", "0.8086", "0.5961", "0.6364", "0.6106", "0.8110"],
        ["4", "Gradient Boosting", "0.8240", "0.6694", "0.5685", "0.6065", "0.8141"],
        ["5", "Baseline Majority", "0.6476", "0.1295", "0.2000", "0.1572", "0.5091"],
    ],
    [0.42, 1.62, 0.78, 1.02, 0.95, 0.75, 0.73],
    caption="Table 8.3: Classification benchmark on the chronological hold-out set.",
    font_size=8.0,
    center_cols={0, 2, 3, 4, 5, 6},
)
p(
    "The majority baseline achieves 64.76% accuracy by always predicting "
    "Dry/Trace. A user who only looks at accuracy might conclude that a 64.8% "
    "classifier is acceptable. The macro F1 of 0.1572 tells the real story: the "
    "model has no ability to identify the Light, Moderate, Heavy or Torrential "
    "classes. This is why the report treats macro F1 and per-class recall as the "
    "primary classification criteria."
)

h2("8.7 Classification Diagnostic")
add_figure(
    "fig9_classification.png",
    "Figure 8.4: Classification performance comparison and random-forest confusion matrix.",
)
p(
    "The confusion matrix shows that the random forest is very reliable on "
    "Dry/Trace days (1,794 correct out of 1,979) and reasonably good on Light "
    "days (445 correct out of 576). The main confusions are between adjacent "
    "classes: Light with Moderate, Moderate with Light/Heavy, and Heavy with "
    "Moderate/Torrential. This is physically intuitive because intensity "
    "boundaries are artificial cuts through a continuous distribution. The model "
    "rarely confuses a dry day with a torrential day, which is the most important "
    "error to avoid for public messaging."
)
add_table(
    ["Class", "Precision", "Recall", "F1-score", "Support"],
    [
        ["Dry / Trace", "0.964", "0.907", "0.934", "1,979"],
        ["Light", "0.605", "0.773", "0.678", "576"],
        ["Moderate", "0.614", "0.558", "0.585", "328"],
        ["Heavy", "0.609", "0.592", "0.600", "142"],
        ["Torrential", "0.696", "0.516", "0.593", "31"],
    ],
    [1.60, 1.08, 1.08, 1.08, 1.00],
    caption="Table 8.4: Per-class performance of the random-forest classifier.",
    font_size=8.8,
    center_cols=set(range(1, 5)),
)
p(
    "Torrential recall is 0.516: the model identifies about half of the 31 "
    "torrential days in the test period. This is a meaningful achievement given "
    "that torrential days are only 0.79% of the data, but it is not sufficient for "
    "an operational warning system. A future version should combine the "
    "classifier with a regression threshold, a cost-sensitive decision rule and "
    "external severe-weather indicators."
)

h2("8.8 Time-Series Cross-Validation")
add_table(
    ["Fold", "Training rows", "Validation rows", "R\u00b2", "RMSE (mm)", "MAE (mm)"],
    [
        ["Fold 1", "2,549", "2,546", "0.4941", "6.389", "1.158"],
        ["Fold 2", "5,095", "2,546", "0.6862", "4.604", "0.908"],
        ["Fold 3", "7,641", "2,546", "0.6180", "7.744", "1.612"],
        ["Fold 4", "10,187", "2,546", "0.5408", "8.557", "1.640"],
        ["Fold 5", "12,733", "2,546", "0.6848", "5.733", "1.590"],
        ["Mean", "\u2014", "\u2014", "0.6048 \u00b1 0.086", "6.605", "\u2014"],
    ],
    [0.90, 1.22, 1.22, 1.25, 1.05, 1.05],
    caption="Table 8.5: Expanding-window time-series cross-validation results.",
    font_size=8.6,
    center_cols={0, 1, 2, 3, 4, 5},
)
add_figure(
    "fig11_cv.png",
    "Figure 8.5: Fold-level R\u00b2 and RMSE for expanding-window cross-validation.",
)
p(
    "The fold-level spread is large. Fold 2 has an R\u00b2 of 0.686 and an RMSE of "
    "4.604 mm, while Fold 4 has an R\u00b2 of 0.541 and an RMSE of 8.557 mm. The "
    "difference reflects the particular years in each validation block; a fold "
    "that contains an extreme monsoon season is harder to predict. The mean "
    "R\u00b2 of 0.605 is consistent with the hold-out R\u00b2 of the random forest "
    "and gives confidence that the result is not a single lucky split."
)

h2("8.9 Hyperparameter Tuning Result")
add_table(
    ["Item", "Result"],
    [
        ["Search space", "50/100/150 trees; depth 6/10/14; minimum split 2/5/10"],
        ["Cross-validation", "4-fold `TimeSeriesSplit`, negative RMSE scoring"],
        ["Best parameters", "`n_estimators=50`, `max_depth=10`, `min_samples_split=2`"],
        ["Best CV RMSE", "7.191 mm"],
        ["Tuned test R\u00b2", "0.6249"],
        ["Tuned test MAE", "1.811 mm"],
        ["Tuned test RMSE", "6.453 mm"],
        ["Comparison", "Improves on the default random forest (R\u00b2 0.6035) but remains below the Hurdle model (R\u00b2 0.6465)."],
    ],
    [1.70, 4.57],
    caption="Table 8.6: Random-forest hyperparameter tuning summary.",
    font_size=8.8,
)

h2("8.10 Comparative Discussion")
p(
    "The results support three conclusions. First, non-linear tree ensembles are "
    "substantially better than linear models for this target. The best tree-based "
    "model explains about 65% of the hold-out variance, whereas OLS explains about "
    "39%. The improvement comes from threshold effects in humidity, interactions "
    "between pressure and wind, and the ability to represent the monsoon regime "
    "without imposing a single linear seasonal slope."
)
p(
    "Second, the Hurdle decomposition is worth its additional complexity. It "
    "improves R\u00b2 by 4.3 percentage points over the default random forest and "
    "reduces RMSE by about 0.37 mm. More importantly, it cuts dry-day MAE from "
    "0.075 mm to 0.062 mm and prevents the small positive false-rain cloud that "
    "the single-stage forest still produces. The probability-weighted variant "
    "goes slightly further on some metrics (R\u00b2 = 0.6558, RMSE = 6.181 mm), "
    "but the hard-threshold version is easier to explain and is used as the "
    "primary result."
)
p(
    "Third, classification accuracy alone is misleading. The best classifier "
    "reaches 82.5% accuracy, but its macro F1 is only 0.678 because Heavy and "
    "Torrential events are rare and adjacent intensity classes are easy to "
    "confuse. The per-class table is therefore the most honest summary of "
    "operational readiness: strong dry-day performance, moderate light-rain "
    "performance and limited but non-trivial extreme-event recall."
)

h2("8.11 Summary of Evaluation")
bullets([
    "Best regression model: Two-Stage Hurdle, R\u00b2 0.6465, MAE 1.775 mm, RMSE 6.264 mm.",
    "Best single-stage regressor: Random Forest, R\u00b2 0.6035, MAE 1.835 mm, RMSE 6.635 mm.",
    "Best classifier: Random Forest, accuracy 82.53%, macro F1 0.6780, weighted F1 0.8296.",
    "Best dry-day control: Hurdle, dry-day MAE 0.062 mm versus 0.891 mm for OLS.",
    "Cross-validation: mean R\u00b2 0.6048 \u00b1 0.086, mean RMSE 6.605 mm.",
    "Tuned forest: R\u00b2 0.6249, MAE 1.811 mm, RMSE 6.453 mm.",
    "Extreme events remain the main weakness; torrential recall is 0.516.",
])


# ===========================================================================
# CHAPTER 9
# ===========================================================================
h1("CHAPTER 9: IMPLEMENTATION & CODING")

h2("9.1 Code Organization")
p(
    "The codebase separates reusable library code from notebooks, scripts and the "
    "web application. This structure makes it possible to reproduce the analysis "
    "without opening a notebook and to import the same feature logic in the Flask "
    "service. Table 9.1 lists the main implementation units."
)
add_table(
    ["Path", "Responsibility"],
    [
        ["`src/data_processing.py`", "Dataset discovery, schema normalization, physical validation and cleaning helpers."],
        ["`src/feature_engineering.py`", "Calendar, lag, rolling and pressure-difference features; intensity labels; chronological split."],
        ["`src/model_training.py`", "Regression and classification suites, baselines, metrics, time-series cross-validation and tuning."],
        ["`src/redesigned_models.py`", "Two-stage Hurdle regressor, blended ensemble, soft-voting classifier and model serialization."],
        ["`src/prediction.py`", "Inference validation, feature preparation, prediction, consistency gating and advisory generation."],
        ["`src/climate_analytics.py`", "Annual totals, climatology, anomalies and summary tables."],
        ["`Website/app.py`", "Flask routes for the interface, dashboard API, prediction API, dataset explorer, exports and health checks."],
        ["`Website/ml/preprocessing.py`", "Web-side feature contract and input bounds."],
        ["`Website/ml/prediction.py`", "Model loading, live inference, model comparison and recursive 7-day simulation."],
        ["`scripts/build_report_assets.py`", "Reproducible benchmark, metrics exports and report figures."],
        ["`notebooks/`", "Exploratory and explanatory notebooks for data understanding, features, models and final inference."],
    ],
    [1.90, 4.37],
    caption="Table 9.1: Main implementation units.",
    font_size=8.5,
)

h2("9.2 Data Ingestion and Cleaning")
p(
    "The ingestion code is intentionally small and explicit. It reads the primary "
    "sheet, converts the date, removes duplicate dates and sorts the result. The "
    "validation stage is separated so that it can also be applied to an uploaded "
    "CSV without duplicating the logic."
)
code_block(
    """
from pathlib import Path
import pandas as pd

DATA_PATH = Path("data/RainVision_Historical_1985_to_Today.xlsx")

df = pd.read_excel(
    DATA_PATH,
    sheet_name="Rainfall_Data_1985_to_Today"
)

df["date"] = pd.to_datetime(df["date"])
df = (
    df.drop_duplicates(subset=["date"])
      .sort_values("date")
      .reset_index(drop=True)
)

required = [
    "date", "temperature", "humidity", "pressure",
    "wind_speed", "previous_rainfall", "rainfall"
]
missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")

if df["rainfall"].isna().any() or (df["rainfall"] < 0).any():
    raise ValueError("Target contains missing or negative values.")
""",
    caption="Code 9.1: Dataset loading and basic validation.",
)

h2("9.3 Feature Engineering")
p(
    "The feature builder is the most important part of the implementation because "
    "it defines the information that every model is allowed to see. The code below "
    "shows the leakage-safe construction of the annual cycle, the rainfall lags, "
    "the rolling windows and the pressure tendency. Every rainfall-derived "
    "feature uses `shift(1)` or an earlier observation."
)
code_block(
    """
doy = df["date"].dt.dayofyear

df["sin_day_of_year"] = np.sin(2 * np.pi * doy / 365.25)
df["cos_day_of_year"] = np.cos(2 * np.pi * doy / 365.25)

# Autoregressive rainfall history
df["rain_lag_1"] = df["rainfall"].shift(1).fillna(0.0)
df["rain_lag_2"] = df["rainfall"].shift(2).fillna(0.0)
df["rain_lag_3"] = df["rainfall"].shift(3).fillna(0.0)

# Rolling windows summarise only antecedent rainfall
shifted = df["rainfall"].shift(1)
df["rain_roll_mean_7"]  = shifted.rolling(7,  min_periods=1).mean().fillna(0.0)
df["rain_roll_sum_7"]   = shifted.rolling(7,  min_periods=1).sum().fillna(0.0)
df["rain_roll_max_7"]   = shifted.rolling(7,  min_periods=1).max().fillna(0.0)
df["rain_roll_mean_14"] = shifted.rolling(14, min_periods=1).mean().fillna(0.0)

# Atmospheric persistence and tendency
df["temp_lag_1"] = df["temperature"].shift(1).bfill()
df["humidity_lag_1"] = df["humidity"].shift(1).bfill()
df["pressure_diff_1"] = (
    df["pressure"] - df["pressure"].shift(1)
).fillna(0.0)

df["is_monsoon"] = df["date"].dt.month.isin([6, 7, 8, 9]).astype(int)
""",
    caption="Code 9.2: Leakage-safe calendar, lag, rolling and pressure features.",
)

h2("9.4 Chronological Split")
p(
    "The split is deliberately implemented with integer row positions rather than "
    "with a random sampler. Because the data are sorted by date, the first 80% of "
    "rows are the earliest observations and the final 20% are the future "
    "hold-out. No row is ever assigned to both partitions."
)
code_block(
    """
n = len(df)
split_index = int(n * 0.80)

train = df.iloc[:split_index].copy().reset_index(drop=True)
test  = df.iloc[split_index:].copy().reset_index(drop=True)

assert train["date"].max() < test["date"].min()

FEATURES = [
    "temperature", "humidity", "pressure", "wind_speed",
    "rain_lag_1", "rain_lag_2", "rain_lag_3",
    "rain_roll_mean_7", "rain_roll_sum_7",
    "rain_roll_max_7", "rain_roll_mean_14",
    "temp_lag_1", "humidity_lag_1", "pressure_diff_1",
    "sin_day_of_year", "cos_day_of_year", "is_monsoon",
]

X_train, y_train = train[FEATURES], train["rainfall"]
X_test,  y_test  = test[FEATURES],  test["rainfall"]
""",
    caption="Code 9.3: Forward-in-time training and test partitions.",
)

h2("9.5 Two-Stage Hurdle Implementation")
p(
    "The Hurdle model is implemented as a scikit-learn compatible estimator. The "
    "occurrence classifier is trained on a binary wet/dry label, while the severity "
    "regressor is trained only on wet days. The prediction method supports both "
    "hard-threshold and expected-value modes."
)
code_block(
    """
class TwoStageHurdleRegressor(BaseEstimator, RegressorMixin):
    def __init__(self, classifier=None, regressor=None,
                 rain_threshold=0.05):
        self.rain_threshold = rain_threshold
        self.classifier = classifier or RandomForestClassifier(
            n_estimators=100, max_depth=8,
            class_weight="balanced", random_state=42
        )
        self.regressor = regressor or RandomForestRegressor(
            n_estimators=100, max_depth=10,
            min_samples_split=5, random_state=42
        )

    def fit(self, X, y):
        X_df = pd.DataFrame(X)
        y = np.asarray(y)
        is_wet = (y > self.rain_threshold).astype(int)
        self.classifier.fit(X_df, is_wet)

        wet_mask = y > self.rain_threshold
        self.regressor.fit(X_df[wet_mask], y[wet_mask])
        return self

    def predict(self, X, mode="hard_threshold"):
        X_df = pd.DataFrame(X)
        p_wet = self.classifier.predict_proba(X_df)[:, 1]
        severity = np.clip(self.regressor.predict(X_df), 0.0, None)

        if mode == "expected_value":
            pred = p_wet * severity
        else:
            wet = self.classifier.predict(X_df)
            pred = np.where(wet == 1, severity, 0.0)

        return np.clip(pred, 0.0, None)
""",
    caption="Code 9.4: Two-stage Hurdle regressor.",
)

h2("9.6 Training and Evaluation Loop")
p(
    "The benchmark loop is intentionally uniform across models. It records "
    "training time, computes the same metric set, clips negative predictions to "
    "zero and stores the fitted object for later diagnostics. The persistence "
    "baseline is inserted separately because it has no fitting step."
)
code_block(
    """
def regression_metrics(y_true, y_pred):
    y_pred = np.clip(np.asarray(y_pred, float), 0.0, None)
    y_true = np.asarray(y_true, float)
    wet = y_true > 0.05

    return {
        "MAE":  mean_absolute_error(y_true, y_pred),
        "RMSE": np.sqrt(mean_squared_error(y_true, y_pred)),
        "R2":   r2_score(y_true, y_pred),
        "WetMAE": mean_absolute_error(y_true[wet], y_pred[wet]),
        "DryMAE": mean_absolute_error(y_true[~wet], y_pred[~wet]),
        "Bias": float(np.mean(y_pred - y_true)),
    }

results = []
for name, model in models.items():
    t0 = time.time()
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    results.append({
        "Model": name,
        **regression_metrics(y_test, pred),
        "TrainTime": round(time.time() - t0, 2),
    })
""",
    caption="Code 9.5: Uniform regression evaluation loop.",
)

h2("9.7 Flask Prediction Endpoint")
p(
    "The web service exposes a single prediction endpoint that accepts JSON. It "
    "delegates validation and inference to the `ml` package, records a lightweight "
    "history entry and returns a stable response schema. Invalid inputs are "
    "reported as HTTP 400 rather than causing an unhandled exception."
)
code_block(
    """
@app.route("/api/predict", methods=["POST"])
def api_predict():
    payload = request.get_json(force=True, silent=True) or {}
    model_name = payload.get("model", "random_forest")

    try:
        result = predict_rainfall(MODELS_DIR, model_name, payload)

        history_entry = {
            "id": f"PRED-{int(time.time() * 1000)}",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "model": result["model_name"],
            "predicted_rainfall_mm": result["predicted_rainfall_mm"],
            "category": result["category"],
        }
        _HISTORY_CACHE.insert(0, history_entry)

        result["prediction_id"] = history_entry["id"]
        result["timestamp"] = history_entry["timestamp"]
        return jsonify(result)

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as exc:
        return jsonify({"error": f"Prediction failed: {exc}"}), 500
""",
    caption="Code 9.6: Flask prediction endpoint.",
)

h2("9.8 Inference Validation and Consistency Gate")
p(
    "The inference module applies the same physical bounds as the training "
    "pipeline. The consistency gate is a small but important post-processing step: "
    "if the classifier predicts a dry day and the regressor returns a modest "
    "positive depth, the depth is set to zero. Large disagreements are preserved "
    "so that a potentially severe event is not suppressed."
)
code_block(
    """
VALIDATION_BOUNDS = {
    "temperature": (-10.0, 60.0, "C"),
    "humidity":    (0.0, 100.0, "%"),
    "pressure":    (850.0, 1100.0, "hPa"),
    "wind_speed":  (0.0, 180.0, "km/h"),
}

def validate_weather_inputs(inputs):
    for field in ["temperature", "humidity", "pressure", "wind_speed"]:
        if field not in inputs:
            raise ValueError(f"Missing required field: {field}")
        value = inputs[field]
        low, high, unit = VALIDATION_BOUNDS[field]
        if not (low <= float(value) <= high):
            raise ValueError(
                f"{field}={value} outside valid range "
                f"{low} to {high} {unit}"
            )
    return {k: float(v) for k, v in inputs.items()
            if k in VALIDATION_BOUNDS}

# Multi-task prediction and physical consistency
category = classifier.predict(features)[0]
amount = max(0.0, float(regressor.predict(features)[0]))
if category == "No Rain" and amount < 15.0:
    amount = 0.0
""",
    caption="Code 9.7: Input validation and consistency gating.",
)

h2("9.9 Model Serialization and Metadata")
p(
    "Trained models are persisted with joblib, while a JSON metadata file records "
    "the feature order, model version, serialization time and the evaluation "
    "metrics. The application loads the artefacts once at startup rather than "
    "re-fitting on every request. This is essential for a responsive interface and "
    "for reproducibility: the same bytes are served until a deliberate retraining "
    "step replaces them."
)
code_block(
    """
import json
import joblib

joblib.dump(regressor, models_dir / "rainvision_regressor.joblib")
joblib.dump(classifier, models_dir / "rainvision_classifier.joblib")

metadata = {
    "version": "2.0.0",
    "features": FEATURE_COLUMNS,
    "target": "rainfall",
    "training_period": ["1985-01-01", "2018-06-19"],
    "test_period": ["2018-06-20", "2026-10-31"],
    "metrics": {
        "hurdle_r2": 0.6465,
        "hurdle_mae_mm": 1.775,
        "hurdle_rmse_mm": 6.264,
    },
}

with open(models_dir / "model_metadata.json", "w") as fh:
    json.dump(metadata, fh, indent=4)
""",
    caption="Code 9.8: Model persistence and metadata registry.",
)

h2("9.10 Coding Practices")
bullets([
    "Type hints and docstrings are used in the reusable modules to make the "
    "contract of each function explicit.",
    "The feature list is defined once and passed to both training and inference; "
    "it is not re-typed in each notebook.",
    "Model outputs are clipped at zero at the boundary, not inside the target "
    "column, so observed rainfall is never altered.",
    "The Flask layer catches validation errors separately from unexpected "
    "server errors, producing actionable messages for the user.",
    "The project avoids hard-coded absolute paths in application code and resolves "
    "paths relative to the project root.",
    "Generated reports and figures are written to dedicated output directories so "
    "that raw data and model artefacts remain untouched.",
])


# ===========================================================================
# CHAPTER 10
# ===========================================================================
h1("CHAPTER 10: SYSTEM INTERFACE / SCREEN LAYOUTS")

h2("10.1 Interface Design Goals")
p(
    "The interface is designed for demonstration and exploratory use rather than "
    "for a trained meteorologist. It therefore prioritises a small number of "
    "clear actions, immediate visual feedback and a visible distinction between "
    "the statistical prediction and the operational advisory. A persistent top "
    "navigation bar gives access to the dashboard, prediction studio, model "
    "comparison, dataset explorer, historical analytics and project information."
)
p(
    "The visual language uses white cards on a light background, a dark navy "
    "primary colour and a restrained accent palette. Numerical results are shown "
    "in large type, while secondary detail is placed in smaller labels beneath "
    "them. Charts are used to show context rather than to replace the numerical "
    "answer. The layout is responsive: on a narrow screen the cards stack "
    "vertically, and the prediction controls remain usable without horizontal "
    "scrolling."
)

h2("10.2 Dashboard")
add_figure(
    "ui_dashboard_report.png",
    "Figure 10.1: RainVision dashboard with dataset KPIs, recent rainfall, distribution and annual comparison.",
    width=5.7,
)
p(
    "The dashboard answers the question \u201cwhat does the historical record look "
    "like right now?\u201d The top row shows the dataset record count (15,279), the "
    "mean daily rainfall (2.09 mm), the maximum recorded rainfall (339.9 mm), the "
    "minimum (0.0 mm) and the number of available ML models (4). A latest-prediction "
    "card provides continuity with the prediction studio. The lower cards show a "
    "30-day rainfall and humidity trend, a rainfall distribution doughnut, a "
    "monthly seasonal profile and a year-by-year annual comparison from 1985 to "
    "2026."
)
p(
    "The dashboard is deliberately descriptive. It does not claim that the charts "
    "are forecasts. Its purpose is to orient the user before a prediction is made "
    "and to make the long-run context visible: a 58 mm prediction, for example, is "
    "unusual but not unprecedented in a record that contains a 339.9 mm day."
)

h2("10.3 Prediction Studio")
add_figure(
    "ui_prediction_report.png",
    "Figure 10.2: Rainfall Prediction Studio with inputs, predicted depth, intensity gauge, advisory and attribution.",
    width=5.55,
)
p(
    "The prediction studio is the main interaction screen. The user can choose a "
    "quick preset (heavy monsoon, dry sunny, humid pre-monsoon or winter breeze), "
    "synchronise a live weather reading, or move five sliders for temperature, "
    "humidity, pressure, wind speed and previous-day rainfall. The valid range is "
    "shown beneath each control, which reduces the chance of an avoidable "
    "validation error."
)
p(
    "The illustrated scenario uses 28 \u00b0C, 92% relative humidity, 998 hPa, "
    "28 km/h wind and 45 mm of previous-day rainfall. The selected model returns "
    "58.11 mm and classifies the event as Torrential. The gauge places the value "
    "above the 50 mm torrential threshold, and the advisory warns of underpass "
    "waterlogging, traffic disruption and a municipal storm-drainage response. "
    "The interface also reports a 98% precipitation probability, a derived dew "
    "point of 26.4 \u00b0C and an inference time of 85.08 ms. These values are "
    "displayed as model outputs, not as official weather warnings."
)
add_table(
    ["Element", "Illustrated value", "Interpretation"],
    [
        ["Temperature", "28 \u00b0C", "Warm, humid monsoon-like conditions."],
        ["Relative humidity", "92%", "Close to saturation; strong moisture signal."],
        ["Pressure", "998 hPa", "Below the station mean, consistent with unsettled weather."],
        ["Wind speed", "28 km/h", "Moderate advection and mixing."],
        ["Previous-day rainfall", "45 mm", "Very wet antecedent conditions."],
        ["Predicted depth", "58.11 mm", "Above the 50 mm torrential threshold."],
        ["Predicted class", "Torrential", "High-impact rainfall category."],
        ["Precipitation probability", "98%", "Model confidence indicator shown in the interface."],
        ["Inference time", "85.08 ms", "Server-side response time for the illustrated request."],
        ["Advisory", "Critical urban-flood alert", "Prototype guidance requiring human verification."],
    ],
    [1.60, 1.62, 3.05],
    caption="Table 10.1: Illustrated prediction scenario.",
    font_size=8.8,
    center_cols={1},
)
p(
    "Below the result, the interface shows a feature-attribution panel (relative "
    "humidity 31.5%, pressure drop 32.3%, antecedent rainfall 22.8%, wind "
    "advection 8.0% and thermal energy 5.3%), a domain-impact panel with urban "
    "flood and agricultural guidance, and a recursive 7-day outlook. The 7-day "
    "outlook is a scenario simulator, not a numerical weather prediction: it feeds "
    "each predicted day back as antecedent moisture for the next. The interface "
    "labels it as a recursive outlook for this reason."
)

h2("10.4 Dataset Explorer")
add_figure(
    "ui_explorer_report.png",
    "Figure 10.3: Dataset Explorer with search, filters, pagination and batch-inference panel.",
    width=5.45,
)
p(
    "The dataset explorer makes the underlying record inspectable. It shows the "
    "source workbook, total records, data authority (ECMWF ERA5 reanalysis) and "
    "station location. A search box filters by date or location, a year selector "
    "supports 1985\u20132026, and a rainfall filter can show all records, rain-only "
    "days, dry days or heavy-rain days. The table is paginated at 20 rows per page, "
    "with 764 pages for the full record."
)
p(
    "The visible rows illustrate the end of the record: 31 October 2026 is dry, "
    "30 and 29 October are light-rain days, and the preceding week is mostly dry. "
    "The category badges, temperature, humidity, pressure, wind and previous "
    "rainfall columns make the feature vector understandable without opening the "
    "workbook. The lower panel supports batch inference on an uploaded CSV and a "
    "download of the annotated result."
)

h2("10.5 Model Comparison and Historical Analytics")
p(
    "The model comparison page runs two or more compatible models on the same "
    "input and displays their predictions, classes and stored evaluation metrics "
    "side by side. This is useful for demonstrating that the Hurdle model is more "
    "conservative on dry days while the single-stage forest may produce a small "
    "positive amount. The page is intentionally read-only with respect to model "
    "training; it does not allow a user to upload a new model."
)
p(
    "The historical analytics page provides annual anomaly, monthly seasonality "
    "and long-run trend charts derived from the same dataset. During the final "
    "review, the analytics chart was found to render only the early part of the "
    "series because of a front-end date-axis issue. It is therefore described here "
    "but not presented as a verified screenshot. The dashboard and the EDA figures "
    "in Chapter 6 provide the validated visual evidence for the same climate "
    "statistics."
)

h2("10.6 API Endpoints")
p(
    "The interface is a client of the Flask API. The endpoint contract is "
    "summarised below; all responses are JSON unless a file download is requested."
)
add_table(
    ["Method", "Endpoint", "Purpose"],
    [
        ["GET", "/api/health", "Report service status, model availability and dataset readiness."],
        ["GET", "/api/dashboard/summary", "KPIs, monthly and annual aggregates, distribution bins and recent trends."],
        ["GET", "/api/dataset/columns", "Column names, data types, missing counts and feature/target roles."],
        ["GET", "/api/dataset/preview", "Paginated dataset search, filtering and sorting."],
        ["GET", "/api/models", "Available models and their display metadata."],
        ["GET", "/api/models/metrics", "Evaluation metrics for the stored models."],
        ["POST", "/api/predict", "Single live prediction from weather inputs."],
        ["POST", "/api/predict/compare", "Run compatible models on the same input."],
        ["POST", "/api/predict/7day-forecast", "Recursive 7-day scenario simulation."],
        ["GET", "/api/rainfall/trends", "Monthly and annual historical trend series."],
        ["GET", "/api/predictions/history", "In-memory prediction audit history."],
        ["GET", "/api/reports/export", "Download prediction, metrics or dataset reports as CSV."],
        ["GET", "/api/dataset/download-excel", "Download the source workbook."],
        ["POST", "/api/dataset/upload", "Batch inference on an uploaded weather CSV."],
        ["GET", "/api/dataset/download-batch-result", "Download the annotated batch result."],
        ["GET", "/api/weather/live", "Optional live-weather synchronisation for the prediction form."],
    ],
    [0.65, 2.35, 3.27],
    caption="Table 10.2: Main Flask API endpoints.",
    font_size=8.6,
    center_cols={0},
)

h2("10.7 Formatted Reports and Exports")
p(
    "Although formatted reports are optional in the prescribed format, the "
    "application provides three practical outputs that support analysis and "
    "demonstration. They are generated from the same data and model layer as the "
    "interface, so they do not introduce a separate reporting code path."
)
add_table(
    ["Report", "Format", "Contents", "Typical use"],
    [
        ["Prediction history", "CSV", "Prediction ID, timestamp, model, depth, class and input summary.", "Audit a demonstration session or compare repeated scenarios."],
        ["Model metrics", "CSV", "Regression and classification metrics for the stored models.", "Attach a compact evaluation summary to a review or viva."],
        ["Batch prediction result", "CSV", "Original weather columns plus predicted depth, class and advisory for every uploaded row.", "Score a weather log without entering rows manually."],
        ["Dataset workbook", "XLSX", "Full multi-sheet historical dataset and summary tables.", "Offline analysis and reproducibility."],
    ],
    [1.30, 0.65, 2.85, 1.47],
    caption="Table 10.3: Generated reports and exports.",
    font_size=8.5,
    center_cols={1},
)

h2("10.8 Usability and Error Handling")
bullets([
    "Every numeric control shows its valid range, and the server repeats the same "
    "validation so that a crafted request cannot bypass the browser.",
    "Preset scenarios reduce the effort required for a first demonstration and "
    "make the effect of humidity and antecedent rainfall easy to show.",
    "The result card separates depth, class, probability, dew point and inference "
    "time, so a user can see both the answer and its context.",
    "The advisory is visually distinct from the numerical prediction and uses "
    "explicit language such as \u201cprototype\u201d and \u201crequires human "
    "verification\u201d in the project documentation.",
    "Dataset filters and pagination prevent the browser from rendering all 15,279 "
    "rows at once.",
    "Errors are returned as readable JSON messages and displayed in the interface "
    "rather than leaving a blank result panel.",
])

h2("10.9 Interface Limitations")
p(
    "The interface is a single-user demonstration environment. It has no login, "
    "no role-based access control and no persistent database for prediction "
    "history; the history is held in memory and is lost when the server restarts. "
    "The live-weather sync depends on an external service and is optional. These "
    "choices keep the project self-contained, but they mean that the current "
    "interface should not be presented as a production public-warning portal."
)


# ===========================================================================
# CHAPTER 11
# ===========================================================================
h1("CHAPTER 11: RESULTS & DISCUSSION")

h2("11.1 Experimental Context")
p(
    "All results in this chapter come from the reproducible benchmark described in "
    "Chapters 4, 5 and 7. The training period contains 12,223 observations from "
    "1 January 1985 to 19 June 2018. The hold-out period contains 3,056 "
    "observations from 20 June 2018 to 31 October 2026. The five intensity classes "
    "are Dry/Trace (73.39%), Light (15.77%), Moderate (7.28%), Heavy (2.76%) and "
    "Torrential (0.79%). No test observation was used for fitting, scaling or "
    "hyperparameter selection."
)
p(
    "The results are discussed in three layers. The first layer is predictive "
    "accuracy: how well does each model estimate the depth and class? The second "
    "layer is behavioural: how does the model behave on dry days, wet days and "
    "extremes? The third layer is operational: what would a user actually see, and "
    "where are the risks of over-interpreting the output?"
)

h2("11.2 Regression Findings")
p(
    "The two-stage Hurdle model is the best regression approach on every primary "
    "metric. It achieves R\u00b2 = 0.6465, MAE = 1.775 mm and RMSE = 6.264 mm. The "
    "random forest is a close second (R\u00b2 = 0.6035, MAE = 1.835 mm, RMSE = "
    "6.635 mm), and gradient boosting is third (R\u00b2 = 0.5732). The gap between "
    "the Hurdle model and the linear models is large: OLS explains only 38.7% of "
    "the variance and has an RMSE of 8.247 mm, about 32% larger than the Hurdle "
    "model's RMSE."
)
p(
    "The ranking is consistent with the shape of the data. Humidity has a "
    "threshold-like relationship with rainfall, pressure and wind interact, and the "
    "monsoon produces a distinct regime. A linear model cannot represent these "
    "effects without explicit interaction and spline terms. A single decision tree "
    "can represent thresholds but is unstable; its R\u00b2 of 0.055 and RMSE of "
    "10.242 mm show that one tree is not enough. Bagging and boosting reduce this "
    "instability, and the Hurdle decomposition adds a explicit dry/wet decision."
)
p(
    "The mean and persistence baselines have negative R\u00b2 on the future test "
    "period. This is a useful sanity check: the test period is not a trivial "
    "continuation of the training mean. Persistence has a lower MAE than the mean "
    "baseline because yesterday's rainfall is informative, but its RMSE is worse "
    "(11.060 mm) because it fails badly at the onset and decay of wet spells. A "
    "model that merely repeats yesterday would therefore not satisfy the project "
    "objective."
)

h2("11.3 Classification Findings")
p(
    "The random forest is the best intensity classifier by accuracy (82.53%), "
    "macro F1 (0.6780) and weighted F1 (0.8296). Its per-class profile is strong "
    "for Dry/Trace (F1 0.934) and acceptable for Light (0.678), Moderate (0.585) "
    "and Heavy (0.600), but only moderate for Torrential (0.593). The model "
    "correctly identifies 1,794 of 1,979 dry days and 445 of 576 light-rain days. "
    "The largest confusions are between adjacent intensity tiers, which is expected "
    "because the classes are thresholds on a continuous variable."
)
p(
    "Logistic regression has a higher macro recall (0.6911) than the random forest "
    "(0.6689), which means it finds more of the rare classes. This is a useful "
    "trade-off to report: if the operational cost of a missed heavy-rain day is "
    "much larger than the cost of a false alarm, a higher-recall model may be "
    "preferable even if its accuracy is slightly lower. The project keeps the "
    "random forest as the balanced default and exposes the comparison so that this "
    "choice can be discussed explicitly."
)
p(
    "The majority baseline illustrates why accuracy is a poor sole criterion. It "
    "reaches 64.76% accuracy by always predicting Dry/Trace, but its macro F1 is "
    "0.1572 and it never identifies a heavy or torrential event. A useful "
    "classifier must improve the rare-class recall without collapsing the dry-day "
    "performance, which is exactly what the balanced random forest does."
)

h2("11.4 Dry-Day and Extreme-Day Behaviour")
p(
    "The dry-day diagnostic is one of the most important results of the project. "
    "On the 1,979 observed dry days in the test set, the Hurdle model has a mean "
    "prediction of 0.062 mm and a dry-day MAE of 0.062 mm. The random forest is "
    "close at 0.075 mm, while OLS produces a mean of 0.891 mm and a dry-day MAE of "
    "0.891 mm. The practical difference is substantial: OLS would generate a small "
    "rainfall advisory on many days that are actually dry, whereas the Hurdle model "
    "usually returns zero."
)
p(
    "The extreme-day behaviour is less satisfactory. Both tree ensembles "
    "under-predict the largest events because the loss function averaged over all "
    "days does not justify a prediction near 300 mm when such values are extremely "
    "rare. The Hurdle model preserves more of the wet-day signal than OLS, but its "
    "residual plot still shows a negative tail at high predicted values. This is a "
    "fundamental limitation of point forecasting under a heavy-tailed distribution "
    "and is the main reason the report recommends probabilistic or quantile "
    "extensions in Chapter 13."
)

h2("11.5 Held-Out Timeline Behaviour")
add_figure(
    "fig8_timeline.png",
    "Figure 11.1: Ninety-day held-out forecast timeline for the random forest, OLS and Hurdle models.",
)
p(
    "The 90-day timeline from August to October 2026 shows that the tree-based "
    "models capture the timing of the two large events in mid-September. The "
    "random forest and Hurdle curves follow the observed rise and fall more closely "
    "than OLS, which produces a much flatter peak. All models still under-estimate "
    "the highest event, and the differences between the models are largest exactly "
    "where the operational stakes are highest. The timeline is a useful reminder "
    "that a good average score can coexist with a significant peak error."
)
p(
    "The timeline also shows the value of the dry/wet gate: during the long dry "
    "stretches, the Hurdle and random-forest curves remain near zero, while OLS "
    "maintains a small positive offset. This is consistent with the dry-day "
    "diagnostic and helps explain why the Hurdle model has a lower MAE despite "
    "similar overall shape."
)

h2("11.6 Feature Importance and Interpretation")
add_figure(
    "fig10_feature_importance.png",
    "Figure 11.2: Impurity-based feature importance for the random forest and gradient boosting models.",
    width=5.7,
)
p(
    "Relative humidity is the dominant feature, with 52.65% of the random-forest "
    "impurity importance. Wind speed is second (19.25%), followed by pressure "
    "(4.16%), one-day pressure change (3.51%), temperature (3.20%) and previous-day "
    "temperature (2.76%). The rainfall lags and rolling windows each contribute a "
    "smaller share, while the explicit monsoon flag has almost no marginal "
    "importance (0.01%)."
)
p(
    "The dominance of humidity is meteorologically plausible: relative humidity is "
    "the variable most directly connected to saturation and cloud formation. The "
    "strong wind contribution is also reasonable for a coastal monsoon region, where "
    "moisture advection and convective mixing are important. The low importance of "
    "the monsoon flag does not mean that the monsoon is unimportant; much of its "
    "information is already carried by humidity, temperature and the cyclical "
    "day-of-year terms. Tree impurity importance is also biased toward variables "
    "that offer many split points, so the ranking should be read as a descriptive "
    "signal rather than a causal attribution."
)
p(
    "The pressure tendency is more important than the absolute pressure. This is "
    "consistent with synoptic meteorology: a falling barometer indicates an "
    "approaching disturbance, whereas a low but steady pressure can persist for "
    "days. The model appears to have learned this distinction from the difference "
    "feature, which is a useful example of domain-guided feature engineering."
)

h2("11.7 Sensitivity and Robustness")
p(
    "The probability-weighted Hurdle variant provides a sensitivity check on the "
    "decision rule. It achieved R\u00b2 = 0.6558, MAE = 1.779 mm and RMSE = 6.181 "
    "mm, slightly better than the hard-threshold version on R\u00b2 and RMSE but "
    "almost identical on MAE. The improvement is not large enough to justify the "
    "additional interpretation burden in the primary comparison, but it suggests "
    "that a calibrated probability output is a promising direction for future work."
)
p(
    "The tuned random forest is another robustness check. The grid search selected "
    "a smaller forest (50 trees) with a depth of 10 and a minimum split of 2. On "
    "the hold-out set it achieved R\u00b2 = 0.6249, MAE = 1.811 mm and RMSE = 6.453 "
    "mm. This is better than the default forest but still below the Hurdle model. "
    "The result is encouraging because it shows that the Hurdle advantage is not an "
    "artefact of an untuned baseline."
)
p(
    "The five cross-validation folds range from R\u00b2 0.494 to 0.686, with a mean "
    "of 0.605 and a standard deviation of 0.086. A spread of this size is a warning "
    "against reporting a single number without context. The hold-out result lies "
    "within the observed fold range, which supports the credibility of the "
    "evaluation."
)

h2("11.8 Operational Performance")
p(
    "The demonstrated live prediction returned in 85.08 ms in the browser "
    "screenshot, and the model suite trains in under 20 seconds on the development "
    "machine. The slowest component is gradient boosting (9.47 s), while OLS and "
    "Ridge train in about 0.04 s. The Hurdle model trains in 2.31 s because it "
    "fits two random forests. These times are small enough that the application can "
    "load pre-trained artefacts at startup and respond interactively."
)
p(
    "The dataset explorer paginates 15,279 records at 20 rows per page, producing "
    "764 pages. The dashboard computes monthly and annual aggregates from the "
    "cached dataset on the first request and reuses them thereafter. Batch inference "
    "is necessarily slower because it processes every uploaded row, but it remains "
    "a batch operation rather than an interactive request. No GPU is required for "
    "any of these operations."
)

h2("11.9 Objective-Wise Assessment")
add_table(
    ["Objective", "Status", "Evidence"],
    [
        ["Assemble and validate a long-run dataset", "Achieved", "15,279 rows, 1985\u20132026, zero missing values and zero duplicate dates."],
        ["Design leakage-safe pre-processing and features", "Achieved", "Shifted lags, rolling windows, cyclical encoding, chronological split and documented controls."],
        ["Train and compare regression models", "Achieved", "Eight approaches including baselines, linear models, trees and a Hurdle model."],
        ["Train and compare intensity classifiers", "Achieved", "Five models with accuracy, macro/weighted F1 and per-class analysis."],
        ["Evaluate on a future hold-out and with time-series CV", "Achieved", "3,056-row future test set and five expanding-window folds."],
        ["Identify and interpret important features", "Achieved", "Humidity, wind, pressure tendency and antecedent rainfall analysed."],
        ["Integrate into a usable application", "Achieved", "Flask dashboard, prediction studio, explorer, comparison, batch inference and exports."],
        ["Document results and limitations", "Achieved", "Fourteen-chapter report with reproducible figures, references and a future roadmap."],
    ],
    [2.05, 0.92, 3.30],
    caption="Table 11.1: Assessment of project objectives.",
    font_size=8.8,
    center_cols={1},
)

h2("11.10 Threats to Validity")
add_table(
    ["Threat", "Effect on the results", "Mitigation / interpretation"],
    [
        ["Single-station data", "The model may not transfer to other rainfall regimes.", "Present the result as a station-specific case study, not a regional forecast product."],
        ["Reanalysis rather than gauge data", "Grid-cell averages may smooth local extremes.", "State the provenance clearly and recommend gauge/AWS validation."],
        ["Single contiguous test era", "The score is sensitive to 2018\u20132026 climate variability.", "Report fold-level variability alongside the hold-out score."],
        ["Point forecasts", "A single depth cannot express uncertainty or a range.", "Discuss probabilistic and quantile extensions; avoid over-confident advisories."],
        ["Artificial class thresholds", "Adjacent classes are intrinsically confusable.", "Report per-class metrics and the confusion matrix rather than accuracy alone."],
        ["Tree importance bias", "Impurity importance can favour high-cardinality features.", "Use it as a descriptive signal and recommend permutation/SHAP analysis."],
        ["Prototype deployment", "No authentication, persistent history or operational monitoring.", "Treat the interface as a demonstration and require human verification."],
    ],
    [1.55, 2.45, 2.27],
    caption="Table 11.2: Threats to validity and their treatment.",
    font_size=8.7,
)

h2("11.11 Discussion")
p(
    "The most important finding is not a single R\u00b2 value. It is that the "
    "choice of problem formulation changes the practical behaviour of the system. "
    "A single-stage regressor with a respectable MAE can still invent rain on dry "
    "days; a classifier with high accuracy can still miss most torrential events. "
    "By separating occurrence from severity, reporting wet-day and dry-day errors, "
    "and examining per-class recall, RainVision produces a more honest picture of "
    "what the model can and cannot do."
)
p(
    "The results are good enough to demonstrate a complete machine learning "
    "lifecycle and to support exploratory decision scenarios, but they are not good "
    "enough for an operational warning system. The model under-predicts the largest "
    "events, torrential recall is about 52%, and the evaluation covers one station. "
    "These limitations do not invalidate the project; they define the boundary "
    "between a successful academic prototype and a production meteorological "
    "service. The next chapter summarises the achievements within that boundary, "
    "and Chapter 13 sets out a responsible path beyond it."
)


# ===========================================================================
# CHAPTER 12
# ===========================================================================
h1("CHAPTER 12: CONCLUSION")

h2("12.1 Summary of the Work")
p(
    "This project designed, implemented and evaluated RainVision, an end-to-end "
    "machine learning platform for daily rainfall-depth prediction, intensity "
    "classification and climate analytics. The system uses a 42-year record of "
    "15,279 daily observations from the Metropolis Central Station, a leakage-safe "
    "17-feature pipeline, a chronological 80/20 split, a suite of regression and "
    "classification models, a two-stage Hurdle model, expanding-window "
    "cross-validation and a Flask web interface."
)
p(
    "The final benchmark shows that the Hurdle model is the strongest regression "
    "approach, with R\u00b2 = 0.6465, MAE = 1.775 mm and RMSE = 6.264 mm on the "
    "future hold-out period. The random forest is the strongest classifier, with "
    "82.53% accuracy, 0.6780 macro F1 and 0.8296 weighted F1. The Hurdle model also "
    "has the best dry-day behaviour, with a mean prediction of 0.062 mm on observed "
    "dry days compared with 0.891 mm for OLS. Cross-validation confirms that the "
    "result is not a single lucky split: the mean fold R\u00b2 is 0.6048 with a "
    "standard deviation of 0.086."
)
p(
    "The project does not claim operational-grade accuracy. The largest events are "
    "under-predicted, torrential recall is about 52%, and the evaluation covers one "
    "station. What it does demonstrate is a reproducible, methodologically "
    "defensible workflow that connects raw meteorological data to an interactive "
    "prediction and analytics application, and that reports its own limitations "
    "rather than hiding them behind a single aggregate score."
)

h2("12.2 Achievement of Objectives")
p(
    "All eight objectives stated in Section 1.4 were addressed. A validated "
    "long-run dataset was assembled; a leakage-safe feature pipeline was "
    "implemented; regression and classification suites were trained and compared; "
    "the Hurdle model was developed and evaluated; time-series cross-validation and "
    "hyperparameter tuning were performed; feature importance was interpreted; the "
    "models were integrated into a Flask application; and the complete system was "
    "documented in this report. The objective-wise assessment is summarised in "
    "Table 11.1."
)

h2("12.3 Contributions")
bullets([
    "A reproducible benchmark for a 42-year daily rainfall record with a strict "
    "forward-in-time test period.",
    "A clear demonstration of why zero-inflation and temporal leakage require "
    "special treatment in environmental machine learning.",
    "A two-stage Hurdle formulation that improves regression accuracy and "
    "substantially reduces false rain on dry days.",
    "A balanced multi-class intensity evaluation that reports rare-class recall "
    "instead of relying on accuracy alone.",
    "A modular Flask application that exposes live prediction, comparison, "
    "dataset exploration, batch inference and downloadable reports.",
    "A complete academic report with documented data provenance, code excerpts, "
    "figures, limitations and a future roadmap.",
])

h2("12.4 Concluding Remarks")
p(
    "Rainfall prediction is a useful test case for applied machine learning "
    "because it combines a physically meaningful problem with awkward statistical "
    "properties: many zeros, a heavy tail, strong seasonality and a strict temporal "
    "ordering. RainVision shows that careful problem formulation, domain-guided "
    "features and disaggregated evaluation can produce a system that is both more "
    "accurate and more honest than a generic regression model. The project also "
    "shows where the boundary lies: point forecasts from a single station are a "
    "starting point for decision support, not a substitute for a calibrated, "
    "multi-source early-warning service."
)


# ===========================================================================
# CHAPTER 13
# ===========================================================================
h1("CHAPTER 13: LIMITATIONS & FUTURE ENHANCEMENTS")

h2("13.1 Current Limitations")
add_table(
    ["Area", "Limitation", "Consequence"],
    [
        ["Spatial coverage", "One station (Metropolis Central) represents a single point in the Gujarat corridor.", "The model cannot produce district or statewide maps and may not transfer to a different rainfall regime."],
        ["Temporal resolution", "The target is 24-hour accumulated rainfall.", "Sub-daily cloudbursts and flash-flood timing are not represented."],
        ["Data source", "The record is based on ECMWF ERA5 reanalysis rather than a dense gauge network.", "Local extremes may be smoothed; gauge validation is required before operational use."],
        ["Extreme events", "Tree ensembles under-predict the largest rainfall amounts.", "Torrential recall is 0.516 and the highest events have large negative residuals."],
        ["Uncertainty", "The interface returns a point estimate and a heuristic probability, not a calibrated prediction interval.", "Users cannot see the full range of plausible outcomes."],
        ["Class boundaries", "Intensity tiers are fixed thresholds on a continuous target.", "Adjacent classes are intrinsically confusable and macro F1 is limited."],
        ["Explainability", "Feature attribution in the interface is a physics-informed summary, not a full SHAP explanation of every model.", "The explanation is useful for communication but not a formal causal analysis."],
        ["Deployment", "Single-user Flask development server, in-memory history and no authentication.", "Not suitable for public or mission-critical operation without additional engineering."],
        ["Data freshness", "The workbook ends on 31 October 2026 and is not automatically updated.", "The application is a historical/offline prototype unless a live feed is connected."],
    ],
    [1.23, 2.48, 2.56],
    caption="Table 13.1: Current limitations of RainVision.",
    font_size=8.5,
)

h2("13.2 Future Enhancements")
add_table(
    ["Enhancement", "Description", "Expected benefit"],
    [
        ["Multi-station ingestion", "Add a station dimension, spatial features and gridded IMD/AWS feeds.", "Move from a point case study to a regional rainfall product."],
        ["Probabilistic forecasting", "Use quantile regression, conformal prediction or a distributional model.", "Provide prediction intervals and better communicate extreme-event risk."],
        ["Sequence models", "Evaluate LSTM, Temporal CNN or Transformer encoders on the daily sequence.", "Capture longer-range dependencies that hand-crafted lags may miss."],
        ["Radar and satellite fusion", "Incorporate Doppler weather radar reflectivity and satellite cloud-top temperature.", "Improve short-duration and extreme-event detection."],
        ["Cost-sensitive decisions", "Assign explicit costs to missed heavy rain and false alarms and optimise the decision threshold.", "Align the classifier with operational priorities rather than raw accuracy."],
        ["Explainability", "Add SHAP or permutation importance per prediction and a model card for each artefact.", "Increase transparency and support domain review."],
        ["Persistent backend", "Move history, metadata and user feedback into PostgreSQL or SQLite with authentication.", "Support multi-user deployment, audit trails and monitoring."],
        ["Automated retraining", "Schedule data ingestion, drift checks and model retraining with versioned artefacts.", "Keep the system current and detect performance degradation."],
        ["Mobile and alerting layer", "Add a responsive PWA or mobile client with opt-in notifications.", "Improve accessibility for field users and decision makers."],
    ],
    [1.55, 2.65, 2.07],
    caption="Table 13.2: Future enhancement opportunities.",
    font_size=8.5,
)

h2("13.3 Phased Roadmap")
add_table(
    ["Phase", "Focus", "Deliverables"],
    [
        ["Phase 1 (short term)", "Data and validation", "Gauge validation, multi-station schema, automated quality flags, additional extreme-event tests."],
        ["Phase 2 (medium term)", "Modelling", "Probabilistic/quantile models, sequence-model comparison, cost-sensitive thresholds and calibrated probabilities."],
        ["Phase 3 (medium term)", "Explainability and reporting", "Per-prediction SHAP, model cards, automated PDF/CSV reports and a richer analytics page."],
        ["Phase 4 (long term)", "Deployment", "Persistent database, authentication, scheduled ingestion, monitoring and a containerised production service."],
        ["Phase 5 (research)", "Regional extension", "Gridded spatial model, radar/satellite fusion and collaboration with a meteorological domain expert."],
    ],
    [1.35, 1.55, 3.37],
    caption="Table 13.3: Phased enhancement roadmap.",
    font_size=8.8,
)

h2("13.4 Responsible Deployment")
p(
    "Any extension beyond the current prototype should be accompanied by a formal "
    "model card, a documented validation protocol and human review of high-impact "
    "alerts. Rainfall predictions can influence irrigation, transport and public "
    "safety decisions; a false sense of certainty is therefore more dangerous than "
    "a clearly stated range. The project's advisory text and interface labels are "
    "designed with this principle in mind, and future work should preserve the "
    "distinction between a statistical estimate and an official warning."
)


# ===========================================================================
# CHAPTER 14
# ===========================================================================
h1("CHAPTER 14: REFERENCES / BIBLIOGRAPHY")

references = [
    "India Meteorological Department, \u201cRainfall information and monsoon reports,\u201d Government of India, 2024. [Online]. Available: https://mausam.imd.gov.in/",
    "World Meteorological Organization, Guide to Meteorological Instruments and Methods of Observation, WMO-No. 8, 2021 ed. Geneva: WMO, 2021.",
    "H. Hersbach et al., \u201cThe ERA5 global reanalysis,\u201d Quarterly Journal of the Royal Meteorological Society, vol. 146, no. 730, pp. 1999\u20132049, 2020.",
    "L. Breiman, \u201cRandom forests,\u201d Machine Learning, vol. 45, no. 1, pp. 5\u201332, 2001.",
    "J. H. Friedman, \u201cGreedy function approximation: A gradient boosting machine,\u201d Annals of Statistics, vol. 29, no. 5, pp. 1189\u20131232, 2001.",
    "F. Pedregosa et al., \u201cScikit-learn: Machine learning in Python,\u201d Journal of Machine Learning Research, vol. 12, pp. 2825\u20132830, 2011.",
    "W. McKinney, \u201cData structures for statistical computing in Python,\u201d in Proceedings of the 9th Python in Science Conference, 2010, pp. 56\u201361.",
    "C. R. Harris et al., \u201cArray programming with NumPy,\u201d Nature, vol. 585, pp. 357\u2013362, 2020.",
    "J. D. Hunter, \u201cMatplotlib: A 2D graphics environment,\u201d Computing in Science & Engineering, vol. 9, no. 3, pp. 90\u201395, 2007.",
    "M. L. Waskom, \u201cseaborn: Statistical data visualization,\u201d Journal of Open Source Software, vol. 6, no. 60, p. 3021, 2021.",
    "M. Grinberg, Flask Web Development: Developing Web Applications with Python, 2nd ed. Sebastopol, CA: O\u2019Reilly Media, 2018.",
    "A. G\u00e9ron, Hands-On Machine Learning with Scikit-Learn, Keras, and TensorFlow, 3rd ed. Sebastopol, CA: O\u2019Reilly Media, 2022.",
    "R. J. Hyndman and G. Athanasopoulos, Forecasting: Principles and Practice, 3rd ed. Melbourne: OTexts, 2021.",
    "C. Bergmeir and J. M. Ben\u00edtez, \u201cOn the use of cross-validation for time series predictor evaluation,\u201d Information Sciences, vol. 191, pp. 192\u2013213, 2012.",
    "T. Saito and M. Rehmsmeier, \u201cThe precision-recall plot is more informative than the ROC plot when evaluating binary classifiers on imbalanced datasets,\u201d PLoS ONE, vol. 10, no. 3, e0118432, 2015.",
    "S. M. Lundberg and S.-I. Lee, \u201cA unified approach to interpreting model predictions,\u201d in Advances in Neural Information Processing Systems, vol. 30, 2017.",
    "scikit-learn developers, \u201cTimeSeriesSplit and model selection documentation,\u201d 2024. [Online]. Available: https://scikit-learn.org/stable/modules/cross_validation.html",
    "Pallets Projects, \u201cFlask documentation,\u201d 2024. [Online]. Available: https://flask.palletsprojects.com/",
    "ECMWF, \u201cERA5 hourly data on single levels from 1940 to present,\u201d Copernicus Climate Change Service, 2024. [Online]. Available: https://cds.climate.copernicus.eu/",
    "RainVision Project Team, \u201cRainVision: Rainfall forecasting, prediction and climate analytics platform \u2014 source code and project workbook,\u201d M.Sc. IT Foundational Project I, 2026.",
]
for i, ref in enumerate(references, 1):
    paragraph = doc.add_paragraph()
    r1 = paragraph.add_run(f"[{i}]  ")
    set_run_font(r1, size=11, bold=True)
    r2 = paragraph.add_run(ref)
    set_run_font(r2, size=11)
    paragraph.paragraph_format.left_indent = Inches(0.45)
    paragraph.paragraph_format.first_line_indent = Inches(-0.45)
    paragraph.paragraph_format.line_spacing = 1.15
    paragraph.paragraph_format.space_after = Pt(6)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

p("", space_after=16)
p(
    "Note: All web references were last accessed in November 2026. The project "
    "workbook and source code are the primary artefacts for reproducing the "
    "results reported in this document.",
    size=9.5, italic=True, align=WD_ALIGN_PARAGRAPH.LEFT, line_spacing=1.15,
)


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------
OUT.parent.mkdir(parents=True, exist_ok=True)
doc.save(OUT)
print(f"Saved: {OUT}")
print(f"Size: {OUT.stat().st_size / 1024:.1f} KB")
