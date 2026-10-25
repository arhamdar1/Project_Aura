# ============================================================
# daily_tools.py — AURA ke rozana kaam ke features 🧰
# 1) Reminders, timers, alarms    2) Music control
# 3) YouTube par play              4) Google search
# 5) Voice typing                  6) Notes / to-do list
# 7) Laptop health                 8) Window control
# Fix: awaaz wale jumle ("okay set a timer", "play a song") bhi samajhti hai
# ============================================================

import ctypes             # Windows ka popup message dikhane ke liye
import json               # notes.json save karne ke liye
import re                 # text mein patterns dhoondne ke liye
import threading          # reminders background mein chalane ke liye
import time               # thora wait karne ke liye
import urllib.parse       # search words ko link ke qabil banana
import webbrowser         # browser mein link kholna
from datetime import datetime, timedelta

import psutil             # CPU, RAM, disk info
import pyautogui          # keyboard shortcuts (media keys, Alt+Tab, Win+Left)
import pyperclip          # clipboard (voice typing ke liye)
import pygetwindow as gw  # windows maximize/minimize
import requests           # YouTube se pehli video dhoondne ke liye


# ============================================================
# SETTINGS
# ============================================================
NOTES_FILE = "notes.json"

# "Play a song" / "Play some music" bolne par YouTube par yehi search hoga.
# Apni pasand likh dein, jaise "Atif Aslam songs" ya "lofi study music"
FAVORITE_MUSIC = "latest Pakistani songs"

# True = typing aur window commands se pehle AURA Alt+Tab se pichli window par jayegi
# (kyun ke abhi aap terminal mein Enter daba kar bolte hain). Phase 3 ke baad False karenge.
SWITCH_WINDOW_FIRST = True

_speaker = None   # aura_core.py yahan apna speak() deta hai (reminder bolne ke liye)


def set_speaker(func):
    global _speaker
    _speaker = func


# ============================================================
# HELPER FUNCTIONS
# ============================================================
# Jumle ke shuru ke faltu words: "okay", "hey aura", "please", "can you"...
FILLER_START = re.compile(
    r"^(?:(?:hey|hi|hello|ok|okay|so|um|uh|please|can you|could you|would you|"
    r"will you|aura|jarvis)\s+)+"
)


def clean(text):
    """Lowercase + punctuation hatao (':' rakho) + shuru ke faltu words hatao."""
    text = text.lower()
    text = re.sub(r"[^\w\s:]", " ", text)
    text = " ".join(text.split())
    return FILLER_START.sub("", text + " ").strip()


def has(text, *words):
    """Kya text mein in mein se koi poora word/phrase hai?"""
    return any(re.search(rf"\b{re.escape(w)}\b", text) for w in words)


def clock_str(dt):
    """datetime -> '5:30 PM'"""
    return dt.strftime("%I:%M %p").lstrip("0")


def go_to_previous_window():
    """Terminal se pichli window (jahan aap kaam kar rahe the) par jao."""
    if SWITCH_WINDOW_FIRST:
        pyautogui.hotkey("alt", "tab")
        time.sleep(0.6)


# ============================================================
# 1) REMINDERS, TIMERS, ALARMS ⏰
# ============================================================
UNIT_PATTERN = r"(seconds?|secs?|minutes?|mins?|hours?|hrs?)"
DURATION_RE = re.compile(rf"\b(\d+)\s*{UNIT_PATTERN}\b")
CLOCK_RE = re.compile(r"\b(?:at|for|by)\s+(\d{1,2})(?:\s*:?\s*(\d{2}))?\s*(a\s?m|p\s?m)?\b")
UNIT_TO_SECONDS = {"s": 1, "m": 60, "h": 3600}

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15,
    "twenty": 20, "twenty five": 25, "thirty": 30, "forty": 40, "forty five": 45,
    "fifty": 50, "sixty": 60, "ninety": 90, "a": 1, "an": 1,
}

