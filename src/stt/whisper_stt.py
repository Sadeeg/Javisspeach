#!/usr/bin/env python3
"""Whisper Speech-to-Text"""

import whisper
import numpy as np
import tempfile
import wave


class WhisperSTT:
    def __init__(self, config):
        stt_config = config['stt']
        self.model_name = stt_config.get('model', 'medium')
        self.language = stt_config.get('language', 'de')
        self.device = stt_config.get('device', 'cpu')
        
        print(f"🎙️  Lade Whisper Modell: {self.model_name}...")
        self.model = whisper.load_model(self.model_name, device=self.device)
        print(f"✅ Whisper geladen (Device: {self.device})")
    
    def transcribe(self, audio_data):
        """
        Transkribiert Audio-Daten.
        audio_data: numpy array (int16)
        
        Returns: String (erkannter Text)
        """
        try:
            # Audio normalisieren und als Float32 konvertieren
            audio_float = audio_data.astype(np.float32) / 32768.0
            
            # An tempfile denken für langen Audio
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                temp_wav = f.name
            
            # WAV schreiben
            sample_rate = 16000
            with wave.open(temp_wav, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(sample_rate)
                wf.writeframes(audio_data.astype(np.int16).tobytes())
            
            # Transkribieren
            result = self.model.transcribe(
                temp_wav,
                language=self.language,
                fp16=False  # CPU mode
            )
            
            # Aufräumen
            import os
            os.unlink(temp_wav)
            
            text = result['text'].strip()
            return text
        
        except Exception as e:
            print(f"❌ STT Fehler: {e}")
            return ""
    
    def transcribe_file(self, filepath):
        """Transkribiert eine WAV-Datei"""
        result = self.model.transcribe(
            filepath,
            language=self.language,
            fp16=False
        )
        return result['text'].strip()
