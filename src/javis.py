#!/usr/bin/env python3
"""JavisVoice - Hauptprogramm"""

import time
import signal
import sys
import yaml
import threading
import numpy as np
import pyaudio
from pathlib import Path

from src.wakeword.porcupine_wake import PorcupineWakeWord
from src.vad.webrtc_vad import WebRTCVAD
from src.stt.whisper_stt import WhisperSTT
from src.tts.thorsten_tts import ThorstenTTS
from src.api.openclaw_client import OpenClawClient

# States
STATE_STANDBY = "standby"
STATE_WAKE = "wake"
STATE_LISTEN = "listen"
STATE_PROCESS = "process"
STATE_RESPOND = "respond"

class JavisVoice:
    def __init__(self, config_path="config/config.yaml"):
        self.config = self._load_config(config_path)
        self.state = STATE_STANDBY
        
        # Audio
        self.audio = pyaudio.PyAudio()
        self.stream_in = None
        self.stream_out = None
        
        # Components
        self.wake_word = PorcupineWakeWord(self.config)
        self.vad = WebRTCVAD(self.config)
        self.stt = WhisperSTT(self.config)
        self.tts = ThorstenTTS(self.config)
        self.api = OpenClawClient(self.config)
        
        # State
        self.running = True
        self.audio_buffer = []
        
        # Setup
        self._setup_audio()
        self._setup_signal_handlers()
    
    def _load_config(self, path):
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    
    def _setup_audio(self):
        """Audio-Stream initialisieren"""
        audio_config = self.config['audio']
        self.stream_in = self.audio.open(
            format=pyaudio.paInt16,
            channels=audio_config['channels'],
            rate=audio_config['sample_rate'],
            input=True,
            input_device_index=audio_config['device_index'],
            frames_per_buffer=audio_config['chunk_size']
        )
        
        # Output stream for TTS
        self.stream_out = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=22050,
            output=True
        )
    
    def _setup_signal_handlers(self):
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        print("\n🛑 Shutdown...")
        self.running = False
    
    def _audio_generator(self):
        """Kontinuierlicher Audio-Generator für Wake Word"""
        chunk_size = self.config['audio']['chunk_size']
        while self.running:
            try:
                data = self.stream_in.read(chunk_size, exception_on_overflow=False)
                yield np.frombuffer(data, dtype=np.int16)
            except Exception as e:
                print(f"Audio error: {e}")
                break
    
    def _play_feedback(self):
        """Spiele Feedback-Ton nach Wake Word"""
        # Kurzer Piep-Ton
        import struct
        import math
        
        sample_rate = 22050
        duration = 0.1  # 100ms
        frequency = 880  # A5
        
        samples = []
        for i in range(int(sample_rate * duration)):
            t = i / sample_rate
            value = int(32767 * math.sin(2 * math.pi * frequency * t))
            samples.append(struct.pack('<h', value))
        
        audio_data = b''.join(samples)
        self.stream_out.write(audio_data)
    
    def _play_audio_file(self, filepath):
        """Spiele WAV-Datei ab"""
        import wave
        import struct
        
        wf = wave.open(filepath, 'rb')
        chunk_size = 1024
        
        data = wf.readframes(chunk_size)
        while data:
            self.stream_out.write(data)
            data = wf.readframes(chunk_size)
        
        wf.close()
    
    def process(self):
        """Hauptschleife"""
        print("🎤 JavisVoice gestartet!")
        print(f"   Warte auf Wake Word: '{self.config['wake_word']['keyword']}'")
        print("   Drücke Ctrl+C zum Beenden\n")
        
        audio_gen = self._audio_generator()
        
        for audio_chunk in audio_gen:
            if not self.running:
                break
            
            if self.state == STATE_STANDBY:
                # Wake Word Detection
                if self.wake_word.is_wake_word(audio_chunk):
                    print(f"\n👋 Wake Word erkannt!")
                    self._play_feedback()
                    self.state = STATE_LISTEN
                    self.audio_buffer = []
            
            elif self.state == STATE_LISTEN:
                # Audio sammeln + VAD
                self.audio_buffer.append(audio_chunk)
                
                is_speech = self.vad.is_speech(audio_chunk.tobytes())
                
                if len(self.audio_buffer) > 200:  # ~6 Sekunden Max
                    print("⏱️  Max. Aufnahmelänge erreicht")
                    self.state = STATE_PROCESS
            
            elif self.state == STATE_PROCESS:
                # Audio an STT → API → TTS
                print("🎙️  Verarbeite...")
                
                # Audio zusammenfügen
                audio_data = np.concatenate(self.audio_buffer)
                
                # STT
                text = self.stt.transcribe(audio_data)
                print(f"   Erkannt: {text}")
                
                if text.strip():
                    # API Call
                    response = self.api.send(text)
                    print(f"   Javis: {response}")
                    
                    # TTS
                    tts_file = self.tts.speak(response)
                    self._play_audio_file(tts_file)
                else:
                    print("   (Keine Sprache erkannt)")
                
                self.state = STATE_STANDBY
                self.audio_buffer = []
        
        self.cleanup()
    
    def cleanup(self):
        """Aufräumen"""
        print("🧹 Aufräumen...")
        if self.stream_in:
            self.stream_in.stop_stream()
            self.stream_in.close()
        if self.stream_out:
            self.stream_out.stop_stream()
            self.stream_out.close()
        self.audio.terminate()
        print("✅ Bis bald!")


def main():
    config_path = Path(__file__).parent / "config" / "config.yaml"
    javis = JavisVoice(str(config_path))
    javis.process()


if __name__ == "__main__":
    main()