REMINDER_WORDS = ("reminders", "reminder", "timers", "timer", "alarms", "alarm")
LIST_WORDS_R = ("what", "list", "show", "any", "how many", "tell me", "do i have", "check", "pending")
CANCEL_WORDS = ("cancel", "delete", "remove", "stop", "clear", "turn off", "dismiss")
CREATE_WORDS = ("set", "start", "create", "add", "remind me", "wake me", "put")
QUESTION_WORDS = ("what is a", "what is an", "explain", "define", "how does", "meaning of")

REMINDERS = []   # chalte hue reminders ki list


def words_to_digits(t):
    """'in five minutes' -> 'in 5 minutes', 'half an hour' -> '30 minutes'"""
    t = t.replace("half an hour", "30 minutes").replace("half a minute", "30 seconds")
    for word in sorted(NUMBER_WORDS, key=len, reverse=True):
        number = NUMBER_WORDS[word]
        t = re.sub(rf"\b{word}\s+{UNIT_PATTERN}\b",
                   lambda m, n=number: f"{n} {m.group(1)}", t)
    return t


def parse_duration(t):
    """'1 hour and 30 minutes' -> 5400 second. Na mile to None."""
    total = sum(int(num) * UNIT_TO_SECONDS[unit[0]] for num, unit in DURATION_RE.findall(t))
    return total or None


def parse_clock(t):
    """'at 5:30 pm' -> aaj (ya kal) 5:30 PM ka datetime. Na mile to None."""
    m = CLOCK_RE.search(t)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    ampm = (m.group(3) or "").replace(" ", "")
    if hour > 23 or minute > 59:
        return None

    if ampm == "pm" and hour < 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0

    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # "at 5" bola (am/pm nahi) aur subah ke 5 guzar gaye -> shaam ke 5
    if not ampm and hour <= 12 and target <= now:
        later = target + timedelta(hours=12)
        if later > now:
            target = later
    if target <= now:
        target += timedelta(days=1)   # aaj ka waqt guzar gaya -> kal
    return target


def format_duration(seconds):
    """5400 -> '1 hour and 30 minutes'"""
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    parts = []
    if h:
        parts.append(f"{h} hour{'s' if h > 1 else ''}")
    if m:
        parts.append(f"{m} minute{'s' if m > 1 else ''}")
    if s and not h:
        parts.append(f"{s} second{'s' if s > 1 else ''}")
    return " and ".join(parts) or "0 seconds"


def strip_time_words(t):
    """Message mein se time wale words hata do."""
    t = re.sub(rf"\b(?:(?:in|for|after)\s+)?\d+\s*{UNIT_PATTERN}"
               rf"(?:\s+and\s+\d+\s*{UNIT_PATTERN})*", " ", t)
    t = CLOCK_RE.sub(" ", t)
    return " ".join(t.split())


def extract_reminder_message(t):
    """'remind me in 20 minutes to drink water' -> 'drink water'"""
    msg = re.sub(r"^(?:(?:(?:set|add|create)\s+(?:a\s+|an\s+)?)?reminder|remind me)\s*", "", t)
    msg = strip_time_words(msg)
    msg = re.sub(r"^(?:to|that|about|of)\s+", "", msg)
    msg = re.sub(r"\s+(?:to|that)$", "", msg)
    return msg.strip()


def _popup(message):
    """Screen par sab se upar Windows popup (OK dabane tak rahega)."""
    # 0x40 = info icon, 0x1000 = system modal, 0x40000 = sab se upar
    ctypes.windll.user32.MessageBoxW(0, message, "⏰ AURA Reminder", 0x40 | 0x1000 | 0x40000)


def _fire(item):
    """Reminder ka waqt aa gaya!"""
    if item in REMINDERS:
        REMINDERS.remove(item)
    message = item["message"]
    print(f"\n⏰ REMINDER: {message}")
    threading.Thread(target=_popup, args=(message,), daemon=True).start()
    if _speaker:
        try:
            _speaker(f"Reminder. {message}")
        except Exception as e:
            print(f"   ⚠️ Reminder bol nahi saki: {e}")


