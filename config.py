import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bautagebuch.db")
PDF_OUTPUT_DIR = os.getenv("PDF_OUTPUT_DIR", "./output")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
