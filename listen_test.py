# ==========================================================
# AURA - Phase 1, Test 2 (v3): Speech-to-Text (faster-whisper)
# English bolo -> English text
# Urdu bolo   -> Roman Urdu (ya English translation, setting ke hisaab se)
# ==========================================================

import sounddevice as sd                 # Mic se recording ke liye
from faster_whisper import WhisperModel  # Awaz -> text wala engine

# ---------- Settings ----------
SAMPLE_RATE = 16000   # Whisper ko 16000 Hz audio chahiye
DURATION = 5          # Kitne second record karna hai
MODEL_SIZE = "small"  # "tiny", "base", "small", "medium"

# 👇 YAHAN SWITCH KAREIN:
#   "roman"     -> Urdu ko English alphabets mein likhne ki koshish (Roman Urdu)
#   "translate" -> Urdu ko seedha English mein translate
URDU_MODE = "roman"

# Whisper Urdu ko kabhi "ur" aur kabhi "hi" (Hindi) samajhta hai
URDU_LIKE = ["ur", "hi"]

# Ye Roman Urdu ke misaali jumle Whisper ko "style" sikhate hain.
# Jitne zyada aap ke apne bolne jaise honge, utna behtar nateeja.
ROMAN_URDU_PROMPT = (
    "Assalam o alaikum. Aap kaise hain? Main theek hoon. "
    "Aaj mausam kaisa hai? Chrome open karo. "
    "Mujhe batao kya time hua hai. Shukriya."
)

# ---------- Model load karo ----------
print("🔄 Whisper model load ho raha hai...")
model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
print("✅ Model ready!\n")


def transcribe(audio):
    """
    Awaz leta hai aur text wapas karta hai.
    English -> English. Urdu -> Roman Urdu ya translation (URDU_MODE ke hisaab se).
    """
    # Pehla try: normal tareeqe se sun kar zubaan pehchano
    segments, info = model.transcribe(audio, beam_size=5, language=None)
    text = " ".join(seg.text.strip() for seg in segments)

    # Agar Urdu/Hindi nikli to dobara chalao
    if info.language in URDU_LIKE:

        if URDU_MODE == "roman":
            print("🔁 Urdu pehchani gayi, Roman Urdu mein likh raha hoon...")
            segments, _ = model.transcribe(
                audio,
                beam_size=5,
                language="en",                    # English alphabets mein likho
                initial_prompt=ROMAN_URDU_PROMPT, # Roman Urdu wala style dikhao
            )

        else:  # "translate"
            print("🔁 Urdu pehchani gayi, English mein translate kar raha hoon...")
            segments, _ = model.transcribe(audio, beam_size=5, task="translate")

        text = " ".join(seg.text.strip() for seg in segments)

    return text, info.language


# ---------- Baar baar test karne ke liye loop ----------
while True:
    choice = input("▶️  Enter dabayein aur 5 second bolein  (band karne ke liye 'q' likhein): ")
    if choice.strip().lower() == "q":
        print("👋 Allah Hafiz!")
        break

    # 1) Mic se record karo
    print("🎤 Sun raha hoon... bolein!")
    recording = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                       channels=1, dtype="float32")
    sd.wait()
    print("⏹️  Recording khatam. Soch raha hoon...")

    # 2) Recording ko seedhi list mein badlo, phir text banao
    audio = recording.flatten()
    text, language = transcribe(audio)

    # 3) Nateeja dikhao
    print(f"🌐 Pehchani gayi zubaan: {language}")
    print(f"📝 AURA ne samjha: {text}\n")