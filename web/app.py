"""FastAPI Web-Dashboard für Instandhaltungsplanung."""
import os
import csv
import io
from datetime import date, datetime
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func

from db.database import get_session
from db.models import Projekt, Benutzer, Eintrag, Foto, Tagesbericht

app = FastAPI(title="Instandhaltungsplanung Dashboard")

# Static files & templates
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# ─── Hilfsfunktionen ─────────────────────────────────────────────────────

PRIO_SORTIERUNG = {"rot": 0, "gelb": 1, "gruen": 2, "": 3}
PRIO_LABEL = {"rot": "Rot – Sofort", "gelb": "Gelb – Zeitnah", "gruen": "Grün – Geplant"}
PRIO_COLOR = {"rot": "#e74c3c", "gelb": "#f1c40f", "gruen": "#27ae60"}

KATEGORIE_EMOJI = {
    "reparatur": "🔧",
    "maengelbeseitigung": "🛠️",
    "wartung": "🔩",
    "pruefung": "🔍",
    "sicherheit": "🚨",
    "sonstiges": "📝",
}


def _parse_ki_zusammenfassung(text: str) -> dict:
    """Versucht, aus ki_zusammenfassung Priorität und Kosten zu extrahieren."""
    return {}


# ─── Routen ───────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Hauptseite – Projektübersicht mit Statistiken."""
    with get_session() as session:
        projekte = session.query(Projekt).all()
        projekt_daten = []
        for p in projekte:
            anzahl = session.query(Eintrag).filter_by(projekt_id=p.id).count()
            anzahl_fotos = (
                session.query(Foto)
                .join(Eintrag)
                .filter(Eintrag.projekt_id == p.id)
                .count()
            )
            anzahl_berichte = session.query(Tagesbericht).filter_by(projekt_id=p.id).count()

            # Prioritäts-Verteilung
            prio_rot = session.query(Eintrag).filter(
                Eintrag.projekt_id == p.id,
                Eintrag.ki_zusammenfassung.like('%"prioritaet": "rot"%')
            ).count()

            # Einfacher: Kategorie-basiert zählen
            letzte_eintraege = (
                session.query(Eintrag)
                .filter_by(projekt_id=p.id)
                .order_by(Eintrag.datum.desc(), Eintrag.uhrzeit.desc())
                .limit(3)
                .all()
            )

            projekt_daten.append({
                "id": p.id,
                "name": p.name,
                "adresse": p.adresse or "–",
                "baubeginn": p.baubeginn.strftime("%d.%m.%Y") if p.baubeginn else "–",
                "anzahl_eintraege": anzahl,
                "anzahl_fotos": anzahl_fotos,
                "anzahl_berichte": anzahl_berichte,
                "letzte_eintraege": [
                    {
                        "datum": e.datum.strftime("%d.%m.") if e.datum else "",
                        "uhrzeit": e.uhrzeit.strftime("%H:%M") if e.uhrzeit else "",
                        "rohinhalt": (e.rohinhalt or "")[:60],
                        "kategorie": e.kategorie or "sonstiges",
                    }
                    for e in letzte_eintraege
                ],
            })

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "projekte": projekt_daten,
        "titel": "Instandhaltungsplanung",
    })


@app.get("/projekt/{projekt_id}", response_class=HTMLResponse)
async def projekt_detail(
    request: Request,
    projekt_id: int,
    datum: str = Query(None, description="Filter: TT.MM.JJJJ"),
    prio: str = Query(None, description="Filter: rot|gelb|gruen"),
    kategorie: str = Query(None, description="Filter: Kategorie"),
):
    """Detailansicht eines Projekts mit Einträgen."""
    filter_datum = None
    if datum:
        try:
            filter_datum = datetime.strptime(datum, "%d.%m.%Y").date()
        except ValueError:
            pass

    with get_session() as session:
        projekt = session.query(Projekt).get(projekt_id)
        if not projekt:
            return HTMLResponse("<h1>Projekt nicht gefunden</h1>", status_code=404)

        projekt_info = {
            "id": projekt.id,
            "name": projekt.name,
            "adresse": projekt.adresse or "–",
            "bauherr": projekt.bauherr or "–",
            "baubeginn": projekt.baubeginn.strftime("%d.%m.%Y") if projekt.baubeginn else "–",
        }

        # Einträge abfragen
        query = session.query(Eintrag).filter_by(projekt_id=projekt_id)
        if filter_datum:
            query = query.filter(Eintrag.datum == filter_datum)
        if kategorie:
            query = query.filter(Eintrag.kategorie == kategorie)

        eintraege = query.order_by(Eintrag.datum.desc(), Eintrag.uhrzeit.desc()).all()

        eintraege_daten = []
        for e in eintraege:
            fotos = [{"id": f.id, "dateipfad": f.dateipfad, "beschreibung": f.beschreibung} for f in e.fotos]
            eintraege_daten.append({
                "id": e.id,
                "datum": e.datum.strftime("%d.%m.%Y") if e.datum else "",
                "uhrzeit": e.uhrzeit.strftime("%H:%M") if e.uhrzeit else "",
                "typ": e.typ,
                "rohinhalt": e.rohinhalt or "",
                "ki_zusammenfassung": e.ki_zusammenfassung or "",
                "kategorie": e.kategorie or "sonstiges",
                "fotos": fotos,
            })

        # Priorität-Filter (aus ki_zusammenfassung – vereinfacht über Kategorie)
        # Da wir keine separate Prio-Spalte haben, filtern wir hier nicht weiter

        # Tagesberichte
        berichte = (
            session.query(Tagesbericht)
            .filter_by(projekt_id=projekt_id)
            .order_by(Tagesbericht.datum.desc())
            .all()
        )
        berichte_daten = [
            {
                "id": b.id,
                "datum": b.datum.strftime("%d.%m.%Y") if b.datum else "",
                "pdf_pfad": b.pdf_pfad,
                "hat_pdf": bool(b.pdf_pfad and os.path.exists(b.pdf_pfad)),
            }
            for b in berichte
        ]

        # Verfügbare Daten für Filter
        daten = (
            session.query(Eintrag.datum)
            .filter_by(projekt_id=projekt_id)
            .distinct()
            .order_by(Eintrag.datum.desc())
            .all()
        )
        verfuegbare_daten = [d[0].strftime("%d.%m.%Y") for d in daten]

        kategorien = (
            session.query(Eintrag.kategorie)
            .filter_by(projekt_id=projekt_id)
            .distinct()
            .all()
        )
        verfuegbare_kategorien = [k[0] for k in kategorien if k[0]]

    return templates.TemplateResponse("projekt.html", {
        "request": request,
        "projekt": projekt_info,
        "eintraege": eintraege_daten,
        "berichte": berichte_daten,
        "verfuegbare_daten": verfuegbare_daten,
        "verfuegbare_kategorien": verfuegbare_kategorien,
        "filter_datum": datum or "",
        "filter_kategorie": kategorie or "",
        "kat_emoji": KATEGORIE_EMOJI,
    })


