"""PDF-Generierung für Tagesberichte."""
import os
from datetime import date, datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

import config

# Jinja2 Template-Umgebung
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


def generiere_pdf(
    projekt_name: str,
    bauleiter_name: str,
    datum: date,
    eintraege_text: list,
    fotos: list,
    ki_bericht: str = "",
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

    html_content = template.render(
        projekt_name=projekt_name,
        datum=datum.strftime("%d.%m.%Y"),
        bauleiter=bauleiter_name,
        eintraege_text=eintraege_text,
        fotos=foto_daten,
        ki_bericht=ki_bericht,
        erstellt_am=datetime.now().strftime("%d.%m.%Y %H:%M"),
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
