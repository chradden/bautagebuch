"""Word-Dokument (DOCX) – layout-getreu zum PDF-Bericht (tagesbericht.html)."""
import os
import re
from datetime import date, datetime

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

import config
from core.pdf import _build_total_cost_estimate

# ── Farben – deckungsgleich mit tagesbericht.html ─────────────────────────

_C_DARK       = "2C3E50"
_C_DARK_RGB   = RGBColor(0x2C, 0x3E, 0x50)
_C_WHITE      = RGBColor(0xFF, 0xFF, 0xFF)
_C_BODY       = RGBColor(0x33, 0x33, 0x33)
_C_META       = RGBColor(0x66, 0x66, 0x66)

_PRIO = {
    "rot": {
        "bg_heading": "FDE2DF",
        "bg_content": "FFF5F5",
        "text":       RGBColor(0x8F, 0x2D, 0x23),
        "border":     "F3C3BE",
    },
    "gelb": {
        "bg_heading": "FFF1BF",
        "bg_content": "FFFBEA",
        "text":       RGBColor(0x7A, 0x5B, 0x00),
        "border":     "EAD68A",
    },
    "gruen": {
        "bg_heading": "DAF2DF",
        "bg_content": "F2FBF5",
        "text":       RGBColor(0x20, 0x60, 0x3A),
        "border":     "B8DDC0",
    },
}

# ── XML-Hilfsfunktionen ────────────────────────────────────────────────────

def _set_cell_bg(cell, hex_color: str) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _remove_cell_borders(cell) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        bd = OxmlElement(f"w:{side}")
        bd.set(qn("w:val"), "none")
        tcBorders.append(bd)
    tcPr.append(tcBorders)


def _set_para_shading(para, hex_color: str) -> None:
    pPr = para._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    pPr.append(shd)


def _set_para_bottom_border(para, hex_color: str = "2C3E50", size: int = 24) -> None:
    pPr = para._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), hex_color)
    pBdr.append(bottom)
    pPr.append(pBdr)


def _set_para_left_border(para, hex_color: str, size: int = 12) -> None:
    pPr = para._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "single")
    left.set(qn("w:sz"), str(size))
    left.set(qn("w:space"), "6")
    left.set(qn("w:color"), hex_color)
    pBdr.append(left)
    pPr.append(pBdr)


def _set_table_no_borders(tbl) -> None:
    tblPr = tbl._tbl.tblPr
    if tblPr is None:
        tblPr = OxmlElement("w:tblPr")
        tbl._tbl.insert(0, tblPr)
    tblBorders = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        bd = OxmlElement(f"w:{side}")
        bd.set(qn("w:val"), "none")
        tblBorders.append(bd)
    tblPr.append(tblBorders)


def _set_para_spacing(para, before: int = 0, after: int = 0) -> None:
    pPr = para._p.get_or_add_pPr()
    spacing = OxmlElement("w:spacing")
    spacing.set(qn("w:before"), str(before))
    spacing.set(qn("w:after"), str(after))
    pPr.append(spacing)


# ── Inline-Markup ─────────────────────────────────────────────────────────

def _add_inline_markup(para, text: str, size: float = 10,
                        color: RGBColor | None = None) -> None:
    for part in re.split(r'(\*\*[^*]+\*\*|\*[^*]+\*)', text):
        if part.startswith("**") and part.endswith("**"):
            run = para.add_run(part[2:-2])
            run.bold = True
        elif part.startswith("*") and part.endswith("*"):
            run = para.add_run(part[1:-1])
            run.italic = True
        else:
            run = para.add_run(part)
        run.font.size = Pt(size)
        if color:
            run.font.color.rgb = color


# ── Header-Block (wie .header im CSS) ─────────────────────────────────────

