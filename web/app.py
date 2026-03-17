"""FastAPI Web-Dashboard für Instandhaltungsplanung."""
import os
import csv
import io
import secrets
import logging
from datetime import date, datetime
from fastapi import FastAPI, Request, Query, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import func

import config
from db.database import get_session
from db.models import Projekt, Benutzer, Eintrag, Foto, Tagesbericht
from core.pdf import generiere_pdf
from core.docx_export import generiere_docx
from core.ki import generiere_bericht_text

logger = logging.getLogger(__name__)

app = FastAPI(title="Instandhaltungsplanung Dashboard")
security = HTTPBasic()

# Static files & templates
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)


# ─── Auth ─────────────────────────────────────────────────────────────────

def auth_pruefen(credentials: HTTPBasicCredentials = Depends(security)):
    """Prüft HTTP Basic Auth, wenn DASHBOARD_PASSWORT gesetzt ist."""
    if not config.DASHBOARD_PASSWORT:
        return True  # Kein Schutz konfiguriert

    korrekt_user = secrets.compare_digest(
        credentials.username.encode("utf-8"),
        config.DASHBOARD_USER.encode("utf-8"),
    )
    korrekt_pw = secrets.compare_digest(
        credentials.password.encode("utf-8"),
        config.DASHBOARD_PASSWORT.encode("utf-8"),
    )

    if not (korrekt_user and korrekt_pw):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falscher Benutzername oder Passwort",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True

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
async def dashboard(
    request: Request,
    erfolg: str = Query(None),
    fehler: str = Query(None),
    auth=Depends(auth_pruefen),
):
    """Hauptseite – Projektübersicht mit Ordnern."""
    with get_session() as session:
        projekte = session.query(Projekt).order_by(Projekt.ordner, Projekt.name).all()
        projekt_daten = []
        ordner_set = set()
        for p in projekte:
            anzahl = session.query(Eintrag).filter_by(projekt_id=p.id).count()
            anzahl_fotos = (
                session.query(Foto)
                .join(Eintrag)
                .filter(Eintrag.projekt_id == p.id)
                .count()
            )
            anzahl_berichte = session.query(Tagesbericht).filter_by(projekt_id=p.id).count()

            letzte_eintraege = (
                session.query(Eintrag)
                .filter_by(projekt_id=p.id)
                .order_by(Eintrag.datum.desc(), Eintrag.uhrzeit.desc())
                .limit(3)
                .all()
            )

            ordner_name = p.ordner or ""
            if ordner_name:
                ordner_set.add(ordner_name)

            projekt_daten.append({
                "id": p.id,
                "name": p.name,
                "adresse": p.adresse or "–",
                "baubeginn": p.baubeginn.strftime("%d.%m.%Y") if p.baubeginn else "–",
                "anzahl_eintraege": anzahl,
                "anzahl_fotos": anzahl_fotos,
                "anzahl_berichte": anzahl_berichte,
                "ordner": ordner_name,
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

        # Ordner-Liste (sortiert) für Verschieben-Dropdown
        ordner_liste = sorted(ordner_set)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "projekte": projekt_daten,
        "ordner_liste": ordner_liste,
        "titel": "Instandhaltungsplanung",
        "erfolg": erfolg or "",
        "fehler": fehler or "",
    })


@app.get("/projekt/{projekt_id}", response_class=HTMLResponse)
async def projekt_detail(
    request: Request,
    projekt_id: int,
    datum: str = Query(None, description="Filter: TT.MM.JJJJ"),
    prio: str = Query(None, description="Filter: rot|gelb|gruen"),
    kategorie: str = Query(None, description="Filter: Kategorie"),
    fehler: str = Query(None),
    erfolg: str = Query(None),
    auth=Depends(auth_pruefen),
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
        berichte_daten = []
        for b in berichte:
            pdf_pfad = b.pdf_pfad or ""
            docx_pfad = pdf_pfad.replace(".pdf", ".docx") if pdf_pfad else ""
            berichte_daten.append({
                "id": b.id,
                "datum": b.datum.strftime("%d.%m.%Y") if b.datum else "",
                "pdf_pfad": pdf_pfad,
                "hat_pdf": bool(pdf_pfad and os.path.exists(pdf_pfad)),
                "hat_docx": bool(docx_pfad and os.path.exists(docx_pfad)),
            })

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
        "fehler": fehler or "",
        "erfolg": erfolg or "",
    })


