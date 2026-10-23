# ==========================================================
# AURA - Actions (App Launcher + WhatsApp Router)
# Ye file AURA ke "haath paon" hai: jo kaam wo khud kar sakti hai.
# ==========================================================

import re                              # Text saaf karne ke liye
import subprocess                      # Windows par apps chalane ke liye
import webbrowser                      # Websites browser mein kholne ke liye
from whatsapp import handle_whatsapp   # 🆕 WhatsApp messaging

# ----------------------------------------------------------
# 🖥️ APPS: "jo aap bolenge" -> "Windows ki command"
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
    "terminal": "wt",

    # --- MS Office ---
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
    "whatsapp": "whatsapp:",
}

# ----------------------------------------------------------
# 🌐 WEBSITES: "jo aap bolenge" -> "website ka link"
# ----------------------------------------------------------
WEBSITES = {
    # --- 🎓 UMT ---
    "umt lms": "https://lms.umt.edu.pk",
    "lms": "https://lms.umt.edu.pk",
    "student portal": "https://online.umt.edu.pk",
    "umt portal": "https://online.umt.edu.pk",
    "portal": "https://online.umt.edu.pk",
    "umt website": "https://www.umt.edu.pk",

    # --- 🎵 Entertainment ---
    "youtube": "https://www.youtube.com",
    "spotify": "https://open.spotify.com",
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

OPEN_WORDS = ["open", "launch", "start"]


def clean_text(text):
    """'Open Chrome.' -> 'open chrome' (chhote huroof, punctuation hatao)"""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def find_target(text, dictionary):
    """Text mein dictionary ka koi naam dhoondo (lambe naam pehle)."""
    padded = f" {text} "
    for name in sorted(dictionary, key=len, reverse=True):
        if f" {name} " in padded:
            return name
    return None


def open_thing(text):
    """App ya website kholo. Kuch na mile to None."""
    app = find_target(text, APPS)
    if app:
        subprocess.Popen(f'start "" {APPS[app]}', shell=True)
        return f"Opening {app}."

    site = find_target(text, WEBSITES)
    if site:
        webbrowser.open(WEBSITES[site])
        return f"Opening {site}."

    return None


# ==========================================================
# 🚦 ROUTER
# ==========================================================
def handle_command(text):
    """
    Command ho to kaam karo aur jawab do, warna None (phir Llama jawab dega).
    """
    # 1) 🆕 WhatsApp message? (Sab se pehle check, taake "send whatsapp..."
    #    ko ghalti se sirf "open whatsapp" na samjha jaye)
    whatsapp_reply = handle_whatsapp(text)
    if whatsapp_reply:
        return whatsapp_reply

    # 2) App ya website kholni hai?
    clean = clean_text(text)
    words = clean.split()

    if any(word in words for word in OPEN_WORDS):
        result = open_thing(clean)
        if result:
            return result
        if words and words[0] in OPEN_WORDS:
            return "Sorry, I don't know how to open that yet."

    return None