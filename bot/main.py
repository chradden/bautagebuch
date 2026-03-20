"""Bautagebuch Telegram Bot – Hauptmodul."""
import logging
import traceback
from telegram import BotCommand, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    TypeHandler,
    filters,
)

import config
from db.database import init_db
from bot.handlers.start import get_start_handler, name_aendern
from bot.handlers.projekt import (
    projekt_command,
    wechsel_command,
    status_command,
    hilfe_command,
    get_projekt_callback_handler,
)
from bot.handlers.standort import standort_command, standort_location
from bot.handlers.eintrag import text_eintrag, foto_eintrag, sprach_eintrag
from bot.handlers.bericht import bericht_command
from bot.handlers.export import export_command


# from bot.handlers.scheduler import erinnerung_registrieren
try:
    from bot.handlers.scheduler import erinnerung_registrieren
except ImportError:
    erinnerung_registrieren = None


# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def error_handler(update: object, context) -> None:
    """Globaler Error-Handler – fängt alle unbehandelten Exceptions."""
    logger.error("Exception bei Update-Verarbeitung:", exc_info=context.error)
    tb = traceback.format_exception(None, context.error, context.error.__traceback__)
    logger.error("Traceback:\n%s", "".join(tb))
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Ein Fehler ist aufgetreten. Bitte versuche es erneut."
            )
    except Exception:
        pass


async def log_all_updates(update: Update, context) -> None:
    """Protokolliert ALLE eingehenden Updates für Debugging."""
    if not isinstance(update, Update):
        return
    msg = update.effective_message
    user = update.effective_user
    who = f"User {user.id}" if user else "?"

    if msg and msg.location:
        logger.info("[LOCATION] %s: lat=%s lon=%s", who, msg.location.latitude, msg.location.longitude)
    elif msg and msg.text:
        logger.info("[TEXT] %s: %s", who, msg.text[:80])
    elif msg and msg.photo:
        logger.info("[PHOTO] %s", who)
    elif msg and msg.voice:
        logger.info("[VOICE] %s", who)
    elif update.callback_query:
        logger.info("[CALLBACK] %s: %s", who, update.callback_query.data)


def main():
    """Bot starten."""
    logger.info("Initialisiere Datenbank...")
    init_db()

    logger.info("Starte Bautagebuch-Bot...")

    async def post_init(application):
        """Setzt das Befehlsmenü in Telegram nach dem Start."""
        await application.bot.set_my_commands([
            BotCommand("start", "Registrierung"),
            BotCommand("projekt", "Neues Objekt/Projekt anlegen"),
            BotCommand("wechsel", "Aktives Projekt wechseln"),
            BotCommand("standort", "Adresse per Standort setzen"),
            BotCommand("status", "Status & heutige Einträge"),
            BotCommand("bericht", "PDF-Instandhaltungsbericht"),
            BotCommand("export", "CSV-Export der Einträge"),
            BotCommand("name", "Namen ändern"),
            BotCommand("hilfe", "Befehlsübersicht"),
        ])

    app = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # Debug-Logger für ALLE Updates (eigene Gruppe, läuft immer zuerst)
    app.add_handler(TypeHandler(Update, log_all_updates), group=-1)

    # 1. Conversation Handler für /start
    app.add_handler(get_start_handler())

    # 2. Befehle
    app.add_handler(CommandHandler("projekt", projekt_command))
    app.add_handler(CommandHandler("wechsel", wechsel_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("bericht", bericht_command))
    app.add_handler(CommandHandler("export", export_command))
    app.add_handler(CommandHandler("hilfe", hilfe_command))
    app.add_handler(CommandHandler("name", name_aendern))
    app.add_handler(CommandHandler("standort", standort_command))

    # 3. Callback für Inline-Buttons
    app.add_handler(get_projekt_callback_handler())

    # 4. Nachrichten-Handler (gleiche Reihenfolge wie im typenschild-scanner)
    app.add_handler(MessageHandler(filters.PHOTO, foto_eintrag))
    app.add_handler(MessageHandler(filters.LOCATION, standort_location))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_eintrag))
    app.add_handler(MessageHandler(filters.VOICE, sprach_eintrag))

    # 5. Error-Handler
    app.add_error_handler(error_handler)

    # 6. Tägliche Erinnerung
    if erinnerung_registrieren:
        erinnerung_registrieren(app.job_queue)

    logger.info("Bot läuft! LOCATION-Handler aktiv.")
    app.run_polling()


if __name__ == "__main__":
    main()
