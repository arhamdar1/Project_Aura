# ==========================================================
# AURA - Phase 1, Test 1: Text-to-Speech (Piper)
# Ye script text ko awaz mein badal kar speaker par sunati hai.
# Pehle English voice bolegi, phir Urdu voice.
# ==========================================================

import wave                  # .wav (audio) files likhne/parhne ke liye (Python ke saath built-in)
import numpy as np           # Audio data ko numbers ki list mein badalne ke liye
import sounddevice as sd     # Speaker par awaz chalane ke liye
from piper import PiperVoice # Piper TTS: text ko awaz banane wala engine


def speak(voice_path, text, output_file):
    """
    Ye function 3 cheezein leta hai:
      voice_path  -> kaunsi awaz (.onnx file) use karni hai
      text        -> kya bolna hai
      output_file -> awaz kis .wav file mein save karni hai
    """

    # 1) Voice model load karo (.onnx file + uske saath wali .onnx.json khud load ho jati hai)
    print(f"🔄 Voice load ho rahi hai: {voice_path}")
    voice = PiperVoice.load(voice_path)

    # 2) Text ko awaz mein badal kar .wav file mein likho
    print("🎙️ Awaz ban rahi hai...")
    with wave.open(output_file, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)

    # 3) Wohi .wav file wapas parho taake speaker par chala sakein
    with wave.open(output_file, "rb") as wav_file:
        sample_rate = wav_file.getframerate()                   # Awaz ki "speed" setting (e.g. 22050)
        frames = wav_file.readframes(wav_file.getnframes())     # Poori awaz ka raw data

    # 4) Raw data ko numbers mein badlo (int16 = audio ka standard format)
    audio = np.frombuffer(frames, dtype=np.int16)

    # 5) Speaker par chalao, aur jab tak khatam na ho, intezaar karo
    print("🔊 Bol raha hoon...\n")
    sd.play(audio, sample_rate)
    sd.wait()


# ==========================================================
# Yahan se program shuru hota hai
# ==========================================================

# --- Test 1: English voice ---
speak(
    voice_path="voices/en_US-lessac-medium.onnx",
    text="Hello! I am AURA, your personal assistant. My voice system is working perfectly.",
    output_file="test_english.wav",
)

# --- Test 2: Urdu voice (Urdu script mein text, Roman Urdu nahi) ---
speak(
    voice_path="voices/ur_PK-fasih-medium.onnx",
    text="السلام علیکم! میں آؤرا ہوں، آپ کی ذاتی اسسٹنٹ۔",
    output_file="test_urdu.wav",
)

print("✅ Test mukammal! Dono awazein chal gayin.")