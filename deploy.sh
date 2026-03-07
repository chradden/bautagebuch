#!/bin/bash
set -euo pipefail

echo "══════════════════════════════════════════════"
echo "  Bautagebuch — Deploy"
echo "══════════════════════════════════════════════"

cd "$(dirname "$0")"

echo "→ Code vom Remote holen..."
git fetch origin main --tags

echo "→ Auf origin/main zurücksetzen..."
git reset --hard origin/main

echo "→ Container stoppen..."
docker compose down

echo "→ Image neu bauen (kein Cache)..."
docker compose build --no-cache

echo "→ Container starten..."
docker compose up -d --force-recreate

echo "→ Alte Docker-Images aufräumen..."
docker image prune -f

echo ""
echo "══════════════════════════════════════════════"
echo "  ✅ Deploy abgeschlossen"
echo "══════════════════════════════════════════════"
