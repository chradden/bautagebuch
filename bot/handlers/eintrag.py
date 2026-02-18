"""Handler für Text-, Foto- und Sprachnachrichten-Einträge."""
import os
import logging
from datetime import date, datetime
from telegram import Update
from telegram.ext import ContextTypes

import config
from db.database import get_session
from db.models import Benutzer, Eintrag, Foto
from core.ki import kategorisiere_eintrag, transkribiere_audio, beschreibe_foto

logger = logging.getLogger(__name__)

KATEGORIE_EMOJI = {
    "reparatur": "🔧",
    "maengelbeseitigung": "🛠️",
    "wartung": "🔩",
    "pruefung": "🔍",
    "sicherheit": "🚨",
    "sonstiges": "📝",
}

PRIORITAET_EMOJI = {
    "rot": "🔴",
    "gelb": "🟡",
    "gruen": "🟢",
}


async def text_eintrag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verarbeitet eingehende Textnachrichten als Bautagebuch-Eintrag."""
    telegram_id = update.effective_user.id
    text = update.message.text

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

        # KI-Kategorisierung
        ki_result = kategorisiere_eintrag(text)

        jetzt = datetime.now()
        eintrag = Eintrag(
            benutzer_id=benutzer.id,
            projekt_id=benutzer.aktives_projekt_id,
            datum=jetzt.date(),
            uhrzeit=jetzt.time(),
            typ="text",
            rohinhalt=text,
            kategorie=ki_result.get("kategorie", "sonstiges"),
            ki_zusammenfassung=ki_result.get("zusammenfassung", ""),
            prioritaet=ki_result.get("prioritaet", "gelb"),
            kostenschaetzung=ki_result.get("kostenschaetzung", ""),
        )
        session.add(eintrag)

    kat = ki_result.get("kategorie", "sonstiges")
    prio = ki_result.get("prioritaet", "gelb")
    kosten = ki_result.get("kostenschaetzung", "")
    kat_emoji = KATEGORIE_EMOJI.get(kat, "📝")
    prio_emoji = PRIORITAET_EMOJI.get(prio, "🟡")

    antwort = f"{kat_emoji} Eintrag erfasst ({jetzt.strftime('%H:%M')})"
    antwort += f"\n{prio_emoji} Priorität: {prio.upper()}"
    antwort += f"\n📂 Kategorie: {kat.replace('ae', 'ä').title()}"
    if kosten:
        antwort += f"\n💰 Kosten: {kosten}"
    if ki_result.get("handlungsbedarf") or prio == "rot":
        antwort += "\n\n🚨 SOFORTIGER HANDLUNGSBEDARF!"
    await update.message.reply_text(antwort)


async def foto_eintrag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verarbeitet eingehende Fotos als Bautagebuch-Eintrag."""
    telegram_id = update.effective_user.id

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

        jetzt = datetime.now()
        caption = update.message.caption or ""
        projekt_id = benutzer.aktives_projekt_id
        benutzer_id = benutzer.id

        eintrag = Eintrag(
            benutzer_id=benutzer_id,
            projekt_id=projekt_id,
            datum=jetzt.date(),
            uhrzeit=jetzt.time(),
            typ="foto",
            rohinhalt=caption,
        )
        session.add(eintrag)
        session.flush()
        eintrag_id = eintrag.id

        # Foto herunterladen
        photo = update.message.photo[-1]  # Höchste Auflösung
        file = await photo.get_file()

        projekt_dir = os.path.join(
            config.UPLOAD_DIR,
            str(projekt_id),
            jetzt.strftime("%Y-%m-%d"),
        )
        os.makedirs(projekt_dir, exist_ok=True)

        dateipfad = os.path.join(
            projekt_dir,
            f"{eintrag_id}_{jetzt.strftime('%H%M%S')}.jpg",
        )
        await file.download_to_drive(dateipfad)

        # KI-Bildbeschreibung
        beschreibung = beschreibe_foto(dateipfad)

        foto_obj = Foto(
            eintrag_id=eintrag_id,
            dateipfad=dateipfad,
            beschreibung=beschreibung,
        )
        session.add(foto_obj)

        # Auch den Eintrag mit KI anreichern
        if caption:
            ki_result = kategorisiere_eintrag(caption)
            eintrag.kategorie = ki_result.get("kategorie", "sonstiges")
            eintrag.ki_zusammenfassung = ki_result.get("zusammenfassung", "")
            eintrag.prioritaet = ki_result.get("prioritaet", "gelb")
            eintrag.kostenschaetzung = ki_result.get("kostenschaetzung", "")

    antwort = f"📷 Foto erfasst ({jetzt.strftime('%H:%M')})"
    if beschreibung:
        antwort += f"\n🤖 {beschreibung[:150]}"
    await update.message.reply_text(antwort)


async def sprach_eintrag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verarbeitet Sprachnachrichten – transkribiert per Whisper."""
    telegram_id = update.effective_user.id

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

        jetzt = datetime.now()
        projekt_id = benutzer.aktives_projekt_id
        benutzer_id = benutzer.id

        # Sprachnachricht herunterladen
        voice = update.message.voice
        file = await voice.get_file()

        voice_dir = os.path.join(config.UPLOAD_DIR, "voice")
        os.makedirs(voice_dir, exist_ok=True)
        voice_path = os.path.join(voice_dir, f"{telegram_id}_{jetzt.strftime('%Y%m%d_%H%M%S')}.ogg")
        await file.download_to_drive(voice_path)

        # Whisper-Transkription
        transkript = transkribiere_audio(voice_path)

        if not transkript:
            await update.message.reply_text("❌ Sprachnachricht konnte nicht transkribiert werden.")
            return

        # KI-Kategorisierung des Transkripts
        ki_result = kategorisiere_eintrag(transkript)

        eintrag = Eintrag(
            benutzer_id=benutzer_id,
            projekt_id=projekt_id,
            datum=jetzt.date(),
            uhrzeit=jetzt.time(),
            typ="sprache",
            rohinhalt=transkript,
            kategorie=ki_result.get("kategorie", "sonstiges"),
            ki_zusammenfassung=ki_result.get("zusammenfassung", ""),
            prioritaet=ki_result.get("prioritaet", "gelb"),
            kostenschaetzung=ki_result.get("kostenschaetzung", ""),
        )
        session.add(eintrag)

    kat = ki_result.get("kategorie", "sonstiges")
    prio = ki_result.get("prioritaet", "gelb")
    kosten = ki_result.get("kostenschaetzung", "")
    kat_emoji = KATEGORIE_EMOJI.get(kat, "📝")
    prio_emoji = PRIORITAET_EMOJI.get(prio, "🟡")

    antwort = (
        f"🎙️ Sprachnachricht transkribiert ({jetzt.strftime('%H:%M')})\n\n"
        f"📝 \"{transkript[:300]}\"\n\n"
        f"{kat_emoji} {kat.replace('ae', 'ä').title()}\n"
        f"{prio_emoji} Priorität: {prio.upper()}"
    )
    if kosten:
        antwort += f"\n💰 Kosten: {kosten}"
    if ki_result.get("handlungsbedarf") or prio == "rot":
        antwort += "\n\n🚨 SOFORTIGER HANDLUNGSBEDARF!"
    await update.message.reply_text(antwort)
