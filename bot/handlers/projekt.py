"""Handler für /projekt, /wechsel, /status – Projektverwaltung."""
import logging
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, CallbackQueryHandler

from db.database import get_session
from db.models import Benutzer, Projekt, Eintrag
from bot.keyboards import projekt_auswahl_keyboard, standort_keyboard
from core.geocoding import reverse_geocode
from datetime import date

logger = logging.getLogger(__name__)


async def projekt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Neues Projekt anlegen: /projekt <Name>"""
    telegram_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text(
            "Bitte gib einen Projektnamen an:\n"
            "/projekt <Name>\n\n"
            "Beispiel: /projekt Schönhauser Allee 45"
        )
        return

    projektname = " ".join(context.args)

    with get_session() as session:
        benutzer = session.query(Benutzer).filter_by(telegram_id=telegram_id).first()
        if not benutzer:
            await update.message.reply_text("Bitte zuerst /start ausführen.")
            return

        projekt = Projekt(name=projektname)
        session.add(projekt)
        session.flush()  # ID generieren

        benutzer.aktives_projekt_id = projekt.id

    await update.message.reply_text(
        f"✅ Projekt \"{projektname}\" angelegt und aktiviert.\n\n"
        f"Du kannst jetzt Mängel & Reparaturen melden:\n"
        f"• Textnachrichten – Mangel beschreiben\n"
        f"• Fotos – Schaden dokumentieren\n"
        f"• Sprachnachrichten – Befund diktieren\n\n"
        f"Die KI priorisiert automatisch (🔴🟡🟢) und schätzt Kosten.\n"
        f"/bericht für den Instandhaltungsbericht als PDF."
    )


async def wechsel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aktives Projekt wechseln."""
    telegram_id = update.effective_user.id

    with get_session() as session:
        benutzer = session.query(Benutzer).filter_by(telegram_id=telegram_id).first()
        if not benutzer:
            await update.message.reply_text("Bitte zuerst /start ausführen.")
            return

        projekte = session.query(Projekt).all()

    if not projekte:
        await update.message.reply_text(
            "Noch keine Projekte vorhanden.\n"
            "Erstelle eins mit /projekt <Name>"
        )
        return

    await update.message.reply_text(
        "Wähle ein Projekt:",
        reply_markup=projekt_auswahl_keyboard(projekte)
    )


async def projekt_auswahl_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback für Inline-Button Projektauswahl."""
    query = update.callback_query
    await query.answer()

    projekt_id = int(query.data.split("_")[1])
    telegram_id = update.effective_user.id

    with get_session() as session:
        benutzer = session.query(Benutzer).filter_by(telegram_id=telegram_id).first()
        projekt = session.query(Projekt).get(projekt_id)

        if benutzer and projekt:
            benutzer.aktives_projekt_id = projekt_id
            name = projekt.name
        else:
            await query.edit_message_text("Fehler: Projekt nicht gefunden.")
            return

    await query.edit_message_text(f"✅ Aktives Projekt: \"{name}\"")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt Status: aktives Projekt & heutige Einträge."""
    telegram_id = update.effective_user.id
    heute = date.today()

    with get_session() as session:
        benutzer = session.query(Benutzer).filter_by(telegram_id=telegram_id).first()
        if not benutzer:
            await update.message.reply_text("Bitte zuerst /start ausführen.")
            return

        if not benutzer.aktives_projekt_id:
            await update.message.reply_text(
                "Kein aktives Projekt.\n"
                "Erstelle eins mit /projekt <Name>"
            )
            return

        projekt = session.query(Projekt).get(benutzer.aktives_projekt_id)
        eintraege_heute = (
            session.query(Eintrag)
            .filter_by(projekt_id=projekt.id, datum=heute)
            .all()
        )

        text_count = sum(1 for e in eintraege_heute if e.typ == "text")
        foto_count = sum(1 for e in eintraege_heute if e.typ == "foto")
        sprach_count = sum(1 for e in eintraege_heute if e.typ == "sprache")
        gesamt = len(eintraege_heute)
        projekt_name = projekt.name

    await update.message.reply_text(
        f"📋 **Status**\n\n"
        f"**Objekt:** {projekt_name}\n"
        f"**Datum:** {heute.strftime('%d.%m.%Y')}\n\n"
        f"**Heutige Meldungen:**\n"
        f"• Texte: {text_count}\n"
        f"• Fotos: {foto_count}\n"
        f"• Sprache: {sprach_count}\n"
        f"• Gesamt: {gesamt}\n\n"
        f"Nutze /bericht für den Instandhaltungsbericht.\n"
        f"Nutze /export für CSV-Export.",
        parse_mode="Markdown"
    )


