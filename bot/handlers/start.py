"""Handler für /start – Registrierung neuer Benutzer mit Passwort-Schutz."""
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

import config
from db.database import get_session
from db.models import Benutzer

# Conversation States
WARTE_AUF_PASSWORT = 0
WARTE_AUF_NAME = 1


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prüft ob Benutzer existiert, sonst Registrierung starten."""
    telegram_id = update.effective_user.id
    name = None

    with get_session() as session:
        benutzer = session.query(Benutzer).filter_by(telegram_id=telegram_id).first()
        if benutzer:
            name = benutzer.name

    if name:
        await update.message.reply_text(
            f"Willkommen zurück, {name}! 🔧\n\n"
            f"Nutze /status um dein aktives Projekt zu sehen.\n"
            f"Nutze /hilfe für alle Befehle."
        )
        return ConversationHandler.END

    # Passwort-Schutz aktiv?
    if config.BOT_PASSWORT:
        await update.message.reply_text(
            "🔒 Willkommen bei der Instandhaltungsplanung!\n\n"
            "Dieser Bot ist passwortgeschützt.\n"
            "Bitte gib das Zugangspasswort ein:"
        )
        return WARTE_AUF_PASSWORT
    else:
        await update.message.reply_text(
            "Willkommen bei der Instandhaltungsplanung! 🔧\n\n"
            "Ich helfe dir, Mängel & Reparaturen zu erfassen, "
            "zu priorisieren und Kosten zu schätzen.\n\n"
            "Bitte gib deinen Namen ein:"
        )
        return WARTE_AUF_NAME


async def passwort_eingabe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prüft das eingegebene Passwort."""
    eingabe = update.message.text.strip()

    # Nachricht mit Passwort sofort löschen (Datenschutz)
    try:
        await update.message.delete()
    except Exception:
        pass  # Löschen fehlgeschlagen (Bot hat keine Rechte)

    if eingabe == config.BOT_PASSWORT:
        await update.effective_chat.send_message(
            "✅ Passwort korrekt!\n\n"
            "Willkommen bei der Instandhaltungsplanung! 🔧\n"
            "Ich helfe dir, Mängel & Reparaturen zu erfassen, "
            "zu priorisieren und Kosten zu schätzen.\n\n"
            "Bitte gib deinen Namen ein:"
        )
        return WARTE_AUF_NAME
    else:
        # Fehlversuche zählen
        versuche = context.user_data.get("passwort_versuche", 0) + 1
        context.user_data["passwort_versuche"] = versuche

        if versuche >= 3:
            await update.effective_chat.send_message(
                "❌ Zu viele Fehlversuche. Zugang gesperrt.\n"
                "Kontaktiere den Administrator."
            )
            return ConversationHandler.END

        await update.effective_chat.send_message(
            f"❌ Falsches Passwort. Versuch {versuche}/3.\n"
            "Bitte erneut eingeben:"
        )
        return WARTE_AUF_PASSWORT


async def name_eingabe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Speichert den Namen und schließt die Registrierung ab."""
    name = update.message.text.strip()
    telegram_id = update.effective_user.id

    with get_session() as session:
        benutzer = Benutzer(telegram_id=telegram_id, name=name)
        session.add(benutzer)

    # Fehlversuche zurücksetzen
    context.user_data.pop("passwort_versuche", None)

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
            WARTE_AUF_PASSWORT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, passwort_eingabe)
            ],
            WARTE_AUF_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, name_eingabe)
            ],
        },
        fallbacks=[CommandHandler("abbrechen", abbrechen)],
    )
