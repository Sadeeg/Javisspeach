# OpenClaw RabbitMQ Voice Plugin

**Plugin-ID:** `rabbitmq-voice`

RabbitMQ Integration für JavisVoice. Ermöglicht Kommunikation über AMQP statt HTTP.

## Architektur

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        JavisVoice (Raspberry Pi)                          │
│  ┌─────────────┐    ┌───────────┐    ┌─────────┐    ┌──────────────────┐ │
│  │  Wake Word  │───▶│   VAD     │───▶│ Whisper │───▶│ RabbitMQ Client │ │
│  │ (Porcupine) │    │ (webrtc)  │    │  (STT)  │    │  send_and_wait()│ │
│  └─────────────┘    └───────────┘    └─────────┘    └────────┬─────────┘ │
│                                                               │           │
│  ◀────────────────── TTS Playback ◀───────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ AMQP
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              RabbitMQ Server                                 │
│                         localhost:5672 (AMQP)                               │
│                         localhost:15672 (Management UI)                     │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                        Queues                                        │  │
│  │  • javis.voice.in  (Pi → OpenClaw)                                  │  │
│  │  • javis.voice.out (OpenClaw → Pi)                                 │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ AMQP Consumer
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           OpenClaw Gateway                                  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                   rabbitmq-voice Plugin                              │  │
│  │  • Service: Connection + Consumer Lifecycle                         │  │
│  │  • Channel: Outbound messaging                                      │  │
│  │  • RPC: Status + Manual Publish                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    │ Session Routing                         │
│                                    ▼                                        │
│                         ┌─────────────────────┐                            │
│                         │   OpenClaw Agent    │                            │
│                         │   (Javis/LLM)       │                            │
│                         └─────────────────────┘                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Message Format

### Inbound (Pi → OpenClaw)

Queue: `javis.voice.in`

```json
{
  "sessionId": "pi-001-abc123",
  "text": "Hallo Javis, wie wird das Wetter morgen?",
  "timestamp": 1743168000000
}
```

### Outbound (OpenClaw → Pi)

Queue: `javis.voice.out`

```json
{
  "sessionId": "pi-001-abc123",
  "response": "Morgen wird das Wetter sonnig mit Temperaturen um 20 Grad.",
  "timestamp": 1743168005000
}
```

## Installation

### 1. RabbitMQ Server

```bash
# Docker (empfohlen)
docker run -d \
  --name javis-rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  -e RABBITMQ_DEFAULT_USER=javis \
  -e RABBITMQ_DEFAULT_PASS=javis123 \
  rabbitmq:3-management
```

Oder ohne Docker:
```bash
sudo apt install rabbitmq-server
```

### 2. Plugin installieren

```bash
cd /path/to/Javisspeach
openclaw plugins install ./openclaw-rabbitmq-plugin
```

### 3. Konfiguration

```bash
# Gateway neustarten
openclaw gateway restart

# Config setzen
openclaw config set plugins.entries.rabbitmq-voice.enabled true
openclaw config set plugins.entries.rabbitmq-voice.config.host localhost
openclaw config set plugins.entries.rabbitmq-voice.config.port 5672
openclaw config set plugins.entries.rabbitmq-voice.config.username test
openclaw config set plugins.entries.rabbitmq-voice.config.password test123
openclaw config set plugins.entries.rabbitmq-voice.config.queue javis.voice.in
openclaw config set plugins.entries.rabbitmq-voice.config.replyQueue javis.voice.out
```

Oder direkt in `openclaw.json`:

```json
{
  "plugins": {
    "entries": {
      "rabbitmq-voice": {
        "enabled": true,
        "config": {
          "host": "localhost",
          "port": 5672,
          "username": "test",
          "password": "test123",
          "queue": "javis.voice.in",
          "replyQueue": "javis.voice.out"
        }
      }
    }
  }
}
```

### 4. Gateway neustarten

```bash
openclaw gateway restart
```

## Konfiguration Reference

| Parameter | Default | Beschreibung |
|-----------|---------|---------------|
| `host` | `localhost` | RabbitMQ Server Host |
| `port` | `5672` | AMQP Port |
| `username` | `guest` | AMQP Username |
| `password` | `guest` | AMQP Password |
| `queue` | `javis.voice.in` | Inbound Queue (Pi → OpenClaw) |
| `replyQueue` | `javis.voice.out` | Outbound Queue (OpenClaw → Pi) |
| `vhost` | `/` | Virtual Host |
| `prefetch` | `1` | Prefetch Count |

## Benutzer erstellen (falls nötig)

```bash
# Im RabbitMQ Container
docker exec javis-rabbitmq rabbitmqctl add_user test test123
docker exec javis-rabbitmq rabbitmqctl set_permissions -p / test ".*" ".*" ".*"
```

## Status prüfen

```bash
# Gateway Logs
tail -f /tmp/openclaw/openclaw-$(date +%Y-%m-%d).log | grep rabbitmq

# Plugin Status via RPC
openclaw gateway rpc rabbitmq-voice.status
```

## Management UI

RabbitMQ Management Interface: http://localhost:15672

- User: `javis` / `javis123`
- Queues beobachten
- Messages inspecten

## Troubleshooting

### Plugin startet nicht

```bash
# Logs prüfen
tail -50 /tmp/openclaw/openclaw-$(date +%Y-%m-%d).log

# Doctor
openclaw plugins doctor
```

### Access refused

```bash
# Benutzer und Rechte prüfen
docker exec javis-rabbitmq rabbitmqctl list_users
docker exec javis-rabbitmq rabbitmqctl list_permissions -p /
```

### Verbindung verloren

Plugin versucht automatisch wiederzuverbinden. Bei dauerhaften Problemen Gateway neustarten:

```bash
openclaw gateway restart
```

## Dateien

```
openclaw-rabbitmq-plugin/
├── openclaw.plugin.json   # Plugin Manifest + Config Schema
├── index.ts              # TypeScript Plugin Source
├── package.json          # NPM Package
└── README.md             # Diese Datei
```

## Siehe auch

- [JavisVoice README](../README.md) - Hauptprojekt
- [RabbitMQ Client](../src/api/rabbitmq_client.py) - Python Client für Pi