async def hilfe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt alle verfügbaren Befehle."""
    await update.message.reply_text(
        "🔧 **Instandhaltungsplanung – Befehle**\n\n"
        "/start – Registrierung\n"
        "/projekt <Name> – Neues Objekt/Projekt anlegen\n"
        "/wechsel – Aktives Projekt wechseln\n"
        "/standort – Adresse per Standort setzen\n"
        "/status – Status & heutige Einträge\n"
        "/bericht – PDF-Instandhaltungsbericht generieren\n"
        "/bericht <TT.MM.JJJJ> – Bericht für bestimmtes Datum\n"
        "/export – CSV-Export aller Einträge\n"
        "/export <TT.MM.JJJJ> – CSV-Export für bestimmtes Datum\n"
        "/hilfe – Diese Übersicht\n\n"
        "**Mängel & Reparaturen melden:**\n"
        "Einfach Text, Fotos oder Sprachnachrichten senden.\n"
        "Die KI priorisiert automatisch:\n"
        "🔴 ROT = Sofort handeln\n"
        "🟡 GELB = Zeitnah beheben\n"
        "🟢 GRÜN = Kann geplant werden\n\n"
        "💰 Kostenschätzung wird automatisch erstellt.\n\n"
        "📍 **Standort teilen:** Sende /standort um die Adresse\n"
        "des Projekts automatisch per GPS zu setzen.\n\n"
        "🌐 **Web-Dashboard:** http://localhost:8090",
        parse_mode="Markdown"
    )


def get_projekt_callback_handler():
    """Erstellt den CallbackQueryHandler für Projektauswahl."""
    return CallbackQueryHandler(projekt_auswahl_callback, pattern=r"^projekt_\d+$")


async def standort_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fordert den Benutzer auf, seinen Standort zu teilen: /standort"""
    telegram_id = update.effective_user.id

    with get_session() as session:
        benutzer = session.query(Benutzer).filter_by(telegram_id=telegram_id).first()
        if not benutzer:
            await update.message.reply_text("Bitte zuerst /start ausführen.")
            return

        if not benutzer.aktives_projekt_id:
            await update.message.reply_text(
                "Kein aktives Projekt vorhanden.\n"
                "Erstelle eins mit /projekt <Name>"
            )
            return

        projekt = session.query(Projekt).get(benutzer.aktives_projekt_id)
        projekt_name = projekt.name if projekt else "Unbekannt"

    await update.message.reply_text(
        f"📍 Teile deinen Standort, um die Adresse für "
        f"\"{projekt_name}\" automatisch zu setzen.\n\n"
        f"Klicke auf den Button unten oder sende einen Standort manuell.",
        reply_markup=standort_keyboard(),
    )


async def standort_empfangen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verarbeitet einen geteilten Standort und setzt die Adresse im aktiven Projekt."""
    telegram_id = update.effective_user.id
    message = update.effective_message

    if not message or not message.location:
        logger.warning("standort_empfangen: Kein Standort in Nachricht (User %s)", telegram_id)
        return

    location = message.location
    logger.info(
        "Standort empfangen von User %s: lat=%s, lon=%s",
        telegram_id, location.latitude, location.longitude,
    )

    # Prüfen ob Benutzer und aktives Projekt existieren
    try:
        with get_session() as session:
            benutzer = session.query(Benutzer).filter_by(telegram_id=telegram_id).first()
            if not benutzer:
                await message.reply_text(
                    "Bitte zuerst /start ausführen.",
                    reply_markup=ReplyKeyboardRemove(),
                )
                return

            if not benutzer.aktives_projekt_id:
                await message.reply_text(
                    "Kein aktives Projekt vorhanden.\n"
                    "Erstelle eins mit /projekt <Name>",
                    reply_markup=ReplyKeyboardRemove(),
                )
                return

            aktives_projekt_id = benutzer.aktives_projekt_id
            logger.info("Aktives Projekt ID: %s", aktives_projekt_id)
    except Exception as e:
        logger.error("DB-Fehler beim Standort-Empfangen (Benutzer-Check): %s", e)
        await message.reply_text(
            "❌ Datenbankfehler. Bitte versuche es erneut.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    # Reverse Geocoding
    await message.reply_text(
        "🔍 Ermittle Adresse aus Koordinaten...",
        reply_markup=ReplyKeyboardRemove(),
    )

    try:
        geo_result = await reverse_geocode(location.latitude, location.longitude)
        logger.info("Geocoding-Ergebnis: %s", geo_result)
    except Exception as e:
        logger.error("Geocoding-Exception: %s", e)
        geo_result = None

    # Koordinaten + Adresse speichern
    try:
        with get_session() as session:
            projekt = session.query(Projekt).get(aktives_projekt_id)
            if not projekt:
                await message.reply_text("Projekt nicht gefunden.")
                return

            projekt.latitude = location.latitude
            projekt.longitude = location.longitude

            if geo_result:
                projekt.adresse = geo_result["adresse"]
                logger.info("Adresse gespeichert: %s", geo_result["adresse"])
    except Exception as e:
        logger.error("DB-Fehler beim Speichern der Geodaten: %s", e)
        await message.reply_text(
            "❌ Fehler beim Speichern. Bitte versuche es erneut."
        )
        return

    if not geo_result:
        await message.reply_text(
            f"⚠️ Adresse konnte nicht ermittelt werden.\n\n"
            f"Koordinaten wurden gespeichert:\n"
            f"📍 {location.latitude:.6f}, {location.longitude:.6f}"
        )
        return

    await message.reply_text(
        f"✅ Adresse für das Projekt gesetzt!\n\n"
        f"📍 **Adresse:** {geo_result['adresse']}\n"
        f"🗺️ **Koordinaten:** {location.latitude:.6f}, {location.longitude:.6f}",
        parse_mode="Markdown",
    )
