#!/usr/bin/env python3
"""WebRTC Voice Activity Detection"""

import webrtcvad
import struct


class WebRTCVAD:
    def __init__(self, config):
        vad_config = config['vad']
        
        self.vad = webrtcvad.Vad(vad_config.get('aggressiveness', 3))
        self.sample_rate = config['audio']['sample_rate']
        self.frame_duration_ms = vad_config.get('frame_duration_ms', 30)
        self.silence_threshold_ms = vad_config.get('silence_threshold_ms', 1500)
        
        # Frames sammeln für Stille-Erkennung
        self.silence_frames = 0
        self.speech_frames = 0
        self.is_speaking = False
        
        # Berechne wie viele Frames Stille vor Aufnahmeschluss
        self.frames_for_silence = int(self.silence_threshold_ms / self.frame_duration_ms)
        
        print(f"🔇 VAD aktiv (WebRTC, Aggressiveness: {vad_config.get('aggressiveness', 3)})")
    
    def is_speech(self, audio_bytes):
        """
        Prüft ob im Audio-Frame Sprache enthalten ist.
        audio_bytes: Raw PCM Audio (16-bit, 16kHz)
        """
        try:
            # WebRTC VAD works on 10, 20, or 30 ms frames
            # Für 30ms @ 16kHz = 480 samples = 960 bytes
            frame_size = int(self.sample_rate * self.frame_duration_ms / 1000) * 2  # 2 bytes per sample
            
            if len(audio_bytes) < frame_size:
                return False
            
            # Prüfe ersten Frame
            frame = audio_bytes[:frame_size]
            
            is_speech = self.vad.is_speech(frame, self.sample_rate)
            
            if is_speech:
                self.speech_frames += 1
                self.silence_frames = 0
                self.is_speaking = True
            else:
                self.silence_frames += 1
                if self.silence_frames >= self.frames_for_silence:
                    self.is_speaking = False
            
            return is_speech
        
        except Exception as e:
            return False
    
    def reset(self):
        """Zähler zurücksetzen"""
        self.silence_frames = 0
        self.speech_frames = 0
        self.is_speaking = False
