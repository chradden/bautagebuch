"""Word-Dokument (DOCX)-Generierung für Tagesberichte (nachträglich editierbar)."""
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


# ──────────────────────────────────────────────
# Hilfsfunktionen
# ──────────────────────────────────────────────

_PRIO_COLORS = {
    "rot":   RGBColor(0xC0, 0x39, 0x2B),
    "gelb":  RGBColor(0xD3, 0x9A, 0x00),
    "gruen": RGBColor(0x27, 0xAE, 0x60),
}

_HEADER_COLOR = RGBColor(0x2C, 0x3E, 0x50)
_LIGHT_GRAY   = RGBColor(0xF2, 0xF2, 0xF2)


def _set_cell_bg(cell, hex_color: str):
    """Setzt die Hintergrundfarbe einer Tabellenzelle."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tc_pr.append(shd)


def _cell_para(cell, text: str, bold=False, font_size=10, color: RGBColor | None = None,
               align=WD_ALIGN_PARAGRAPH.LEFT) -> None:
    """Schreibt Text in eine Tabellenzelle mit optionaler Formatierung."""
    para = cell.paragraphs[0]
    para.alignment = align
    run = para.add_run(text)
    run.bold = bold
    run.font.size = Pt(font_size)
    if color:
        run.font.color.rgb = color


def _add_heading(doc: Document, text: str, level: int = 1) -> None:
    """Fügt eine formatierte Überschrift ein."""
    para = doc.add_paragraph()
    run = para.add_run(text)
    run.bold = True
    run.font.color.rgb = _HEADER_COLOR
    if level == 1:
        run.font.size = Pt(16)
        para.space_before = Pt(14)
    elif level == 2:
        run.font.size = Pt(13)
        para.space_before = Pt(10)
    else:
        run.font.size = Pt(11)
        para.space_before = Pt(6)
    para.space_after = Pt(4)


def _prio_color(prio: str) -> RGBColor:
    """Gibt die RGB-Farbe zur Prioritätsstufe zurück."""
    key = (prio or "gelb").lower()
    if "rot" in key:
        return _PRIO_COLORS["rot"]
    if "grün" in key or "gruen" in key or "green" in key:
        return _PRIO_COLORS["gruen"]
    return _PRIO_COLORS["gelb"]


# ──────────────────────────────────────────────
# Markdown → DOCX-Paragraphen
# ──────────────────────────────────────────────

def _add_markdown_paragraph(doc: Document, line: str) -> None:
    """Konvertiert eine einzelne Markdown-Zeile in einen DOCX-Absatz."""
    # Überschriften
    h3 = re.match(r'^###\s+(.*)', line)
    h2 = re.match(r'^##\s+(.*)', line)
    h1 = re.match(r'^#\s+(.*)', line)
    if h1:
        _add_heading(doc, h1.group(1), level=1)
        return
    if h2:
        _add_heading(doc, h2.group(1), level=2)
        return
    if h3:
        _add_heading(doc, h3.group(1), level=3)
        return

    # Aufzählungspunkte
    bullet = re.match(r'^[\-\*]\s+(.*)', line)
    if bullet:
        para = doc.add_paragraph(style="List Bullet")
        _add_inline_markup(para, bullet.group(1))
        para.paragraph_format.left_indent = Cm(0.5)
        return

    # Normaler Absatz
    para = doc.add_paragraph()
    _add_inline_markup(para, line)


def _add_inline_markup(para, text: str) -> None:
    """Verarbeitet **fett** und *kursiv* Inline-Markup in einem Paragraphen."""
    # Teile am **...** und *...* aufsplitten
    parts = re.split(r'(\*\*.*?\*\*|\*.*?\*)', text)
    for part in parts:
        if part.startswith("**") and part.endswith("**"):
            run = para.add_run(part[2:-2])
            run.bold = True
        elif part.startswith("*") and part.endswith("*"):
            run = para.add_run(part[1:-1])
            run.italic = True
        else:
            para.add_run(part)


def _add_markdown_block(doc: Document, markdown_text: str) -> None:
    """Wandelt einen mehrzeiligen Markdown-Text in DOCX-Absätze um."""
    if not markdown_text:
        return
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if not stripped:
            doc.add_paragraph()
            continue
        _add_markdown_paragraph(doc, stripped)


# ──────────────────────────────────────────────
# Hauptfunktion
# ──────────────────────────────────────────────

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
    Generiert einen editierbaren Word-Tagesbericht (.docx).

    Returns:
        Pfad zur generierten DOCX-Datei.
    """
    doc = Document()

    # ── Seitenränder ──────────────────────────
    for section in doc.sections:
        section.top_margin    = Cm(2.0)
        section.bottom_margin = Cm(2.0)
        section.left_margin   = Cm(2.5)
        section.right_margin  = Cm(2.5)

    # ── Titelblock ────────────────────────────
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_para.add_run("Instandhaltungsbericht")
    title_run.bold = True
    title_run.font.size = Pt(20)
    title_run.font.color.rgb = _HEADER_COLOR

    doc.add_paragraph()

    # ── Metadaten-Tabelle ─────────────────────
    meta_table = doc.add_table(rows=4, cols=2)
    meta_table.style = "Table Grid"
    meta_table.alignment = WD_TABLE_ALIGNMENT.LEFT

    meta_rows = [
        ("Projekt",      projekt_name),
        ("Datum",        datum.strftime("%d.%m.%Y")),
        ("Bauleiter/in", bauleiter_name),
        ("Adresse",      projekt_adresse or "–"),
    ]
    for row_idx, (label, value) in enumerate(meta_rows):
        row = meta_table.rows[row_idx]
        _set_cell_bg(row.cells[0], "2C3E50")
        _cell_para(row.cells[0], label, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF), font_size=10)
        _cell_para(row.cells[1], value, font_size=10)

    # Spaltenbreiten
    for row in meta_table.rows:
        row.cells[0].width = Cm(4)
        row.cells[1].width = Cm(12)

    doc.add_paragraph()

    # ── KI-Bericht ────────────────────────────
    if ki_bericht:
        _add_heading(doc, "KI-Priorisierter Instandhaltungsbericht", level=2)
        _add_markdown_block(doc, ki_bericht)
        doc.add_paragraph()

    # ── Eintrags-Tabelle ──────────────────────
    _add_heading(doc, "Einzelne Meldungen", level=2)

    col_headers = ["Uhrzeit", "Kategorie", "Meldung / KI-Zusammenfassung", "Priorität", "Kostenschätzung"]
    entry_table = doc.add_table(rows=1, cols=len(col_headers))
    entry_table.style = "Table Grid"

    # Kopfzeile
    hdr_row = entry_table.rows[0]
    for idx, header in enumerate(col_headers):
        _set_cell_bg(hdr_row.cells[idx], "2C3E50")
        _cell_para(hdr_row.cells[idx], header, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF), font_size=9)

    # Einträge
    for eintrag in eintraege_text:
        row = entry_table.add_row()

        uhrzeit   = getattr(eintrag, "uhrzeit_str", "") or getattr(eintrag, "uhrzeit", "") or ""
        kategorie = (getattr(eintrag, "kategorie", "") or "").capitalize()
        prio      = getattr(eintrag, "prioritaet", "gelb") or "gelb"
        kosten    = getattr(eintrag, "kostenschaetzung", "") or "–"
        ki_text   = getattr(eintrag, "ki_zusammenfassung", "") or getattr(eintrag, "rohinhalt", "") or ""

        _cell_para(row.cells[0], uhrzeit,   font_size=9)
        _cell_para(row.cells[1], kategorie, font_size=9)

        # Meldung mit KI-Text
        para_msg = row.cells[2].paragraphs[0]
        para_msg.add_run(ki_text).font.size = Pt(9)

        # Priorität farbig
        prio_cell = row.cells[3]
        _cell_para(prio_cell, prio.capitalize(), bold=True, font_size=9, color=_prio_color(prio))

        _cell_para(row.cells[4], kosten, font_size=9)

    # Spaltenbreiten
    widths = [Cm(1.8), Cm(2.5), Cm(9.0), Cm(2.2), Cm(3.0)]
    for row in entry_table.rows:
        for idx, width in enumerate(widths):
            row.cells[idx].width = width

    # Gesamtkostenschätzung
    gesamt = _build_total_cost_estimate(eintraege_text)
    if gesamt:
        doc.add_paragraph()
        p = doc.add_paragraph()
        run_label = p.add_run("Gesamtkostenschätzung: ")
        run_label.bold = True
        run_label.font.size = Pt(10)
        run_val = p.add_run(gesamt)
        run_val.font.size = Pt(10)
        run_val.font.color.rgb = _PRIO_COLORS["rot"]

    # ── Foto-Dokumentation ────────────────────
    foto_liste = [f for f in fotos if getattr(f, "dateipfad", None)]
    if foto_liste:
        doc.add_paragraph()
        _add_heading(doc, "Fotodokumentation", level=2)

        foto_table = doc.add_table(rows=0, cols=2)
        foto_table.style = "Table Grid"

        row_cells = None
        for foto_idx, foto in enumerate(foto_liste):
            dateipfad = os.path.abspath(foto.dateipfad)
            if not os.path.exists(dateipfad):
                continue

            col = foto_idx % 2
            if col == 0:
                row_cells = foto_table.add_row().cells

            cell = row_cells[col]
            try:
                para_img = cell.paragraphs[0]
                run_img  = para_img.add_run()
                run_img.add_picture(dateipfad, width=Cm(8))
            except Exception:
                cell.paragraphs[0].add_run("[Bild nicht verfügbar]")

            beschreibung = getattr(foto, "beschreibung", "") or ""
            uhrzeit      = getattr(foto, "uhrzeit", None)
            caption_parts = []
            if uhrzeit:
                try:
                    caption_parts.append(uhrzeit.strftime("%H:%M"))
                except AttributeError:
                    caption_parts.append(str(uhrzeit))
            if beschreibung:
                caption_parts.append(beschreibung)

            caption_para = cell.add_paragraph(" – ".join(caption_parts) if caption_parts else "")
            caption_para.runs[0].font.size = Pt(8)
            caption_para.runs[0].italic    = True

    # ── Fußzeile ──────────────────────────────
    doc.add_paragraph()
    footer_para = doc.add_paragraph()
    footer_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    footer_run = footer_para.add_run(
        f"Erstellt am {datetime.now().strftime('%d.%m.%Y %H:%M')} | {projekt_name}"
    )
    footer_run.font.size = Pt(8)
    footer_run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

    # ── Datei speichern ───────────────────────
    os.makedirs(config.PDF_OUTPUT_DIR, exist_ok=True)
    safe_name = projekt_name.replace(" ", "_").replace("/", "-")
    dateiname = f"Tagesbericht_{safe_name}_{datum.strftime('%Y-%m-%d')}.docx"
    docx_pfad = os.path.join(config.PDF_OUTPUT_DIR, dateiname)
    doc.save(docx_pfad)

    return docx_pfad
