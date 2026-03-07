# Instandhaltungsplanung – Umsetzungsplan

## 1. Überblick

Das System ermöglicht es **Bauleitern** und verantwortlichen Objektbetreuern, per **Telegram** Instandhaltungseinträge zu erfassen (Text, Sprachnachrichten, Fotos). Eine **KI** verarbeitet diese Eingaben und generiert automatisch professionelle **PDF-Tagesberichte**.

```
┌──────────────┐     ┌──────────────────┐     ┌───────────────────┐
│  Bauleiter   │     │   Backend-Server  │     │   PDF-Tagesbericht│
│  (Telegram)  │────▶│   + KI (OpenAI)   │────▶│   (automatisch)   │
│              │◀────│   + Datenbank      │     │                   │
│ Text/Fotos/  │     │   + PDF-Generator  │     │ Projekt: XYZ      │
│ Sprache      │     │                    │     │ Datum: 21.09.25   │
└──────────────┘     └──────────────────┘     └───────────────────┘
```

---

## 2. Tech-Stack

| Komponente        | Technologie                  | Begründung                                    |
|-------------------|------------------------------|-----------------------------------------------|
| **Bot-Interface** | Telegram Bot API (python-telegram-bot) | Kostenlos, gut dokumentiert, Datei-Upload einfach |
| **Backend**       | Python (FastAPI)             | Schnell, async-fähig, gute KI-Integration     |
| **KI**            | OpenAI GPT-4o / GPT-4o-mini | Textverarbeitung, Strukturierung, Zusammenfassung |
| **Sprache→Text**  | OpenAI Whisper API           | Sprachnachrichten transkribieren               |
| **Datenbank**     | SQLite → PostgreSQL          | Start einfach, später skalierbar               |
| **PDF-Generator** | WeasyPrint / ReportLab       | Professionelle PDF-Erstellung aus Templates    |
| **Dateispeicher** | Lokales Filesystem → S3      | Fotos/Dokumente speichern                      |
| **Hosting**       | Docker auf VPS (Hetzner)     | Günstig, DSGVO-konform (DE-Server)             |

---

## 3. Datenmodell

```sql
-- Projekte/Baustellen
CREATE TABLE projekte (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,           -- z.B. "Schönhauser Allee"
    adresse         TEXT,
    bauherr         TEXT,
    baubeginn       DATE,
    erstellt_am     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Benutzer (Bauleiter)
CREATE TABLE benutzer (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id     BIGINT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    rolle           TEXT DEFAULT 'bauleiter', -- bauleiter, polier, architekt
    aktives_projekt INTEGER REFERENCES projekte(id),
    erstellt_am     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Einzelne Einträge (Nachrichten)
CREATE TABLE eintraege (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    benutzer_id     INTEGER REFERENCES benutzer(id),
    projekt_id      INTEGER REFERENCES projekte(id),
    datum           DATE NOT NULL,
    uhrzeit         TIME NOT NULL,
    typ             TEXT NOT NULL,            -- 'text', 'foto', 'sprache'
    rohinhalt       TEXT,                     -- Original-Nachricht/Transkript
    ki_zusammenfassung TEXT,                  -- KI-strukturierter Text
    kategorie       TEXT,                     -- 'arbeit', 'material', 'mangel', 'wetter', 'personal'
    erstellt_am     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fotos zu Einträgen
CREATE TABLE fotos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    eintrag_id      INTEGER REFERENCES eintraege(id),
    dateipfad       TEXT NOT NULL,
    beschreibung    TEXT,                     -- KI-generierte Bildbeschreibung
    erstellt_am     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Generierte Tagesberichte
CREATE TABLE tagesberichte (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    projekt_id      INTEGER REFERENCES projekte(id),
    datum           DATE NOT NULL,
    pdf_pfad        TEXT,
    erstellt_am     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(projekt_id, datum)
);

-- Wetterdaten (automatisch abgerufen)
CREATE TABLE wetter (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    projekt_id      INTEGER REFERENCES projekte(id),
    datum           DATE NOT NULL,
    temperatur_min  REAL,
    temperatur_max  REAL,
    niederschlag    TEXT,                     -- 'keiner', 'regen', 'schnee'
    wind            TEXT,
    bedingungen     TEXT,                     -- 'sonnig', 'bewölkt', etc.
    UNIQUE(projekt_id, datum)
);
```

---

## 4. Telegram-Bot: Befehle & Interaktion

### 4.1 Befehle

| Befehl              | Beschreibung                                      |
|----------------------|--------------------------------------------------|
| `/start`             | Registrierung & Willkommensnachricht              |
| `/projekt <name>`    | Neues Projekt anlegen                             |
| `/wechsel`           | Aktives Projekt wechseln (Inline-Buttons)         |
| `/bericht`           | Tagesbericht für heute generieren & als PDF senden|
| `/bericht <datum>`   | Bericht für bestimmtes Datum generieren           |
| `/status`            | Zeigt aktives Projekt & heutige Einträge          |
| `/hilfe`             | Befehlsübersicht                                  |