def _add_report_header(doc: Document, projekt_name: str, projekt_adresse: str,
                        datum: date, bauleiter_name: str) -> None:
    title_para = doc.add_paragraph()
    run = title_para.add_run("Instandhaltungsplanung")
    run.bold = True
    run.font.size = Pt(22)
    run.font.color.rgb = _C_DARK_RGB
    _set_para_spacing(title_para, before=0, after=0)

    meta_tbl = doc.add_table(rows=1, cols=4)
    _set_table_no_borders(meta_tbl)
    meta_items = [
        ("Objekt",         projekt_name),
        ("Adresse",        projekt_adresse or "–"),
        ("Datum",          datum.strftime("%d.%m.%Y")),
        ("Verantwortlich", bauleiter_name),
    ]
    for idx, (label, value) in enumerate(meta_items):
        cell = meta_tbl.rows[0].cells[idx]
        _remove_cell_borders(cell)
        para = cell.paragraphs[0]
        r_label = para.add_run(label + ": ")
        r_label.bold = True
        r_label.font.size = Pt(9)
        r_label.font.color.rgb = _C_META
        r_value = para.add_run(value)
        r_value.font.size = Pt(9)
        r_value.font.color.rgb = _C_META

    sep = doc.add_paragraph()
    _set_para_bottom_border(sep, hex_color=_C_DARK, size=24)
    _set_para_spacing(sep, before=60, after=120)


# ── Abschnitts-Header (wie .section h2 im CSS) ────────────────────────────

def _add_section_header(doc: Document, text: str) -> None:
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    cell = tbl.rows[0].cells[0]
    _set_cell_bg(cell, _C_DARK)
    para = cell.paragraphs[0]
    run = para.add_run(text)
    run.bold = True
    run.font.size = Pt(12)
    run.font.color.rgb = _C_WHITE
    para.paragraph_format.space_before = Pt(4)
    para.paragraph_format.space_after = Pt(4)
    para.paragraph_format.left_indent = Cm(0.3)
    gap = doc.add_paragraph()
    _set_para_spacing(gap, before=0, after=60)


# ── Prio-Erkennung ────────────────────────────────────────────────────────

def _detect_prio(text: str) -> str | None:
    lower = text.lower()
    if "rot" in lower or "🔴" in text or "sofort" in lower:
        return "rot"
    if "gelb" in lower or "🟡" in text or "zeitnah" in lower:
        return "gelb"
    if "grün" in lower or "gruen" in lower or "🟢" in text or "geplant" in lower:
        return "gruen"
    return None


# ── KI-Bericht Renderer ───────────────────────────────────────────────────

