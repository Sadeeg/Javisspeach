#!/usr/bin/env python3
"""RabbitMQ Client für JavisVoice - Alternative zum HTTP API Client"""

import json
import uuid
import time
import threading
from typing import Optional, Callable


class JavisRabbitMQ:
    """RabbitMQ Client für Kommunikation mit OpenClaw via AMQP"""
    
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 5672,
        username: str = 'guest',
        password: str = 'guest',
        queue: str = 'javis.voice.in',
        reply_queue: str = 'javis.voice.out',
        session_id: Optional[str] = None
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.queue = queue
        self.reply_queue = reply_queue
        self.session_id = session_id or f"javis-{uuid.uuid4().hex[:8]}"
        
        self._connection = None
        self._channel = None
        self._callback_thread = None
        self._running = False
        self._callbacks: dict[str, Callable] = {}
    
    def connect(self) -> bool:
        """Verbindung zu RabbitMQ herstellen"""
        try:
            import pika
            
            credentials = pika.PlainCredentials(self.username, self.password)
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            
            self._connection = pika.BlockingConnection(parameters)
            self._channel = self._connection.channel()
            
            # Queues deklarieren (erstellt sie wenn nicht vorhanden)
            self._channel.queue_declare(queue=self.queue, durable=True)
            self._channel.queue_declare(queue=self.reply_queue, durable=True)
            
            print(f"✅ Verbunden mit RabbitMQ ({self.host}:{self.port})")
            print(f"   Queue: {self.queue}")
            print(f"   Reply Queue: {self.reply_queue}")
            print(f"   Session ID: {self.session_id}")
            
            return True
            
        except ImportError:
            print("❌ pika nicht installiert. Installiere mit: pip install pika")
            return False
        except Exception as e:
            print(f"❌ Verbindung fehlgeschlagen: {e}")
            return False
    
    def _on_reply(self, ch, method, properties, body):
        """Callback für Reply-Nachrichten"""
        try:
            msg = json.loads(body)
            reply_session_id = msg.get('sessionId')
            
            if reply_session_id in self._callbacks:
                callback = self._callbacks.pop(reply_session_id)
                callback(msg.get('response', ''))
                ch.basic_ack(delivery_tag=method.delivery_tag)
            else:
                # Acknowledge ohne Callback
                ch.basic_ack(delivery_tag=method.delivery_tag)
                
        except Exception as e:
            print(f"❌ Reply Callback Fehler: {e}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
    
    def start_consuming(self):
        """Startet den Consumer im Hintergrund"""
        if self._running:
            return
        
        self._running = True
        self._channel.basic_consume(
            queue=self.reply_queue,
            on_message_callback=self._on_reply
        )
        self._callback_thread = threading.Thread(target=self._channel.start_consuming)
        self._callback_thread.daemon = True
        self._callback_thread.start()
        print(f"👂 Warte auf Antworten auf {self.reply_queue}")
    
    def stop_consuming(self):
        """Stoppt den Consumer"""
        self._running = False
        if self._channel and self._channel.is_open:
            self._channel.stop_consuming()
        if self._connection and self._connection.is_open:
            self._connection.close()
    
    def send_and_wait(self, text: str, timeout: float = 30.0) -> Optional[str]:
        """
        Sendet eine Nachricht und wartet auf Antwort.
        
        Args:
            text: Der zu sendende Text
            timeout: Wartezeit in Sekunden
            
        Returns:
            Die Antwort von Javis oder None bei Timeout
        """
        if not self._channel or not self._channel.is_open:
            if not self.connect():
                return None
        
        response = [None]
        event = threading.Event()
        
        def callback(response_text: str):
            response[0] = response_text
            event.set()
        
        # Callback registrieren
        self._callbacks[self.session_id] = callback
        
        # Nachricht senden
        message = {
            'sessionId': self.session_id,
            'text': text,
            'timestamp': int(time.time() * 1000)
        }
        
        try:
            self._channel.basic_publish(
                exchange='',
                routing_key=self.queue,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistent
                    content_type='application/json'
                )
            )
            
            print(f"📤 Nachricht gesendet (Session: {self.session_id})")
            
            # Auf Antwort warten
            event.wait(timeout=timeout)
            
            if response[0] is None:
                print(f"⏱️  Timeout nach {timeout}s")
                self._callbacks.pop(self.session_id, None)
            
            return response[0]
            
        except Exception as e:
            print(f"❌ Sende-Fehler: {e}")
            self._callbacks.pop(self.session_id, None)
            return None
    
    def send_async(self, text: str, callback: Callable[[str], None]) -> bool:
        """
        Sendet eine Nachricht asynchron (mit Callback).
        
        Args:
            text: Der zu sendende Text
            callback: Wird aufgerufen wenn Antwort kommt
            
        Returns:
            True wenn erfolgreich gesendet
        """
        if not self._channel or not self._channel.is_open:
            if not self.connect():
                return False
        
        # Ensure consuming is running
        if not self._running:
            self.start_consuming()
        
        # Callback mit neuer Session registrieren
        msg_session_id = f"{self.session_id}-{int(time.time() * 1000)}"
        self._callbacks[msg_session_id] = callback
        
        message = {
            'sessionId': msg_session_id,
            'text': text,
            'timestamp': int(time.time() * 1000)
        }
        
        try:
            self._channel.basic_publish(
                exchange='',
                routing_key=self.queue,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type='application/json'
                )
            )
            return True
        except Exception as e:
            print(f"❌ Async Sende-Fehler: {e}")
            self._callbacks.pop(msg_session_id, None)
            return False


# ============ Integration mit bestehendem javis.py ============

def create_rabbitmq_client(config: dict) -> JavisRabbitMQ:
    """Erstellt einen RabbitMQ Client aus der Config"""
    openclaw_config = config.get('openclaw', {})
    rabbitmq_config = config.get('rabbitmq', {})
    
    return JavisRabbitMQ(
        host=rabbitmq_config.get('host', 'localhost'),
        port=rabbitmq_config.get('port', 5672),
        username=rabbitmq_config.get('username', 'guest'),
        password=rabbitmq_config.get('password', 'guest'),
        queue=rabbitmq_config.get('queue', 'javis.voice.in'),
        reply_queue=rabbitmq_config.get('reply_queue', 'javis.voice.out')
    )


if __name__ == '__main__':
    # Test
    client = JavisRabbitMQ(
        host='localhost',
        username='guest',
        password='guest'
    )
    
    if client.connect():
        #client.start_consuming()
        #response = client.send_async("Hallo Javis, kannst du mich hören?", print)
        #time.sleep(5)
        
        response = client.send_and_wait("Hallo Javis, kannst du mich hören?")
        print(f"Antwort: {response}")
        
        client.stop_consuming()
