# ============================================================
# whatsapp.py — AURA se WhatsApp message bhejna 💬
# Misaal: "Send a WhatsApp message to Ali saying I'm on my way"
# Fix: WhatsApp ka intezar + message box par click + Enter
# ============================================================

import json               # contacts.json parhne ke liye
import os                 # whatsapp:// link kholne ke liye
import re                 # text mein words dhoondne ke liye
import time               # wait karne ke liye
import urllib.parse       # message ko link ke qabil banana (spaces -> %20)
import pyautogui          # mouse click aur Enter ke liye
import pygetwindow as gw  # WhatsApp ki window dhoondne ke liye

CONTACTS_FILE = "contacts.json"

# True  = AURA khud message bhej degi ✅
# False = chat khulegi, message likha hoga, Enter aap dabayenge
AUTO_SEND = True

MAX_WAIT = 15             # WhatsApp window ka zyada se zyada intezar (second)
CHAT_LOAD_SECONDS = 3     # window aane ke baad chat load hone ka intezar
                          # Message likha reh jaye, bheja na jaye -> isay 5 kar dein

WHATSAPP_TITLES = {"whatsapp", "whatsapp beta"}   # asli WhatsApp window ke titles
MESSAGE_WORDS = {"message", "send", "text", "saying", "msg"}
SELF_WORDS = {"me", "myself", "my number", "my own number"}


# ============================================================
# CONTACTS
# ============================================================
def load_contacts():
    """contacts.json se naam aur numbers parho."""
    try:
        with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {name.lower().strip(): str(num).strip() for name, num in data.items()}
    except FileNotFoundError:
        print("   ⚠️ contacts.json nahi mili")
        return {}
    except json.JSONDecodeError as e:
        print(f"   ⚠️ contacts.json mein ghalti hai (comma ya quote check karein): {e}")
        return {}


def find_contact(text, contacts):
    """Text mein contact ka naam dhoondo. Wapas: (naam, number) ya (None, None)."""
    for word in sorted(SELF_WORDS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(word)}\b", text):
            if "me" in contacts:
                return "you", contacts["me"]
            return "me", None

    for name in sorted(contacts.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(name)}\b", text):
            return name, contacts[name]

    return None, None


# ============================================================
# WHATSAPP WINDOW
# ============================================================
def is_whatsapp_window(win):
    """Kya ye ASLI WhatsApp window hai? (title bilkul 'WhatsApp' ho, VS Code nahi)"""
    try:
        return win.title.strip().lower() in WHATSAPP_TITLES
    except Exception:
        return False


def get_whatsapp_window():
    """Asli, nazar aane wali WhatsApp window wapas do (ya None)."""
    candidates = [w for w in gw.getAllWindows() if is_whatsapp_window(w)]

    for w in candidates:
        try:
            if w.isMinimized:
                w.restore()          # minimize ho to wapas bara karo
                time.sleep(0.5)
        except Exception:
            pass

    # Chhupi hui chhoti windows chhor do, sirf asli bari window lo
    visible = [w for w in candidates if w.width > 300 and w.height > 300]
    if not visible:
        return None
    return max(visible, key=lambda w: w.width * w.height)


def wait_for_whatsapp():
    """WhatsApp window aane tak ruko (MAX_WAIT second tak)."""
    start = time.time()
    while time.time() - start < MAX_WAIT:
        win = get_whatsapp_window()
        if win:
            return win
        time.sleep(0.5)
    return None


def click_and_send(win):
    """
    Message box par click karo (WhatsApp saamne aa jata hai aur cursor box mein),
    phir Enter dabao. Mouse wapas purani jagah par.
    """
    old_mouse = pyautogui.position()           # mouse kahan tha, yaad rakho

    # Message box window ke bilkul neeche hota hai, darmiyan se thora daen
    x = win.left + int(win.width * 0.65)
    y = win.top + win.height - 40
    print(f"   🖱️ Clicking message box at ({x}, {y})")

    pyautogui.click(x, y)
    time.sleep(0.5)
    pyautogui.press("enter")
    time.sleep(0.3)

    pyautogui.moveTo(old_mouse)                # mouse wapas


# ============================================================
# MAIN FUNCTION: aura_core.py isi ko call karta hai
# ============================================================
def handle_whatsapp(text):
    """
    WhatsApp command ho to message bhejo aur AURA ka jawab wapas do.
    Command na ho to None (sawal Llama ke paas jayega).
    """
    lower = text.lower()

    # 1) Kya ye WhatsApp message wali command hai?
    if "whatsapp" not in lower:
        return None
    if not any(w in lower for w in MESSAGE_WORDS):
        return None   # sirf "open whatsapp", wo actions.py sambhalega

    # 2) Message alag karo: "saying" ya "that" ke baad wala hissa
    match = re.search(r"\b(saying|that says|that)\b\s*(.*)", text, re.IGNORECASE)
    if not match or not match.group(2).strip():
        return "What should the message say? Please say it like: send a WhatsApp message to Ali saying hello."

    message = match.group(2).strip().rstrip(".")
    before = lower[:match.start()]

    # 3) Contact dhoondo
    contacts = load_contacts()
    name, number = find_contact(before, contacts)

    if name == "me" and number is None:
        return "I don't have your own number. Please add a 'me' entry in contacts.json."
    if number is None:
        return "I couldn't find that person in your contacts. Please add them to contacts.json."

    # 4) WhatsApp kholo, message pehle se likha hua
    link = f"whatsapp://send?phone={number}&text={urllib.parse.quote(message)}"
    os.startfile(link)

    if not AUTO_SEND:
        return f"WhatsApp is open with your message to {name}. Press Enter to send it."

    # 5) Auto-send
    print("   ⏳ Waiting for WhatsApp...")
    win = wait_for_whatsapp()
    if win is None:
        print("   ⚠️ WhatsApp ki window nahi mili")
        return f"I opened the chat with {name}, but couldn't find the WhatsApp window. Please press Enter to send."

    print(f"   🪟 WhatsApp mil gaya: {win.width}x{win.height}")
    time.sleep(CHAT_LOAD_SECONDS)              # chat aur message load hone do
    click_and_send(win)
    return f"Message sent to {name}."


# ============================================================
# TEST MODE: python whatsapp.py
# ============================================================
if __name__ == "__main__":
    print("🧪 Test mode — command likhein (band karne ke liye 'q')")
    while True:
        cmd = input("\n⌨️  Command: ")
        if cmd.strip().lower() == "q":
            break
        reply = handle_whatsapp(cmd)
        print("🤖", reply if reply else "(WhatsApp command nahi thi — Llama ke paas jati)")