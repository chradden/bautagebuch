"""PDF-Generierung für Tagesberichte."""
import os
import re
import html
import markdown
from datetime import date, datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

import config

# Jinja2 Template-Umgebung
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


def _build_eintrag_foto_map(eintraege_text: list) -> dict[int, list[dict]]:
    """Erzeugt eine Zuordnung von Eintragsnummern zu Foto-Metadaten."""
    eintrag_fotos = {}
    for index, eintrag in enumerate(eintraege_text, 1):
        fotos = []
        for foto in getattr(eintrag, "fotos", []):
            dateipfad = foto.get("dateipfad")
            if not dateipfad:
                continue
            fotos.append({
                "dateipfad_abs": os.path.abspath(dateipfad),
                "beschreibung": foto.get("beschreibung", ""),
            })
        eintrag_fotos[index] = fotos
    return eintrag_fotos


def _build_photo_cell(photos: list[dict]) -> str:
    """Rendert die Fotodokumentation für eine Tabellenzelle."""
    if not photos:
        return '<span class="foto-placeholder">Keine Fotos</span>'

    items = []
    for photo in photos:
        beschreibung = html.escape(photo.get("beschreibung", ""))
        items.append(
            '<div class="foto-item">'
            f'<img src="file://{photo["dateipfad_abs"]}" alt="Fotodokumentation">'
            f'<div class="foto-note">{beschreibung}</div>'
            '</div>'
        )

    return f'<div class="foto-cell">{"".join(items)}</div>'


def _inject_entry_photos(html_content: str, eintrag_fotos: dict[int, list[dict]]) -> str:
    """Ergänzt die KI-Tabellen um eine visuelle Fotospalte je Eintrag."""
    def update_header(match):
        row_html = match.group(0)
        headers = re.findall(r'<th>(.*?)</th>', row_html, re.DOTALL | re.IGNORECASE)
        if not headers:
            return row_html
        if len(headers) >= 7:
            headers[-1] = 'Fotodokumentation'
        else:
            headers.append('Fotodokumentation')
        rebuilt = ''.join(f'<th>{header}</th>' for header in headers)
        return f'<tr>{rebuilt}</tr>'

    def update_row(match):
        row_html = match.group(0)
        cells = re.findall(r'<td>(.*?)</td>', row_html, re.DOTALL | re.IGNORECASE)
        if not cells:
            return row_html

        cell_text = re.sub(r'<.*?>', '', cells[0])
        nr_match = re.search(r'Nr\.\s*(\d+)', cell_text)
        photos = []
        if nr_match:
            photos = eintrag_fotos.get(int(nr_match.group(1)), [])

        photo_cell = _build_photo_cell(photos)
        if len(cells) >= 7:
            cells[-1] = photo_cell
        else:
            cells.append(photo_cell)

        rebuilt = ''.join(f'<td>{cell}</td>' for cell in cells)
        return f'<tr>{rebuilt}</tr>'

    html_content = re.sub(
        r'<thead>\s*<tr>.*?</tr>\s*</thead>',
        lambda match: '<thead>' + update_header(re.search(r'<tr>.*</tr>', match.group(0), re.DOTALL | re.IGNORECASE)) + '</thead>',
        html_content,
        count=0,
        flags=re.DOTALL | re.IGNORECASE,
    )
    html_content = re.sub(
        r'<tbody>(.*?)</tbody>',
        lambda tbody_match: '<tbody>' + re.sub(
            r'<tr>.*?</tr>',
            update_row,
            tbody_match.group(1),
            flags=re.DOTALL | re.IGNORECASE,
        ) + '</tbody>',
        html_content,
        count=0,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return html_content


def _apply_prio_colors(html_content: str) -> str:
    """Umschließt Prioritäts-Abschnitte (ROT/GELB/GRÜN) mit farbigen Karten."""
    # Muster: <h...>...ROT...</h...> gefolgt von Inhalt bis zum nächsten <h...> oder Ende
    # Wir splitten nach Überschriften und wrappen die passenden Sektionen

    # Regulärer Ausdruck für Überschriften mit Prio-Keywords
    section_pattern = re.compile(
        r'(<h[1-3][^>]*>.*?</h[1-3]>)',
        re.DOTALL | re.IGNORECASE,
    )

    parts = section_pattern.split(html_content)
    result = []
    current_prio = None

    for part in parts:
        # Prüfen ob es eine Überschrift ist
        if re.match(r'<h[1-3]', part, re.IGNORECASE):
            # Vorherige Prio-Section schließen
            if current_prio:
                result.append('</div>')
                current_prio = None

            # Prio erkennen
            part_lower = part.lower()
            if 'rot' in part_lower or '🔴' in part or 'sofortmaß' in part_lower:
                current_prio = 'rot'
                result.append('<div class="prio-section prio-section-rot">')
            elif 'gelb' in part_lower or '🟡' in part or 'zeitnah' in part_lower:
                current_prio = 'gelb'
                result.append('<div class="prio-section prio-section-gelb">')
            elif 'grün' in part_lower or 'gruen' in part_lower or '🟢' in part or 'geplant' in part_lower:
                current_prio = 'gruen'
                result.append('<div class="prio-section prio-section-gruen">')

            result.append(part)
        else:
            result.append(part)

    # Letzte Section schließen
    if current_prio:
        result.append('</div>')

    return ''.join(result)


def generiere_pdf(
    projekt_name: str,
    bauleiter_name: str,
    datum: date,
    eintraege_text: list,
    fotos: list,
    ki_bericht: str = "",
    projekt_adresse: str = "",
) -> str:
    """
    Generiert einen PDF-Tagesbericht.

    Returns:
        Pfad zur generierten PDF-Datei.
    """
    template = env.get_template("tagesbericht.html")

    # Foto-Pfade absolut machen
    foto_daten = []
    for foto in fotos:
        foto_daten.append({
            "dateipfad_abs": os.path.abspath(foto.dateipfad),
            "beschreibung": foto.beschreibung or "",
            "uhrzeit": getattr(foto, 'uhrzeit', None),
        })

    eintrag_fotos = _build_eintrag_foto_map(eintraege_text)

    # KI-Bericht: Markdown → HTML konvertieren + Prio-Farben
    ki_bericht_html = ""
    if ki_bericht:
        ki_bericht_html = markdown.markdown(
            ki_bericht,
            extensions=["tables", "sane_lists"],
        )
        ki_bericht_html = _inject_entry_photos(ki_bericht_html, eintrag_fotos)
        ki_bericht_html = _apply_prio_colors(ki_bericht_html)

    html_content = template.render(
        projekt_name=projekt_name,
        datum=datum.strftime("%d.%m.%Y"),
        bauleiter=bauleiter_name,
        eintraege_text=eintraege_text,
        fotos=foto_daten,
        ki_bericht=ki_bericht_html,
        erstellt_am=datetime.now().strftime("%d.%m.%Y %H:%M"),
        projekt_adresse=projekt_adresse,
    )

    # Output-Verzeichnis vorbereiten
    os.makedirs(config.PDF_OUTPUT_DIR, exist_ok=True)

    # Dateiname: Projekt_Datum.pdf
    safe_name = projekt_name.replace(" ", "_").replace("/", "-")
    dateiname = f"Tagesbericht_{safe_name}_{datum.strftime('%Y-%m-%d')}.pdf"
    pdf_pfad = os.path.join(config.PDF_OUTPUT_DIR, dateiname)

    # PDF generieren
    HTML(string=html_content, base_url=".").write_pdf(pdf_pfad)

    return pdf_pfad
