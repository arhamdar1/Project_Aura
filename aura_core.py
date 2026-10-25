# ============================================================
# aura_core.py — AURA ka dimagh 🧠 (main file)
# Flow: Suno (Whisper) -> Samjho (Router) -> Bolo (Piper)
# Fix: English bolo to seedha English, sirf Urdu ho to translate
#      + recording wapas fixed 8 second (smart mode optional)
# ============================================================

import difflib                # milte julte naam dhoondne ke liye ("not pad" -> "notepad")
import io                     # awaaz ko memory mein rakhne ke liye
import re                     # text saaf karne ke liye
import threading              # audio lock (reminder aur recording takrayein nahi)
import wave                   # .wav format padhne/likhne ke liye
from collections import deque # bolne se thora pehle ki awaaz yaad rakhne ke liye
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

# Apps/websites ke saare naam (fuzzy match ke liye)
try:
    from actions import ALL_TARGETS
except Exception:
    ALL_TARGETS = []

# Speaker mute karne ke liye (system_control wala volume control)
try:
    from system_control import get_volume_control
    VOLUME_OK = True
except Exception:
    VOLUME_OK = False

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
VOICE_PATH = "voices/en_US-lessac-medium.onnx"
MAX_HISTORY = 11              # kitne purane messages yaad rakhe

# ---- Listening (sunna) ----
# "base"   = sab se tez, lekin accent par kamzor
# "small"  = achha balance ✅
# "medium" = sab se behtar accent, lekin slow
WHISPER_MODEL = "small"

# "auto"    = English ho to seedha English, Urdu/Roman Urdu ho to English mein translate 🌍
# "english" = hamesha English samjho (translate kabhi nahi)
LISTEN_MODE = "auto"
ENGLISH_MIN_CHANCE = 0.25     # English ka chance itna ho to English hi maano

BEAM_SIZE = 5                 # 1 = tez, 5 = zyada sahi

# ---- Recording ----
# "fixed" = hamesha FIXED_SECONDS tak record ✅ (pehle wala, bharosemand)
# "smart" = chup hote hi ruk jaye (agar fixed pasand na aaye to try karein)
RECORD_MODE = "fixed"
FIXED_SECONDS = 8

SAMPLE_RATE = 16000           # Whisper 16000 Hz audio chahta hai
SILENCE_SECONDS = 1.8         # (smart) itni der chup rahein to recording khatam
WAIT_FOR_SPEECH = 6           # (smart) itni der tak kuch na bolein to "didn't hear"
MAX_RECORD_SECONDS = 15       # (smart) zyada se zyada itni lambi recording
CALIBRATE_SECONDS = 0.3       # (smart) shuru mein kamre ka shor naapne ka waqt
NOISE_MULTIPLIER = 2.5        # (smart) awaaz shor se kitni guna tez ho to "bolna" samjho
MIN_THRESHOLD = 0.004         # (smart) bilkul khamosh kamre ke liye kam se kam had
BLOCK_SECONDS = 0.03          # (smart) har 30 ms baad awaaz check

# True = sunte waqt laptop ki awaaz mute (video/gaane ki awaaz mic mein na jaye)
MUTE_WHILE_LISTENING = True

GREETING = "Hello, I am AURA. How can I help you?"   # shuru wali greeting 👋

# Whisper ko pehle se batao ke ye words aksar aayenge, taake sahi likhe
WHISPER_HINT = ("AURA, Notepad, WhatsApp, YouTube, LMS, UMT, student portal, Chrome, "
                "VS Code, Spotify, Bluetooth, WiFi, Pomodoro, study mode, reminder, timer.")

SYSTEM_PROMPT = (
    "You are AURA (Automated Ultra-Responsive Assistant), a friendly, smart and "
    "private desktop voice assistant running fully offline on the user's laptop. "
    "The user is from Pakistan and may mix Urdu and English. "
    "ALWAYS reply in clear, simple English, never in Urdu or Roman Urdu. "
    "Keep answers short and clear (2-3 sentences) because they will be spoken aloud. "
    "Do not use markdown, bullet points, emojis or special symbols. "
    "If live information is given to you, use it to answer accurately. "
    "Answer ONLY the user's latest message. Never repeat one of your previous answers. "
    "If the message is unclear or looks like a misheard command, say you did not "
    "understand and ask the user to say it again."
)