def _render_ki_bericht(doc: Document, markdown_text: str) -> None:
    current_prio: str | None = None

    for line in markdown_text.splitlines():
        stripped = line.strip()

        if not stripped:
            gap = doc.add_paragraph()
            _set_para_spacing(gap, before=0, after=40)
            continue

        # H1
        m = re.match(r'^# (.*)', stripped)
        if m:
            current_prio = _detect_prio(m.group(1)) or current_prio
            para = doc.add_paragraph()
            run = para.add_run(m.group(1))
            run.bold = True
            run.font.size = Pt(13)
            run.font.color.rgb = _C_DARK_RGB
            _set_para_spacing(para, before=120, after=60)
            continue

        # H2
        m = re.match(r'^## (.*)', stripped)
        if m:
            text = m.group(1)
            current_prio = _detect_prio(text)
            colors = _PRIO.get(current_prio) if current_prio else None
            para = doc.add_paragraph()
            if colors:
                _set_para_shading(para, colors["bg_heading"])
            run = para.add_run(text)
            run.bold = True
            run.font.size = Pt(11)
            run.font.color.rgb = colors["text"] if colors else _C_DARK_RGB
            para.paragraph_format.left_indent = Cm(0.3)
            _set_para_spacing(para, before=120, after=30)
            continue

        # H3
        m = re.match(r'^### (.*)', stripped)
        if m:
            text = m.group(1)
            prio = _detect_prio(text)
            if prio:
                current_prio = prio
            colors = _PRIO.get(current_prio) if current_prio else None
            para = doc.add_paragraph()
            if colors:
                _set_para_shading(para, colors["bg_heading"])
            run = para.add_run(text)
            run.bold = True
            run.font.size = Pt(10.5)
            run.font.color.rgb = colors["text"] if colors else _C_DARK_RGB
            para.paragraph_format.left_indent = Cm(0.3)
            _set_para_spacing(para, before=80, after=20)
            continue

        # Aufzählungspunkt
        m = re.match(r'^[-*] (.*)', stripped)
        if m:
            colors = _PRIO.get(current_prio) if current_prio else None
            para = doc.add_paragraph()
            if colors:
                _set_para_shading(para, colors["bg_content"])
                _set_para_left_border(para, colors["border"])
            para.paragraph_format.left_indent = Cm(0.8)
            para.paragraph_format.first_line_indent = Cm(-0.35)
            bullet_run = para.add_run("• ")
            bullet_run.font.size = Pt(10)
            if colors:
                bullet_run.font.color.rgb = colors["text"]
            _add_inline_markup(para, m.group(1), size=10)
            _set_para_spacing(para, before=20, after=20)
            continue

        # Markdown-Tabellen-Zeile
        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(re.match(r'^[-: ]+$', c) for c in cells if c):
                continue
            colors = _PRIO.get(current_prio) if current_prio else None
            para = doc.add_paragraph()
            if colors:
                _set_para_shading(para, colors["bg_content"])
                _set_para_left_border(para, colors["border"])
                para.paragraph_format.left_indent = Cm(0.3)
            text = "   |   ".join(c for c in cells if c)
            _add_inline_markup(para, text, size=9.5)
            _set_para_spacing(para, before=20, after=20)
            continue

        # Normaler Absatz
        colors = _PRIO.get(current_prio) if current_prio else None
        para = doc.add_paragraph()
        if colors:
            _set_para_shading(para, colors["bg_content"])
            _set_para_left_border(para, colors["border"])
            para.paragraph_format.left_indent = Cm(0.3)
        _add_inline_markup(para, stripped, size=10)
        _set_para_spacing(para, before=20, after=20)


# ── Gesamtkosten-Box (wie .kosten-summary im CSS) ─────────────────────────

def _add_kosten_box(doc: Document, gesamt: str) -> None:
    tbl = doc.add_table(rows=1, cols=1)
    _set_table_no_borders(tbl)
    cell = tbl.rows[0].cells[0]
    _set_cell_bg(cell, "F8FAFC")
    _remove_cell_borders(cell)

    label_para = cell.paragraphs[0]
    r_label = label_para.add_run("Gesamtkostenschätzung")
    r_label.bold = True
    r_label.font.size = Pt(9)
    r_label.font.color.rgb = _C_DARK_RGB

    val_para = cell.add_paragraph()
    r_val = val_para.add_run(gesamt)
    r_val.bold = True
    r_val.font.size = Pt(12)
    r_val.font.color.rgb = RGBColor(0x1F, 0x2D, 0x3D)

    label_para.paragraph_format.left_indent = Cm(0.3)
    val_para.paragraph_format.left_indent = Cm(0.3)
    _set_para_spacing(label_para, before=60, after=20)
    _set_para_spacing(val_para, before=0, after=60)


# ── Foto-Dokumentation ────────────────────────────────────────────────────

def _add_foto_section(doc: Document, fotos: list) -> None:
    foto_liste = [
        f for f in fotos
        if getattr(f, "dateipfad", None) and os.path.exists(os.path.abspath(f.dateipfad))
    ]
    if not foto_liste:
        return

    doc.add_paragraph()
    _add_section_header(doc, "Fotodokumentation")

    foto_tbl = doc.add_table(rows=0, cols=3)
    _set_table_no_borders(foto_tbl)

    row_cells = None
    for idx, foto in enumerate(foto_liste):
        col = idx % 3
        if col == 0:
            row_cells = foto_tbl.add_row().cells
            for c in row_cells:
                _remove_cell_borders(c)

        cell = row_cells[col]
        try:
            img_run = cell.paragraphs[0].add_run()
            img_run.add_picture(os.path.abspath(foto.dateipfad), width=Cm(8.5))
        except Exception:
            cell.paragraphs[0].add_run("[Bild nicht verfügbar]")

        parts = []
        uhrzeit = getattr(foto, "uhrzeit", None)
        if uhrzeit:
            try:
                parts.append(uhrzeit.strftime("%H:%M"))
            except AttributeError:
                parts.append(str(uhrzeit))
        beschreibung = getattr(foto, "beschreibung", "") or ""
        if beschreibung:
            parts.append(beschreibung)
        if parts:
            cap = cell.add_paragraph(" – ".join(parts))
            if cap.runs:
                cap.runs[0].font.size = Pt(8)
                cap.runs[0].italic = True
                cap.runs[0].font.color.rgb = _C_META


