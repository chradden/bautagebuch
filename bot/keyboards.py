"""Keyboard-Layouts für Inline-Buttons."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def projekt_auswahl_keyboard(projekte):
    """Erstellt Inline-Buttons zur Projektauswahl."""
    buttons = [
        [InlineKeyboardButton(p.name, callback_data=f"projekt_{p.id}")]
        for p in projekte
    ]
    return InlineKeyboardMarkup(buttons)


def standort_keyboard():
    """Erstellt ein Reply-Keyboard mit Standort-Teilen-Button."""
    button = KeyboardButton("📍 Standort teilen", request_location=True)
    return ReplyKeyboardMarkup(
        [[button]],
        one_time_keyboard=True,
        resize_keyboard=True,
    )
