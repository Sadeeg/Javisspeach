#!/usr/bin/env python3
"""Porcupine Wake Word Detection"""

import numpy as np
import pvporcupine


class PorcupineWakeWord:
    def __init__(self, config):
        self.config = config['wake_word']
        self.sample_rate = config['audio']['sample_rate']
        
        # Porcupine Access Key (kostenlos auf picovoice.ai)
        access_key = self.config.get('access_key', '')
        
        # Keywords: 'jarvis', 'alexa', 'hey google', etc.
        # oder eigenes .ppn Modell
        keyword = self.config.get('keyword', 'jarvis')
        
        try:
            self.porcupine = pvporcupine.create(
                access_key=access_key,
                keywords=[keyword],
                sensitivities=[self.config.get('sensitivity', 0.5)]
            )
            print(f"🔔 Wake Word '{keyword}' geladen (Porcupine)")
        except Exception as e:
            print(f"❌ Porcupine Fehler: {e}")
            print("   → Access Key in config.yaml eintragen (picovoice.ai/console)")
            raise
    
    def is_wake_word(self, audio_chunk):
        """Prüft ob Wake Word im Audio-Chunk enthalten ist"""
        try:
            # Konvertiere numpy array zu passendem Format
            pcm = audio_chunk.astype(np.int16)
            
            # Porcupine erwartet 16-bit PCM als bytes
            if pcm.dtype != np.int16:
                pcm = pcm.astype(np.int16)
            
            pcm_bytes = pcm.tobytes()
            
            # Process mit Porcupine
            result = self.porcupine.process(pcm_bytes)
            return result >= 0  # Index des erkannten Keywords
        except Exception as e:
            return False
    
    def release(self):
        """Ressourcen freigeben"""
        if hasattr(self, 'porcupine'):
            self.porcupine.delete()