# ── Footer (wie .footer im CSS) ───────────────────────────────────────────

def _add_footer(doc: Document) -> None:
    sep = doc.add_paragraph()
    _set_para_bottom_border(sep, hex_color="CCCCCC", size=4)
    _set_para_spacing(sep, before=200, after=40)

    tbl = doc.add_table(rows=1, cols=2)
    _set_table_no_borders(tbl)
    for cell in tbl.rows[0].cells:
        _remove_cell_borders(cell)

    left_para = tbl.rows[0].cells[0].paragraphs[0]
    r_left = left_para.add_run(f"Erstellt am {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    r_left.font.size = Pt(8)
    r_left.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

    right_para = tbl.rows[0].cells[1].paragraphs[0]
    right_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_right = right_para.add_run("Instandhaltungsplanung – automatisch generiert")
    r_right.font.size = Pt(8)
    r_right.font.color.rgb = RGBColor(0x99, 0x99, 0x99)


# ── Hauptfunktion ─────────────────────────────────────────────────────────

def generiere_docx(
    projekt_name: str,
    bauleiter_name: str,
    datum: date,
    eintraege_text: list,
    fotos: list,
    ki_bericht: str = "",
    projekt_adresse: str = "",
) -> str:
    """
    Generiert einen editierbaren Word-Tagesbericht (.docx) im PDF-Layout.

    Returns:
        Pfad zur generierten DOCX-Datei.
    """
    doc = Document()

    # A4 Querformat + Ränder 1.2 cm (wie PDF: size: A4 landscape; margin: 1.2cm)
    for section in doc.sections:
        section.page_width    = Cm(29.7)
        section.page_height   = Cm(21.0)
        section.top_margin    = Cm(1.2)
        section.bottom_margin = Cm(1.2)
        section.left_margin   = Cm(1.2)
        section.right_margin  = Cm(1.2)

    # Standardschrift Arial (wie PDF body)
    doc.styles["Normal"].font.name = "Arial"
    doc.styles["Normal"].font.size = Pt(11)
    doc.styles["Normal"].font.color.rgb = _C_BODY

    # 1. Header ────────────────────────────────────────────────────────────
    _add_report_header(doc, projekt_name, projekt_adresse, datum, bauleiter_name)

    # 2. KI-Analyse ────────────────────────────────────────────────────────
    if ki_bericht:
        _add_section_header(doc, "KI-Analyse & Priorisierung")
        _render_ki_bericht(doc, ki_bericht)

        gesamt = _build_total_cost_estimate(eintraege_text)
        if gesamt:
            doc.add_paragraph()
            _add_kosten_box(doc, gesamt)

    # 3. Fotodokumentation ─────────────────────────────────────────────────
    _add_foto_section(doc, fotos)

    # 4. Footer ────────────────────────────────────────────────────────────
    _add_footer(doc)

    # Speichern
    os.makedirs(config.PDF_OUTPUT_DIR, exist_ok=True)
    safe_name = projekt_name.replace(" ", "_").replace("/", "-")
    dateiname = f"Tagesbericht_{safe_name}_{datum.strftime('%Y-%m-%d')}.docx"
    docx_pfad = os.path.join(config.PDF_OUTPUT_DIR, dateiname)
    doc.save(docx_pfad)
    return docx_pfad
