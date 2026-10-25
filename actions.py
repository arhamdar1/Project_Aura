# ============================================================
# actions.py — AURA ke "haath" 🖐️
# Kaam: apps aur websites KHOLNA aur BAND karna
# Naya: website ka tab peeche bhi ho to dhoond kar band karti hai
# ============================================================

import re                    # text mein words dhoondne ke liye
import subprocess            # Windows commands chalane ke liye (start, taskkill)
import time                  # thora wait karne ke liye
import webbrowser            # websites browser mein kholne ke liye
import pyautogui             # keyboard keys dabane ke liye (Ctrl + W, Ctrl + Tab)
import pygetwindow as gw     # khuli hui windows dhoondne ke liye


# ------------------------------------------------------------
# 1) APPS: naam -> Windows command (kholne ke liye)
# ------------------------------------------------------------
APPS = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "vs code": "code",
    "visual studio code": "code",
    "cmd": "cmd",
    "command prompt": "cmd",
    "terminal": "wt",
    "word": "winword",
    "microsoft word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "notepad": "notepad",
    "calculator": "calc",
    "paint": "mspaint",
    "file explorer": "explorer",
    "explorer": "explorer",
    "task manager": "taskmgr",
    "settings": "ms-settings:",
    "camera": "microsoft.windows.camera:",
    "microsoft store": "ms-windows-store:",
    "store": "ms-windows-store:",
    "whatsapp": "whatsapp:",
    "snipping tool": "snippingtool",
    "photos": "ms-photos:",
    "clock": "ms-clock:",
    "control panel": "control",
}

# ------------------------------------------------------------
# 2) WEBSITES: naam -> link
# ------------------------------------------------------------
WEBSITES = {
    "umt lms": "https://lms.umt.edu.pk",
    "lms": "https://lms.umt.edu.pk",
    "student portal": "https://online.umt.edu.pk",
    "umt portal": "https://online.umt.edu.pk",
    "portal": "https://online.umt.edu.pk",
    "umt website": "https://www.umt.edu.pk",
    "umt": "https://www.umt.edu.pk",
    "youtube": "https://www.youtube.com",
    "spotify": "https://open.spotify.com",
    "netflix": "https://www.netflix.com",
    "google drive": "https://drive.google.com",
    "google classroom": "https://classroom.google.com",
    "classroom": "https://classroom.google.com",
    "google meet": "https://meet.google.com",
    "google docs": "https://docs.google.com",
    "google sheets": "https://sheets.google.com",
    "google maps": "https://maps.google.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "outlook": "https://outlook.live.com",
    "canva": "https://www.canva.com",
    "github": "https://github.com",
    "stack overflow": "https://stackoverflow.com",
    "stackoverflow": "https://stackoverflow.com",
    "chatgpt": "https://chatgpt.com",
    "claude": "https://claude.ai",
    "facebook": "https://www.facebook.com",
    "instagram": "https://www.instagram.com",
    "linkedin": "https://www.linkedin.com",
    "twitter": "https://x.com",
    "x": "https://x.com",
    "daraz": "https://www.daraz.pk",
    "whatsapp web": "https://web.whatsapp.com",
    "wikipedia": "https://www.wikipedia.org",
}

# ------------------------------------------------------------
# 3) PROCESS_NAMES: app band karne ke liye uski .exe ka naam
# ------------------------------------------------------------
PROCESS_NAMES = {
    "chrome": ["chrome.exe"],
    "google chrome": ["chrome.exe"],
    "edge": ["msedge.exe"],
    "microsoft edge": ["msedge.exe"],
    "word": ["WINWORD.EXE"],
    "microsoft word": ["WINWORD.EXE"],
    "excel": ["EXCEL.EXE"],
    "powerpoint": ["POWERPNT.EXE"],
    "notepad": ["notepad.exe"],
    "calculator": ["CalculatorApp.exe"],
    "paint": ["mspaint.exe"],
    "task manager": ["Taskmgr.exe"],
    "settings": ["SystemSettings.exe"],
    "camera": ["WindowsCamera.exe"],
    "microsoft store": ["WinStore.App.exe"],
    "store": ["WinStore.App.exe"],
    "whatsapp": ["WhatsApp.exe", "WhatsApp.Root.exe"],
    "snipping tool": ["SnippingTool.exe"],
    "photos": ["Photos.exe"],
    "clock": ["Time.exe"],
}

