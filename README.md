# JavisVoice 🦞

**Sprachinterface für Javis auf Raspberry Pi**

## Features

- 🎤 **Wake Word Detection** — "Jarvis" erkennt dich (Porcupine)
- 🎙️ **Lokale Spracherkennung** — Whisper (medium, Deutsch)
- 🔊 **Lokale TTS-Stimme** — Thorsten (Coqui TTS, Deutsche Stimme)
- 🌐 **OpenClaw Integration** — Dein persönlicher AI Assistant
- 🐰 **RabbitMQ Support** — Robuste Kommunikation via AMQP (optional)

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

## Kommunikation mit OpenClaw

### Option 1: HTTP (Standard)

```yaml
openclaw:
  gateway_url: "http://OPENCLAW_HOST:18789"
```

### Option 2: RabbitMQ (Robust)

```yaml
rabbitmq:
  enabled: true
  host: "RABBITMQ_HOST"
  port: 5672
  username: "test"
  password: "test123"
  queue: "javis.voice.in"
  reply_queue: "javis.voice.out"
```

Siehe [openclaw-rabbitmq-plugin/README.md](openclaw-rabbitmq-plugin/README.md) für Details.

## Wake Word aktivieren

1. **Kostenloser Picovoice Access Key:**
   → https://picovoice.ai/console/

2. Key in `config/config.yaml` eintragen:
   ```yaml
   wake_word:
     access_key: "DEIN_KEY_HIER"
   ```

## Architektur

### HTTP Modus

```
[JavisVoice] ──HTTP──> [OpenClaw Gateway]
```

### RabbitMQ Modus

```
[JavisVoice] ──AMQP──> [RabbitMQ] ──consume──> [OpenClaw Plugin] ──> [Agent]
                              ▲
                              │
                    [Response Queue]
                              ▲
                              │
                    [OpenClaw] ──publish──> [RabbitMQ] ──AMQP──> [JavisVoice]
```

Siehe [ARCHITECTURE.md](ARCHITECTURE.md) für Details.

## Projektstruktur

```
Javisspeach/
├── ARCHITECTURE.md           # Architektur-Dokumentation
├── config/
│   └── config.yaml           # Konfiguration
├── src/
│   ├── javis.py              # Hauptprogramm
│   ├── wakeword/             # Porcupine Wake Word
│   │   └── porcupine_wake.py
│   ├── vad/                  # WebRTC VAD
│   │   └── webrtc_vad.py
│   ├── stt/                  # Whisper STT
│   │   └── whisper_stt.py
│   ├── tts/                  # Thorsten TTS
│   │   └── thorsten_tts.py
│   └── api/                  # Kommunikation
│       ├── openclaw_client.py    # HTTP Client
│       └── rabbitmq_client.py    # RabbitMQ Client
├── scripts/
│   ├── install.sh            # Setup-Script
│   └── test_audio.sh         # Audio-Test
├── openclaw-rabbitmq-plugin/ # OpenClaw Plugin (optional)
│   ├── openclaw.plugin.json
│   ├── index.ts
│   ├── package.json
│   └── README.md
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

**Problem:** RabbitMQ Verbindung fehlgeschlagen
→ Siehe [openclaw-rabbitmq-plugin/README.md](openclaw-rabbitmq-plugin/README.md)