# Ye commands hain. Samajh na aayein to Llama ke paas NAHI bhejni
COMMAND_VERBS = ("open", "close", "launch", "quit", "exit", "kill")
FILLER_WORDS = {"the", "my", "app", "application", "please", "website", "tab", "a", "an"}


# ============================================================
# MODELS LOAD KARNA (sirf aik dafa, start par)
# ============================================================
def load_whisper():
    """NVIDIA GPU ho to us par, warna CPU par Whisper load karo."""
    device, compute = "cpu", "int8"
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() > 0:
            device, compute = "cuda", "float16"
    except Exception:
        pass

    try:
        model = WhisperModel(WHISPER_MODEL, device=device, compute_type=compute)
    except Exception as e:
        if device != "cuda":
            raise
        print(f"   ⚠️ GPU par load nahi hua ({e}), CPU use kar rahe hain")
        device = "cpu"
        model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")

    print(f"   🖥️ Whisper '{WHISPER_MODEL}' chal raha hai: {device.upper()}")
    return model


print(f"⏳ Loading Whisper ({WHISPER_MODEL})...")
whisper = load_whisper()

print("⏳ Loading Piper voice...")
voice = PiperVoice.load(VOICE_PATH)

print("✅ AURA is ready!\n")

history = []                      # baat-cheet ki yaadasht
audio_lock = threading.Lock()     # aik waqt mein sirf aik kaam: ya sunna ya bolna


# ============================================================
# 1) SUNNA 🎤
# ============================================================
def mute_speakers():
    """Laptop ki awaaz mute karo. Wapas: (volume control, pehle se mute tha ya nahi)."""
    if not (MUTE_WHILE_LISTENING and VOLUME_OK):
        return None, None
    try:
        vol = get_volume_control()
        was_muted = bool(vol.GetMute())
        vol.SetMute(1, None)
        return vol, was_muted
    except Exception as e:
        print(f"   ⚠️ Mute nahi ho saka: {e}")
        return None, None


def restore_speakers(vol, was_muted):
    """Awaaz wapas on karo (agar pehle se mute nahi thi)."""
    if vol is None or was_muted:
        return
    try:
        vol.SetMute(0, None)
    except Exception as e:
        print(f"   ⚠️ Unmute nahi ho saka: {e}")


def record_fixed():
    """Hamesha FIXED_SECONDS tak record."""
    print("🎤 Listening... speak now!")
    audio = sd.rec(int(FIXED_SECONDS * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                   channels=1, dtype="float32")
    sd.wait()
    return audio.flatten()


def record_smart():
    """
    Smart recording (optional):
    shor naapo -> bolna shuru hone ka intezar -> chup hote hi ruk jao
    """
    block = int(SAMPLE_RATE * BLOCK_SECONDS)
    pre_roll = deque(maxlen=int(0.5 / BLOCK_SECONDS))   # bolne se 0.5 sec pehle ki awaaz bhi rakho
    chunks = []
    started = False
    silence = 0.0
    elapsed = 0.0

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                        blocksize=block) as stream:
        calib = [stream.read(block)[0] for _ in range(int(CALIBRATE_SECONDS / BLOCK_SECONDS))]
        noise = float(np.sqrt(np.mean(np.concatenate(calib) ** 2)))
        threshold = max(noise * NOISE_MULTIPLIER, MIN_THRESHOLD)
        print(f"   🎚️ Shor: {noise:.4f} | Had: {threshold:.4f}")
        print("🎤 Listening... speak now!")

        while True:
            data, _ = stream.read(block)
            elapsed += BLOCK_SECONDS
            level = float(np.sqrt(np.mean(data ** 2)))

            if level > threshold:
                if not started:
                    started = True
                    chunks.extend(pre_roll)
                silence = 0.0
            elif started:
                silence += BLOCK_SECONDS

            if started:
                chunks.append(data)
            else:
                pre_roll.append(data)

            if started and silence >= SILENCE_SECONDS:
                break
            if not started and elapsed >= WAIT_FOR_SPEECH:
                break
            if elapsed >= MAX_RECORD_SECONDS:
                break

    if not chunks:
        return None
    return np.concatenate(chunks).flatten()


