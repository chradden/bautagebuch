"""KI-Modul – OpenAI GPT & Whisper Integration für Instandhaltungsplanung."""
import json
import base64
import logging
from openai import OpenAI

import config

logger = logging.getLogger(__name__)

client = OpenAI(api_key=config.OPENAI_API_KEY)

# ─── Eintrag kategorisieren & bewerten ────────────────────────────────────

KATEGORISIERUNG_PROMPT = """Du bist ein KI-Assistent für Instandhaltungsplanung. Analysiere die folgende Meldung und bewerte sie.

Antworte NUR mit validem JSON (kein Markdown, kein ```):
{
  "kategorie": "reparatur|maengelbeseitigung|wartung|pruefung|sicherheit|sonstiges",
  "prioritaet": "rot|gelb|gruen",
  "zusammenfassung": "Kurze, professionelle Zusammenfassung in einem Satz",
  "kostenschaetzung": "Geschätzte Kosten als Text, z.B. '500-1.000 €' oder 'gering' wenn unklar",
  "handlungsbedarf": false
}

Kategorien:
- reparatur: Reparaturarbeiten, Instandsetzung
- maengelbeseitigung: Beseitigung von Mängeln, Schäden
- wartung: Regelmäßige Wartung, Inspektion
- pruefung: Prüfungen, Abnahmen, Kontrollen
- sicherheit: Sicherheitsmängel, Gefahren
- sonstiges: Alles andere

Priorisierung:
- rot: Sofort handeln – Sicherheitsrisiko, Gefahr, schwerer Mangel
- gelb: Zeitnah handeln – Mangel beeinträchtigt Funktion, sollte bald behoben werden
- gruen: Kann geplant werden – kosmetisch, geringer Mangel, Routinewartung

Kostenschätzung:
- Schätze die Kosten realistisch basierend auf dem Aufwand
- Bei unklaren Angaben: 'nicht einschätzbar'"""


def kategorisiere_eintrag(text: str) -> dict:
    """Kategorisiert und priorisiert einen Instandhaltungs-Eintrag per GPT."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": KATEGORISIERUNG_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0.1,
            max_tokens=300,
        )
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        logger.error(f"KI-Kategorisierung fehlgeschlagen: {e}")
        return {
            "kategorie": "sonstiges",
            "prioritaet": "gelb",
            "zusammenfassung": text[:100],
            "kostenschaetzung": "nicht einschätzbar",
            "handlungsbedarf": False,
        }


# ─── Sprachnachricht transkribieren ──────────────────────────────────────

def transkribiere_audio(dateipfad: str) -> str:
    """Transkribiert eine Audiodatei per Whisper."""
    try:
        with open(dateipfad, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="de",
            )
        return response.text
    except Exception as e:
        logger.error(f"Whisper-Transkription fehlgeschlagen: {e}")
        return ""


# ─── Foto beschreiben (Vision) ───────────────────────────────────────────

VISION_PROMPT = """Du bist ein Experte für Gebäude-Instandhaltung. Analysiere dieses Foto in 1-2 Sätzen.
Konzentriere dich auf: Erkennbare Mängel, Schäden, Reparaturbedarf, Sicherheitsaspekte, Zustand von Bauteilen.
Bewerte kurz die Dringlichkeit (hoch/mittel/gering).
Antworte auf Deutsch, kurz und sachlich."""


def beschreibe_foto(dateipfad: str) -> str:
    """Beschreibt ein Baufoto per GPT-4o Vision."""
    try:
        with open(dateipfad, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": VISION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}",
                                "detail": "low",
                            },
                        },
                    ],
                }
            ],
            max_tokens=150,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Vision-Beschreibung fehlgeschlagen: {e}")
        return ""


# ─── Tagesbericht generieren ─────────────────────────────────────────────

BERICHT_PROMPT = """Du bist ein professioneller Assistent für Instandhaltungsplanung. Erstelle aus den folgenden {anzahl} Einträgen einen strukturierten Instandhaltungsbericht.

ALLE {anzahl} Einträge (Nr. 1 bis Nr. {anzahl}) MÜSSEN jeweils als eigene Tabellenzeile erscheinen. KEINEN Eintrag auslassen oder zusammenfassen!

Strukturiere den Bericht in diese Abschnitte (nur wenn passende Daten vorhanden):
1. **🔴 Sofortmaßnahmen (Priorität ROT)** – Sicherheitsrelevant, sofort handeln
2. **🟡 Zeitnaher Handlungsbedarf (Priorität GELB)** – Bald beheben
3. **🟢 Geplante Maßnahmen (Priorität GRÜN)** – Kann eingeplant werden

WICHTIG – AUSGABEFORMAT: Jeder Abschnitt MUSS eine Markdown-Tabelle enthalten mit EXAKT diesen 4 Spalten:

| Eintrag | Details | Bild | Bildbeschreibung |
|---------|---------|------|-----------------|
| Nr. X - Kurztitel | Zustand: ... **Problem:** ... **Maßnahme:** ... **Dringlichkeit:** ... **Kostenschätzung:** ... | | |

Regeln:
- ALLE {anzahl} Einträge MÜSSEN vorkommen – jeder als eigene Tabellenzeile
- Schreibe in professionellem, sachlichem Stil
- Die Spalten "Bild" und "Bildbeschreibung" bleiben IMMER leer (werden automatisch befüllt)
- "Nr. X" MUSS die Originalentragnummer aus den Eingabedaten sein (z.B. Nr. 1, Nr. 2)
- Keine leeren Tabellenzeilen. Kein Abschnitt ohne Einträge.
- Behalte wichtige Details (Maße, Materialien, Ortsangaben)
- Verwende EXAKT die Kostenschätzungen aus den Einträgen – erfinde keine eigenen Zahlen
- Erfinde KEINE Informationen – nur was in den Einträgen steht
- Antworte auf Deutsch
- KRITISCH: Jede Tabellenzeile MUSS vollständig auf EINER einzigen Zeile stehen. Kein Zeilenumbruch innerhalb einer Tabellenzelle.

Nach den Tabellen: Füge einen Abschnitt **## Empfehlungen** mit konkreten nächsten Schritten als Aufzählung hinzu.

Einträge des Tages:
{eintraege}"""


def generiere_bericht_text(eintraege: list[dict]) -> str:
    """Generiert einen strukturierten Berichtstext aus Einträgen per GPT."""
    eintraege_text = ""
    for i, e in enumerate(eintraege, 1):
        typ = e.get("typ", "text")
        inhalt = e.get("rohinhalt", "")
        kategorie = e.get("kategorie", "")
        prio = e.get("prioritaet", "")
        kosten = e.get("kostenschaetzung", "")
        foto_beschreibungen = e.get("foto_beschreibungen", [])

        eintraege_text += f"[Nr. {i}] ({typ}, {kategorie}, Priorität: {prio})"
        if kosten:
            eintraege_text += f" [Kostenschätzung: {kosten}]"
        eintraege_text += f" {inhalt}\n"
        for fb in foto_beschreibungen:
            eintraege_text += f"  → Foto: {fb}\n"

    try:
        n = len(eintraege)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": BERICHT_PROMPT.format(
                        eintraege=eintraege_text,
                        anzahl=n,
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=3000,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"KI-Berichtserstellung fehlgeschlagen: {e}")
        return ""
