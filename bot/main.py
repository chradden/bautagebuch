"""Bautagebuch Telegram Bot – Hauptmodul."""
import logging
import traceback
import html
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    TypeHandler,
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
    debug_standort_command,
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


async def error_handler(update: object, context) -> None:
    """Globaler Error-Handler – fängt alle unbehandelten Exceptions."""
    logger.error("Exception bei Update-Verarbeitung:", exc_info=context.error)
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    logger.error("Traceback:\n%s", tb_string)

    # Versuche dem User eine Fehlermeldung zu senden
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Ein Fehler ist aufgetreten. Bitte versuche es erneut."
            )
    except Exception:
        pass


async def log_all_updates(update: Update, context) -> None:
    """Debug-Logger: protokolliert ALLE eingehenden Updates."""
    if not isinstance(update, Update):
        return
    msg = update.effective_message
    user = update.effective_user
    user_info = f"User {user.id} ({user.first_name})" if user else "Unknown"

    if msg and msg.location:
        logger.info(
            "📍 UPDATE [LOCATION] von %s: lat=%s, lon=%s",
            user_info, msg.location.latitude, msg.location.longitude,
        )
    elif msg and msg.text:
        logger.info("💬 UPDATE [TEXT] von %s: %s", user_info, msg.text[:50])
    elif msg and msg.photo:
        logger.info("📷 UPDATE [PHOTO] von %s", user_info)
    elif msg and msg.voice:
        logger.info("🎤 UPDATE [VOICE] von %s", user_info)
    elif update.callback_query:
        logger.info("🔘 UPDATE [CALLBACK] von %s: %s", user_info, update.callback_query.data)
    else:
        logger.info("❓ UPDATE [OTHER] von %s: %s", user_info, type(update))


def main():
    """Bot starten."""
    logger.info("Initialisiere Datenbank...")
    init_db()

    logger.info("Starte Bautagebuch-Bot...")
    app = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Handler registrieren (Reihenfolge wichtig!)

    # 0. Debug-Logger für ALLE Updates (eigene Gruppe, läuft immer)
    app.add_handler(TypeHandler(Update, log_all_updates), group=-1)

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
    app.add_handler(CommandHandler("debugstandort", debug_standort_command))

    # 3. Callback für Inline-Buttons
    app.add_handler(get_projekt_callback_handler())

    # 4. Nachrichten-Handler – LOCATION zuerst (vor TEXT!)
    app.add_handler(MessageHandler(filters.LOCATION, standort_empfangen))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_eintrag))
    app.add_handler(MessageHandler(filters.PHOTO, foto_eintrag))
    app.add_handler(MessageHandler(filters.VOICE, sprach_eintrag))

    # 5. Globaler Error-Handler
    app.add_error_handler(error_handler)

    # 6. Tägliche Erinnerung registrieren (18:00 Uhr)
    erinnerung_registrieren(app.job_queue)

    logger.info("=== Handler registriert ===")
    logger.info("  LOCATION-Handler: filters.LOCATION → standort_empfangen")
    logger.info("  Debug-Logger: TypeHandler(Update) in group=-1")
    logger.info("  Error-Handler: aktiv")
    logger.info("Bot läuft! Drücke Ctrl+C zum Beenden.")
    app.run_polling()


if __name__ == "__main__":
    main()
