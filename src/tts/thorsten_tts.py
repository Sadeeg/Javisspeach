#!/usr/bin/env python3
"""Thorsten TTS - Deutsche Stimme"""

import os
import sys
import tempfile
from TTS.api import TTS


class ThorstenTTS:
    def __init__(self, config):
        tts_config = config['tts']
        self.model_name = tts_config.get('model', 'tts_models/de/thorsten/vits')
        self.output_file = tts_config.get('output_file', '/tmp/javis_response.wav')
        
        # Coqui TTS initialisieren
        print(f"🔊 Lade TTS Modell: {self.model_name}...")
        self.tts = TTS(model_name=self.model_name, progress_bar=False)
        print(f"✅ TTS geladen")
    
    def speak(self, text, output_file=None):
        """
        Generiert Sprache und speichert als WAV.
        text: String
        output_file: Optional, sonst self.output_file
        
        Returns: Pfad zur WAV-Datei
        """
        if output_file is None:
            output_file = self.output_file
        
        try:
            self.tts.tts_to_file(
                text=text,
                file_path=output_file
            )
            return output_file
        except Exception as e:
            print(f"❌ TTS Fehler: {e}")
            return None
    
    def speak_to_file(self, text, output_file):
        """Generiert Sprache direkt in angegebene Datei"""
        self.tts.tts_to_file(text=text, file_path=output_file)
        return output_file
