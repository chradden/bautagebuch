"""Bautagebuch Telegram Bot – Hauptmodul."""
import logging
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

import config
from db.database import init_db
from bot.handlers.start import get_start_handler
from bot.handlers.projekt import (
    projekt_command,
    wechsel_command,
    status_command,
    hilfe_command,
    standort_command,
    standort_empfangen,
    get_projekt_callback_handler,
)
from bot.handlers.eintrag import text_eintrag, foto_eintrag, sprach_eintrag
from bot.handlers.bericht import bericht_command
from bot.handlers.export import export_command
from bot.handlers.scheduler import erinnerung_registrieren

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    """Bot starten."""
    logger.info("Initialisiere Datenbank...")
    init_db()

    logger.info("Starte Bautagebuch-Bot...")
    app = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Handler registrieren (Reihenfolge wichtig!)
    # 1. Conversation Handler für /start (hat Priorität)
    app.add_handler(get_start_handler())

    # 2. Befehle
    app.add_handler(CommandHandler("projekt", projekt_command))
    app.add_handler(CommandHandler("wechsel", wechsel_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("bericht", bericht_command))
    app.add_handler(CommandHandler("export", export_command))
    app.add_handler(CommandHandler("hilfe", hilfe_command))
    app.add_handler(CommandHandler("standort", standort_command))

    # 3. Callback für Inline-Buttons
    app.add_handler(get_projekt_callback_handler())

    # 4. Nachrichten-Handler (Text, Fotos, Sprache als Einträge)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_eintrag))
    app.add_handler(MessageHandler(filters.PHOTO, foto_eintrag))
    app.add_handler(MessageHandler(filters.VOICE, sprach_eintrag))

    # 5. Standort-Handler in eigener Gruppe (group=1),
    #    damit er NICHT vom ConversationHandler blockiert werden kann
    app.add_handler(MessageHandler(filters.LOCATION, standort_empfangen), group=1)

    # 6. Tägliche Erinnerung registrieren (18:00 Uhr)
    erinnerung_registrieren(app.job_queue)

    logger.info("Bot läuft! Drücke Ctrl+C zum Beenden.")
    app.run_polling()


if __name__ == "__main__":
    main()
