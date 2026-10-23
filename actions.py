# ==========================================================
# AURA - Phase 2.1: Actions (App Launcher)
# Ye file AURA ke "haath paon" hai: jo kaam wo khud kar sakti hai.
# ==========================================================

import re            # Text saaf karne ke liye (punctuation hatana)
import subprocess    # Windows par apps chalane ke liye
import webbrowser    # Websites browser mein kholne ke liye

# ----------------------------------------------------------
# 🖥️ APPS: "jo aap bolenge" -> "Windows ki command"
# Naya app add karna ho to bas yahan aik line likh dein.
# ----------------------------------------------------------
APPS = {
    # --- Browsers ---
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "msedge",
    "microsoft edge": "msedge",

    # --- Coding ---
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "command prompt": "cmd",
    "terminal": "wt",                    # Windows Terminal

    # --- MS Office (agar laptop mein installed hai) ---
    "word": "winword",
    "microsoft word": "winword",
    "excel": "excel",
    "microsoft excel": "excel",
    "powerpoint": "powerpnt",
    "power point": "powerpnt",

    # --- Windows ke apne apps ---
    "notepad": "notepad",
    "calculator": "calc",
    "paint": "mspaint",
    "file explorer": "explorer",
    "explorer": "explorer",
    "task manager": "taskmgr",
    "settings": "ms-settings:",
    "camera": "microsoft.windows.camera:",
    "microsoft store": "ms-windows-store:",

    # --- Messaging ---
    "whatsapp": "whatsapp:",             # WhatsApp Desktop
}

# ----------------------------------------------------------
# 🌐 WEBSITES: "jo aap bolenge" -> "website ka link"
# ----------------------------------------------------------
WEBSITES = {
    # --- 🎓 UMT (link ghalat ho to yahan apna asal link daal dein) ---
    "umt lms": "https://lms.umt.edu.pk",
    "lms": "https://lms.umt.edu.pk",
    "student portal": "https://online.umt.edu.pk",
    "umt portal": "https://online.umt.edu.pk",
    "portal": "https://online.umt.edu.pk",
    "umt website": "https://www.umt.edu.pk",

    # --- 🎵 Entertainment ---
    "youtube": "https://www.youtube.com",
    "spotify": "https://open.spotify.com",   # Spotify app ho to APPS mein "spotify": "spotify:" daal dein
    "netflix": "https://www.netflix.com",

    # --- 📚 Parhai / Kaam ---
    "google": "https://www.google.com",
    "google drive": "https://drive.google.com",
    "drive": "https://drive.google.com",
    "google classroom": "https://classroom.google.com",
    "classroom": "https://classroom.google.com",
    "google meet": "https://meet.google.com",
    "gmail": "https://mail.google.com",
    "outlook": "https://outlook.office.com",
    "canva": "https://www.canva.com",
    "wikipedia": "https://www.wikipedia.org",

    # --- 💻 Coding / AI ---
    "github": "https://github.com",
    "stack overflow": "https://stackoverflow.com",
    "chatgpt": "https://chat.openai.com",
    "claude": "https://claude.ai",

    # --- 📱 Social Media ---
    "facebook": "https://www.facebook.com",
    "instagram": "https://www.instagram.com",
    "linkedin": "https://www.linkedin.com",
    "twitter": "https://x.com",
    "x": "https://x.com",

    # --- 🛒 Shopping ---
    "daraz": "https://www.daraz.pk",
}

# Wo alfaaz jo "kholne" ka hukam dete hain
OPEN_WORDS = ["open", "launch", "start"]


def clean_text(text):
    """
    Whisper aksar "Open Chrome." likhta hai (bare huroof + full stop).
    Ye function sab chhote huroof kar deta hai aur punctuation hata deta hai.
    Misaal: "Open Chrome." -> "open chrome"
    """
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)   # Har punctuation ko space se badlo
    return " ".join(text.split())          # Faltu spaces hatao


def find_target(text, dictionary):
    """
    Text mein dictionary ka koi naam dhoondta hai.
    Lambe naam pehle check hote hain, taake "google drive" ko
    ghalti se sirf "google" na samajh liya jaye.
    """
    padded = f" {text} "
    for name in sorted(dictionary, key=len, reverse=True):
        if f" {name} " in padded:
            return name
    return None


def open_thing(text):
    """
    Text mein app ya website dhoond kar kholta hai.
    Jo khola, uska jawab (AURA ki boli) wapas karta hai.
    Kuch na mila to None.
    """
    # Pehle apps check karo
    app = find_target(text, APPS)
    if app:
        # 'start ""' Windows ki command hai jo app ko alag se chala deti hai
        subprocess.Popen(f'start "" {APPS[app]}', shell=True)
        return f"Opening {app}."

    # Phir websites check karo
    site = find_target(text, WEBSITES)
    if site:
        webbrowser.open(WEBSITES[site])
        return f"Opening {site}."

    return None


# ==========================================================
# 🚦 ROUTER: AURA ka traffic police
# ==========================================================
def handle_command(text):
    """
    User ki baat dekh kar faisla karta hai:
      - Agar koi command hai -> kaam karo aur jawab wapas do
      - Agar command nahi    -> None wapas do (phir Llama jawab dega)
    """
    clean = clean_text(text)
    words = clean.split()

    # Kya baat mein "open/launch/start" mein se koi lafz hai?
    if any(word in words for word in OPEN_WORDS):
        result = open_thing(clean)
        if result:
            return result

        # Agar jumla hi "open" se shuru hua tha lekin app pehchana nahi gaya
        if words and words[0] in OPEN_WORDS:
            return "Sorry, I don't know how to open that yet."

    # Koi command nahi mili -> Llama ko jawab dene do
    return None