# ============================================================
# aura_core.py — AURA ka dimagh 🧠 (main file)
# Flow: Suno (Whisper) -> Samjho (Router) -> Bolo (Piper)
# ============================================================

import io                     # awaaz ko memory mein rakhne ke liye
import threading              # audio lock (reminder aur recording takrayein nahi)
import wave                   # .wav format padhne/likhne ke liye
from datetime import datetime # aaj ki date aur time

import numpy as np            # audio data ke liye
import sounddevice as sd      # mic se record + speaker par play
import ollama                 # Llama 3.2 se baat karne ke liye
from faster_whisper import WhisperModel   # awaaz -> text
from piper import PiperVoice              # text -> awaaz

# ---- AURA ke apne modules ----
from actions import handle_command                        # apps/websites kholna aur band karna
from whatsapp import handle_whatsapp                      # WhatsApp message
from system_control import handle_system                  # volume, brightness, wifi, files
from daily_tools import handle_priority, handle_daily, set_speaker   # reminders, music, notes...
from student_tools import handle_student, set_speaker as set_student_speaker   # deadlines, study mode
from umt import handle_umt, start_auto_sync, set_speaker as set_umt_speaker    # UMT LMS
from web_search import needs_search, search_web           # Tavily web search

# Weather module (load na ho to bhi AURA chalti rahe)
try:
    from weather import is_weather_question, find_city, get_weather
    WEATHER_OK = True
except Exception as e:
    print(f"⚠️ weather.py load nahi hui: {e}")
    WEATHER_OK = False


# ============================================================
# SETTINGS
# ============================================================
LLM_MODEL = "llama3.2:3b"
WHISPER_MODEL = "base"        # zyada accuracy chahiye to "small" (thora slow)
VOICE_PATH = "voices/en_US-lessac-medium.onnx"
SAMPLE_RATE = 16000           # Whisper 16000 Hz audio chahta hai
DURATION = 8                  # kitne second record kare
MAX_HISTORY = 11              # kitne purane messages yaad rakhe

GREETING = "Hello, I am AURA. How can I help you?"   # shuru wali greeting 👋

SYSTEM_PROMPT = (
    "You are AURA (Automated Ultra-Responsive Assistant), a friendly, smart and "
    "private desktop voice assistant running fully offline on the user's laptop. "
    "Keep answers short and clear (2-3 sentences) because they will be spoken aloud. "
    "Do not use markdown, bullet points, emojis or special symbols. "
    "If live information is given to you, use it to answer accurately."
)


# ============================================================
# MODELS LOAD KARNA (sirf aik dafa, start par)
# ============================================================
print("⏳ Loading Whisper...")
whisper = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")

print("⏳ Loading Piper voice...")
voice = PiperVoice.load(VOICE_PATH)

print("✅ AURA is ready!\n")

history = []                      # baat-cheet ki yaadasht
audio_lock = threading.Lock()     # aik waqt mein sirf aik kaam: ya sunna ya bolna


# ============================================================
# 1) SUNNA 🎤
# ============================================================
def listen():
    with audio_lock:              # recording ke dauraan reminder intezar kare
        print("🎤 Listening... speak now!")
        audio = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                       channels=1, dtype="float32")
        sd.wait()
    print("⏹️ Processing...")

    segments, _ = whisper.transcribe(
        audio.flatten(),
        language="en",
        beam_size=1,
        vad_filter=True,
    )
    return " ".join(seg.text for seg in segments).strip()


# ============================================================
# 2) BOLNA 🔊
# ============================================================
def speak(text):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)

    buffer.seek(0)
    with wave.open(buffer, "rb") as wav_file:
        rate = wav_file.getframerate()
        frames = wav_file.readframes(wav_file.getnframes())

    audio = np.frombuffer(frames, dtype=np.int16)
    with audio_lock:              # do awaazein aik saath na bajein
        sd.play(audio, rate)
        sd.wait()


# Reminders, study mode aur LMS ko bolne ke liye speak() de do
set_speaker(speak)
set_student_speaker(speak)
set_umt_speaker(speak)


# ============================================================
# 3) LIVE DATA 🌐
# ============================================================
def get_live_context(text):
    """Weather ya taaza khabar ka sawal ho to live data lao. Warna None."""
    if WEATHER_OK and is_weather_question(text):
        print("🌐 Searching the web...")
        try:
            data = get_weather(find_city(text))
            if data:
                print("   🌞 Live data: Open-Meteo")
                return data
        except Exception as e:
            print(f"   ⚠️ Weather fail: {e}")

    if needs_search(text):
        try:
            return search_web(text)
        except Exception as e:
            print(f"   ⚠️ Search fail: {e}")
    return None


# ============================================================
# 4) SOCHNA 🧠
# ============================================================
def think(text, context=None):
    global history

    now = datetime.now().strftime("%A, %d %B %Y, %I:%M %p")
    system = {"role": "system",
              "content": f"{SYSTEM_PROMPT} Current date and time: {now}."}

    if context:
        prompt = (f"Live information:\n{context}\n\n"
                  f"Using the live information above, answer this: {text}")
    else:
        prompt = text

    messages = [system] + history + [{"role": "user", "content": prompt}]

    print("🧠 Thinking...")
    response = ollama.chat(model=LLM_MODEL, messages=messages)
    reply = response["message"]["content"].strip()

    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": reply})
    history = history[-MAX_HISTORY:]

    return reply


# ============================================================
# 5) ROUTER 🚦: kaun sambhalega? (upar se neeche check hota hai)
# ============================================================
ROUTES = [
    handle_priority,     # (a) typing + reminders/timers/alarms
    handle_whatsapp,     # (b) WhatsApp message
    handle_umt,          # (c) UMT LMS + portal
    handle_system,       # (d) volume, brightness, wifi, bluetooth, files
    handle_student,      # (e) deadlines + study mode
    handle_daily,        # (f) YouTube, Google, music, notes, health, windows
    handle_command,      # (g) apps/websites kholna aur band karna
]


def process(text):
    for route in ROUTES:
        reply = route(text)
        if reply:
            print(f"   🛣️ Route: {route.__name__}")     # kis ne sambhala (debugging ke liye)
            return reply

    print("   🛣️ Route: Llama")
    context = get_live_context(text)     # (h) Live data + Llama
    return think(text, context)


# ============================================================
# MAIN LOOP 🔁
# ============================================================
def main():
    print(f"🤖 AURA: {GREETING}")
    speak(GREETING)
    start_auto_sync()                    # LMS background mein check hota rahega

    while True:
        choice = input("\n▶️ Press Enter and speak  (type 'q' to quit): ")
        if choice.strip().lower() == "q":
            print("👋 AURA is going to sleep. Goodbye!")
            speak("Goodbye!")
            break

        text = listen()
        if not text:
            print("⚠️ I didn't hear anything, please try again.")
            continue

        print(f"🧑 You: {text}")

        try:
            reply = process(text)
        except Exception as e:
            print(f"❌ Error: {e}")
            reply = "Sorry, something went wrong. Please try again."

        print(f"🤖 AURA: {reply}")
        speak(reply)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 AURA is going to sleep. Goodbye!")