def schedule(seconds, message, label):
    """Background mein timer lagao. Wapas: kis waqt bajega."""
    fire_at = datetime.now() + timedelta(seconds=seconds)
    item = {"message": message, "time": fire_at, "label": label}
    timer = threading.Timer(seconds, _fire, args=(item,))
    timer.daemon = True          # AURA band ho to timer bhi band
    item["timer"] = timer
    REMINDERS.append(item)
    timer.start()
    return fire_at


def handle_reminders(t):
    t = words_to_digits(t)

    # Kya baat reminder/timer/alarm ki hai?
    if not (has(t, *REMINDER_WORDS) or has(t, "remind me", "wake me")):
        return None
    if has(t, *QUESTION_WORDS):          # "what is a timer?" sawal hai
        return None

    seconds = parse_duration(t)
    target = None if seconds else parse_clock(t)
    has_time = bool(seconds or target)

    # ---- Cancel: "cancel my timer", "stop the alarm" ----
    if has(t, *CANCEL_WORDS) and not has_time:
        count = len(REMINDERS)
        for r in REMINDERS:
            r["timer"].cancel()
        REMINDERS.clear()
        if count == 0:
            return "There was nothing to cancel."
        return f"Cancelled {count} reminders and timers."

    # ---- List: "what are my reminders" ----
    if has(t, *LIST_WORDS_R) and not has_time and not has(t, *CREATE_WORDS):
        if not REMINDERS:
            return "You have no reminders or timers right now."
        items = sorted(REMINDERS, key=lambda r: r["time"])
        parts = [f"{r['label']} at {clock_str(r['time'])}" for r in items]
        return f"You have {len(items)}: " + "; ".join(parts) + "."

    if target:
        seconds = (target - datetime.now()).total_seconds()

    # ---- Timer: "set a timer for 10 minutes" / "timer for 5 minutes" ----
    if has(t, "timer", "timers"):
        if not seconds:
            return "For how long? Please say something like: set a timer for 10 minutes."
        label = format_duration(seconds)
        schedule(seconds, f"Your {label} timer is done.", f"{label} timer")
        return f"Timer set for {label}."

    # ---- Alarm: "set an alarm for 7 am" / "wake me up in 30 minutes" ----
    if has(t, "alarm", "alarms", "wake me"):
        if not seconds:
            return "What time? Please say something like: set an alarm for 7 am."
        fire_at = schedule(seconds, "Wake up! This is your alarm.", "alarm")
        return f"Alarm set for {clock_str(fire_at)}."

    # ---- Reminder: "remind me in 20 minutes to drink water" ----
    if not seconds:
        return "When should I remind you? Please say something like: remind me in 20 minutes to drink water."
    message = extract_reminder_message(t) or "This is your reminder."
    fire_at = schedule(seconds, message, message)
    return (f"Okay, in {format_duration(seconds)}, at {clock_str(fire_at)}, "
            f"I will remind you: {message}.")


# ============================================================
# 2) VOICE TYPING ⌨️  "Type: I will be late today"
# ============================================================
TYPING_RE = re.compile(
    r"^\s*(?:(?:hey|hi|ok|okay|so|please|can you|could you|aura|jarvis)[\s,.!]+)*"
    r"type\b(?:\s+out\b)?\s*[:,.\-]?\s*(.+)$",
    re.IGNORECASE | re.DOTALL,
)


def handle_typing(original_text):
    m = TYPING_RE.match(original_text)
    if not m:
        return None
    words = m.group(1).strip()

    go_to_previous_window()
    try:
        old_clipboard = pyperclip.paste()       # purana clipboard yaad rakho
    except Exception:
        old_clipboard = ""

    pyperclip.copy(words)                       # clipboard se paste (Urdu/emoji bhi chal jaye)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.5)
    pyperclip.copy(old_clipboard)               # clipboard wapas
    return "Done, I typed it."


