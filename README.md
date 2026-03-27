# JavisVoice 🦞

**Sprachinterface für Javis auf Raspberry Pi**

## Features

- 🎤 **Wake Word Detection** — "Jarvis" erkennt dich (Porcupine)
- 🎙️ **Lokale Spracherkennung** — Whisper (medium, Deutsch)
- 🔊 **Lokale TTS-Stimme** — Thorsten (Coqui TTS, Deutsche Stimme)
- 🌐 **OpenClaw Integration** — Dein persönlicher AI Assistant

## Hardware

- **Raspberry Pi 4** (empfohlen) oder Pi 3B+
- **USB-Mikrofon** (Array-Mikrofon empfohlen)
- **Lautsprecher** (3.5mm Klinke oder USB)

## Quick Start

```bash
# 1. Repository klonen
git clone git@github.com:Sadeeg/Javisspeach.git
cd Javisspeach

# 2. Installation (auf dem Pi)
chmod +x scripts/install.sh
./scripts/install.sh

# 3. Config anpassen
nano config/config.yaml

# 4. Starten
source venv/bin/activate
python -m src.javis
```

## Wake Word aktivieren

1. **Kostenloser Picovoice Access Key:**
   → https://picovoice.ai/console/

2. Key in `config/config.yaml` eintragen:
   ```yaml
   wake_word:
     access_key: "DEIN_KEY_HIER"
   ```

## Architektur

Siehe [ARCHITECTURE.md](ARCHITECTURE.md) für Details.

## Projektstruktur

```
Javisspeach/
├── config/config.yaml       # Konfiguration
├── src/
│   ├── javis.py            # Hauptprogramm
│   ├── wakeword/           # Porcupine Wake Word
│   ├── vad/                # WebRTC VAD
│   ├── stt/                # Whisper STT
│   ├── tts/                # Thorsten TTS
│   └── api/                # OpenClaw Client
├── scripts/
│   ├── install.sh          # Setup-Script
│   └── test_audio.sh       # Audio-Test
└── requirements.txt
```

## Troubleshooting

**Problem:** "No module named 'pvporcupine'"
```bash
pip install pvporcupine
```

**Problem:** Wake Word reagiert nicht
```bash
# Mikrofon-Pegel prüfen
alsamixer
# Oder mit GUI
pavucontrol
```

**Problem:** Whisper zu langsam
→ In `config/config.yaml` auf `small` oder `tiny` wechseln

**Problem:** TTS klingt abgeschnitten
→ Siehe [TTS Troubleshooting](https://github.com/coqui-ai/TTS)
