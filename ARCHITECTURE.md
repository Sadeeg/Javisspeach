# JavisVoice — Architektur

## Überblick

```
                    ┌──────────────────────────────────────────────────────────────┐
                    │                      Raspberry Pi                            │
                    │                                                               │
┌─────────┐         │  ┌──────────┐    ┌───────┐    ┌──────────┐    ┌──────────┐  │
│  Mic    │────────▶│  │  Wake    │───▶│  VAD  │───▶│ Whisper  │───▶│ OpenClaw │  │
│  (USB)  │         │  │  Word    │    │       │    │  (STT)   │    │   API    │  │
└─────────┘         │  │(Porcupine)   │(webrtc)│    │  medium  │    │          │  │
                    │  └──────────┘    └───────┘    └──────────┘    └────┬─────┘  │
                    │        ▲                                            │        │
                    │        │                         ┌──────────┐        │        │
                    │        └─────────────────────────│ Thorsten │◀───────┘        │
                    │                                   │  (TTS)  │                 │
                    │                                   └────┬────┘                 │
                    │                                        │                      │
                    │                                   ┌────▼────┐                 │
                    │                                   │ Speaker │                 │
                    └───────────────────────────────────┴─────────┴─────────────────┘
```

## Komponenten

### 1. Wake Word Engine — `pvporcupine`
- **Library:** Picovoice Porcupine (lightweight, ~1MB)
- **Wake Word:** "Jarvis" (oder "Hey Jarvis")
- **Modell:** `.ppn` file (pulses)
- **Betrieb:** Kontinuierlich im Hintergrund, niedrige CPU-Last (~1%)
- **Pin:** BCM 4 (optional, für LED)

### 2. Voice Activity Detection — `webrtc-noise-gain`
- **Library:** webrtcvad
- **Mode:** Aggressive (3) für Umgebung mit Hintergrundgeräuschen
- **Frame:** 30ms chunks
- **Zweck:** Erkennt Sprechpausen → Whisper nur mit Speech

### 3. Speech-to-Text — `openai-whisper`
- **Modell:** `medium` (Deutsch optimiert)
- **Device:** CPU (Pi 4 kann das)
- **Sprache:** Deutsch ("de")
- **Input:** WAV (16kHz, mono, 16-bit)

### 4. Agent — OpenClaw API
- **Endpoint:** OpenClaw Gateway API (lokal oder Remote)
- **Kommunikation:** REST/JSON
- **Session:** Persistente Session für Kontext

### 5. Text-to-Speech — Coqui TTS
- **Modell:** `tts_models/de/thorsten/vits`
- **Output:** WAV, 16kHz
- **Player:** `aplay` (ALSA) oder `pygame`
- **Feedback-LED:** GPIO 17 (optional)

## Datenfluss

```
1. [STANDBY]    Porcupine lauscht auf "Jarvis"
2. [WECKWORT]   "Jarvis" erkannt → LED blinkt, Feedback-Ton
3. [AUFNAHME]   VAD aktiv, Audio wird gepuffert (max 30s)
4. [STille]     VAD erkennt Ende (1.5s Stille) → Aufnahme stoppt
5. [STT]        Whisper transkribiert → Text
6. [AGENT]      OpenClaw API: Text senden, Antwort empfangen
7. [TTS]        Thorsten TTS: Antwort → WAV
8. [ANTWORT]    WAV abspielen
9. [STANDBY]    Zurück zu Porcupine
```

## Verzeichnisstruktur