# ============================================================
# 3) YOUTUBE PAR PLAY ▶️
# ============================================================
# "play a song" jaise aam jumle -> FAVORITE_MUSIC chalega
GENERIC_MUSIC = {
    "a song", "song", "songs", "some songs", "music", "some music", "a music",
    "any song", "something", "a random song", "random song", "some song",
    "a good song", "a nice song", "my music", "my songs", "a playlist",
}
# "play" / "play it" -> jo ruka hua hai wohi chalao (resume)
RESUME_REST = {"", "it", "again", "it again"}


def first_youtube_video(query):
    """YouTube search se pehli video ka link. Na mile to search page ka link."""
    search_url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)
    try:
        html = requests.get(search_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8).text
        match = re.search(r'"videoId":"([\w-]{11})"', html)
        if match:
            return f"https://www.youtube.com/watch?v={match.group(1)}"
    except Exception as e:
        print(f"   ⚠️ YouTube search fail: {e}")
    return search_url


def handle_youtube(t):
    # ---- YouTube par search (play nahi): "search youtube for cooking" ----
    m = (re.search(r"\bsearch\s+(?:on\s+)?youtube\s+for\s+(.+)", t)
         or re.search(r"\bsearch\s+(?:for\s+)?(.+?)\s+on\s+youtube\b", t))
    if m:
        query = m.group(1)
        webbrowser.open("https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query))
        return f"Searching YouTube for {query}."

    # ---- Play: "play a song" / "play atif aslam" / "play kahani suno on youtube" ----
    m = re.match(r"^play\b\s*(.*)$", t)
    if not m:
        return None

    rest = m.group(1)
    rest = re.sub(r"\s*\b(?:on|in|from)\s+youtube$", "", rest).strip()   # "on youtube" hatao
    rest = re.sub(r"\s+for me$", "", rest).strip()                        # "for me" hatao

    if rest in RESUME_REST:                  # sirf "play" -> resume
        pyautogui.press("playpause")
        return "Playing."

    if rest in GENERIC_MUSIC:                # "play a song" -> pasandeeda music
        query = FAVORITE_MUSIC
    else:                                    # "play the song kahani suno" -> "kahani suno"
        query = re.sub(r"^(?:a\s+|the\s+|some\s+)?(?:song|songs|music|video)\s+"
                       r"(?:called\s+|named\s+|by\s+|of\s+)?", "", rest).strip() or FAVORITE_MUSIC

    print(f"   🔎 YouTube: {query}")
    webbrowser.open(first_youtube_video(query))
    return f"Playing {query} on YouTube."


# ============================================================
# 4) GOOGLE SEARCH 🔍
# ============================================================
GOOGLE_PATTERNS = [
    r"\bsearch\s+(?:on\s+)?google\s+(?:for\s+)?(.+)",
    r"\bgoogle\s+search\s+(?:for\s+)?(.+)",
    r"\bsearch\s+(?:for\s+)?(.+?)\s+on\s+google\b",
    r"^google\s+for\s+(.+)",
    r"\blook\s+up\s+(.+?)\s+on\s+google\b",
]


def handle_google(t):
    for pattern in GOOGLE_PATTERNS:
        m = re.search(pattern, t)
        if m:
            query = m.group(1).strip()
            webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote_plus(query))
            return f"Searching Google for {query}."
    return None


# ============================================================
# 5) MUSIC CONTROL 🎵 (pause, next, previous, resume)
# ============================================================
MEDIA_WORDS = ("music", "song", "songs", "track", "video", "spotify", "playback", "audio", "youtube")


def handle_music(t):
    if not has(t, *MEDIA_WORDS) and t not in ("pause", "resume", "next", "previous", "stop"):
        return None

    if has(t, "next", "skip"):
        pyautogui.press("nexttrack")
        return "Next track."
    if has(t, "previous", "last", "back"):
        pyautogui.press("prevtrack")
        return "Previous track."
    if has(t, "pause", "stop"):
        pyautogui.press("playpause")
        return "Paused."
    if has(t, "resume", "continue", "unpause"):
        pyautogui.press("playpause")
        return "Playing."
    return None


