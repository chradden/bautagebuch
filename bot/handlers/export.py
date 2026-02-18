"""Handler für /export – CSV-Export der Einträge."""
import csv
import io
import os
from datetime import date, datetime
from telegram import Update
from telegram.ext import ContextTypes

from db.database import get_session
from db.models import Benutzer, Projekt, Eintrag


async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exportiert alle Einträge des aktiven Projekts als CSV-Datei."""
    telegram_id = update.effective_user.id

    # Optional: Datum angeben
    filter_datum = None
    if context.args:
        try:
            filter_datum = datetime.strptime(context.args[0], "%d.%m.%Y").date()
        except ValueError:
            await update.message.reply_text(
                "❌ Ungültiges Datum. Format: TT.MM.JJJJ\n"
                "Beispiel: /export 21.09.2025\n"
                "Oder einfach /export für alle Einträge."
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
        projekt_id = projekt.id

        query = session.query(Eintrag).filter_by(projekt_id=projekt_id)
        if filter_datum:
            query = query.filter(Eintrag.datum == filter_datum)

        eintraege = query.order_by(Eintrag.datum, Eintrag.uhrzeit).all()

        if not eintraege:
            msg = f"📭 Keine Einträge"
            if filter_datum:
                msg += f" für {filter_datum.strftime('%d.%m.%Y')}"
            msg += " gefunden."
            await update.message.reply_text(msg)
            return

        # CSV erstellen
        rows = []
        for e in eintraege:
            rows.append({
                "Datum": e.datum.strftime("%d.%m.%Y") if e.datum else "",
                "Uhrzeit": e.uhrzeit.strftime("%H:%M") if e.uhrzeit else "",
                "Typ": e.typ,
                "Kategorie": e.kategorie or "",
                "Meldung": e.rohinhalt or "",
                "KI-Zusammenfassung": e.ki_zusammenfassung or "",
                "Anzahl Fotos": str(len(e.fotos)),
            })

    # CSV in Speicher schreiben
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys(), delimiter=";")
    writer.writeheader()
    writer.writerows(rows)

    # Als Datei senden
    safe_name = projekt_name.replace(" ", "_")
    datum_str = filter_datum.strftime("%Y-%m-%d") if filter_datum else "gesamt"
    filename = f"Export_{safe_name}_{datum_str}.csv"

    csv_bytes = output.getvalue().encode("utf-8-sig")

    await update.message.reply_document(
        document=io.BytesIO(csv_bytes),
        filename=filename,
        caption=(
            f"📥 CSV-Export: **{projekt_name}**\n"
            f"📋 {len(rows)} Einträge"
            + (f"\n📅 Datum: {filter_datum.strftime('%d.%m.%Y')}" if filter_datum else "")
        ),
        parse_mode="Markdown",
    )
