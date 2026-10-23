# ==========================================================
# AURA - Core Voice Loop (Phase 2.2)
# Listen -> Router -> [Action | Web Search + Think | Think] -> Speak
# ==========================================================

import io                                # Awaz ko memory mein rakhne ke liye
import wave                              # .wav audio format
import numpy as np                       # Audio data -> numbers
import sounddevice as sd                 # Mic aur speaker
import ollama                            # Local Llama
from datetime import datetime            # Aaj ki date/time ke liye
from faster_whisper import WhisperModel  # Awaz -> text
from piper import PiperVoice             # Text -> awaz
from actions import handle_command       # App launcher router
from web_search import needs_search, search_web  # Web search

# ==========================================================
# SETTINGS
# ==========================================================
SAMPLE_RATE = 16000
DURATION = 5
WHISPER_MODEL = "small"
LLM_MODEL = "llama3.2:3b"
VOICE_PATH = "voices/en_US-lessac-medium.onnx"

EXIT_WORDS = ["goodbye", "bye bye", "exit", "stop listening"]

SYSTEM_PROMPT = """You are AURA, a friendly personal voice assistant running on the user's laptop.
Always reply in simple, clear English.
Keep every reply short: 1 to 3 sentences, because your answer will be spoken aloud.
Never use markdown, bullet points, emojis, special symbols, or web links."""

# ==========================================================
# MODELS LOAD KARO
# ==========================================================
print("🔄 AURA is waking up... (loading models)")
whisper = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
voice = PiperVoice.load(VOICE_PATH)

history = [{"role": "system", "content": SYSTEM_PROMPT}]

print("✅ AURA is ready!\n")


# ==========================================================
# 👂 LISTEN
# ==========================================================
def listen():
    print("🎤 Listening... speak now!")
    recording = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                       channels=1, dtype="float32")
    sd.wait()
    print("⏹️  Processing...")
    audio = recording.flatten()

    segments, _ = whisper.transcribe(audio, beam_size=5, language="en")
    text = " ".join(seg.text.strip() for seg in segments)
    return text.strip()


# ==========================================================
# 🧠 THINK (web results ke saath bhi soch sakti hai)
# ==========================================================
def think(user_text, context=None):
    # Har dafa system prompt mein taza date/time daalo
    now = datetime.now().strftime("%A, %d %B %Y, %I:%M %p")
    history[0]["content"] = SYSTEM_PROMPT + f"\nCurrent date and time: {now}."

    # Agar web results hain to unhein sawaal ke saath jod do
    if context:
        prompt = (
            "Answer the question using these fresh web search results. "
            "If the results do not contain the answer, say you could not find it.\n\n"
            f"{context}\n\nQuestion: {user_text}"
        )
    else:
        prompt = user_text

    # Llama ko yaad-dasht + naya sawaal bhejo
    messages = history + [{"role": "user", "content": prompt}]
    response = ollama.chat(model=LLM_MODEL, messages=messages)
    reply = response["message"]["content"].strip()

    # Yaad-dasht mein sirf asal sawaal rakho (lambe search results nahi)
    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": reply})

    if len(history) > 11:
        history[:] = [history[0]] + history[-10:]

    return reply


# ==========================================================
# 🗣️ SPEAK
# ==========================================================
def speak(text):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)

    buffer.seek(0)
    with wave.open(buffer, "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        frames = wav_file.readframes(wav_file.getnframes())

    audio = np.frombuffer(frames, dtype=np.int16)
    sd.play(audio, sample_rate)
    sd.wait()


# ==========================================================
# 🔁 MAIN LOOP
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
    if not user_text:
        print("⚠️  I didn't hear anything, please try again.\n")
        continue

    print(f"🧑 You: {user_text}")

    # 2) Goodbye?
    if any(word in user_text.lower() for word in EXIT_WORDS):
        bye = "Goodbye! Have a great day."
        print(f"🤖 AURA: {bye}")
        speak(bye)
        break

    # 3) Command? (open chrome, open lms...)
    action_reply = handle_command(user_text)
    if action_reply:
        print(f"⚡ AURA: {action_reply}\n")
        speak(action_reply)
        continue

    # 4) Taza info chahiye? -> Web search
    context = None
    if needs_search(user_text):
        print("🌐 Searching the web...")
        context = search_web(user_text)

    # 5) Think (search results ke saath ya baghair)
    print("🧠 Thinking...")
    reply = think(user_text, context)
    print(f"🤖 AURA: {reply}\n")

    # 6) Speak
    speak(reply)

print("👋 AURA is going to sleep. Goodbye!")