"""
generate_docx.py
Generates the complete, publication-quality Microsoft Word (.docx) technical report.
Internship Technical Report for Infosys Springboard
Project: Lead Management and Outreach Automation System (SalesGenie AI)
Student: Mahek Saba Shaikh | Role: Frontend Developer | Team: Team C
"""

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

from report_content import (
    METADATA, CERTIFICATE_TEXT, ACKNOWLEDGEMENT_TEXT, ABSTRACT_TEXT,
    CHAPTER_6_TEXT, CHAPTER_7_TEXT, CHAPTER_8_TEXT, CHAPTER_9_TEXT,
    CHAPTER_10_TEXT, CHAPTER_11_TEXT, CHAPTER_12_TEXT
)
from report_content_part2 import (
    CHAPTER_13_TEXT, CHAPTER_14_TEXT, CHAPTER_15_TEXT, CHAPTER_16_TEXT,
    CHAPTER_17_TEXT, CHAPTER_18_TEXT, CHAPTER_19_TEXT, CHAPTER_20_TEXT,
    CHAPTER_21_TEXT, CHAPTER_22_TEXT, DAYWISE_SCHEDULE_ROWS
)
from report_content_part3 import (
    CHAPTER_23_TEXT, CHAPTER_24_TEXT, CHAPTER_25_TEXT, CHAPTER_26_TEXT,
    CHAPTER_27_TEXT
)

# Color Constants
COLOR_PRIMARY = RGBColor(0, 112, 173)      # Infosys Corporate Blue #0070AD
COLOR_SECONDARY = RGBColor(3, 105, 161)    # Deep Slate Blue #0369A1
COLOR_TEXT = RGBColor(30, 41, 59)          # Dark Slate #1E293B
COLOR_MUTED = RGBColor(100, 116, 139)      # Muted Gray #64748B
COLOR_ACCENT = RGBColor(6, 182, 212)       # Cyan Accent #06B6D4

HEX_PRIMARY = "0070AD"
HEX_LIGHT_BG = "F0F9FF"
HEX_ZEBRA = "F8FAFC"
HEX_BORDER = "CBD5E1"
HEX_CODE_BG = "F1F5F9"

