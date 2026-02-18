"""Handler für /start – Registrierung neuer Benutzer."""
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

from db.database import get_session
from db.models import Benutzer

# Conversation States
WARTE_AUF_NAME = 0


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prüft ob Benutzer existiert, sonst Registrierung starten."""
    telegram_id = update.effective_user.id

    with get_session() as session:
        benutzer = session.query(Benutzer).filter_by(telegram_id=telegram_id).first()

    if benutzer:
        await update.message.reply_text(
            f"Willkommen zurück, {benutzer.name}! 🔧\n\n"
            f"Nutze /status um dein aktives Projekt zu sehen.\n"
            f"Nutze /hilfe für alle Befehle."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "Willkommen bei der Instandhaltungsplanung! 🔧\n\n"
        "Ich helfe dir, Mängel & Reparaturen zu erfassen, "
        "zu priorisieren und Kosten zu schätzen.\n\n"
        "Bitte gib deinen Namen ein:"
    )
    return WARTE_AUF_NAME


async def name_eingabe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Speichert den Namen und schließt die Registrierung ab."""
    name = update.message.text.strip()
    telegram_id = update.effective_user.id

    with get_session() as session:
        benutzer = Benutzer(telegram_id=telegram_id, name=name)
        session.add(benutzer)

    await update.message.reply_text(
        f"Hallo {name}! ✅\n\n"
        f"Dein Account wurde erstellt.\n"
        f"Lege jetzt dein erstes Objekt/Projekt an mit:\n"
        f"/projekt <Name>\n\n"
        f"Beispiel: /projekt Bürogebäude Schönhauser Allee 45"
    )
    return ConversationHandler.END


async def abbrechen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bricht die Registrierung ab."""
    await update.message.reply_text("Registrierung abgebrochen.")
    return ConversationHandler.END


def get_start_handler():
    """Erstellt den ConversationHandler für /start."""
    return ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            WARTE_AUF_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, name_eingabe)
            ],
        },
        fallbacks=[CommandHandler("abbrechen", abbrechen)],
    )