# ============================================================
# 6) NOTES / TO-DO LIST 📝
# ============================================================
LIST_WORDS = ("my list", "my notes", "to do list", "todo list", "my to do", "my todo", "shopping list")


def load_notes():
    try:
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_notes(notes):
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2, ensure_ascii=False)


def handle_notes(t):
    if has(t, "according to"):          # "according to my notes" PDF wala feature hai (Batch 5)
        return None
    notes = load_notes()

    # ---- Add ----
    m = (re.match(r"^(?:note down|take a note|make a note|write down|jot down)"
                  r"\s+(?:that\s+)?(?:to\s+)?(.+)", t)
         or re.match(r"^add\s+(.+?)\s+to\s+(?:my\s+)?"
                     r"(?:list|notes|to do list|todo list|to do|shopping list)$", t))
    if m:
        item = m.group(1).strip()
        notes.append({"text": item, "added": datetime.now().strftime("%Y-%m-%d %H:%M")})
        save_notes(notes)
        return f"Added to your list: {item}. You now have {len(notes)} items."

    # ---- Sab clear ----
    if has(t, "clear", "delete all", "remove all", "empty") and has(t, *LIST_WORDS):
        save_notes([])
        return "Your list is now empty."

    # ---- Number se delete: "delete item 2" ----
    m = re.search(r"\b(?:delete|remove)\s+(?:note|item|number)\s+(?:number\s+)?(\d+)", t)
    if m:
        index = int(m.group(1)) - 1
        if 0 <= index < len(notes):
            removed = notes.pop(index)
            save_notes(notes)
            return f"Removed: {removed['text']}."
        return f"There is no item number {index + 1}."

    # ---- Naam se delete: "remove milk from my list" ----
    m = re.match(r"^(?:delete|remove)\s+(.+?)\s+from\s+(?:my\s+)?"
                 r"(?:list|notes|to do list|todo list)$", t)
    if m:
        word = m.group(1)
        for note in notes:
            if word in note["text"]:
                notes.remove(note)
                save_notes(notes)
                return f"Removed: {note['text']}."
        return f"I couldn't find {word} in your list."

    # ---- Parho ----
    if has(t, *LIST_WORDS) and has(t, "what", "whats", "read", "show", "tell", "check"):
        if not notes:
            return "Your list is empty."
        items = "; ".join(f"{i}, {n['text']}" for i, n in enumerate(notes, 1))
        return f"You have {len(notes)} items: {items}."
    return None


# ============================================================
# 7) LAPTOP HEALTH 💻
# ============================================================
SKIP_PROCESSES = {"System Idle Process", "System", "Registry", "Memory Compression", ""}


def top_memory_apps(n=3):
    """Sab se zyada RAM lene wali apps (Chrome ke sab tabs aik saath gine jate hain)."""
    usage = {}
    for p in psutil.process_iter(["name", "memory_info"]):
        try:
            name = (p.info["name"] or "").replace(".exe", "")
            if name in SKIP_PROCESSES:
                continue
            usage[name] = usage.get(name, 0) + p.info["memory_info"].rss
        except Exception:
            continue
    top = sorted(usage.items(), key=lambda x: x[1], reverse=True)[:n]
    result = []
    for name, mem in top:
        if mem >= 1e9:
            result.append(f"{name} {mem / 1e9:.1f} gigabytes")
        else:
            result.append(f"{name} {mem / 1e6:.0f} megabytes")
    return result