@app.post("/bericht/{projekt_id}/generieren")
async def bericht_generieren(
    projekt_id: int,
    datum: str = Form(...),
    auth=Depends(auth_pruefen),
):
    """Generiert einen PDF-Tagesbericht über das Dashboard."""
    # Datum parsen
    try:
        berichtsdatum = datetime.strptime(datum, "%d.%m.%Y").date()
    except ValueError:
        try:
            berichtsdatum = datetime.strptime(datum, "%Y-%m-%d").date()
        except ValueError:
            return HTMLResponse("<h1>Ungültiges Datum</h1>", status_code=400)

    with get_session() as session:
        projekt = session.query(Projekt).get(projekt_id)
        if not projekt:
            return HTMLResponse("<h1>Projekt nicht gefunden</h1>", status_code=404)

        projekt_name = projekt.name

        # Einträge für dieses Datum laden
        eintraege = (
            session.query(Eintrag)
            .filter_by(projekt_id=projekt_id, datum=berichtsdatum)
            .order_by(Eintrag.uhrzeit)
            .all()
        )

        if not eintraege:
            return RedirectResponse(
                url=f"/projekt/{projekt_id}?fehler=keine_eintraege&datum={datum}",
                status_code=303,
            )

        # Daten aus Session extrahieren
        eintraege_daten = []
        for e in eintraege:
            foto_beschreibungen = [f.beschreibung for f in e.fotos if f.beschreibung]
            foto_dateien = []
            for f in e.fotos:
                foto_dateien.append({
                    "dateipfad": f.dateipfad,
                    "beschreibung": f.beschreibung or e.rohinhalt or "",
                })
            eintraege_daten.append({
                "typ": e.typ,
                "uhrzeit": e.uhrzeit.strftime("%H:%M") if e.uhrzeit else "",
                "rohinhalt": e.rohinhalt or "",
                "kategorie": e.kategorie or "sonstiges",
                "ki_zusammenfassung": e.ki_zusammenfassung or "",
                "prioritaet": e.prioritaet or "gelb",
                "kostenschaetzung": e.kostenschaetzung or "",
                "foto_beschreibungen": foto_beschreibungen,
                "foto_dateien": foto_dateien,
            })

        foto_daten = []
        for e in eintraege:
            for f in e.fotos:
                beschreibung = f.beschreibung or e.rohinhalt or ""
                foto_daten.append({
                    "dateipfad": f.dateipfad,
                    "beschreibung": beschreibung,
                    "uhrzeit": e.uhrzeit,
                })

        # Tagesbericht-Eintrag in DB
        tb = (
            session.query(Tagesbericht)
            .filter_by(projekt_id=projekt_id, datum=berichtsdatum)
            .first()
        )
        if not tb:
            tb = Tagesbericht(projekt_id=projekt_id, datum=berichtsdatum)
            session.add(tb)
            session.commit()

    # KI-Zusammenfassung generieren
    logger.info(f"Generiere Bericht für Projekt {projekt_id}, Datum {berichtsdatum}")
    ki_bericht = generiere_bericht_text(eintraege_daten)

    # View-Objekte für PDF-Template
    class EintragView:
        def __init__(self, d):
            self.uhrzeit = d["uhrzeit"]
            self.rohinhalt = d["rohinhalt"]
            self.kategorie = d["kategorie"]
            self.ki_zusammenfassung = d["ki_zusammenfassung"]
            self.prioritaet = d.get("prioritaet", "gelb")
            self.kostenschaetzung = d.get("kostenschaetzung", "")
            self.fotos = d.get("foto_dateien", [])
            self.uhrzeit_str = d["uhrzeit"]

    class FotoView:
        def __init__(self, d):
            self.dateipfad = d["dateipfad"]
            self.beschreibung = d["beschreibung"]
            self.uhrzeit = d["uhrzeit"]

    eintraege_text = [EintragView(e) for e in eintraege_daten if e["typ"] in ("text", "foto", "sprache")]
    fotos = [FotoView(f) for f in foto_daten]

    # Bauleiter — für Web-Berichte unbekannt, daher "Dashboard"
    bauleiter_name = "Dashboard-Benutzer"

    # PDF generieren
    try:
        pdf_pfad = generiere_pdf(
            projekt_name=projekt_name,
            bauleiter_name=bauleiter_name,
            datum=berichtsdatum,
            eintraege_text=eintraege_text,
            fotos=fotos,
            ki_bericht=ki_bericht,
        )
    except Exception as e:
        logger.error(f"PDF-Erstellung fehlgeschlagen: {e}")
        return HTMLResponse(f"<h1>Fehler bei PDF-Erstellung</h1><p>{e}</p>", status_code=500)

    # DOCX generieren
    try:
        logger.info("DOCX-Generierung startet: %d Einträge, ki_bericht=%d Zeichen",
                    len(eintraege_text), len(ki_bericht) if ki_bericht else 0)
        docx_result = generiere_docx(
            projekt_name=projekt_name,
            bauleiter_name=bauleiter_name,
            datum=berichtsdatum,
            eintraege_text=eintraege_text,
            fotos=fotos,
            ki_bericht=ki_bericht,
        )
        logger.info("DOCX erfolgreich generiert: %s", docx_result)
    except Exception as e:
        logger.error("DOCX-Erstellung fehlgeschlagen: %s", e, exc_info=True)

    # PDF-Pfad in DB speichern
    with get_session() as session:
        tb = (
            session.query(Tagesbericht)
            .filter_by(projekt_id=projekt_id, datum=berichtsdatum)
            .first()
        )
        if tb:
            tb.pdf_pfad = pdf_pfad

    logger.info(f"Bericht erstellt: {pdf_pfad}")
    return RedirectResponse(
        url=f"/projekt/{projekt_id}?erfolg=bericht_erstellt&datum={datum}",
        status_code=303,
    )


