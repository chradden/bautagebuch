"""Launcher – Startet Telegram-Bot und Web-Dashboard gleichzeitig."""
import threading
import logging
import uvicorn

import config
from db.database import init_db

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def start_web_dashboard():
    """Startet das FastAPI Web-Dashboard in einem separaten Thread."""
    logger.info("Starte Web-Dashboard auf http://0.0.0.0:8093")
    uvicorn.run(
        "web.app:app",
        host="0.0.0.0",
        port=8093,
        log_level="info",
        reload=False,
    )


def main():
    """Startet beide Services."""
    logger.info("=== Instandhaltungsplanung – Systemstart ===")
    init_db()

    if config.BOT_AKTIV:
        # Web-Dashboard in separatem Thread starten, Bot im Hauptthread
        web_thread = threading.Thread(target=start_web_dashboard, daemon=True)
        web_thread.start()
        logger.info("Web-Dashboard gestartet (Port 8093)")

        logger.info("Starte Telegram-Bot...")
        from bot.main import main as bot_main
        bot_main()
    else:
        # Nur Dashboard – kein Bot (z.B. im Codespace/Entwicklung)
        logger.info("BOT_AKTIV=false → nur Web-Dashboard wird gestartet (kein Telegram-Bot)")
        start_web_dashboard()  # blockiert


if __name__ == "__main__":
    main()