def set_cell_background(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    tcPr.append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>'))

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def set_cell_borders(cell, top=None, bottom=None, left=None, right=None):
    tcPr = cell._tc.get_or_add_tcPr()
    borders_elm = parse_xml(f'<w:tcBorders {nsdecls("w")}/>')
    
    for side, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        if val:
            color, sz = val
            borders_elm.append(parse_xml(f'<w:{side} {nsdecls("w")} w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'))
        else:
            borders_elm.append(parse_xml(f'<w:{side} {nsdecls("w")} w:val="none"/>'))
    tcPr.append(borders_elm)

def add_callout(doc, text, title=None):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    
    cell = table.cell(0, 0)
    cell.width = Inches(6.5)
    set_cell_background(cell, HEX_LIGHT_BG)
    set_cell_margins(cell, top=140, bottom=140, left=200, right=180)
    set_cell_borders(cell, left=(HEX_PRIMARY, 24), top=(HEX_BORDER, 4), right=(HEX_BORDER, 4), bottom=(HEX_BORDER, 4))
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    
    if title:
        rt = p.add_run(f"📌 {title}\n")
        rt.bold = True
        rt.font.name = "Calibri"
        rt.font.size = Pt(10.5)
        rt.font.color.rgb = COLOR_PRIMARY
        
    r = p.add_run(text.strip())
    r.font.name = "Calibri"
    r.font.size = Pt(10)
    r.font.color.rgb = COLOR_TEXT
    r.italic = True
    
    # Add spacing after callout
    sp = doc.add_paragraph()
    sp.paragraph_format.space_before = Pt(0)
    sp.paragraph_format.space_after = Pt(4)

def add_code_block(doc, code_text):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    
    cell = table.cell(0, 0)
    cell.width = Inches(6.5)
    set_cell_background(cell, HEX_CODE_BG)
    set_cell_margins(cell, top=120, bottom=120, left=160, right=160)
    set_cell_borders(cell, top=(HEX_BORDER, 4), bottom=(HEX_BORDER, 4), left=(HEX_BORDER, 4), right=(HEX_BORDER, 4))
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.05
    
    r = p.add_run(code_text.strip())
    r.font.name = "Consolas"
    r.font.size = Pt(9.0)
    r.font.color.rgb = RGBColor(15, 23, 42)
    
    sp = doc.add_paragraph()
    sp.paragraph_format.space_before = Pt(0)
    sp.paragraph_format.space_after = Pt(4)

def setup_page_header_footer(doc):
    for s in doc.sections:
        s.top_margin = Inches(1.0)
        s.bottom_margin = Inches(1.0)
        s.left_margin = Inches(1.0)
        s.right_margin = Inches(1.0)
        
        # Header
        header = s.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run("Infosys Springboard Technical Internship Program 2026 | Technical Report")
        hrun.font.name = "Calibri"
        hrun.font.size = Pt(8.5)
        hrun.font.color.rgb = COLOR_MUTED
        
        # Footer
        footer = s.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.LEFT
        frun1 = fp.add_run("Lead Management & Outreach Automation System | Frontend Developer: Mahek Saba Shaikh (Team C)")
        frun1.font.name = "Calibri"
        frun1.font.size = Pt(8.5)
        frun1.font.color.rgb = COLOR_MUTED
        
        # Add Page Number via field
        frun2 = fp.add_run("\t\tPage ")
        frun2.font.name = "Calibri"
        frun2.font.size = Pt(8.5)
        frun2.font.color.rgb = COLOR_MUTED
        
        fld = parse_xml(f'<w:fldSimple {nsdecls("w")} w:instr="PAGE"/>')
        fp._p.append(fld)

def render_markdown_section(doc, text):
    lines = text.strip().split("\n")
    i = 0
    in_code = False
    code_buffer = []
    
    while i < len(lines):
        line = lines[i]
        
        # Code fence handling
        if line.strip().startswith("```"):
            if in_code:
                # End of code block
                add_code_block(doc, "\n".join(code_buffer))
                code_buffer = []
                in_code = False
            else:
                in_code = True
            i += 1
            continue
            
        if in_code:
            code_buffer.append(line)
            i += 1
            continue
            
        # Markdown table detection
        if line.strip().startswith("|") and line.strip().endswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            render_text_table(doc, table_lines)
            continue
            
        # Headings
        if line.startswith("### "):
            h = doc.add_paragraph()
            h.paragraph_format.space_before = Pt(12)
            h.paragraph_format.space_after = Pt(4)
            h.paragraph_format.keep_with_next = True
            r = h.add_run(line[4:].strip())
            r.font.name = "Calibri"
            r.font.size = Pt(13)
            r.bold = True
            r.font.color.rgb = COLOR_SECONDARY
            i += 1
            continue
            
        if line.startswith("#### "):
            h = doc.add_paragraph()
            h.paragraph_format.space_before = Pt(8)
            h.paragraph_format.space_after = Pt(2)
            h.paragraph_format.keep_with_next = True
            r = h.add_run(line[5:].strip())
            r.font.name = "Calibri"
            r.font.size = Pt(11.5)
            r.bold = True
            r.font.color.rgb = COLOR_TEXT
            i += 1
            continue
            
        # Bullet items
        if line.strip().startswith("- ") or line.strip().startswith("* "):
            p = doc.add_paragraph(style='List Bullet')
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.line_spacing = 1.15
            parse_inlines_to_paragraph(p, line.strip()[2:])
            i += 1
            continue
            
        # Numbered items
        if len(line.strip()) > 2 and line.strip()[0].isdigit() and line.strip()[1] == ".":
            p = doc.add_paragraph(style='List Number')
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.line_spacing = 1.15
            parse_inlines_to_paragraph(p, line.strip()[3:])
            i += 1
            continue
            
        # Empty line
        if not line.strip():
            i += 1
            continue
            
        # Regular paragraph
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.15
        parse_inlines_to_paragraph(p, line.strip())
        i += 1

def parse_inlines_to_paragraph(paragraph, text):
    # Parses basic bold (**text**) and inline code (`code`)
    import re
    tokens = re.split(r'(\*\*.*?\*\*|`.*?`|\*.*?\*)', text)
    for token in tokens:
        if not token:
            continue
        if token.startswith("**") and token.endswith("**") and len(token) >= 4:
            r = paragraph.add_run(token[2:-2])
            r.bold = True
            r.font.name = "Calibri"
            r.font.size = Pt(11)
            r.font.color.rgb = COLOR_TEXT
        elif token.startswith("`") and token.endswith("`") and len(token) >= 2:
            r = paragraph.add_run(token[1:-1])
            r.font.name = "Consolas"
            r.font.size = Pt(9.5)
            r.font.color.rgb = RGBColor(180, 40, 40)
        elif token.startswith("*") and token.endswith("*") and len(token) >= 2:
            r = paragraph.add_run(token[1:-1])
            r.italic = True
            r.font.name = "Calibri"
            r.font.size = Pt(11)
            r.font.color.rgb = COLOR_TEXT
        else:
            r = paragraph.add_run(token)
            r.font.name = "Calibri"
            r.font.size = Pt(11)
            r.font.color.rgb = COLOR_TEXT

def render_text_table(doc, table_lines):
    if len(table_lines) < 2:
        return
        
    # Header row
    headers = [c.strip() for c in table_lines[0].split("|")[1:-1]]
    num_cols = len(headers)
    
    # Rows (skip separator line like |---|---|)
    rows_data = []
    for l in table_lines[1:]:
        if ":---" in l or "---" in l:
            continue
        cols = [c.strip() for c in l.split("|")[1:-1]]
        if len(cols) == num_cols:
            rows_data.append(cols)
            
    table = doc.add_table(rows=len(rows_data) + 1, cols=num_cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    
    # Header format
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = h.replace("**", "")
        set_cell_background(hdr_cells[i], HEX_PRIMARY)
        set_cell_margins(hdr_cells[i], top=120, bottom=120, left=140, right=140)
        set_cell_borders(hdr_cells[i], top=(HEX_PRIMARY, 8), bottom=(HEX_PRIMARY, 8), left=(HEX_PRIMARY, 4), right=(HEX_PRIMARY, 4))
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in p.runs:
            r.font.name = "Calibri"
            r.font.size = Pt(9.5)
            r.bold = True
            r.font.color.rgb = RGBColor(255, 255, 255)
            
    # Body rows
    for r_idx, row_items in enumerate(rows_data):
        row_cells = table.rows[r_idx + 1].cells
        bg_color = HEX_ZEBRA if (r_idx % 2 == 1) else "FFFFFF"
        for c_idx, val in enumerate(row_items):
            row_cells[c_idx].text = val.replace("**", "")
            set_cell_background(row_cells[c_idx], bg_color)
            set_cell_margins(row_cells[c_idx], top=80, bottom=80, left=120, right=120)
            set_cell_borders(row_cells[c_idx], top=(HEX_BORDER, 4), bottom=(HEX_BORDER, 4), left=(HEX_BORDER, 4), right=(HEX_BORDER, 4))
            p = row_cells[c_idx].paragraphs[0]
            p.paragraph_format.line_spacing = 1.05
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            for r in p.runs:
                r.font.name = "Calibri"
                r.font.size = Pt(9.0)
                r.font.color.rgb = COLOR_TEXT
                
    sp = doc.add_paragraph()
    sp.paragraph_format.space_before = Pt(2)
    sp.paragraph_format.space_after = Pt(6)

def add_chapter_heading(doc, num, title):
    doc.add_page_break()
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.keep_with_next = True
    
    r_sub = p.add_run(f"CHAPTER {num}\n")
    r_sub.font.name = "Calibri"
    r_sub.font.size = Pt(11)
    r_sub.bold = True
    r_sub.font.color.rgb = COLOR_ACCENT
    
    r_main = p.add_run(title)
    r_main.font.name = "Calibri"
    r_main.font.size = Pt(20)
    r_main.bold = True
    r_main.font.color.rgb = COLOR_PRIMARY
    
    # Underline bar
    bar_table = doc.add_table(rows=1, cols=1)
    bar_cell = bar_table.cell(0, 0)
    bar_cell.width = Inches(6.5)
    set_cell_background(bar_cell, HEX_PRIMARY)
    set_cell_margins(bar_cell, top=10, bottom=10, left=0, right=0)
    set_cell_borders(bar_cell)
    
    sp = doc.add_paragraph()
    sp.paragraph_format.space_before = Pt(4)
    sp.paragraph_format.space_after = Pt(6)

def build_cover_page(doc):
    p_org = doc.add_paragraph()
    p_org.paragraph_format.space_before = Pt(36)
    p_org.paragraph_format.space_after = Pt(4)
    p_org.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_org = p_org.add_run("INFOSYS SPRINGBOARD")
    r_org.font.name = "Calibri"
    r_org.font.size = Pt(16)
    r_org.bold = True
    r_org.font.color.rgb = COLOR_PRIMARY
    
    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(36)
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run("TECHNICAL INTERNSHIP PROGRAM 2026")
    r_sub.font.name = "Calibri"
    r_sub.font.size = Pt(12)
    r_sub.font.color.rgb = COLOR_MUTED
    
    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(18)
    p_title.paragraph_format.space_after = Pt(12)
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run("LEAD MANAGEMENT AND OUTREACH\nAUTOMATION SYSTEM")
    r_title.font.name = "Calibri"
    r_title.font.size = Pt(24)
    r_title.bold = True
    r_title.font.color.rgb = RGBColor(15, 23, 42)
    
    p_badge = doc.add_paragraph()
    p_badge.paragraph_format.space_before = Pt(0)
    p_badge.paragraph_format.space_after = Pt(28)
    p_badge.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_badge = p_badge.add_run("⚡ SalesGenie AI — Autonomous Sales Intelligence Platform")
    r_badge.font.name = "Calibri"
    r_badge.font.size = Pt(12)
    r_badge.bold = True
    r_badge.font.color.rgb = COLOR_SECONDARY
    
    p_desc = doc.add_paragraph()
    p_desc.paragraph_format.space_before = Pt(0)
    p_desc.paragraph_format.space_after = Pt(40)
    p_desc.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_desc = p_desc.add_run("A Comprehensive Technical Internship Report on Frontend Architecture,\nInteractive Streamlit Engineering, Custom Design Systems, and RESTful API Integration")
    r_desc.font.name = "Calibri"
    r_desc.font.size = Pt(11)
    r_desc.italic = True
    r_desc.font.color.rgb = COLOR_TEXT
    
    # Metadata Box Card
    card_table = doc.add_table(rows=6, cols=2)
    card_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    card_table.autofit = False
    
    metadata_rows = [
        ("Student Name:", METADATA["student_name"]),
        ("Designated Role:", METADATA["role"]),
        ("Engineering Squad:", METADATA["team"]),
        ("Organization:", METADATA["organization"]),
        ("Evaluation Track:", "Full-Stack AI & Autonomous Systems"),
        ("Submission Date:", METADATA["submission_date"])
    ]
    
    col_widths = [Inches(2.2), Inches(4.0)]
    for idx, (label, val) in enumerate(metadata_rows):
        row_cells = card_table.rows[idx].cells
        row_cells[0].width = col_widths[0]
        row_cells[1].width = col_widths[1]
        
        row_cells[0].text = label
        row_cells[1].text = val
        
        for c in row_cells:
            set_cell_background(c, HEX_LIGHT_BG if idx % 2 == 1 else "FFFFFF")
            set_cell_margins(c, top=80, bottom=80, left=140, right=140)
            set_cell_borders(c, top=(HEX_BORDER, 4), bottom=(HEX_BORDER, 4), left=(HEX_PRIMARY if c == row_cells[0] else HEX_BORDER, 12 if c == row_cells[0] else 4), right=(HEX_BORDER, 4))
            p = c.paragraphs[0]
            p.paragraph_format.line_spacing = 1.15
            for r in p.runs:
                r.font.name = "Calibri"
                r.font.size = Pt(10.5)
                r.font.color.rgb = COLOR_TEXT
        row_cells[0].paragraphs[0].runs[0].bold = True
        row_cells[0].paragraphs[0].runs[0].font.color.rgb = COLOR_PRIMARY

def build_certificate_page(doc):
    doc.add_page_break()
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(24)
    p.paragraph_format.space_after = Pt(18)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("CERTIFICATE OF COMPLETION\n(INTERNSHIP EVALUATION PLACEHOLDER)")
    r.font.name = "Calibri"
    r.font.size = Pt(18)
    r.bold = True
    r.font.color.rgb = COLOR_PRIMARY
    
    p_body = doc.add_paragraph()
    p_body.paragraph_format.space_before = Pt(12)
    p_body.paragraph_format.space_after = Pt(18)
    p_body.paragraph_format.line_spacing = 1.25
    r_body = p_body.add_run(CERTIFICATE_TEXT.strip())
    r_body.font.name = "Calibri"
    r_body.font.size = Pt(11)
    r_body.font.color.rgb = COLOR_TEXT
    
    # Signature Table
    sig_table = doc.add_table(rows=4, cols=2)
    sig_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    sig_table.autofit = False
    
    sig_data = [
        ("Mahek Saba Shaikh\nFrontend Developer, Team C\n(Student Signature)", "Industry Mentor / Technical Lead\nInfosys Springboard\n(Mentor Signature)"),
        ("\nDate: ________________________", "\nDate: ________________________"),
        ("Project Coordinator\nInternship Evaluation Committee\n(Internal Guide)", "Department Head / Academic Supervisor\nComputer Science & Engineering\n(Institutional Seal & Signature)"),
        ("\nDate: ________________________", "\nDate: ________________________")
    ]
    
    for idx, (left_text, right_text) in enumerate(sig_data):
        cells = sig_table.rows[idx].cells
        cells[0].width = Inches(3.2)
        cells[1].width = Inches(3.2)
        cells[0].text = left_text
        cells[1].text = right_text
        for c in cells:
            set_cell_margins(c, top=80, bottom=80, left=100, right=100)
            set_cell_borders(c)
            p = c.paragraphs[0]
            p.paragraph_format.line_spacing = 1.15
            for r in p.runs:
                r.font.name = "Calibri"
                r.font.size = Pt(10)
                r.font.color.rgb = COLOR_TEXT

def build_table_of_contents_page(doc):
    doc.add_page_break()
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(20)
    p.paragraph_format.space_after = Pt(14)
    r = p.add_run("TABLE OF CONTENTS")
    r.font.name = "Calibri"
    r.font.size = Pt(18)
    r.bold = True
    r.font.color.rgb = COLOR_PRIMARY
    
    toc_data = [
        ("Chapter 1", "Cover Page", "1"),
        ("Chapter 2", "Certificate Page (Evaluation Placeholder)", "2"),
        ("Chapter 3", "Acknowledgement", "3"),
        ("Chapter 4", "Abstract", "4"),
        ("Chapter 5", "Table of Contents", "5"),
        ("Chapter 6", "Introduction to Infosys Springboard Internship", "6"),
        ("Chapter 7", "Project Overview (SalesGenie AI)", "7"),
        ("Chapter 8", "Problem Statement", "8"),
        ("Chapter 9", "Project Objectives", "9"),
        ("Chapter 10", "Technologies and Tools Used", "10"),
        ("Chapter 11", "Frontend Architecture and Project Structure", "11"),
        ("Chapter 12", "My Role and Responsibilities (Frontend Developer)", "12"),
        ("Chapter 13", "Detailed Frontend Module Implementation", "13"),
        ("Chapter 14", "Leads Dashboard Implementation", "14"),
        ("Chapter 15", "Lead Intelligence Dashboard Implementation", "15"),
        ("Chapter 16", "Outreach Interface Implementation", "16"),
        ("Chapter 17", "AI Email Generator Implementation", "17"),
        ("Chapter 18", "Lead Scoring and Outreach Recommendations", "18"),
        ("Chapter 19", "Frontend and Backend API Integration", "19"),
        ("Chapter 20", "UI Testing and Validation", "20"),
        ("Chapter 21", "Challenges Faced and Engineering Solutions", "21"),
        ("Chapter 22", "Day-wise and Milestone-wise Progress (40-Day SDLC Schedule)", "22"),
        ("Chapter 23", "Screenshots of Actual Project UI (Figures 1 to 6)", "23"),
        ("Chapter 24", "Skills and Learning Outcomes", "24"),
        ("Chapter 25", "Conclusion", "25"),
        ("Chapter 26", "Future Enhancements", "26"),
        ("Chapter 27", "References", "27")
    ]
    
    toc_table = doc.add_table(rows=len(toc_data) + 1, cols=3)
    toc_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    toc_table.autofit = False
    
    col_w = [Inches(1.5), Inches(4.2), Inches(0.8)]
    
    # Header
    hdr = toc_table.rows[0].cells
    hdr[0].text = "Chapter"
    hdr[1].text = "Title / Subject Matter"
    hdr[2].text = "Page"
    for i, c in enumerate(hdr):
        c.width = col_w[i]
        set_cell_background(c, HEX_PRIMARY)
        set_cell_margins(c, top=80, bottom=80, left=100, right=100)
        set_cell_borders(c, top=(HEX_PRIMARY, 4), bottom=(HEX_PRIMARY, 4), left=(HEX_PRIMARY, 4), right=(HEX_PRIMARY, 4))
        p = c.paragraphs[0]
        if i == 2:
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        for r in p.runs:
            r.font.name = "Calibri"
            r.font.size = Pt(10)
            r.bold = True
            r.font.color.rgb = RGBColor(255, 255, 255)
            
    for idx, (ch, name, pg) in enumerate(toc_data):
        row_c = toc_table.rows[idx + 1].cells
        row_c[0].width = col_w[0]
        row_c[1].width = col_w[1]
        row_c[2].width = col_w[2]
        
        row_c[0].text = ch
        row_c[1].text = name
        row_c[2].text = pg
        
        bg_col = HEX_ZEBRA if idx % 2 == 1 else "FFFFFF"
        for i, c in enumerate(row_c):
            set_cell_background(c, bg_col)
            set_cell_margins(c, top=60, bottom=60, left=100, right=100)
            set_cell_borders(c, top=(HEX_BORDER, 2), bottom=(HEX_BORDER, 2), left=(HEX_BORDER, 2), right=(HEX_BORDER, 2))
            p = c.paragraphs[0]
            if i == 2:
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            for r in p.runs:
                r.font.name = "Calibri"
                r.font.size = Pt(9.5)
                r.font.color.rgb = COLOR_TEXT
                if i == 0:
                    r.bold = True
                    r.font.color.rgb = COLOR_PRIMARY

def add_image_figure(doc, img_path, fig_title, fig_caption, explanation):
    if not os.path.exists(img_path):
        print(f"Warning: Image file not found: {img_path}")
        return
        
    p_img = doc.add_paragraph()
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_img.paragraph_format.space_before = Pt(12)
    p_img.paragraph_format.space_after = Pt(4)
    run_img = p_img.add_run()
    run_img.add_picture(img_path, width=Inches(6.2))
    
    p_cap = doc.add_paragraph()
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.space_before = Pt(2)
    p_cap.paragraph_format.space_after = Pt(8)
    p_cap.paragraph_format.keep_with_next = True
    
    r_cap_lbl = p_cap.add_run(fig_title + ": ")
    r_cap_lbl.font.name = "Calibri"
    r_cap_lbl.font.size = Pt(9.5)
    r_cap_lbl.bold = True
    r_cap_lbl.font.color.rgb = COLOR_PRIMARY
    
    r_cap_txt = p_cap.add_run(fig_caption)
    r_cap_txt.font.name = "Calibri"
    r_cap_txt.font.size = Pt(9.5)
    r_cap_txt.italic = True
    r_cap_txt.font.color.rgb = COLOR_MUTED
    
    p_exp = doc.add_paragraph()
    p_exp.paragraph_format.space_before = Pt(2)
    p_exp.paragraph_format.space_after = Pt(14)
    p_exp.paragraph_format.line_spacing = 1.15
    parse_inlines_to_paragraph(p_exp, explanation)

def build_complete_report():
    print("Initiating Microsoft Word Document compilation...")
    doc = docx.Document()
    setup_page_header_footer(doc)
    
    # 1. Cover Page
    print("Building Cover Page...")
    build_cover_page(doc)
    
    # 2. Certificate Page
    print("Building Certificate Page...")
    build_certificate_page(doc)
    
    # 3. Acknowledgement
    print("Building Acknowledgement...")
    add_chapter_heading(doc, 3, "Acknowledgement")
    render_markdown_section(doc, ACKNOWLEDGEMENT_TEXT)
    
    # 4. Abstract
    print("Building Abstract...")
    add_chapter_heading(doc, 4, "Abstract")
    render_markdown_section(doc, ABSTRACT_TEXT)
    
    # 5. Table of Contents
    print("Building Table of Contents...")
    build_table_of_contents_page(doc)
    
    # 6. Introduction to Infosys Springboard Internship
    print("Building Chapter 6: Introduction...")
    add_chapter_heading(doc, 6, "Introduction to Infosys Springboard Internship")
    render_markdown_section(doc, CHAPTER_6_TEXT)
    
    # 7. Project Overview
    print("Building Chapter 7: Project Overview...")
    add_chapter_heading(doc, 7, "Project Overview (SalesGenie AI)")
    render_markdown_section(doc, CHAPTER_7_TEXT)
    
    # 8. Problem Statement
    print("Building Chapter 8: Problem Statement...")
    add_chapter_heading(doc, 8, "Problem Statement")
    render_markdown_section(doc, CHAPTER_8_TEXT)
    
    # 9. Project Objectives
    print("Building Chapter 9: Project Objectives...")
    add_chapter_heading(doc, 9, "Project Objectives")
    render_markdown_section(doc, CHAPTER_9_TEXT)
    
    # 10. Technologies and Tools Used
    print("Building Chapter 10: Technologies and Tools Used...")
    add_chapter_heading(doc, 10, "Technologies and Tools Used")
    render_markdown_section(doc, CHAPTER_10_TEXT)
    
    # 11. Frontend Architecture and Project Structure
    print("Building Chapter 11: Frontend Architecture...")
    add_chapter_heading(doc, 11, "Frontend Architecture and Project Structure")
    render_markdown_section(doc, CHAPTER_11_TEXT)
    
    # 12. My Role and Responsibilities
    print("Building Chapter 12: My Role and Responsibilities...")
    add_chapter_heading(doc, 12, "My Role and Responsibilities")
    render_markdown_section(doc, CHAPTER_12_TEXT)
    
    # 13. Detailed Frontend Module Implementation
    print("Building Chapter 13: Detailed Frontend Module Implementation...")
    add_chapter_heading(doc, 13, "Detailed Frontend Module Implementation")
    render_markdown_section(doc, CHAPTER_13_TEXT)
    
    # 14. Leads Dashboard Implementation
    print("Building Chapter 14: Leads Dashboard Implementation...")
    add_chapter_heading(doc, 14, "Leads Dashboard Implementation")
    render_markdown_section(doc, CHAPTER_14_TEXT)
    
    # 15. Lead Intelligence Dashboard Implementation
    print("Building Chapter 15: Lead Intelligence Dashboard Implementation...")
    add_chapter_heading(doc, 15, "Lead Intelligence Dashboard Implementation")
    render_markdown_section(doc, CHAPTER_15_TEXT)
    
    # 16. Outreach Interface Implementation
    print("Building Chapter 16: Outreach Interface Implementation...")
    add_chapter_heading(doc, 16, "Outreach Interface Implementation")
    render_markdown_section(doc, CHAPTER_16_TEXT)
    
    # 17. AI Email Generator Implementation
    print("Building Chapter 17: AI Email Generator Implementation...")
    add_chapter_heading(doc, 17, "AI Email Generator Implementation")
    render_markdown_section(doc, CHAPTER_17_TEXT)
    
    # 18. Lead Scoring and Outreach Recommendations
    print("Building Chapter 18: Lead Scoring and Recommendations...")
    add_chapter_heading(doc, 18, "Lead Scoring and Outreach Recommendations")
    render_markdown_section(doc, CHAPTER_18_TEXT)
    
    # 19. Frontend and Backend API Integration
    print("Building Chapter 19: Frontend and Backend API Integration...")
    add_chapter_heading(doc, 19, "Frontend and Backend API Integration")
    render_markdown_section(doc, CHAPTER_19_TEXT)
    
    # 20. UI Testing and Validation
    print("Building Chapter 20: UI Testing and Validation...")
    add_chapter_heading(doc, 20, "UI Testing and Validation")
    render_markdown_section(doc, CHAPTER_20_TEXT)
    
    # 21. Challenges Faced and Solutions
    print("Building Chapter 21: Challenges Faced and Solutions...")
    add_chapter_heading(doc, 21, "Challenges Faced and Solutions")
    render_markdown_section(doc, CHAPTER_21_TEXT)
    
    # 22. Day-wise and Milestone-wise Progress
    print("Building Chapter 22: Day-wise Progress...")
    add_chapter_heading(doc, 22, "Day-wise and Milestone-wise Progress (40-Day SDLC Schedule)")
    render_markdown_section(doc, CHAPTER_22_TEXT)
    
    # Build 40-Day SDLC Table
    print("Building 40-Day SDLC Schedule Table in Word...")
    table_lines = ["| Timeline | Milestone | Frontend Task Description | Status |", "| :--- | :--- | :--- | :--- |"]
    for day, ms, desc, st in DAYWISE_SCHEDULE_ROWS:
        table_lines.append(f"| {day} | {ms} | {desc} | {st} |")
    render_text_table(doc, table_lines)
    
    # 23. Screenshots of Actual Project UI
    print("Building Chapter 23: Screenshots Gallery...")
    add_chapter_heading(doc, 23, "Screenshots of Actual Project UI")
    
    intro_p = doc.add_paragraph()
    intro_p.paragraph_format.space_before = Pt(6)
    intro_p.paragraph_format.space_after = Pt(12)
    intro_p.paragraph_format.line_spacing = 1.15
    intro_p.add_run(
        "This chapter presents actual, high-resolution screenshots captured directly from the live, running SalesGenie AI frontend application "
        "executing on http://localhost:8501. Each screenshot illustrates a core frontend component designed and engineered by the author, "
        "accompanied by formal figure numbering, descriptive titles, captions, and in-depth architectural explanations."
    )
    
    # Figure 1
    add_image_figure(
        doc,
        "Internship_Report/screenshots/fig1_main_dashboard.png",
        "Figure 1",
        "Executive Dashboard Top View illustrating high-level KPI cards and pipeline activity metrics.",
        "Figure 1 captures the executive command center of SalesGenie AI (`tab_dash`). The top KPI strip presents five primary pipeline metrics: Total Prospects (5), Hot Leads (1), Warm Leads (1), Cold Leads (0), and Conversion Rate (20.0%). The secondary metrics row highlights campaign drafting volume, call interaction logs, and platform velocity. The persistent sidebar on the left displays the active target prospect card for 'TechCorp Solutions' along with company initial badge, industry, and funding stage tags."
    )
    
    # Figure 1b
    add_image_figure(
        doc,
        "Internship_Report/screenshots/fig1b_dashboard_analytics.png",
        "Figure 1b",
        "Executive Pipeline Analytics Charts & Top Ranked Prospects Leaderboard.",
        "Figure 1b illustrates the analytics visualizations and dynamic leaderboard of the Executive Dashboard. Two native Streamlit bar charts render the quantitative distribution of leads grouped by qualification status (Hot 70–100, Warm 50–69, Cold 0–49) and industry vertical (Enterprise Software, AI, Cloud Computing, Fintech, Healthcare AI). Directly below the charts, the Top Ranked Prospects Leaderboard displays all active database records sorted dynamically in descending order of their AI qualification score."
    )
    
    # Figure 2
    add_image_figure(
        doc,
        "Internship_Report/screenshots/fig2_leads_management.png",
        "Figure 2",
        "Leads Management interface displaying the 'Add New Prospect' validated manual entry form.",
        "Figure 2 displays the primary prospect onboarding form within the Leads Management tab (`tab_leads`). The layout is organized into two symmetrical columns (`col_m1` and `col_m2`) encapsulated inside an `st.form` container to optimize network requests. The form enforces client-side validation on Company Name, Contact Name, and Business Email before dispatching a POST request to `/leads/`. The bottom text area captures the prospect's primary technical pain point."
    )
    
    # Figure 2b
    add_image_figure(
        doc,
        "Internship_Report/screenshots/fig2b_leads_directory.png",
        "Figure 2b",
        "Active Prospects Directory sub-tab with live search, industry/stage filters, and data grid.",
        "Figure 2b illustrates the directory view where sales representatives inspect and filter active prospects. The interface features a 3-way filtering strip: a live text query input matching company name or contact, an industry dropdown filter, and a funding stage dropdown filter. Filtered records populate a clean DataFrame table with hidden row indexes. Directly below the table, a horizontal radio selector strip allows the sales rep to bind any prospect row directly as the active global prospect across the entire application."
    )
    
    # Figure 3
    add_image_figure(
        doc,
        "Internship_Report/screenshots/fig3_lead_intelligence.png",
        "Figure 3",
        "Lead Intelligence & Qualification Engine presenting AI-synthesized company profiling cards.",
        "Figure 3 captures the strategic intelligence briefing generated for the active prospect (TechCorp Solutions). The top section provides action trigger buttons for 'Generate AI Company Profile Analysis' and 'Compute Qualification Score'. Below, three glassmorphic cards with distinct left accent borders present synthesized company context: Stated Business Needs (Amber Border), High-Value Opportunities (Cyan Border), and Market Situation & Trends (Purple Border)."
    )
    
    # Figure 4
    add_image_figure(
        doc,
        "Internship_Report/screenshots/fig4_lead_scoring.png",
        "Figure 4",
        "Lead Qualification Score hero card with 🔥 VERY HOT badge, 82% conversion probability, and scoring attribution.",
        "Figure 4 depicts the core qualification decision engine. The visual hero card features an emerald green top border and displays a bold 87/100 score alongside an eye-catching `🔥 VERY HOT (87/100) — CALL TODAY` status badge. The estimated conversion probability is calculated at 82%. Directly below, two glassmorphic cards outline the Qualification Rationale and Recommended Next Action. The expanded accordion displays individual score factors derived from the heuristic model (+25 pts for Series C funding, +15 pts for 250–500 employees, +12 pts for product-market fit, +10 pts for urgency)."
    )
    
    # Figure 5
    add_image_figure(
        doc,
        "Internship_Report/screenshots/fig5_outreach_studio.png",
        "Figure 5",
        "Outreach Studio interface illustrating AI Outreach Strategy & Personalization Guidance.",
        "Figure 5 captures the preparation stage of the Outreach Studio (`tab_outreach`). Based on the prospect's 87/100 score, the heuristic strategy engine generates a high-urgency briefing recommending a direct pitch within 24 hours focusing on 65% processing gains. The personalization highlights box extracts the prospect's funding stage and specific pain point. Below the guidance cards, the user selects the desired voice tone (Professional, Friendly, Urgent) and clicks 'Generate Personalized Email' to initiate the drafting sequence."
    )
    
    # Figure 6
    add_image_figure(
        doc,
        "Internship_Report/screenshots/fig6_ai_email_generator.png",
        "Figure 6",
        "Superhuman-style email drafting suite featuring live editor, real-time stats, and truthful dispatch handler.",
        "Figure 6 displays the complete authoring environment. The drafting container features simulated macOS window control dots and displays the recipient's contact information. The AI-drafted subject line and personalized body are rendered inside live editable fields, seamlessly referencing the prospect's Series C funding milestone, data scaling challenges, and quantifiable peer benchmarks (65% cycle reduction, 40% cost reduction). Below the editor, a real-time telemetry strip displays word count (88 words), character count (662 chars), reading time (~26 sec), and tone badge. The interface includes a one-click copyable markdown code block and an email dispatch trigger that truthfully reports backend SMTP availability."
    )
    
    # 24. Skills and Learning Outcomes
    print("Building Chapter 24: Skills and Learning Outcomes...")
    add_chapter_heading(doc, 24, "Skills and Learning Outcomes")
    render_markdown_section(doc, CHAPTER_24_TEXT)
    
    # 25. Conclusion
    print("Building Chapter 25: Conclusion...")
    add_chapter_heading(doc, 25, "Conclusion")
    render_markdown_section(doc, CHAPTER_25_TEXT)
    
    # 26. Future Enhancements
    print("Building Chapter 26: Future Enhancements...")
    add_chapter_heading(doc, 26, "Future Enhancements")
    render_markdown_section(doc, CHAPTER_26_TEXT)
    
    # 27. References
    print("Building Chapter 27: References...")
    add_chapter_heading(doc, 27, "References")
    render_markdown_section(doc, CHAPTER_27_TEXT)
    
    # Save final docx
    docx_output_path = os.path.abspath("Internship_Report/Internship_Technical_Report_Mahek_Saba_Shaikh.docx")
    doc.save(docx_output_path)
    print(f"\n🎉 SUCCESS: Technical Report (.docx) successfully generated!")
    print(f"File Path: {docx_output_path}")
    print(f"File Size: {os.path.getsize(docx_output_path)} bytes")

if __name__ == "__main__":
    build_complete_report()
