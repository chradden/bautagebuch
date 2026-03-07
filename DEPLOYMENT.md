# Deployment auf Hostinger VPS – Schritt für Schritt

## Übersicht

Hinweis: Das Repository und die Server-Pfade heißen aus historischen Gründen weiterhin `bautagebuch`. Die fachliche Anwendung ist jedoch die Instandhaltungsplanung.

Diese Anleitung erklärt, wie du die Instandhaltungsplanung-App auf einem **Hostinger VPS** installierst. Am Ende läuft:
- **Telegram Bot** – 24/7, reagiert auf Nachrichten
- **Web-Dashboard** – erreichbar über `http://deine-ip:8093` (oder über Domain)

---

## Voraussetzungen

### Was du brauchst:
1. **Hostinger VPS** (KVM 1 oder höher reicht aus – ab ~5€/Monat)
   - Empfohlen: **Ubuntu 22.04 oder 24.04**
   - Mindestens 1 GB RAM, 20 GB SSD
2. **SSH-Zugang** zum VPS (Zugangsdaten bekommst du im Hostinger Panel)
3. **Domain** (optional, aber empfohlen) – z.B. `instandhaltung.deine-domain.de`

### Was du schon haben solltest:
- Telegram Bot Token (von @BotFather)
- OpenAI API Key (von platform.openai.com)
- Die Passwörter aus deiner `.env`-Datei

---

## Methode 1: Mit Docker (empfohlen) 🐳

### Schritt 1: Per SSH auf den VPS verbinden

```bash
ssh root@DEINE-VPS-IP
```

Die IP findest du im Hostinger Panel unter **VPS → Überblick**.

### Schritt 2: Docker installieren

```bash
# Docker installieren (ein Befehl)
curl -fsSL https://get.docker.com | sh

# Docker Compose ist seit Docker 24+ enthalten, prüfen:
docker compose version
```

### Schritt 3: Repository klonen

```bash
cd /opt
git clone https://github.com/chradden/bautagebuch.git
cd bautagebuch
```

### Schritt 4: .env-Datei erstellen

```bash
nano .env
```

Folgenden Inhalt einfügen (deine echten Werte einsetzen!):

```env
TELEGRAM_BOT_TOKEN=dein-bot-token-hier
OPENAI_API_KEY=sk-dein-key-hier

# Passwort-Schutz
BOT_PASSWORT=DeinSicheresPasswort
DASHBOARD_USER=admin
DASHBOARD_PASSWORT=DeinDashboardPasswort
```

Speichern: `Ctrl+O`, dann `Enter`, dann `Ctrl+X`

### Schritt 5: Daten-Verzeichnis erstellen

```bash
mkdir -p data
```

### Schritt 6: App starten

```bash
docker compose up -d --build
```

Das war's! 🎉

### Prüfen ob alles läuft:

```bash
# Container-Status
docker compose ps

# Logs ansehen
docker compose logs -f

# Nur die letzten 50 Zeilen
docker compose logs --tail 50
```

### Web-Dashboard öffnen:

```
http://DEINE-VPS-IP:8093
```

Login mit den Zugangsdaten aus der `.env` (`admin` / `DeinDashboardPasswort`).

### Updates einspielen:

```bash
cd /opt/bautagebuch
./deploy.sh
```

Oder manuell:

```bash
git pull origin main
docker compose up -d --build
```

### App stoppen:

```bash
docker compose down
```

---

## Auto-Deployment: Codespace → GitHub → VPS 🚀

Jeder `git push` auf `main` aus dem Codespace löst automatisch ein Deployment auf dem VPS aus. Der GitHub Actions Workflow [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) verbindet sich per SSH auf den VPS und führt `deploy.sh` aus.

### Einmalige Einrichtung (GitHub Secrets)

Im GitHub Repository unter **Settings → Secrets and variables → Actions** folgende Secrets anlegen:

| Secret | Inhalt |
|--------|--------|
| `VPS_HOST` | IP-Adresse oder Domain des VPS |
| `VPS_USER` | SSH-Benutzer (z.B. `root`) |
| `VPS_SSH_KEY` | Privater SSH-Key (Inhalt von `~/.ssh/id_rsa`) |
| `VPS_PROJECT_PATH` | Pfad zum Projektverzeichnis (z.B. `/opt/bautagebuch`) |

### SSH-Key für GitHub Actions erstellen

Auf dem VPS einmalig ausführen:

```bash
# Neues Key-Paar für GitHub Actions erstellen
ssh-keygen -t ed25519 -C "github-actions-bautagebuch" -f ~/.ssh/github_actions -N ""

# Public Key bei authorized_keys hinterlegen
cat ~/.ssh/github_actions.pub >> ~/.ssh/authorized_keys

# Private Key anzeigen → Inhalt als VPS_SSH_KEY Secret eintragen
cat ~/.ssh/github_actions
```

### Ablauf nach einem Push

```
git push origin main
       │
       ▼
GitHub Actions (.github/workflows/deploy.yml)
       │
       ▼ SSH
VPS: git pull origin main
     docker compose down
     docker compose build --no-cache
     docker compose up -d --force-recreate
     docker image prune -f
       │
       ▼
✅ Neue Version läuft auf dem VPS
```

---

## Methode 2: Ohne Docker (direkt auf dem VPS)

### Schritt 1: Per SSH verbinden

```bash
ssh root@DEINE-VPS-IP
```

### Schritt 2: System-Pakete installieren

```bash
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv git \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
    libffi-dev shared-mime-info
```

### Schritt 3: Repository klonen

```bash
cd /opt
git clone https://github.com/chradden/bautagebuch.git
cd bautagebuch
```

