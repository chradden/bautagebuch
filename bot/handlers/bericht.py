"""Handler für /bericht – PDF-Tagesbericht generieren & senden."""
import os
from datetime import date, datetime
from telegram import Update
from telegram.ext import ContextTypes

from db.database import get_session
from db.models import Benutzer, Projekt, Eintrag, Tagesbericht
from core.pdf import generiere_pdf
from core.docx_export import generiere_docx
from core.ki import generiere_bericht_text


async def bericht_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generiert einen PDF-Tagesbericht und sendet ihn im Chat."""
    telegram_id = update.effective_user.id

    # Datum bestimmen (Standard: heute)
    berichtsdatum = date.today()
    if context.args:
        try:
            berichtsdatum = datetime.strptime(context.args[0], "%d.%m.%Y").date()
        except ValueError:
            await update.message.reply_text(
                "❌ Ungültiges Datum. Format: TT.MM.JJJJ\n"
                "Beispiel: /bericht 21.09.2025"
            )
            return

    with get_session() as session:
        benutzer = session.query(Benutzer).filter_by(telegram_id=telegram_id).first()
        if not benutzer:
            await update.message.reply_text("Bitte zuerst /start ausführen.")
            return

        if not benutzer.aktives_projekt_id:
            await update.message.reply_text(
                "Kein aktives Projekt. Erstelle eins mit /projekt <Name>"
            )
            return

        projekt = session.query(Projekt).get(benutzer.aktives_projekt_id)
        projekt_name = projekt.name
        bauleiter_name = benutzer.name
        projekt_id = projekt.id
        projekt_adresse = projekt.adresse or ""

        # Einträge für dieses Datum laden
        eintraege = (
            session.query(Eintrag)
            .filter_by(projekt_id=projekt_id, datum=berichtsdatum)
            .order_by(Eintrag.uhrzeit)
            .all()
        )

        if not eintraege:
            await update.message.reply_text(
                f"📋 Keine Einträge für {berichtsdatum.strftime('%d.%m.%Y')} gefunden.\n"
                f"Sende zuerst Meldungen (Text, Fotos oder Sprache)."
            )
            return

        # Text-Einträge und Fotos separieren – Werte aus Session extrahieren
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
                "uhrzeit": e.uhrzeit.strftime('%H:%M') if e.uhrzeit else "",
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

        # Tagesbericht in DB vorbereiten
        tb = (
            session.query(Tagesbericht)
            .filter_by(projekt_id=projekt_id, datum=berichtsdatum)
            .first()
        )
        if not tb:
            tb = Tagesbericht(projekt_id=projekt_id, datum=berichtsdatum)
            session.add(tb)

    # Ab hier außerhalb der Session – nur lokale Variablen verwenden
    await update.message.reply_text("📄 Instandhaltungsbericht wird erstellt... 🤖 KI priorisiert & schätzt Kosten...")

    # KI-Zusammenfassung generieren
    ki_bericht = generiere_bericht_text(eintraege_daten)

    # Einfache Objekte für das Template
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

    # PDF generieren
    try:
        pdf_pfad = generiere_pdf(
            projekt_name=projekt_name,
            bauleiter_name=bauleiter_name,
            datum=berichtsdatum,
            eintraege_text=eintraege_text,
            fotos=fotos,
            ki_bericht=ki_bericht,
            projekt_adresse=projekt_adresse,
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Fehler bei PDF-Erstellung: {e}")
        return

    # DOCX generieren
    try:
        docx_pfad = generiere_docx(
            projekt_name=projekt_name,
            bauleiter_name=bauleiter_name,
            datum=berichtsdatum,
            eintraege_text=eintraege_text,
            fotos=fotos,
            ki_bericht=ki_bericht,
            projekt_adresse=projekt_adresse,
        )
    except Exception as e:
        docx_pfad = None
        await update.message.reply_text(f"⚠️ Word-Dokument konnte nicht erstellt werden: {e}")

    # PDF-Pfad in DB speichern
    with get_session() as session:
        tb = (
            session.query(Tagesbericht)
            .filter_by(projekt_id=projekt_id, datum=berichtsdatum)
            .first()
        )
        if tb:
            tb.pdf_pfad = pdf_pfad

    # PDF senden
    with open(pdf_pfad, "rb") as pdf_file:
        await update.message.reply_document(
            document=pdf_file,
            filename=os.path.basename(pdf_pfad),
            caption=f"📄 Instandhaltungsbericht – {projekt_name}\n📅 {berichtsdatum.strftime('%d.%m.%Y')}",
        )

    # DOCX senden
    if docx_pfad:
        with open(docx_pfad, "rb") as docx_file:
            await update.message.reply_document(
                document=docx_file,
                filename=os.path.basename(docx_pfad),
                caption=(
                    f"📝 Word-Version (bearbeitbar) – {projekt_name}\n"
                    f"📅 {berichtsdatum.strftime('%d.%m.%Y')}"
                ),
            )
