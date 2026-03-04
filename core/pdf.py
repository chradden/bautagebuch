"""PDF-Generierung für Tagesberichte."""
import os
import re
import markdown
from datetime import date, datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

import config

# Jinja2 Template-Umgebung
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


def _apply_prio_colors(html: str) -> str:
    """Umschließt Prioritäts-Abschnitte (ROT/GELB/GRÜN) mit farbigen div-Containern."""
    # Muster: <h...>...ROT...</h...> gefolgt von Inhalt bis zum nächsten <h...> oder Ende
    # Wir splitten nach Überschriften und wrappen die passenden Sektionen

    # Regulärer Ausdruck für Überschriften mit Prio-Keywords
    section_pattern = re.compile(
        r'(<h[1-3][^>]*>.*?</h[1-3]>)',
        re.DOTALL | re.IGNORECASE,
    )

    parts = section_pattern.split(html)
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
                result.append('<div class="prio-section-rot">')
            elif 'gelb' in part_lower or '🟡' in part or 'zeitnah' in part_lower:
                current_prio = 'gelb'
                result.append('<div class="prio-section-gelb">')
            elif 'grün' in part_lower or 'gruen' in part_lower or '🟢' in part or 'geplant' in part_lower:
                current_prio = 'gruen'
                result.append('<div class="prio-section-gruen">')

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

    # KI-Bericht: Markdown → HTML konvertieren + Prio-Farben
    ki_bericht_html = ""
    if ki_bericht:
        ki_bericht_html = markdown.markdown(
            ki_bericht,
            extensions=["tables", "sane_lists"],
        )
        # Prio-Sektionen farblich markieren (farbiger Seitenrand)
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
