"""Geplante Aufgaben – Tägliche Erinnerung & automatische Berichte."""
import logging
from datetime import time, datetime
from telegram.ext import ContextTypes

from db.database import get_session
from db.models import Benutzer, Eintrag

logger = logging.getLogger(__name__)


async def erinnerung_senden(context: ContextTypes.DEFAULT_TYPE):
    """
    Wird täglich um 18:00 aufgerufen.
    Sendet an alle aktiven Benutzer eine Erinnerung, ihren Bericht zu erstellen.
    """
    logger.info("Tägliche Erinnerung wird gesendet...")

    with get_session() as session:
        benutzer_liste = session.query(Benutzer).filter(
            Benutzer.aktives_projekt_id.isnot(None)
        ).all()

        for b in benutzer_liste:
            telegram_id = b.telegram_id
            name = b.name
            projekt_id = b.aktives_projekt_id

            # Prüfen, ob heute bereits Einträge gemacht wurden
            heute = datetime.now().date()
            anzahl_heute = (
                session.query(Eintrag)
                .filter_by(benutzer_id=b.id, projekt_id=projekt_id, datum=heute)
                .count()
            )

            try:
                if anzahl_heute > 0:
                    text = (
                        f"📋 Guten Abend, {name}!\n\n"
                        f"Du hast heute **{anzahl_heute} Meldung{'en' if anzahl_heute != 1 else ''}** erfasst.\n\n"
                        f"💡 Vergiss nicht, den Tagesbericht zu erstellen:\n"
                        f"➡️ /bericht"
                    )
                else:
                    text = (
                        f"⚠️ Guten Abend, {name}!\n\n"
                        f"Du hast heute noch **keine Meldungen** erfasst.\n\n"
                        f"📝 Gibt es etwas zu dokumentieren?\n"
                        f"Sende einfach Text, Fotos oder Sprachnachrichten."
                    )

                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=text,
                    parse_mode="Markdown",
                )
                logger.info(f"Erinnerung an {name} (ID {telegram_id}) gesendet.")
            except Exception as e:
                logger.error(f"Erinnerung an {telegram_id} fehlgeschlagen: {e}")

    logger.info("Tägliche Erinnerung abgeschlossen.")


def erinnerung_registrieren(job_queue):
    """
    Registriert die tägliche Erinnerung im JobQueue.
    Wird um 18:00 Uhr (lokal) ausgelöst.
    """
    job_queue.run_daily(
        erinnerung_senden,
        time=time(hour=18, minute=0, second=0),
        name="taegliche_erinnerung",
    )
    logger.info("Tägliche Erinnerung registriert: 18:00 Uhr")
