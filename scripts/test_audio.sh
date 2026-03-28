#!/bin/bash
# test_audio.sh - Audio-Geräte testen

echo "=========================================="
echo "  JavisVoice Audio Test"
echo "=========================================="

echo ""
echo "🎤 Verfügbare Mikrofone:"
echo "========================="
arecord -l

echo ""
echo "🔊 Verfügbare Speaker:"
echo "========================="
aplay -l

echo ""
echo "🎚️  Mikrofon-Pegel (5 Sekunden):"
echo "=================================="
echo "(Sprich etwas hinein!)"
echo ""
rec -c 1 -r 16000 /tmp/test_mic.wav trim 0 5 2>/dev/null || \
    arecord -d 5 -c 1 -r 16000 -f S16_LE /tmp/test_mic.wav
echo "Aufnahme gespeichert: /tmp/test_mic.wav"

echo ""
echo "▶️  Wiedergabe (Aufnahme abspielen):"
echo "====================================="
aplay /tmp/test_mic.wav

echo ""
echo "✅ Audio Test abgeschlossen!"
