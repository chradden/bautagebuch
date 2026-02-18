"""Launcher – Startet Telegram-Bot und Web-Dashboard gleichzeitig."""
import asyncio
import threading
import logging
import uvicorn

from db.database import init_db
from bot.main import main as bot_main

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def start_web_dashboard():
    """Startet das FastAPI Web-Dashboard in einem separaten Thread."""
    logger.info("Starte Web-Dashboard auf http://0.0.0.0:8080")
    uvicorn.run(
        "web.app:app",
        host="0.0.0.0",
        port=8080,
        log_level="info",
        reload=False,
    )


def main():
    """Startet beide Services."""
    logger.info("=== Instandhaltungsplanung – Systemstart ===")
    init_db()

    # Web-Dashboard in separatem Thread starten
    web_thread = threading.Thread(target=start_web_dashboard, daemon=True)
    web_thread.start()
    logger.info("Web-Dashboard gestartet (Port 8080)")

    # Telegram-Bot im Hauptthread starten (blockiert)
    logger.info("Starte Telegram-Bot...")
    bot_main()


if __name__ == "__main__":
    main()