### 4.2 Nachrichten-Verarbeitung (ohne Befehl)

Jede normale Nachricht wird als Instandhaltungseintrag erfasst:

- **Textnachricht** → Direkt als Eintrag speichern + KI-Kategorisierung
- **Foto(s)** → Speichern + KI-Bildbeschreibung + optionaler Begleittext
- **Sprachnachricht** → Whisper-Transkription → als Text-Eintrag speichern
- **Dokument (PDF)** → Speichern als Anhang zum Tagesbericht

### 4.3 Beispiel-Dialog

```
Bauleiter: /start
Bot:       Willkommen bei der Instandhaltungsplanung! 🔧
           Bitte geben Sie Ihren Namen ein.

Bauleiter: Max Mustermann
Bot:       Hallo Max! Legen Sie Ihr erstes Projekt an mit /projekt <Name>

Bauleiter: /projekt Schönhauser Allee 45
Bot:       ✅ Projekt "Schönhauser Allee 45" angelegt und aktiviert.

Bauleiter: Heute mit Fundamentierung begonnen.
           Beton C25/30 geliefert, 12m³.
Bot:       ✅ Eintrag erfasst (Kategorie: Arbeit/Material)

Bauleiter: [9 Fotos vom Fundament]
Bot:       ✅ 9 Fotos gespeichert & beschrieben.

Bauleiter: [Sprachnachricht: "Die Risse im Fundament wurden kontrolliert,
           alles im Rahmen, keine Nachbesserung nötig."]
Bot:       ✅ Sprachnachricht transkribiert & erfasst (Kategorie: Kontrolle)

Bauleiter: /bericht
Bot:       📄 Tagesbericht wird erstellt...
           [PDF: Tagesbericht_Schoenhauser_Allee_21.09.2025.pdf]
```

---

## 5. KI-Verarbeitung

### 5.1 Eingangs-Klassifizierung (bei jeder Nachricht)

```python
SYSTEM_PROMPT = """
Du bist ein Assistent für Instandhaltungsplanung. Klassifiziere und strukturiere
den folgenden Baustelleneintrag.

Gib zurück als JSON:
{
  "kategorie": "arbeit|material|mangel|wetter|personal|kontrolle|sonstiges",
  "zusammenfassung": "Kurze, professionelle Zusammenfassung",
  "stichworte": ["Stichwort1", "Stichwort2"],
  "handlungsbedarf": true/false,
  "handlung": "Beschreibung falls nötig"
}
"""
```

### 5.2 Tagesbericht-Generierung

```python
BERICHT_PROMPT = """
Erstelle aus den folgenden Instandhaltungseinträgen einen professionellen
Tagesbericht nach VOB-Standard. Strukturiere nach:

1. Allgemeine Angaben (Projekt, Datum, Wetter)
2. Arbeitskräfte & Geräte
3. Ausgeführte Arbeiten
4. Besondere Vorkommnisse / Mängel
5. Materiallieferungen
6. Anweisungen / Offene Punkte
7. Fotos & Dokumentation

Einträge: {eintraege}
Wetter: {wetter}
"""
```

### 5.3 Bild-Analyse

- GPT-4o Vision analysiert Fotos und generiert Beschreibungen
- Erkennung von: Baufortschritt, Mängeln, Materialien, Sicherheitsaspekten

---

## 6. PDF-Tagesbericht

### 6.1 Template-Struktur

```
┌─────────────────────────────────────┐
│          TAGESBERICHT               │
│    Projekt: Schönhauser Allee 45    │
│    Datum: 21.09.2025                │
│    Bauleiter: Max Mustermann        │
├─────────────────────────────────────┤
│ WETTER                              │
│ Temperatur: 14°C - 19°C            │
│ Bedingungen: Bewölkt, trocken       │
├─────────────────────────────────────┤
│ AUSGEFÜHRTE ARBEITEN                │
│ • Fundamentierung begonnen          │
│ • Beton C25/30 geliefert (12m³)    │
│ • Risse im Fundament kontrolliert   │
│   → Im Rahmen, keine Nachbesserung  │
├─────────────────────────────────────┤
│ MATERIALLIEFERUNGEN                 │
│ • Beton C25/30: 12m³               │
├─────────────────────────────────────┤
│ FOTODOKUMENTATION                   │
│ [Foto 1] [Foto 2] [Foto 3]        │
│ Fundamentarbeiten Ostseite          │
├─────────────────────────────────────┤
│ OFFENE PUNKTE                       │
│ • Steindicke klären                 │
├─────────────────────────────────────┤
│ Unterschrift: ________________      │
└─────────────────────────────────────┘
```

---

## 7. Projektstruktur

