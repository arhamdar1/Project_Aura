# ==========================================================
# AURA - Phase 1: Core Voice Loop (English Only)
# Listen (Whisper) -> Think (Llama 3.2) -> Speak (Piper)
# ==========================================================

import io                                # Awaz ko file ki jagah memory mein rakhne ke liye
import wave                              # .wav audio format handle karne ke liye
import numpy as np                       # Audio data ko numbers mein badalne ke liye
import sounddevice as sd                 # Mic (recording) aur speaker (playback)
import ollama                            # Local Llama se baat karne ke liye
from faster_whisper import WhisperModel  # Awaz -> text
from piper import PiperVoice             # Text -> awaz

# ==========================================================
# SETTINGS (yahan se AURA ka behavior badal sakte hain)
# ==========================================================
SAMPLE_RATE = 16000                             # Whisper ka standard audio rate
DURATION = 5                                    # Har baar kitne second sunna hai
WHISPER_MODEL = "small"                         # Tez karna ho to "small.en" ya "base.en" try karein
LLM_MODEL = "llama3.2:3b"                       # Ollama wala model
VOICE_PATH = "voices/en_US-lessac-medium.onnx"  # AURA ki awaz

# Ye words bolne par AURA band ho jayegi
EXIT_WORDS = ["goodbye", "bye bye", "exit", "stop listening"]

# AURA ki "personality" aur rules. Llama har jawab se pehle ye parhta hai.
SYSTEM_PROMPT = """You are AURA, a friendly personal voice assistant running on the user's laptop.
Always reply in simple, clear English.
Keep every reply short: 1 to 3 sentences, because your answer will be spoken aloud.
Never use markdown, bullet points, emojis, or special symbols."""

# ==========================================================
# MODELS LOAD KARO (sirf aik dafa, program ke shuru mein)
# ==========================================================
print("🔄 AURA is waking up... (loading models)")
whisper = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
voice = PiperVoice.load(VOICE_PATH)

# Baat cheet ki "yaad dasht". Pehla message hamesha rules (system prompt) hota hai.
history = [{"role": "system", "content": SYSTEM_PROMPT}]

print("✅ AURA is ready!\n")


# ==========================================================
# 👂 FUNCTION 1: LISTEN (mic -> text)
# ==========================================================
def listen():
    print("🎤 Listening... speak now!")
    recording = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                       channels=1, dtype="float32")
    sd.wait()
    print("⏹️  Processing...")
    audio = recording.flatten()

    # language="en" -> Whisper ko pehle se bata diya ke sirf English hai.
    # Is se zubaan pehchanne ka waqt bachta hai aur ghalti kam hoti hai.
    segments, _ = whisper.transcribe(audio, beam_size=5, language="en")
    text = " ".join(seg.text.strip() for seg in segments)

    return text.strip()


# ==========================================================
# 🧠 FUNCTION 2: THINK (text -> Llama ka jawab)
# ==========================================================
def think(user_text):
    # User ki baat yaad-dasht mein daalo
    history.append({"role": "user", "content": user_text})

    # Poori baat cheet Llama ko bhejo taake wo pichli baatein bhi yaad rakhe
    response = ollama.chat(model=LLM_MODEL, messages=history)
    reply = response["message"]["content"].strip()

    # AURA ka jawab bhi yaad-dasht mein daalo
    history.append({"role": "assistant", "content": reply})

    # Yaad-dasht ko chhota rakho (rules + aakhri 10 messages), taake AURA slow na ho
    if len(history) > 11:
        history[:] = [history[0]] + history[-10:]

    return reply


# ==========================================================
# 🗣️ FUNCTION 3: SPEAK (text -> speaker)
# ==========================================================
def speak(text):
    # Awaz ko disk par file banaye baghair seedha memory (BytesIO) mein banao
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)

    # Memory wali awaz ko shuru se parho
    buffer.seek(0)
    with wave.open(buffer, "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        frames = wav_file.readframes(wav_file.getnframes())

    # Numbers mein badlo aur speaker par chalao
    audio = np.frombuffer(frames, dtype=np.int16)
    sd.play(audio, sample_rate)
    sd.wait()


# ==========================================================
# 🔁 MAIN LOOP: yahan AURA zinda hoti hai
# ==========================================================
greeting = "Hello! I am AURA. How can I help you today?"
print(f"🤖 AURA: {greeting}\n")
speak(greeting)

while True:
    choice = input("▶️  Press Enter and speak  (type 'q' to quit): ")
    if choice.strip().lower() == "q":
        break

    # 1) Listen
    user_text = listen()

    # Agar kuch sunai na diya ho to dobara try karo
    if not user_text:
        print("⚠️  I didn't hear anything, please try again.\n")
        continue

    print(f"🧑 You: {user_text}")

    # 2) Agar user ne "goodbye" jaisa kuch kaha to band karo
    if any(word in user_text.lower() for word in EXIT_WORDS):
        bye = "Goodbye! Have a great day."
        print(f"🤖 AURA: {bye}")
        speak(bye)
        break

    # 3) Think
    print("🧠 Thinking...")
    reply = think(user_text)
    print(f"🤖 AURA: {reply}\n")

    # 4) Speak
    speak(reply)

print("👋 AURA is going to sleep. Goodbye!")