### Schritt 4: Python Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install "python-telegram-bot[job-queue]"
```

### Schritt 5: .env erstellen

```bash
nano .env
```

(Gleicher Inhalt wie bei Methode 1 – siehe oben)

### Schritt 6: Teststart

```bash
python3 run.py
```

Wenn alles läuft (keine Fehler), mit `Ctrl+C` stoppen.

### Schritt 7: Als systemd-Service einrichten (damit es nach Neustart automatisch läuft)

```bash
nano /etc/systemd/system/instandhaltung.service
```

Inhalt:

```ini
[Unit]
Description=Instandhaltungsplanung Bot + Dashboard
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/bautagebuch
Environment=PATH=/opt/bautagebuch/.venv/bin:/usr/bin
ExecStart=/opt/bautagebuch/.venv/bin/python3 run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Service aktivieren:

```bash
systemctl daemon-reload
systemctl enable instandhaltung
systemctl start instandhaltung
```

### Prüfen:

```bash
# Status
systemctl status instandhaltung

# Logs live
journalctl -u instandhaltung -f

# Neustarten nach Updates
systemctl restart instandhaltung
```

---

## Firewall konfigurieren

Hostinger blockiert standardmäßig alle Ports außer 22 (SSH). Du musst Port 8093 freigeben:

### Im Hostinger Panel:
1. Gehe zu **VPS → Einstellungen → Firewall**
2. Füge eine Regel hinzu: **Port 8093, TCP, erlauben**

### Oder per SSH:

```bash
ufw allow 8093/tcp
ufw allow 22/tcp
ufw enable
```

---

## Domain einrichten (optional aber empfohlen)

Wenn du eine Domain hast (z.B. bei Hostinger), kannst du sie auf das Dashboard zeigen lassen:

### Schritt 1: DNS-Eintrag setzen

Im Hostinger DNS-Panel:
- **Typ:** A
- **Name:** `instandhaltung` (oder was du willst)
- **Wert:** Deine VPS-IP
- **TTL:** 14400

→ Ergibt: `instandhaltung.deine-domain.de`

### Schritt 2: Nginx als Reverse Proxy (für Port 80/443)

```bash
apt install -y nginx certbot python3-certbot-nginx
```

Nginx-Config erstellen:

```bash
nano /etc/nginx/sites-available/instandhaltung
```

```nginx
server {
    listen 80;
    server_name instandhaltung.deine-domain.de;

    location / {
        proxy_pass http://127.0.0.1:8093;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Aktivieren:

```bash
ln -s /etc/nginx/sites-available/instandhaltung /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

### Schritt 3: SSL-Zertifikat (HTTPS) – kostenlos mit Let's Encrypt

```bash
certbot --nginx -d instandhaltung.deine-domain.de
```

→ Jetzt erreichbar über `https://instandhaltung.deine-domain.de` 🔒

---

## Sicherheits-Checkliste ✅

- [x] **BOT_PASSWORT** in `.env` gesetzt → Nur mit Passwort kann man den Bot nutzen
- [x] **DASHBOARD_PASSWORT** in `.env` gesetzt → Web-Dashboard per HTTP Basic Auth geschützt
- [ ] **SSH-Key** statt Passwort verwenden (Hostinger Panel → SSH-Keys)
- [ ] **Firewall** konfiguriert (nur Ports 22, 80, 443, 8093)
- [ ] **HTTPS** eingerichtet (mit Let's Encrypt / Certbot)
- [ ] **Regelmäßige Backups** der Datenbank (`data/bautagebuch.db`)

### Backup-Script (optional):

```bash
# Erstelle ein tägliches Backup
nano /opt/bautagebuch/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR=/opt/backups/bautagebuch
mkdir -p $BACKUP_DIR
DATE=$(date +%Y-%m-%d_%H%M)
cp /opt/bautagebuch/data/bautagebuch.db "$BACKUP_DIR/bautagebuch_$DATE.db"
# Alte Backups löschen (älter als 30 Tage)
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
echo "Backup erstellt: bautagebuch_$DATE.db"
```

```bash
chmod +x /opt/bautagebuch/backup.sh

# Tägliches Backup um 02:00 Uhr
crontab -e
# Folgende Zeile hinzufügen:
# 0 2 * * * /opt/bautagebuch/backup.sh
```

---

## Kosten-Übersicht

| Posten | Kosten |
|---|---|
| Hostinger VPS KVM 1 | ~5 €/Monat |
| Domain (.de) | ~10 €/Jahr |
| OpenAI API | ~5-15 €/Monat (je nach Nutzung) |
| Telegram Bot | kostenlos |
| SSL-Zertifikat | kostenlos (Let's Encrypt) |
| **Gesamt** | **~10-25 €/Monat** |

---

## Troubleshooting

### Bot antwortet nicht
```bash
# Logs prüfen
docker compose logs --tail 100  # oder: journalctl -u instandhaltung --tail 100

# Häufige Ursachen:
# - TELEGRAM_BOT_TOKEN falsch → In .env prüfen
# - Anderer Bot-Prozess läuft → Nur EINE Instanz erlaubt
# - Netzwerk-Problem → ping api.telegram.org
```

### Dashboard nicht erreichbar
```bash
# Läuft der Service?
docker compose ps  # oder: systemctl status instandhaltung

# Port offen?
curl http://localhost:8093

# Firewall prüfen
ufw status
```

### OpenAI-Fehler (429 / insufficient_quota)
- Gehe zu https://platform.openai.com/billing
- Lade Guthaben auf (5-10 € reichen für den Anfang)
- Die App funktioniert auch ohne OpenAI – KI-Features werden übersprungen

### Datenbank zurücksetzen
```bash
# VORSICHT: Löscht alle Daten!
rm data/bautagebuch.db
docker compose restart  # Neue leere DB wird erstellt
```