def english_chance(audio):
    """
    Whisper se pucho: is awaaz ke English hone ka kitna chance hai?
    Wapas: (english_chance, sab se zyada chance wali zubaan, us ka chance)
    """
    try:
        lang, prob, all_probs = whisper.detect_language(audio)
        return dict(all_probs).get("en", 0.0), lang, prob
    except Exception as e:
        print(f"   ⚠️ Zubaan pehchan nahi saka ({e}), English maan rahe hain")
        return 1.0, "en", 1.0


def transcribe(audio):
    """Awaaz -> English text. English ho to seedha, Urdu ho to translate."""
    task, language = "transcribe", "en"

    if LISTEN_MODE == "auto":
        en, lang, prob = english_chance(audio)
        if en >= ENGLISH_MIN_CHANCE:
            print(f"   🌍 English ({en:.0%}) -> seedha likh rahe hain")
        else:
            task, language = "translate", lang
            print(f"   🌍 {lang} ({prob:.0%}) -> English mein translate")

    segments, _ = whisper.transcribe(
        audio,
        task=task,
        language=language,
        beam_size=BEAM_SIZE,
        vad_filter=True,
        condition_on_previous_text=False,       # purani baat se ghalat andaze na lagaye
        initial_prompt=WHISPER_HINT,            # 🎯 "notepad" ko "not pad" na likhe
    )
    return " ".join(seg.text for seg in segments).strip()


def listen():
    with audio_lock:              # recording ke dauraan reminder intezar kare
        vol, was_muted = mute_speakers()      # 🔇 video/gaane ki awaaz band
        try:
            audio = record_smart() if RECORD_MODE == "smart" else record_fixed()
        finally:
            restore_speakers(vol, was_muted)  # 🔊 awaaz wapas (error aaye tab bhi)

    if audio is None or len(audio) < SAMPLE_RATE * 0.3:
        return ""
    print("⏹️ Processing...")
    return transcribe(audio)


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
                  f"Using the live information above, answer this in English: {text}")
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
# 5) FUZZY COMMAND 🔧 ("close not pad" -> "close notepad")
# ============================================================
def fuzzy_command(text):
    """
    Open/close wali command jo pehchani nahi gayi:
    - milta julta app/website naam ho to wahi chala do
    - kuch na mile to "samajh nahi aaya" bolo (Llama ke paas mat bhejo)
    """
    words = re.sub(r"[^\w\s]", " ", text.lower()).split()

    verb, rest = None, []
    for i, w in enumerate(words[:3]):            # command shuru mein hoti hai
        if w in COMMAND_VERBS:
            verb = w
            rest = [x for x in words[i + 1:] if x not in FILLER_WORDS]
            break
    if not verb or not rest:
        return None

    phrase = " ".join(rest)
    for candidate in (phrase, phrase.replace(" ", "")):   # "not pad" aur "notpad" dono try
        match = difflib.get_close_matches(candidate, ALL_TARGETS, n=1, cutoff=0.75)
        if match:
            print(f"   🔧 Samjha: '{phrase}' -> '{match[0]}'")
            return handle_command(f"{verb} {match[0]}")

    return f"Sorry, I couldn't find an app or website called {phrase}. Please say it again."


# ============================================================
# 6) ROUTER 🚦: kaun sambhalega? (upar se neeche check hota hai)
# ============================================================
ROUTES = [
    handle_priority,     # (a) typing + reminders/timers/alarms
    handle_whatsapp,     # (b) WhatsApp message
    handle_umt,          # (c) UMT LMS + portal
    handle_system,       # (d) volume, brightness, wifi, bluetooth, files
    handle_student,      # (e) deadlines + study mode
    handle_daily,        # (f) YouTube, Google, music, notes, health, windows
    handle_command,      # (g) apps/websites kholna aur band karna
    fuzzy_command,       # (h) milta julta naam / samajh na aane wali command
]


def process(text):
    for route in ROUTES:
        reply = route(text)
        if reply:
            print(f"   🛣️ Route: {route.__name__}")     # kis ne sambhala (debugging ke liye)
            return reply

    print("   🛣️ Route: Llama")
    context = get_live_context(text)     # (i) Live data + Llama
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