#!/bin/bash
# ─────────────────────────────────────────────────────────────────────
# deploy.sh — Schnelles Deployment / Update auf dem VPS
#
# Verwendung:
#   chmod +x deploy.sh
#   ./deploy.sh
# ─────────────────────────────────────────────────────────────────────

set -euo pipefail

echo "══════════════════════════════════════════════"
echo "  Bautagebuch — Deploy"
echo "══════════════════════════════════════════════"

# Git aktualisieren
echo "→ Code aktualisieren..."
git pull origin main

# Container neu bauen und starten
echo "→ Container stoppen..."
docker compose down
echo "→ Image neu bauen (kein Cache)..."
docker compose build --no-cache
echo "→ Container starten..."
docker compose up -d --force-recreate

# Alte Images aufräumen
echo "→ Alte Docker-Images aufräumen..."
docker image prune -f

echo ""
echo "══════════════════════════════════════════════"
echo "  ✅ Deploy abgeschlossen"
echo "══════════════════════════════════════════════"