def handle_health(t):
    if has(t, "what is a", "what is the meaning", "explain", "define"):
        return None   # "what is a CPU?" sawal hai, Llama jawab de

    wants_cpu = has(t, "cpu", "processor")
    wants_ram = has(t, "ram") or (has(t, "memory") and not has(t, "remember"))
    wants_disk = has(t, "disk", "storage space", "hard drive", "ssd", "drive space", "space left")
    wants_all = has(t, "system status", "laptop health", "pc health", "laptop status",
                    "computer status", "how is my laptop", "system health")
    if not (wants_cpu or wants_ram or wants_disk or wants_all):
        return None

    parts = []
    if wants_cpu or wants_all:
        cpu = psutil.cpu_percent(interval=0.5)
        parts.append(f"CPU usage is {cpu:.0f} percent.")
        if has(t, "hot", "temperature", "temp", "heat"):
            parts.append("Windows does not share the CPU temperature with apps, so I can only tell you the usage.")

    if wants_ram or wants_all:
        mem = psutil.virtual_memory()
        parts.append(f"RAM usage is {mem.percent:.0f} percent, "
                     f"{mem.used / 1e9:.1f} of {mem.total / 1e9:.1f} gigabytes.")
        top = top_memory_apps(3)
        if top:
            parts.append("Top apps: " + ", ".join(top) + ".")

    if wants_disk or wants_all:
        disk = psutil.disk_usage("C:\\")
        parts.append(f"Your C drive has {disk.free / 1e9:.0f} gigabytes free "
                     f"out of {disk.total / 1e9:.0f}.")

    if wants_all:
        battery = psutil.sensors_battery()
        if battery:
            state = "charging" if battery.power_plugged else "not charging"
            parts.append(f"Battery is at {battery.percent:.0f} percent and {state}.")

    return " ".join(parts)


# ============================================================
# 8) WINDOW CONTROL 🪟
# ============================================================
def handle_window(t):
    if has(t, "minimize all", "minimise all"):
        return None   # ye system_control.py ka "show desktop" sambhalega
    if not (has(t, "window") or has(t, "all windows", "show windows")):
        return None

    if has(t, "all windows", "show windows", "task view"):
        pyautogui.hotkey("win", "tab")
        return "Showing all windows."

    if has(t, "switch", "next", "change", "other"):
        pyautogui.hotkey("alt", "tab")
        return "Switched window."

    if has(t, "left"):
        go_to_previous_window()
        pyautogui.hotkey("win", "left")
        return "Window snapped to the left."

    if has(t, "right"):
        go_to_previous_window()
        pyautogui.hotkey("win", "right")
        return "Window snapped to the right."

    if has(t, "maximize", "maximise", "full screen", "bigger"):
        go_to_previous_window()
        win = gw.getActiveWindow()
        if win:
            win.maximize()
        return "Window maximized."

    if has(t, "minimize", "minimise", "hide"):
        go_to_previous_window()
        win = gw.getActiveWindow()
        if win:
            win.minimize()
        return "Window minimized."
    return None


# ============================================================
# MAIN FUNCTIONS: aura_core.py inhein call karta hai
# ============================================================
def _run(handlers, value):
    for handler in handlers:
        try:
            reply = handler(value)
        except Exception as e:
            print(f"   ❌ {handler.__name__} error: {e}")
            return "Sorry, I couldn't do that."
        if reply:
            return reply
    return None


def handle_priority(text):
    """
    Sab se PEHLE check hone wale: typing aur reminders.
    (Taake "remind me to turn off wifi at 9" abhi WiFi band na kar de)
    """
    reply = _run([handle_typing], text)            # typing ko asli text chahiye
    if reply:
        return reply
    t = clean(text)
    if not t:
        return None
    return _run([handle_reminders], t)


def handle_daily(text):
    """Baaqi rozana features."""
    t = clean(text)
    if not t:
        return None
    return _run([handle_youtube, handle_google, handle_music,
                 handle_notes, handle_health, handle_window], t)


# ============================================================
# TEST MODE: python daily_tools.py
# ============================================================
if __name__ == "__main__":
    print("🧪 Test mode — command likhein (band karne ke liye 'q')")
    while True:
        cmd = input("\n⌨️  Command: ")
        if cmd.strip().lower() == "q":
            break
        reply = handle_priority(cmd) or handle_daily(cmd)
        print("🤖", reply if reply else "(daily command nahi thi — aage jati)")