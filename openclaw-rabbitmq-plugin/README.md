# RabbitMQ Voice Plugin für OpenClaw

**Plugin-ID:** `rabbitmq-voice`

Ermöglicht JavisVoice auf dem Raspberry Pi, über RabbitMQ mit OpenClaw zu kommunizieren, statt über HTTP.

## Architektur

```
[JavisVoice Pi] ──AMQP──> [javis.voice.in queue]
                              │
                              ▼
                    [OpenClaw RabbitMQ Plugin]
                              │
                              │ (processes message)
                              ▼
                       [OpenClaw Agent]
                              │
                              │ (response)
                              ▼
                    [javis.voice.out queue]
                              │
                              ▼
[JavisVoice Pi] ◀──AMQP── (receives response, TTS plays)
```

## Installation

### 1. RabbitMQ installieren (falls noch nicht vorhanden)

```bash
# Auf dem Server:
sudo apt install rabbitmq-server
sudo systemctl enable rabbitmq-server
sudo systemctl start rabbitmq-server
```

### 2. Plugin installieren

```bash
# In deinem Workspace:
cd /home/sascha/.openclaw/workspace/Javisspeach/openclaw-rabbitmq-plugin

# Abhängigkeiten installieren
npm install

# Oder direkt in OpenClaw installieren:
openclaw plugins install ./openclaw-rabbitmq-plugin
```

### 3. Konfiguration

In `openclaw.json` oder über `openclaw config`:

```json
{
  "plugins": {
    "entries": {
      "rabbitmq-voice": {
        "enabled": true,
        "config": {
          "host": "localhost",
          "port": 5672,
          "username": "guest",
          "password": "guest",
          "queue": "javis.voice.in",
          "replyQueue": "javis.voice.out"
        }
      }
    }
  }
}
```

Oder mit CLI:
```bash
openclaw config set plugins.entries.rabbitmq-voice.enabled true
# ... etc
```

### 4. Gateway neustarten

```bash
openclaw gateway restart
```

## Message Format

### Inbound (Pi → OpenClaw)

Queue: `javis.voice.in`

```json
{
  "sessionId": "pi-001-abc123",
  "text": "Wie wird das Wetter morgen?",
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

## JavisVoice anpassen

In JavisVoice `src/api/rabbitmq_client.py` erstellen:

```python
#!/usr/bin/env python3
"""RabbitMQ Client für JavisVoice"""

import pika
import json
import uuid

class JavisRabbitMQ:
    def __init__(self, host='openclaw-server.local', queue='javis.voice.in', 
                 reply_queue='javis.voice.out'):
        self.host = host
        self.queue = queue
        self.reply_queue = reply_queue
        self.connection = None
        self.channel = None
        self.session_id = str(uuid.uuid4())[:8]
    
    def connect(self):
        credentials = pika.PlainCredentials('guest', 'guest')
        parameters = pika.ConnectionParameters(
            host=self.host,
            credentials=credentials
        )
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        
        # Ensure queues exist
        self.channel.queue_declare(queue=self.queue, durable=True)
        self.channel.queue_declare(queue=self.reply_queue, durable=True)
    
    def send_and_wait(self, text, timeout=30):
        """Send message and wait for response"""
        # Set up consumer for reply queue
        response = [None]
        
        def callback(ch, method, properties, body):
            msg = json.loads(body)
            if msg.get('sessionId') == self.session_id:
                response[0] = msg.get('response')
                ch.basic_ack(delivery_tag=method.delivery_tag)
                ch.stop_consuming()
        
        self.channel.basic_consume(
            queue=self.reply_queue,
            on_message_callback=callback
        )
        
        # Publish message
        message = {
            'sessionId': self.session_id,
            'text': text,
            'timestamp': int(time.time() * 1000)
        }
        
        self.channel.basic_publish(
            exchange='',
            routing_key=self.queue,
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        
        # Start consuming (with timeout)
        self.channel.start_consuming(timeout=timeout)
        
        return response[0]
    
    def close(self):
        if self.connection:
            self.connection.close()
```

## Troubleshooting

### Plugin startet nicht

```bash
# Status prüfen
openclaw plugins doctor

# Logs ansehen
openclaw gateway logs --tail 50
```

### Keine Verbindung zu RabbitMQ

```bash
# RabbitMQ Status prüfen
sudo systemctl status rabbitmq-server

# Ports prüfen
ss -tlnp | grep 5672
```

### Queue nicht gefunden

```bash
# RabbitMQ Management UI
sudo rabbitmq-plugins enable rabbitmq_management
# Dann: http://localhost:15672 (guest/guest)
```

## Status prüfen

```bash
# Gateway Method aufrufen
openclaw gateway rpc rabbitmq-voice.status
```

## Dateien

```
openclaw-rabbitmq-plugin/
├── openclaw.plugin.json   # Plugin Manifest
├── index.ts               # Hauptplugin
├── package.json           # NPM Package
└── README.md              # Diese Datei
```