# Ye AURA band NAHI karegi (AURA khud inke andar chalti hai / desktop gayab ho jata hai)
PROTECTED = {
    "vs code", "visual studio code", "cmd", "command prompt",
    "terminal", "file explorer", "explorer", "control panel",
}

# Website ka naam -> tab ke title mein kya likha hota hai
TAB_KEYWORDS = {
    "umt lms": "lms",
    "lms": "lms",
    "student portal": "umt",
    "umt portal": "umt",
    "portal": "umt",
    "umt website": "umt",
    "google drive": "drive",
    "google classroom": "classroom",
    "google meet": "meet",
    "google docs": "docs",
    "google sheets": "sheets",
    "google maps": "maps",
    "stack overflow": "stack overflow",
    "stackoverflow": "stack overflow",
    "twitter": "/ x",
    "x": "/ x",
    "whatsapp web": "whatsapp",
}

# Browser window ke title ke aakhir mein inmein se koi naam hota hai
BROWSER_NAMES = ["google chrome", "microsoft edge", "mozilla firefox", "brave"]

OPEN_WORDS = {"open", "launch", "start", "run"}
CLOSE_WORDS = {"close", "quit", "exit", "shut", "kill"}

MAX_TABS = 30   # aik window mein zyada se zyada itne tabs check karega