```
bautagebuch/
├── bot/
│   ├── __init__.py
│   ├── main.py              # Bot-Start & Handler-Registrierung
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py         # /start, Registrierung
│   │   ├── projekt.py       # /projekt, /wechsel
│   │   ├── eintrag.py       # Text/Foto/Sprach-Verarbeitung
│   │   └── bericht.py       # /bericht → PDF generieren
│   └── keyboards.py         # Inline-Buttons & Menüs
├── core/
│   ├── __init__.py
│   ├── ki.py                # OpenAI API-Calls (GPT + Whisper)
│   ├── pdf.py               # PDF-Generierung (WeasyPrint)
│   ├── wetter.py            # Wetter-API Abfrage
│   └── models.py            # SQLAlchemy/Pydantic Models
├── db/
│   ├── __init__.py
│   ├── database.py          # DB-Verbindung & Session
│   └── migrations/          # Alembic Migrations
├── templates/
│   ├── tagesbericht.html    # HTML-Template für PDF
│   └── style.css            # PDF-Styling
├── uploads/                 # Fotos & Dokumente
├── output/                  # Generierte PDFs
├── config.py                # Konfiguration & Env-Vars
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 8. Umsetzungsplan (Phasen)

### Phase 1: MVP (1-2 Wochen)
- [x] Projektplanung & Schema
- [ ] Telegram-Bot Grundgerüst (`/start`, `/hilfe`)
- [ ] SQLite-Datenbank aufsetzen
- [ ] Text-Einträge erfassen & speichern
- [ ] Einfache PDF-Generierung (ohne KI)
- [ ] `/bericht` Befehl → PDF im Chat

### Phase 2: KI-Integration (1-2 Wochen)
- [ ] OpenAI GPT Integration für Kategorisierung
- [ ] Sprachnachrichten → Whisper Transkription
- [ ] Foto-Upload & Speicherung
- [ ] KI-generierte Tagesberichte
- [ ] GPT-4o Vision für Bildbeschreibungen

### Phase 3: Professionalisierung (1-2 Wochen)
- [ ] Professionelles PDF-Template (VOB-konform)
- [ ] Automatischer Wetter-Abruf (OpenWeatherMap)
- [ ] Mehrere Projekte pro Benutzer
- [ ] Projekt-Wechsel via Inline-Buttons
- [ ] Tägliche automatische Bericht-Erinnerung (18:00)

### Phase 4: Erweiterungen (optional)
- [ ] Web-Dashboard zur Übersicht aller Berichte
- [ ] Mehrbenutzer pro Projekt (Polier, Architekt)
- [ ] PostgreSQL Migration für Produktion
- [ ] Foto-Galerie im Web-Dashboard
- [ ] Export: Gesamte Instandhaltungsdokumentation als PDF-Sammelband
- [ ] Schnittstelle zu Bauprojekt-Software (z.B. PlanRadar)

---

## 9. Konfiguration & Secrets

```env
# .env
TELEGRAM_BOT_TOKEN=xxx          # von @BotFather
OPENAI_API_KEY=sk-xxx           # OpenAI API Key
WEATHER_API_KEY=xxx             # OpenWeatherMap (kostenlos)
DATABASE_URL=sqlite:///bautagebuch.db
PDF_OUTPUT_DIR=./output
UPLOAD_DIR=./uploads
```

---

## 10. Kosten-Schätzung (monatlich)

| Posten                      | Kosten/Monat     |
|-----------------------------|------------------|
| Telegram Bot API            | **kostenlos**    |
| Hetzner VPS (CX22)         | ~€4,50           |
| OpenAI API (GPT-4o-mini)   | ~€5-15*          |
| OpenAI Whisper              | ~€2-5*           |
| OpenWeatherMap              | **kostenlos**    |
| **Gesamt**                  | **~€12-25**      |

*Abhängig von Nutzung (geschätzt: 50 Einträge/Tag, 1 Bericht/Tag)

---

## 11. Vorteile gegenüber WhatsApp

| Kriterium              | Telegram              | WhatsApp                      |
|------------------------|-----------------------|-------------------------------|
| Bot-API                | Kostenlos, offen      | Business API: €€€/Monat       |
| Einrichtung            | 5 Minuten (@BotFather)| Langwieriger Verifizierungsprozess |
| Datei-Upload           | Bis 2GB               | 16MB Limit                    |
| DSGVO                  | Gut handhabbar        | Problematisch (Meta)          |
| Gruppenintegration     | Einfach               | Eingeschränkt                 |
| Kosten                 | €0                    | Ab €50+/Monat                 |

---

## Nächster Schritt

Soll ich mit **Phase 1 (MVP)** beginnen? Dafür benötige ich:
1. Einen **Telegram Bot Token** (erstellen via [@BotFather](https://t.me/botfather))
2. Einen **OpenAI API Key** (für Phase 2)