@app.get("/bericht/{bericht_id}/download")
async def bericht_download(bericht_id: int):
    """PDF-Tagesbericht herunterladen."""
    with get_session() as session:
        bericht = session.query(Tagesbericht).get(bericht_id)
        if not bericht or not bericht.pdf_pfad:
            return HTMLResponse("<h1>Bericht nicht gefunden</h1>", status_code=404)
        pdf_pfad = bericht.pdf_pfad

    if not os.path.exists(pdf_pfad):
        return HTMLResponse("<h1>PDF-Datei nicht gefunden</h1>", status_code=404)

    return FileResponse(
        pdf_pfad,
        media_type="application/pdf",
        filename=os.path.basename(pdf_pfad),
    )


@app.get("/foto/{foto_id}")
async def foto_anzeigen(foto_id: int):
    """Foto anzeigen."""
    with get_session() as session:
        foto = session.query(Foto).get(foto_id)
        if not foto:
            return HTMLResponse("<h1>Foto nicht gefunden</h1>", status_code=404)
        dateipfad = foto.dateipfad

    abs_pfad = os.path.abspath(dateipfad)
    if not os.path.exists(abs_pfad):
        return HTMLResponse("<h1>Fotodatei nicht gefunden</h1>", status_code=404)

    return FileResponse(abs_pfad, media_type="image/jpeg")


@app.get("/export/{projekt_id}/csv")
async def export_csv(
    projekt_id: int,
    datum: str = Query(None),
):
    """Exportiert Einträge als CSV."""
    filter_datum = None
    if datum:
        try:
            filter_datum = datetime.strptime(datum, "%d.%m.%Y").date()
        except ValueError:
            pass

    with get_session() as session:
        projekt = session.query(Projekt).get(projekt_id)
        if not projekt:
            return HTMLResponse("<h1>Projekt nicht gefunden</h1>", status_code=404)
        projekt_name = projekt.name

        query = session.query(Eintrag).filter_by(projekt_id=projekt_id)
        if filter_datum:
            query = query.filter(Eintrag.datum == filter_datum)

        eintraege = query.order_by(Eintrag.datum, Eintrag.uhrzeit).all()

        rows = []
        for e in eintraege:
            rows.append({
                "Datum": e.datum.strftime("%d.%m.%Y") if e.datum else "",
                "Uhrzeit": e.uhrzeit.strftime("%H:%M") if e.uhrzeit else "",
                "Typ": e.typ,
                "Kategorie": e.kategorie or "",
                "Meldung": e.rohinhalt or "",
                "KI-Zusammenfassung": e.ki_zusammenfassung or "",
                "Fotos": ", ".join(f.dateipfad for f in e.fotos),
            })

    # CSV erstellen
    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys(), delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
    else:
        output.write("Keine Einträge vorhanden")

    safe_name = projekt_name.replace(" ", "_")
    filename = f"Export_{safe_name}_{date.today().strftime('%Y-%m-%d')}.csv"

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/stats/{projekt_id}")
async def api_stats(projekt_id: int):
    """JSON-API: Statistiken für ein Projekt."""
    with get_session() as session:
        gesamt = session.query(Eintrag).filter_by(projekt_id=projekt_id).count()
        heute = session.query(Eintrag).filter(
            Eintrag.projekt_id == projekt_id,
            Eintrag.datum == date.today(),
        ).count()
        fotos = (
            session.query(Foto).join(Eintrag)
            .filter(Eintrag.projekt_id == projekt_id).count()
        )
        berichte = session.query(Tagesbericht).filter_by(projekt_id=projekt_id).count()

        # Kategorie-Verteilung
        kat_counts = (
            session.query(Eintrag.kategorie, func.count())
            .filter_by(projekt_id=projekt_id)
            .group_by(Eintrag.kategorie)
            .all()
        )

    return {
        "gesamt_eintraege": gesamt,
        "heute_eintraege": heute,
        "fotos": fotos,
        "berichte": berichte,
        "kategorien": {k or "sonstiges": c for k, c in kat_counts},
    }