ALL_TARGETS = list(APPS.keys()) + list(WEBSITES.keys())


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_text(text):
    """Text ko lowercase karo aur punctuation hata do."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def find_target(text, names):
    """Text mein app/website ka naam dhoondo (lambe naam pehle)."""
    for name in sorted(names, key=len, reverse=True):
        if re.search(rf"\b{re.escape(name)}\b", text):
            return name
    return None


def window_title(win):
    """Window ka title lowercase mein (Edge ka chhupa character hata kar)."""
    try:
        return win.title.replace("\u200b", "").lower()
    except Exception:
        return ""


def get_browser_windows():
    """Saari khuli browser windows ki list (sab se recent pehle)."""
    browsers = []
    for win in gw.getAllWindows():
        title = window_title(win)
        if title and any(b in title for b in BROWSER_NAMES):
            browsers.append(win)
    return browsers


def focus_window(win):
    """
    Window ko saamne lao. Kaamyab ho to True, warna False.
    False ho to hum Ctrl + W NAHI dabate (taake VS Code ka tab band na ho).
    """
    try:
        if win.isMinimized:
            win.restore()
        pyautogui.press("alt")   # Windows trick: is ke baad focus badalne deti hai
        win.activate()
    except Exception:
        try:
            win.minimize()
            win.restore()
        except Exception:
            pass
    time.sleep(0.6)

    # Check: kya waqai yehi window ab saamne hai?
    try:
        return gw.getActiveWindow() == win
    except Exception:
        return False


# ============================================================
# KHOLNE WALA FUNCTION
# ============================================================

def open_thing(name):
    if name in APPS:
        subprocess.Popen(f'start "" {APPS[name]}', shell=True)
        return f"Opening {name}."
    if name in WEBSITES:
        webbrowser.open(WEBSITES[name])
        return f"Opening {name}."
    return None


# ============================================================
# APP BAND KARNE WALA FUNCTION
# ============================================================

def close_app(name):
    if name in PROTECTED:
        return f"Sorry, I can't close {name}, because that could stop me or your desktop."

    exe_list = PROCESS_NAMES.get(name)
    if not exe_list:
        return f"Sorry, I don't know how to close {name} yet."

    closed = False
    denied = False

    for exe in exe_list:
        result = subprocess.run(["taskkill", "/IM", exe],
                                capture_output=True, text=True)
        output = (result.stdout + result.stderr).lower()

        if result.returncode == 0:
            closed = True
        elif "not found" in output:
            continue
        elif "access is denied" in output:
            denied = True
        else:
            force = subprocess.run(["taskkill", "/IM", exe, "/F"],
                                   capture_output=True, text=True)
            if force.returncode == 0:
                closed = True

    if closed:
        return f"Closed {name}."
    if denied:
        return f"Windows did not allow me to close {name}."
    return f"{name} is not open."


# ============================================================
# TAB BAND KARNE WALE FUNCTIONS
# ============================================================

def close_current_tab():
    """'Close tab': sab se recent browser ka saamne wala tab band karo."""
    windows = get_browser_windows()
    if not windows:
        return "No browser is open."
    if not focus_window(windows[0]):
        return "I couldn't bring the browser to the front. Please click on it once and try again."
    pyautogui.hotkey("ctrl", "w")
    return "Closed the tab."


def close_website(name):
    """
    Website ka tab dhoond kar band karo, chahe woh peeche wala tab ho.
    Step 1: jis window mein woh tab pehle se saamne hai, usay band karo (tez).
    Step 2: warna har window ke har tab ko Ctrl + Tab se check karo.
    """
    keyword = TAB_KEYWORDS.get(name, name)
    windows = get_browser_windows()
    if not windows:
        return "No browser is open."

    # ---- Step 1: tez tareeqa ----
    for win in windows:
        if keyword in window_title(win):
            if focus_window(win):
                pyautogui.hotkey("ctrl", "w")
                return f"Closed {name}."

    # ---- Step 2: har tab check karo ----
    for win in windows:
        if not focus_window(win):
            continue                          # ye window saamne nahi aayi, agli dekho

        pyautogui.hotkey("ctrl", "1")         # pehle tab par jao
        time.sleep(0.3)
        first_title = window_title(win)       # yaad rakho, taake pura chakkar pata chale

        for _ in range(MAX_TABS):
            if keyword in window_title(win):
                pyautogui.hotkey("ctrl", "w")  # mil gaya, band karo
                return f"Closed {name}."

            pyautogui.hotkey("ctrl", "tab")    # agla tab
            time.sleep(0.25)

            if window_title(win) == first_title:
                break                          # wapas pehle tab par aa gaye, yahan nahi hai

    return f"I couldn't find an open {name} tab."


# ============================================================
# MAIN ROUTER: aura_core.py isi ko call karta hai
# ============================================================

def handle_command(text):
    cleaned = clean_text(text)
    words = cleaned.split()
    if not words:
        return None

    first_words = words[:3]

    # ---------- BAND KARNA ----------
    if any(w in CLOSE_WORDS for w in first_words):
        target = find_target(cleaned, ALL_TARGETS)

        if target in WEBSITES:                   # "close youtube"
            return close_website(target)
        if re.search(r"\btabs?\b", cleaned):     # "close tab"
            return close_current_tab()
        if target in APPS:                       # "close chrome"
            return close_app(target)
        return None

    # ---------- KHOLNA ----------
    if any(w in OPEN_WORDS for w in first_words):
        target = find_target(cleaned, ALL_TARGETS)
        if target:
            return open_thing(target)

    return None


# ============================================================
# TEST MODE: python actions.py
# ============================================================
if __name__ == "__main__":
    print("🧪 Test mode — command likhein (band karne ke liye 'q')")
    while True:
        cmd = input("\n⌨️  Command: ")
        if cmd.strip().lower() == "q":
            break
        reply = handle_command(cmd)
        print("🤖", reply if reply else "(command nahi thi — ye Llama ke paas jata)")