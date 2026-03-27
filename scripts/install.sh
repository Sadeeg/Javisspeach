#!/bin/bash
# install.sh - JavisVoice auf Raspberry Pi installieren

set -e

echo "=========================================="
echo "  JavisVoice Installation (Raspberry Pi)"
echo "=========================================="

# System aktualisieren
echo "📦 System aktualisieren..."
sudo apt update && sudo apt upgrade -y

# Abhängigkeiten installieren
echo "📦 Basis-Abhängigkeiten installieren..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    alsa-utils \
    libasound2-dev \
    portaudio19-dev \
    ffmpeg

# Virtual Environment erstellen
echo "🐍 Virtual Environment erstellen..."
python3 -m venv venv
source venv/bin/activate

# pip aktualisieren
pip install --upgrade pip

# Audio-Bibliotheken (zuerst)
pip install pyaudio webrtcvad

# Porcupine installieren
echo "🔔 Porcupine Wake Word installieren..."
pip install pvporcupine

# Whisper installieren (kann auf Pi länger dauern)
echo "🎙️  Whisper installieren..."
pip install openai-whisper

# TTS installieren
echo "🔊 TTS installieren..."
pip install TTS

# Weitere Dependencies
echo "📚 Weitere Dependencies..."
pip install PyYAML requests numpy

# Projekt installieren
echo "📂 Projekt installieren..."
pip install -e .

# Audio-Geräte prüfen
echo ""
echo "=========================================="
echo "  Audio Setup"
echo "=========================================="
echo ""
echo "Verfügbare Mikrofone:"
arecord -l || echo "Keine Mikrofone gefunden!"
echo ""
echo "Verfügbare Speaker:"
aplay -l || echo "Keine Speaker gefunden!"
echo ""

# Access Key abfragen
echo "=========================================="
echo "  Picovoice Access Key"
echo "=========================================="
echo "Hole deinen kostenlosen Access Key auf:"
echo "  https://picovoice.ai/console/"
echo ""
echo -n "Access Key eingeben (oder Enter zum Überspringen): "
read ACCESS_KEY

if [ -n "$ACCESS_KEY" ]; then
    sed -i "s/YOUR_PICOVOICE_ACCESS_KEY/$ACCESS_KEY/" config/config.yaml
    echo "✅ Access Key gespeichert"
else
    echo "⚠️  Wake Word ohne Access Key deaktiviert!"
    echo "   Trage deinen Key später in config/config.yaml ein"
fi

echo ""
echo "=========================================="
echo "  Installation abgeschlossen!"
echo "=========================================="
echo ""
echo "Starten mit:"
echo "  source venv/bin/activate"
echo "  python -m src.javis"
echo ""
