# Instandhaltungsplanung – Telegram Bot 🔧

Intelligente Instandhaltungsplanung per Telegram. Erfasse Mängel & Reparaturen (Text, Fotos, Sprache), erhalte **automatische KI-Priorisierung** (🔴🟡🟢) mit **Kostenschätzung** und generiere professionelle PDF-Berichte auf Knopfdruck.

---

## Schnellstart

### 1. Voraussetzungen

- Python 3.10+
- Telegram-Account
- Telegram Bot Token (von [@BotFather](https://t.me/botfather))
- OpenAI API Key (für KI-Priorisierung & Kostenschätzung)

### 2. Installation

```bash
git clone https://github.com/chradden/bautagebuch.git
cd bautagebuch
pip install -r requirements.txt
```

### 3. Konfiguration

Erstelle eine `.env`-Datei im Projektverzeichnis:

```env
TELEGRAM_BOT_TOKEN=dein-bot-token-hier
OPENAI_API_KEY=sk-xxx
DATABASE_URL=sqlite:///bautagebuch.db
PDF_OUTPUT_DIR=./output
UPLOAD_DIR=./uploads

# Passwort-Schutz (empfohlen!)
BOT_PASSWORT=DeinBotPasswort
DASHBOARD_USER=admin
DASHBOARD_PASSWORT=DeinDashboardPasswort
```

> **Ohne `BOT_PASSWORT`** kann jeder, der den Bot auf Telegram findet, ihn nutzen.
> **Ohne `DASHBOARD_PASSWORT`** ist das Web-Dashboard offen zugänglich.
> Beide leer lassen = kein Schutz (nur für lokale Tests).

### 4. Bot + Dashboard starten

```bash
python3 run.py
```

Dies startet gleichzeitig:
- **Telegram Bot** (Polling)
- **Web-Dashboard** auf http://localhost:8080

Alternativ nur den Bot:
```bash
python3 -m bot.main
```

---

## Bedienungsanleitung

### Erste Schritte

1. **Bot finden:** Öffne Telegram und suche nach deinem Bot
2. **Registrieren:** Tippe `/start` und gib deinen Namen ein
3. **Objekt anlegen:** Tippe `/projekt Bürogebäude Schönhauser Allee 45`
4. **Fertig!** Melde Mängel & Reparaturen

### Befehle

| Befehl | Beschreibung |
|---|---|
| `/start` | Registrierung – nur beim ersten Mal nötig |
| `/projekt <Name>` | Neues Objekt/Projekt anlegen & aktivieren |
| `/wechsel` | Zwischen Objekten wechseln (Auswahl-Buttons) |
| `/status` | Aktives Objekt & heutige Meldungen anzeigen |
| `/bericht` | PDF-Instandhaltungsbericht für heute erstellen |
| `/bericht 21.09.2025` | Bericht für ein bestimmtes Datum |
| `/export` | CSV-Export aller Einträge |
| `/export 21.09.2025` | CSV-Export für ein bestimmtes Datum |
| `/hilfe` | Alle Befehle anzeigen |

### Mängel & Reparaturen melden

Einfach Nachrichten an den Bot senden – die **KI analysiert automatisch**:

**Textnachricht:**
> Wasserschaden im Kellergeschoss, Wand feucht, Putz blättert ab

→ 🛠️ Eintrag erfasst (14:23)
→ 🔴 Priorität: ROT
→ 📂 Kategorie: Mängelbeseitigung
→ 💰 Kosten: 2.000-5.000 €

**Foto mit Beschreibung:**
> 📷 [Foto vom Riss] + "Riss in Fassade, ca. 2m lang"

→ 📷 Foto erfasst – KI erkennt Schaden und priorisiert

**Sprachnachricht:**
> 🎙️ "Im dritten OG tropft es von der Decke, vermutlich Rohrbruch..."

→ Automatische Transkription + Kategorisierung + Priorisierung

### KI-Priorisierung

Jede Meldung wird automatisch bewertet:

| Priorität | Bedeutung | Beispiel |
|---|---|---|
| 🔴 **ROT** | Sofort handeln – Sicherheitsrisiko | Rohrbruch, Stromausfall, Einsturzgefahr |
| 🟡 **GELB** | Zeitnah beheben – Funktion beeinträchtigt | Defekte Heizung, undichtes Fenster |
| 🟢 **GRÜN** | Kann geplant werden – gering | Kratzer im Parkett, Farbe blättert |

### Kostenschätzung

Die KI schätzt automatisch die Reparaturkosten basierend auf der Beschreibung. Die Schätzung erscheint:
- Bei jedem Eintrag im Chat
- Zusammengefasst im PDF-Bericht

### Instandhaltungsbericht generieren

```
/bericht
```

→ Der Bot erstellt ein **professionelles PDF** mit:
- KI-Analyse sortiert nach Priorität (🔴 → 🟡 → 🟢)
- Farbige Prioritäts-Badges bei jedem Eintrag
- Durchgeführte Reparaturen
- Mängelübersicht mit Kostenschätzung
- Fotodokumentation
- Offene Punkte

### CSV-Export

```
/export
/export 21.09.2025
```

→ Exportiert alle Einträge als CSV-Datei (Semikolon-getrennt, Excel-kompatibel)

### Web-Dashboard

Erreichbar unter **http://localhost:8080** (wenn mit `python3 run.py` gestartet):

- **Objektübersicht** – Alle Projekte mit Statistiken
- **Projektdetails** – Einträge mit Kategorie-Badges, filtern nach Datum & Kategorie
- **PDF-Download** – Berichte direkt herunterladen
- **CSV-Export** – Einträge exportieren
- **Fotogalerie** – Alle Fotos inline anzeigen

### Tägliche Erinnerung

Um **18:00 Uhr** sendet der Bot automatisch eine Erinnerung:
- Hat der Benutzer heute Meldungen erfasst → Erinnerung an `/bericht`
- Keine Meldungen heute → Erinnerung an Dokumentation

---

## Beispiel-Workflow

```
Du:   /start
Bot:  Willkommen bei der Instandhaltungsplanung! 🔧
      Bitte gib deinen Namen ein:

Du:   Max Mustermann
Bot:  Hallo Max! ✅ Lege dein erstes Objekt an mit /projekt <Name>

Du:   /projekt Bürogebäude Schönhauser Allee 45
Bot:  ✅ Projekt "Bürogebäude Schönhauser Allee 45" angelegt.
      Die KI priorisiert automatisch (🔴🟡🟢) und schätzt Kosten.

Du:   Wasserschaden Kellergeschoss, Wand durchfeuchtet
Bot:  🛠️ Eintrag erfasst (08:15)
      🔴 Priorität: ROT
      📂 Kategorie: Mängelbeseitigung
      💰 Kosten: 3.000-8.000 €
      🚨 SOFORTIGER HANDLUNGSBEDARF!

Du:   [Foto vom Wasserschaden]
Bot:  📷 Foto erfasst (08:17)
      🤖 Feuchte Wand mit Putzablösungen, vermutlich aufsteigende Feuchtigkeit

Du:   Fenster in Raum 204 schließt nicht mehr richtig
Bot:  🔧 Eintrag erfasst (10:30)
      🟡 Priorität: GELB
      📂 Kategorie: Reparatur
      💰 Kosten: 150-400 €

Du:   Farbanstrich Flur 2. OG hat Kratzer
Bot:  🔧 Eintrag erfasst (11:00)
      🟢 Priorität: GRÜN
      📂 Kategorie: Wartung
      💰 Kosten: 200-500 €

Du:   /bericht
Bot:  📄 Instandhaltungsbericht wird erstellt... 🤖
Bot:  [PDF] Instandhaltungsbericht_Buerogebaeude_2026-02-18.pdf
```

---

## Projektstruktur

```
bautagebuch/
├── bot/
│   ├── main.py              # Telegram Bot starten
│   ├── keyboards.py         # Inline-Button Layouts
│   └── handlers/
│       ├── start.py         # /start – Registrierung
│       ├── projekt.py       # /projekt /wechsel /status /hilfe
│       ├── eintrag.py       # Text, Foto & Sprach-Verarbeitung + KI
│       ├── bericht.py       # /bericht → PDF mit KI-Analyse
│       ├── export.py        # /export → CSV-Datei
│       └── scheduler.py     # Tägliche Erinnerung (18:00)
├── web/
│   ├── app.py               # FastAPI Web-Dashboard
│   ├── templates/
│   │   ├── dashboard.html   # Objektübersicht
│   │   └── projekt.html     # Projektdetails & Einträge
│   └── static/
│       └── style.css        # Dashboard-Styling
├── core/
│   ├── ki.py                # OpenAI GPT (Priorisierung, Kosten, Vision, Whisper)
│   └── pdf.py               # WeasyPrint PDF-Erstellung
├── db/
│   ├── database.py          # SQLAlchemy Verbindung
│   └── models.py            # Datenmodell (Projekt, Eintrag, Foto, Bericht)
├── templates/
│   └── tagesbericht.html    # HTML/CSS Template für PDF
├── uploads/                 # Gespeicherte Fotos
├── output/                  # Generierte PDF-Berichte
├── config.py                # Konfiguration aus .env
├── run.py                   # Launcher: Bot + Dashboard gleichzeitig
├── Dockerfile               # Docker-Image für Deployment
├── docker-compose.yml       # Docker Compose Konfiguration
├── DEPLOYMENT.md            # Ausführliche VPS-Deployment-Anleitung
├── requirements.txt
├── .env                     # API Keys & Passwörter (nicht im Git!)
└── .gitignore
```

---

## Passwort-Schutz

### Telegram Bot
Setze `BOT_PASSWORT` in der `.env`. Neue Benutzer müssen beim `/start` das Passwort eingeben, bevor sie sich registrieren können. 3 Fehlversuche → Zugang gesperrt. Die Passwort-Nachricht wird automatisch gelöscht.

Bereits registrierte Benutzer sind nicht betroffen.

### Web-Dashboard
Setze `DASHBOARD_USER` und `DASHBOARD_PASSWORT` in der `.env`. Das Dashboard ist per HTTP Basic Auth geschützt – der Browser fragt automatisch nach Zugangsdaten.

---

## Deployment auf VPS

Siehe **[DEPLOYMENT.md](DEPLOYMENT.md)** für eine ausführliche Schritt-für-Schritt-Anleitung:
- Docker-Deployment (empfohlen)
- Direktes Deployment mit systemd
- Domain + HTTPS einrichten
- Firewall, Backups, Sicherheit
```

---

## Tech-Stack

| Komponente | Technologie |
|---|---|
| Bot-Interface | [python-telegram-bot](https://python-telegram-bot.org/) v21 |
| KI | OpenAI GPT-4o-mini (Priorisierung, Kosten) + Whisper (Sprache) |
| Web-Dashboard | FastAPI + Jinja2 + Uvicorn |
| Datenbank | SQLite + SQLAlchemy |
| PDF-Erstellung | WeasyPrint + Jinja2 Templates |

---

## Roadmap

- [x] **Phase 1:** Bot-Grundgerüst, Einträge, PDF-Berichte
- [x] **Phase 2:** KI-Priorisierung (🔴🟡🟢), Kostenschätzung, Whisper, Vision
- [x] **Phase 3:** Web-Dashboard, CSV-Export, Auto-Erinnerungen, Prioritäts-Farben im PDF
- [ ] **Phase 4:** Mehrbenutzer, Schnittstellen, Docker-Deployment

---

## Lizenz

MIT - oder?