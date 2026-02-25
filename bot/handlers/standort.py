"""Handler für Standort-Sharing – Reverse Geocoding für Projektadresse."""
import logging
import requests
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes

from db.database import get_session
from db.models import Benutzer, Projekt
from bot.keyboards import standort_keyboard

logger = logging.getLogger(__name__)


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


async def standort_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verarbeitet geteilten Standort – Reverse Geocoding für Adresse."""
    telegram_id = update.effective_user.id
    location = update.message.location

    if not location:
        return

    lat = location.latitude
    lon = location.longitude
    logger.info("📍 Standort empfangen von User %s: lat=%s, lon=%s", telegram_id, lat, lon)

    with get_session() as session:
        benutzer = session.query(Benutzer).filter_by(telegram_id=telegram_id).first()
        if not benutzer or not benutzer.aktives_projekt_id:
            await update.message.reply_text(
                "Kein aktives Projekt. Erstelle eins mit /projekt <Name>",
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        projekt = session.query(Projekt).get(benutzer.aktives_projekt_id)
        if not projekt:
            await update.message.reply_text(
                "Projekt nicht gefunden.",
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        projekt_name = projekt.name

        # Reverse Geocoding über OpenStreetMap Nominatim (kostenlos)
        try:
            resp = requests.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={
                    "lat": lat,
                    "lon": lon,
                    "format": "json",
                    "addressdetails": 1,
                    "accept-language": "de",
                },
                headers={"User-Agent": "Bautagebuch-Bot/1.0"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            addr = data.get("address", {})

            strasse = addr.get("road", "")
            hausnr = addr.get("house_number", "")
            plz = addr.get("postcode", "")
            ort = (
                addr.get("city")
                or addr.get("town")
                or addr.get("village")
                or addr.get("municipality", "")
            )

            teile = []
            if strasse:
                teile.append(f"{strasse} {hausnr}".strip())
            if plz or ort:
                teile.append(f"{plz} {ort}".strip())
            adresse_text = ", ".join(teile) if teile else data.get("display_name", "")
            logger.info("Geocoding OK: %s", adresse_text)
        except Exception as e:
            logger.error("Reverse Geocoding fehlgeschlagen: %s", e)
            adresse_text = f"{lat:.6f}, {lon:.6f}"

        # Adresse + Koordinaten speichern
        projekt.adresse = adresse_text
        projekt.latitude = lat
        projekt.longitude = lon

    await update.message.reply_text(
        f"✅ Adresse hinterlegt für \"{projekt_name}\":\n\n"
        f"📍 {adresse_text}\n"
        f"🗺️ Koordinaten: {lat:.6f}, {lon:.6f}",
        reply_markup=ReplyKeyboardRemove(),
    )
