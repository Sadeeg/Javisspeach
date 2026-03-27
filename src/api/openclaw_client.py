#!/usr/bin/env python3
"""OpenClaw API Client für JavisVoice"""

import requests
import json


class OpenClawClient:
    def __init__(self, config):
        api_config = config['openclaw']
        
        self.gateway_url = api_config.get('gateway_url', 'http://localhost:18789')
        self.api_key = api_config.get('api_key', '')
        self.session_id = api_config.get('session_id', 'javis-pi-001')
        
        self.session = requests.Session()
        if self.api_key:
            self.session.headers['Authorization'] = f'Bearer {self.api_key}'
        
        print(f"🌐 OpenClaw Gateway: {self.gateway_url}")
    
    def send(self, text):
        """
        Sendet Text an OpenClaw und gibt die Antwort zurück.
        text: String (erkannte Sprache)
        returns: String (Javis' Antwort)
        """
        try:
            # OpenClaw Gateway Voice Endpoint
            url = f"{self.gateway_url}/v1/voice/process"
            
            payload = {
                "text": text,
                "session_id": self.session_id,
                "language": "de"
            }
            
            response = self.session.post(url, json=payload, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            return data.get('response', '')
        
        except requests.exceptions.ConnectionError:
            return "Entschuldigung, ich bin gerade nicht erreichbar."
        
        except requests.exceptions.Timeout:
            return "Entschuldigung, die Anfrage hat zu lange gedauert."
        
        except Exception as e:
            print(f"❌ OpenClaw API Fehler: {e}")
            return "Entschuldigung, es ist ein Fehler aufgetreten."
    
    def send_audio(self, audio_path, text=None):
        """Sendet Audio-Datei an OpenClaw"""
        try:
            url = f"{self.gateway_url}/v1/voice/audio"
            
            files = {'audio': open(audio_path, 'rb')}
            data = {'session_id': self.session_id}
            if text:
                data['text'] = text
            
            response = self.session.post(url, files=files, data=data, timeout=120)
            response.raise_for_status()
            
            return response.json()
        
        except Exception as e:
            print(f"❌ Audio Upload Fehler: {e}")
            return None
