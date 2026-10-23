# ==========================================================
# AURA - Phase 2.3: WhatsApp Messaging
# "Send a WhatsApp message to Ali saying I'm on my way"
#  -> Ali ki chat kholo, message likho, (setting ho to) bhej do
# ==========================================================

import json            # contacts.json parhne ke liye
import os              # File check karne aur WhatsApp kholne ke liye
import re              # Jumle se naam aur message alag karne ke liye
import time            # WhatsApp khulne ka intezaar karne ke liye
import urllib.parse    # Message ko link ke andar safe banane ke liye
import pyautogui       # Enter key dabane ke liye

# ----------------------------------------------------------
# ⚙️ SETTINGS
# ----------------------------------------------------------
CONTACTS_FILE = "contacts.json"

# False = AURA chat khol kar message likh degi, Enter AAP dabayenge (safe ✅)
# True  = AURA khud Enter daba kar bhej degi (jab bharosa ho jaye tab)
AUTO_SEND = True

# WhatsApp khulne mein kitne second lagte hain (laptop slow ho to barha dein)
WAIT_SECONDS = 12

# Ye alfaaz "whatsapp" ke saath hon to message bhejne ka hukam hai
MESSAGE_WORDS = ["message", "send", "text", "saying"]


def simple_clean(text):
    """
    Chhote huroof + punctuation hatao.
    Whisper kabhi "What's app" likh deta hai, use bhi "whatsapp" bana do.
    """
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = " ".join(text.split())
    text = text.replace("what s app", "whatsapp").replace("whats app", "whatsapp")
    return text


def load_contacts():
    """contacts.json parh kar {naam: number} wapas karta hai."""
    if not os.path.exists(CONTACTS_FILE):
        print("⚠️  contacts.json nahi mili!")
        return {}
    with open(CONTACTS_FILE, "r", encoding="utf-8") as file:
        contacts = json.load(file)
    # Saare naam chhote huroof mein kar do taake matching aasaan ho
    return {name.lower(): number for name, number in contacts.items()}


def parse_command(text, contacts):
    """
    Jumle se 2 cheezein nikaalta hai:
      - name:    kisko bhejna hai (contacts mein se)
      - message: kya bhejna hai ("saying" ya "that" ke baad wala hissa)
    """
    # "saying" ya "that" ke baad sab kuch = message
    match = re.search(r"\b(?:saying|that)\b\s*(.+)", text, re.IGNORECASE)
    if not match:
        return None, None

    message = match.group(1).strip().rstrip(".")

    # "saying" se pehle wale hisse mein contact ka naam dhoondo
    before = f" {simple_clean(text[:match.start()])} "
    for name in sorted(contacts, key=len, reverse=True):  # Lambe naam pehle
        if f" {name} " in before:
            return name, message

    return None, message


def send_whatsapp(name, number, message):
    """WhatsApp Desktop mein chat kholta hai, message likhta hai, aur zaroorat ho to bhejta hai."""
    # Message ko link ke andar safe format mein badlo (spaces -> %20 waghaira)
    url = f"whatsapp://send?phone={number}&text={urllib.parse.quote(message)}"
    os.startfile(url)  # Windows ko kaho ye link WhatsApp mein khole

    if AUTO_SEND:
        time.sleep(WAIT_SECONDS)   # WhatsApp khulne ka intezaar
        pyautogui.press("enter")   # Enter daba kar bhej do
        return f"Message sent to {name}."

    return f"I have opened {name}'s chat with your message. Press Enter to send it."


# ==========================================================
# 🚦 Router ke liye main function
# ==========================================================
def handle_whatsapp(text):
    """
    Agar ye WhatsApp message ka hukam hai -> kaam karo aur jawab do.
    Warna None (taake baqi router apna kaam kare).
    """
    clean = simple_clean(text)
    words = clean.split()

    # "whatsapp" + koi message wala lafz hona zaroori hai.
    # (Sirf "open whatsapp" ho to ye None dega, aur app khul jayegi.)
    if "whatsapp" not in words or not any(w in words for w in MESSAGE_WORDS):
        return None

    contacts = load_contacts()
    if not contacts:
        return "Your contacts list is empty. Please add contacts to the contacts file first."

    name, message = parse_command(text, contacts)

    if not message:
        return ("Please tell me who to message and what to say. "
                "For example, send a WhatsApp message to Ali saying hello.")

    if not name:
        return "Sorry, I could not find that person in your contacts."

    print(f"   📱 To: {name} ({contacts[name]})")
    print(f"   💬 Message: {message}")
    return send_whatsapp(name, contacts[name], message)