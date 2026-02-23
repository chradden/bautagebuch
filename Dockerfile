FROM python:3.12-slim

# System-Dependencies für WeasyPrint
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libgdk-pixbuf-xlib-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir "python-telegram-bot[job-queue]"

# App kopieren
COPY . .

# Verzeichnisse erstellen
RUN mkdir -p data/output data/uploads

# Port für Web-Dashboard
EXPOSE 8090

# Launcher starten (Bot + Dashboard)
CMD ["python3", "run.py"]