@app.get("/bericht/{bericht_id}/download")
async def bericht_download(bericht_id: int, auth=Depends(auth_pruefen)):
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


@app.get("/bericht/{bericht_id}/download/docx")
async def bericht_download_docx(bericht_id: int, auth=Depends(auth_pruefen)):
    """Word-Tagesbericht (DOCX) herunterladen."""
    with get_session() as session:
        bericht = session.query(Tagesbericht).get(bericht_id)
        if not bericht or not bericht.pdf_pfad:
            return HTMLResponse("<h1>Bericht nicht gefunden</h1>", status_code=404)
        docx_pfad = bericht.pdf_pfad.replace(".pdf", ".docx")

    if not os.path.exists(docx_pfad):
        return HTMLResponse("<h1>Word-Datei nicht gefunden. Bitte Bericht neu generieren.</h1>", status_code=404)

    return FileResponse(
        docx_pfad,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=os.path.basename(docx_pfad),
    )


@app.get("/foto/{foto_id}")
async def foto_anzeigen(foto_id: int, auth=Depends(auth_pruefen)):
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
    auth=Depends(auth_pruefen),
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
async def api_stats(projekt_id: int, auth=Depends(auth_pruefen)):
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


# ─── Ordner-Verwaltung ───────────────────────────────────────────────────

@app.post("/projekt/{projekt_id}/verschieben")
async def projekt_verschieben(
    projekt_id: int,
    ordner: str = Form(""),
    auth=Depends(auth_pruefen),
):
    """Verschiebt ein Projekt in einen Ordner."""
    with get_session() as session:
        projekt = session.query(Projekt).get(projekt_id)
        if not projekt:
            return HTMLResponse("<h1>Projekt nicht gefunden</h1>", status_code=404)
        projekt.ordner = ordner.strip()
    return RedirectResponse(url="/?erfolg=verschoben", status_code=303)


@app.post("/ordner/umbenennen")
async def ordner_umbenennen(
    alter_name: str = Form(...),
    neuer_name: str = Form(...),
    auth=Depends(auth_pruefen),
):
    """Benennt einen Ordner um (ändert alle zugehörigen Projekte)."""
    neuer = neuer_name.strip()
    if not neuer:
        return RedirectResponse(url="/?fehler=leerer_name", status_code=303)
    with get_session() as session:
        projekte = session.query(Projekt).filter(Projekt.ordner == alter_name.strip()).all()
        for p in projekte:
            p.ordner = neuer
    return RedirectResponse(url="/?erfolg=umbenannt", status_code=303)


@app.post("/ordner/loeschen")
async def ordner_loeschen(
    ordner_name: str = Form(...),
    auth=Depends(auth_pruefen),
):
    """Löst einen Ordner auf – Projekte werden in die Hauptebene verschoben."""
    with get_session() as session:
        projekte = session.query(Projekt).filter(Projekt.ordner == ordner_name.strip()).all()
        for p in projekte:
            p.ordner = ""
    return RedirectResponse(url="/?erfolg=ordner_geloescht", status_code=303)


# ─── Projekt löschen ─────────────────────────────────────────────────────

@app.post("/projekt/{projekt_id}/loeschen")
async def projekt_loeschen(
    projekt_id: int,
    bestaetigung: str = Form(""),
    auth=Depends(auth_pruefen),
):
    """Löscht ein Projekt mit allen zugehörigen Daten."""
    with get_session() as session:
        projekt = session.query(Projekt).get(projekt_id)
        if not projekt:
            return HTMLResponse("<h1>Projekt nicht gefunden</h1>", status_code=404)

        if bestaetigung != projekt.name:
            return RedirectResponse(
                url=f"/projekt/{projekt_id}?fehler=loeschen_name_falsch",
                status_code=303,
            )

        # Fotos löschen (Dateien + DB)
        fotos = session.query(Foto).join(Eintrag).filter(Eintrag.projekt_id == projekt_id).all()
        for foto in fotos:
            if foto.dateipfad and os.path.exists(foto.dateipfad):
                try:
                    os.remove(foto.dateipfad)
                except OSError:
                    pass
            session.delete(foto)

        # Berichte löschen (PDF-Dateien + DB)
        berichte = session.query(Tagesbericht).filter_by(projekt_id=projekt_id).all()
        for b in berichte:
            if b.pdf_pfad and os.path.exists(b.pdf_pfad):
                try:
                    os.remove(b.pdf_pfad)
                except OSError:
                    pass
            session.delete(b)

        # Einträge löschen
        session.query(Eintrag).filter_by(projekt_id=projekt_id).delete()

        # Benutzer-Referenzen aufheben
        session.query(Benutzer).filter_by(aktives_projekt_id=projekt_id).update(
            {"aktives_projekt_id": None}
        )

        # Projekt löschen
        session.delete(projekt)

    return RedirectResponse(url="/?erfolg=geloescht", status_code=303)
