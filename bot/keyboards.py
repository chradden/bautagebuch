"""Keyboard-Layouts für Inline-Buttons."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def projekt_auswahl_keyboard(projekte):
    """Erstellt Inline-Buttons zur Projektauswahl."""
    buttons = [
        [InlineKeyboardButton(p.name, callback_data=f"projekt_{p.id}")]
        for p in projekte
    ]
    return InlineKeyboardMarkup(buttons)