```
Javisspeach/
├── README.md
├── requirements.txt
├── config/
│   └── config.yaml           # Konfiguration (Wake word, GPIO, API)
├── src/
│   ├── __init__.py
│   ├── javis.py              # Hauptprogramm (State Machine)
│   ├── wakeword/
│   │   ├── __init__.py
│   │   └── porcupine_wake.py # Porcupine Wrapper
│   ├── vad/
│   │   ├── __init__.py
│   │   └── webrtc_vad.py     # WebRTC VAD Wrapper
│   ├── stt/
│   │   ├── __init__.py
│   │   └── whisper_stt.py    # Whisper Transkription
│   ├── tts/
│   │   ├── __init__.py
│   │   └── thorsten_tts.py   # Thorsten TTS
│   └── api/
│       ├── __init__.py
│       └── openclaw_client.py # OpenClaw API Client
├── scripts/
│   ├── install.sh             # Setup-Script für Raspberry Pi
│   └── test_audio.sh         # Audio-Test
└── assets/
    ├── jarvis.ppn            # Wake Word Modell
    └── beep.wav              # Feedback-Ton
```

## Abhängigkeiten (requirements.txt)

```
# Wake Word
pvporcupine>=3.0.0

# Audio
pyaudio>=0.2.14
webrtcvad>=2.10.0

# STT
openai-whisper>=20231117

# TTS
TTS>=0.22.0

# Utils
PyYAML>=6.0
requests>=2.31.0
```

## Hardware-Setup (Raspberry Pi)

```
USB Mic ──────────────────► Raspberry Pi ────► Speaker/Headphone
(GPIO 4) LED ◄─────────────  (optional)
```

### Empfohlenes USB-Mikrofon
- mit guter Richtcharakteristik ( array mic)
- z.B. seeed-voicecard oder pluggable USB

## Performance-Ziele

| Komponente | CPU (Pi 4) | RAM |
|------------|------------|-----|
| Porcupine  | ~1%        | ~20MB |
| WebRTC VAD | <1%        | ~5MB |
| Whisper    | ~40-60% (peak) | ~500MB |
| Thorsten TTS | ~30-50% (peak) | ~300MB |

**Durchschnittlich:** ~5-10% CPU (weil Whisper/TTS nur kurz laufen)

## API-Integration (OpenClaw)

### HTTP Modus

```python
# POST /v1/voice/process
{
    "text": "Schalte das Licht ein",
    "session_id": "rpi-001",
    "language": "de"
}

# Response
{
    "response": "Das Licht ist jetzt an.",
    "session_id": "rpi-001"
}
```

### RabbitMQ Modus

**Message Queue Architektur:**

```
┌─────────────────────────────────────────────────────────────────┐
│                       RabbitMQ Server                            │
│                                                                  │
│  ┌─────────────────┐              ┌─────────────────┐           │
│  │ javis.voice.in  │              │ javis.voice.out │           │
│  │   (Inbound)     │              │   (Outbound)    │           │
│  │                 │              │                 │           │
│  │ Pi ──────────▶  │              │  OpenClaw ────▶ │           │
│  └─────────────────┘              └─────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

**Message Format (Inbound):**
```json
{
    "sessionId": "pi-001-abc123",
    "text": "Hallo Javis, wie wird das Wetter?",
    "timestamp": 1743168000000
}
```

**Message Format (Outbound):**
```json
{
    "sessionId": "pi-001-abc123",
    "response": "Morgen wird das Wetter sonnig.",
    "timestamp": 1743168005000
}
```

**OpenClaw Plugin:**
- Verbindet automatisch mit RabbitMQ beim Gateway-Start
- Konsumiert von `javis.voice.in`
- Published Responses zu `javis.voice.out`
- Service: automatisches Reconnect bei Verbindungsverlust

**Python Client:**
```python
from rabbitmq_client import JavisRabbitMQ

client = JavisRabbitMQ(host='RABBITMQ_HOST')
client.connect()

# Synchron (blockiert bis Antwort)
response = client.send_and_wait("Hallo Javis!")

# Async mit Callback
client.send_async("Hallo Javis!", lambda r: play_audio(r))

client.close()
```

## Troubleshooting

- **Wake Word reagiert nicht:** Mikrofon-Pegel prüfen (`alsamixer`)
- **Whisper zu langsam:** `small` statt `medium` Modell nutzen
- **TTS ruckelt:** HDMI-Audio deaktivieren, USB-Speaker nutzen
- **RabbitMQ Access Denied:** Benutzer + Rechte prüfen (`rabbitmqctl list_permissions`)
