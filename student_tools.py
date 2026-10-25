# ============================================================
# student_tools.py — AURA ke student features 🎓
# 1) Assignment / quiz / exam deadlines (deadlines.json mein save)
# 2) Pomodoro study mode + focus guard (distracting tabs band)
# ============================================================

import json               # deadlines.json save karne ke liye
import re                 # text mein patterns dhoondne ke liye
import threading          # study mode background mein chalane ke liye
import time               # wait karne ke liye
from datetime import date, datetime, timedelta

import pyautogui          # Ctrl + W (distracting tab band)
import pygetwindow as gw  # saamne wali window ka title dekhne ke liye

# daily_tools ke helper dobara use kar rahe hain (code repeat nahi karna)
from daily_tools import clean, has, words_to_digits, parse_duration


# ============================================================
# SETTINGS
# ============================================================
DEADLINES_FILE = "deadlines.json"

FOCUS_MINUTES = 25              # aik study session kitne minute ka
SHORT_BREAK_MINUTES = 5         # chhota break
LONG_BREAK_MINUTES = 15         # lamba break
SESSIONS_BEFORE_LONG_BREAK = 4  # kitne sessions baad lamba break

FOCUS_GUARD = True              # study ke dauraan distracting sites check karo
CLOSE_DISTRACTING_TABS = True   # True = tab band kar do, False = sirf tok do

# Ye sites study ke dauraan band hongi.
# YouTube se lectures dekhte hain to "youtube" is list se hata dein.
DISTRACTING_SITES = ["youtube", "instagram", "facebook", "netflix", "tiktok",
                     "twitter", "/ x", "reddit", "snapchat", "twitch"]
BROWSER_NAMES = ["google chrome", "microsoft edge", "mozilla firefox", "brave"]

GUARD_CHECK_SECONDS = 3         # har kitne second baad check kare
WARN_COOLDOWN = 30              # "back to work" baar baar na bole (second)

_speaker = None                 # aura_core.py yahan speak() deta hai


def set_speaker(func):
    global _speaker
    _speaker = func


def _say(text):
    """Background se bolna (study mode ke announcements)."""
    print(f"\n🎓 AURA: {text}")
    if _speaker:
        try:
            _speaker(text)
        except Exception as e:
            print(f"   ⚠️ Bol nahi saki: {e}")


# ============================================================
# PART 1: DEADLINES 📝
# ============================================================
DEADLINE_WORDS = ("assignment", "assignments", "quiz", "quizzes", "project", "projects",
                  "deadline", "deadlines", "exam", "exams", "test", "tests", "lab", "report",
                  "presentation", "homework", "submission", "viva", "midterm", "midterms",
                  "final", "finals", "paper")
LIST_TOPIC_WORDS = ("due", "deadline", "deadlines", "assignments", "quizzes", "exams", "tests",
                    "projects", "homework", "submissions", "presentations", "pending")
LIST_QUESTION_WORDS = ("what", "whats", "which", "any", "show", "list", "tell me",
                       "do i have", "how many", "upcoming", "remaining", "check")
DONE_WORDS = ("finished", "completed", "submitted", "done with", "mark", "i did",
              "have done", "turned in")
DELETE_WORDS = ("delete", "remove", "cancel", "forget")

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MONTH_NAMES = (r"january|february|march|april|may|june|july|august|september|october|"
               r"november|december|jan|feb|mar|apr|jun|jul|aug|sept|sep|oct|nov|dec")
MONTH_NUM = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
             "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
SMALL_NUMBERS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                 "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}

DAY_MONTH_RE = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(" + MONTH_NAMES + r")\b")
MONTH_DAY_RE = re.compile(r"\b(" + MONTH_NAMES + r")\s+(\d{1,2})(?:st|nd|rd|th)?\b")
WEEKDAY_RE = re.compile(r"\b(?:next\s+|this\s+|coming\s+)?(" + "|".join(WEEKDAYS) + r")\b")
IN_DAYS_RE = re.compile(r"\bin\s+(\d+)\s+days?\b")

# Title banate waqt ye date wale hisse hata do
DATE_PATTERNS = [
    r"\bday after tomorrow\b",
    r"\b(?:today|tonight|tomorrow)\b",
    r"\bin\s+\d+\s+days?\b",
    r"\bin\s+a\s+week\b",
    r"\bnext\s+week\b",
    DAY_MONTH_RE.pattern,
    MONTH_DAY_RE.pattern,
    WEEKDAY_RE.pattern,
]

# Title ke aakhir se ye faltu words hata do ("dsa assignment is due on" -> "dsa assignment")
TRAILING_WORDS = {"is", "due", "on", "by", "before", "for", "deadline", "deadlines", "the",
                  "this", "next", "of", "at", "coming", "submit", "in", "to", "my", "list"}
MATCH_STOPWORDS = {"the", "a", "an", "my", "i", "is", "it", "as", "with", "of", "for", "to"}


def load_deadlines():
    try:
        with open(DEADLINES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_deadlines(items):
    with open(DEADLINES_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


def small_numbers_to_digits(t):
    """'in three days' -> 'in 3 days'"""
    for word, number in SMALL_NUMBERS.items():
        t = re.sub(rf"\b{word}\s+(days?)\b", rf"{number} \1", t)
    return t


def _make_date(day, month_name, today):
    """Din + mahina -> date (guzar gaya ho to agle saal ka)."""
    month = MONTH_NUM[month_name[:3]]
    try:
        d = date(today.year, month, day)
        if d < today:
            d = date(today.year + 1, month, day)
        return d
    except ValueError:          # jaise 30 February
        return None


def parse_date(t):
    """'friday' / 'tomorrow' / '5th november' / 'in 3 days' -> date. Na mile to None."""
    t = small_numbers_to_digits(t)
    today = date.today()
    if has(t, "day after tomorrow"):
        return today + timedelta(days=2)
    if has(t, "tomorrow"):
        return today + timedelta(days=1)
    if has(t, "today", "tonight"):
        return today

    m = IN_DAYS_RE.search(t)
    if m:
        return today + timedelta(days=int(m.group(1)))
    if has(t, "in a week", "next week"):
        return today + timedelta(days=7)

    m = DAY_MONTH_RE.search(t)
    if m:
        return _make_date(int(m.group(1)), m.group(2), today)
    m = MONTH_DAY_RE.search(t)
    if m:
        return _make_date(int(m.group(2)), m.group(1), today)

    m = WEEKDAY_RE.search(t)
    if m:
        target = WEEKDAYS.index(m.group(1))
        ahead = (target - today.weekday()) % 7
        if ahead == 0:
            ahead = 7           # aaj Friday hai aur "Friday" bola -> agla Friday
        return today + timedelta(days=ahead)
    return None


def extract_title(t):
    """'add dsa assignment due friday' -> 'dsa assignment'"""
    s = t
    for pattern in DATE_PATTERNS:
        s = re.sub(pattern, " ", s)
    s = " ".join(s.split())

    s = re.sub(r"^(?:add|new|create|save|set|note|put)\s+", "", s)
    s = re.sub(r"^(?:i\s+have\s+to\s+submit|i\s+have\s+got|i\s+have|i\s+ve\s+got|i\s+got|"
               r"there\s+is|there\s+s|we\s+have)\s+", "", s)
    s = re.sub(r"^(?:a|an|the|my|our|new)\s+", "", s)
    s = re.sub(r"^deadline\s+(?:for\s+|of\s+)?", "", s)

    words = s.split()
    while words and words[-1] in TRAILING_WORDS:
        words.pop()
    while words and words[0] in {"a", "an", "the", "my"}:
        words.pop(0)
    return " ".join(words)


def when_str(d):
    """date -> 'due tomorrow' / 'due on Friday' / 'due on 5 November' / 'was due 2 days ago'"""
    diff = (d - date.today()).days
    if diff < 0:
        return f"was due {-diff} day{'s' if diff < -1 else ''} ago"
    if diff == 0:
        return "due today"
    if diff == 1:
        return "due tomorrow"
    if diff < 7:
        return f"due on {d.strftime('%A')}"
    return f"due on {d.day} {d.strftime('%B')}"


def find_deadline(t, items):
    """Text se sab se zyada milti julti deadline dhoondo."""
    words = set(t.split()) - MATCH_STOPWORDS
    best, best_score = None, 0
    for item in sorted(items, key=lambda x: x["due"]):
        score = len(set(item["title"].split()) & words)
        if score > best_score:
            best, best_score = item, score
    return best


def list_deadlines(t, items):
    today = date.today()
    pending = sorted(items, key=lambda x: x["due"])

    def due_of(item):
        return date.fromisoformat(item["due"])

    if has(t, "overdue", "late", "missed"):
        selected, label = [i for i in pending if due_of(i) < today], "overdue"
    elif has(t, "today"):
        selected, label = [i for i in pending if due_of(i) <= today], "today"
    elif has(t, "tomorrow"):
        selected, label = [i for i in pending if due_of(i) == today + timedelta(days=1)], "tomorrow"
    elif has(t, "next week"):
        selected, label = [i for i in pending if due_of(i) <= today + timedelta(days=14)], "in the next two weeks"
    elif has(t, "this week", "week"):
        selected, label = [i for i in pending if due_of(i) <= today + timedelta(days=7)], "this week"
    else:
        selected, label = pending, ""

    if not selected:
        if label:
            return f"Nothing is due {label}. Enjoy!"
        return "You have no pending deadlines."

    parts = [f"{i['title']}, {when_str(due_of(i))}" for i in selected]
    count = len(selected)
    label_text = f" {label}" if label else ""
    return (f"You have {count} deadline{'s' if count > 1 else ''}{label_text}: "
            + "; ".join(parts) + ".")


def deadline_summary(days=1):
    """Agle kuch din ki deadlines ka chhota summary (Batch 3 ki morning briefing ke liye)."""
    items = load_deadlines()
    limit = date.today() + timedelta(days=days)
    soon = [i for i in items if date.fromisoformat(i["due"]) <= limit]
    if not soon:
        return ""
    soon.sort(key=lambda x: x["due"])
    return "; ".join(f"{i['title']}, {when_str(date.fromisoformat(i['due']))}" for i in soon)


def handle_deadlines(t):
    t = small_numbers_to_digits(t)
    if not (has(t, *DEADLINE_WORDS) or has(t, "due")):
        return None
    if has(t, "to my list", "to my notes", "to my to do list", "to my todo list"):
        return None   # "add X to my list" notes wala feature hai (daily_tools)

    items = load_deadlines()

    # ---- List: "what's due this week" ----
    if (has(t, *LIST_QUESTION_WORDS) and has(t, *LIST_TOPIC_WORDS)
            and not re.match(r"^(?:add|new|create|save)\b", t)):
        return list_deadlines(t, items)

    # ---- Done: "i finished the dsa assignment" ----
    if has(t, *DONE_WORDS):
        item = find_deadline(t, items)
        if item:
            items.remove(item)
            save_deadlines(items)
            return f"Great job! I removed {item['title']} from your deadlines."
        return None   # "i finished my dinner" -> Llama jawab de

    # ---- Delete: "delete the physics quiz deadline" ----
    if has(t, *DELETE_WORDS):
        item = find_deadline(t, items)
        if item:
            items.remove(item)
            save_deadlines(items)
            return f"Deleted {item['title']}."
        return "I couldn't find that deadline."

    # ---- Add: "add dsa assignment due friday" / "i have a quiz on monday" ----
    due = parse_date(t)
    explicit_add = re.match(r"^(?:add|new|create|save)\b", t)
    if not due:
        if explicit_add:
            return "When is it due? Please say something like: add DSA assignment due Friday."
        return None

    adding = explicit_add or re.match(
        r"^(?:set|note|put|i have|i ve got|i got|there is|there s|we have|my|the|our)\b", t) or has(t, "due")
    if not adding:
        return None

    title = extract_title(t)
    if not title:
        return "What is it called? Please say something like: add DSA assignment due Friday."

    items.append({"title": title, "due": due.isoformat(),
                  "added": datetime.now().strftime("%Y-%m-%d %H:%M")})
    save_deadlines(items)
    return f"Added {title}, {when_str(due)}."


# ============================================================
# PART 2: STUDY MODE (POMODORO) 🍅
# ============================================================
# "study", "studying", "focus", "pomodoro" kisi bhi shakal mein
# (Whisper "study mode" ko "study more" / "study mood" bhi likh deta hai, sab chalega)
STUDY_RE = re.compile(r"\b(?:study|studying|studies|focus|focusing|pomodoro)\b")
START_WORDS = ("start", "begin", "turn on", "enable", "activate", "switch on", "resume")
STOP_WORDS = ("stop", "end", "finish", "cancel", "turn off", "quit", "exit", "disable", "switch off")
# Sawal ho to study mode shuru NAHI karna ("when does my study start?")
QUESTION_START_RE = re.compile(r"^(?:what|when|why|how|where|who|is|are|do|does|did|will)\b")

_study = {
    "running": False, "phase": None, "ends_at": None,
    "session": 0, "completed": 0, "focus_seconds": FOCUS_MINUTES * 60,
    "stop": threading.Event(), "skip": threading.Event(), "last_warn": 0,
}


def is_status_question(t):
    """
    Kya ye 'kitna time bacha' wala sawal hai?
    "how much time is left", "how much study time is left", "time remaining", "study status"
    """
    return (has(t, "left", "remaining", "status")
            or (has(t, "how much", "how long") and has(t, "time", "minutes", "longer")))


def status_text():
    s = _study
    if not s["running"] or not s["ends_at"]:
        return "Study mode is not on."
    left = max(0, int((s["ends_at"] - datetime.now()).total_seconds()))
    minutes, seconds = divmod(left, 60)
    phase = "focus session" if s["phase"] == "focus" else "break"
    return (f"{minutes} minutes and {seconds} seconds left in this {phase}. "
            f"Completed sessions: {s['completed']}.")


def _guard_check():
    """Saamne YouTube/Instagram ho to tab band karo aur tok do."""
    try:
        win = gw.getActiveWindow()
    except Exception:
        return
    if not win:
        return
    title = win.title.replace("\u200b", "").lower()
    if not any(b in title for b in BROWSER_NAMES):
        return
    site = next((x for x in DISTRACTING_SITES if x in title), None)
    if not site:
        return

    if CLOSE_DISTRACTING_TABS:
        pyautogui.hotkey("ctrl", "w")
        print(f"   🚫 Focus guard: {site.strip(' /')} tab band kar diya")

    now = time.time()
    if now - _study["last_warn"] > WARN_COOLDOWN:
        _study["last_warn"] = now
        threading.Thread(target=_say, args=("This is study time. Back to work!",), daemon=True).start()


def _wait(seconds, guard):
    """Itne second ruko. Stop ho jaye to False, warna True."""
    s = _study
    end = time.time() + seconds
    while True:
        remaining = end - time.time()
        if remaining <= 0:
            return True
        if s["stop"].wait(min(GUARD_CHECK_SECONDS, remaining)):
            return False                 # "stop study mode" bola gaya
        if s["skip"].is_set():
            s["skip"].clear()
            return True                  # "skip the break" bola gaya
        if guard and FOCUS_GUARD:
            _guard_check()


def _study_loop():
    s = _study
    try:
        while not s["stop"].is_set():
            s["session"] += 1
            focus = s["focus_seconds"]
            s["phase"] = "focus"
            s["ends_at"] = datetime.now() + timedelta(seconds=focus)
            if s["session"] > 1:
                _say(f"Break is over. Session {s['session']} starts now. "
                     f"Focus for {focus // 60} minutes.")
            if not _wait(focus, guard=True):
                break

            s["completed"] += 1
            long_break = s["completed"] % SESSIONS_BEFORE_LONG_BREAK == 0
            minutes = LONG_BREAK_MINUTES if long_break else SHORT_BREAK_MINUTES
            s["phase"] = "break"
            s["ends_at"] = datetime.now() + timedelta(minutes=minutes)
            _say(f"Great work! Session {s['completed']} is done. "
                 f"Take a {minutes} minute {'long ' if long_break else ''}break.")
            if not _wait(minutes * 60, guard=False):
                break
    finally:
        s["running"] = False
        s["phase"] = None
        s["ends_at"] = None


def start_study(minutes):
    _study.update(
        running=True, phase="focus", session=0, completed=0,
        focus_seconds=minutes * 60, last_warn=0,
        ends_at=datetime.now() + timedelta(minutes=minutes),
        stop=threading.Event(), skip=threading.Event(),
    )
    threading.Thread(target=_study_loop, daemon=True).start()


def handle_study(t):
    s = _study
    about_study = bool(STUDY_RE.search(t)) or has(t, "break", "session")

    # ---- Skip break ----
    if has(t, "skip") and has(t, "break"):
        if s["running"] and s["phase"] == "break":
            s["skip"].set()
            return "Skipping the break. Back to study!"
        return "You are not on a break right now."

    # ---- Kitna time bacha? ----
    if is_status_question(t):
        if about_study:
            return status_text()
        if s["running"] and has(t, "time", "minutes", "longer"):
            return status_text()

    # ---- Stop: "stop study mode" / "stop studying" / "end focus" ----
    if STUDY_RE.search(t) and has(t, *STOP_WORDS):
        if not s["running"]:
            return "Study mode is not on."
        s["stop"].set()
        n = s["completed"]
        return f"Study mode stopped. You completed {n} focus session{'s' if n != 1 else ''}. Well done!"

    # ---- Start: "start study mode" / "start study more for 2 min" / "start studying" ----
    wants_start = (
        (STUDY_RE.search(t) and has(t, *START_WORDS) and not QUESTION_START_RE.match(t))
        or has(t, "i want to study", "let s study", "lets study", "time to study")
        or t in ("study mode", "study more", "study mood", "focus mode", "pomodoro")
    )
    if not wants_start:
        return None
    if s["running"]:
        return "Study mode is already on. " + status_text()

    seconds = parse_duration(words_to_digits(t))
    minutes = max(1, min(180, round(seconds / 60))) if seconds else FOCUS_MINUTES
    start_study(minutes)

    guard_msg = ""
    if FOCUS_GUARD:
        guard_msg = (" I will close distracting tabs like YouTube and Instagram."
                     if CLOSE_DISTRACTING_TABS else " I will warn you if you open distracting sites.")
    return (f"Study mode on. Focus for {minutes} minutes, then a {SHORT_BREAK_MINUTES} "
            f"minute break.{guard_msg} Let's go!")


# ============================================================
# MAIN FUNCTION: aura_core.py isi ko call karta hai
# ============================================================
def handle_student(text):
    t = clean(text)
    if not t:
        return None
    for handler in (handle_study, handle_deadlines):
        try:
            reply = handler(t)
        except Exception as e:
            print(f"   ❌ {handler.__name__} error: {e}")
            return "Sorry, I couldn't do that."
        if reply:
            return reply
    return None


# ============================================================
# TEST MODE: python student_tools.py
# ============================================================
if __name__ == "__main__":
    print("🧪 Test mode — command likhein (band karne ke liye 'q')")
    while True:
        cmd = input("\n⌨️  Command: ")
        if cmd.strip().lower() == "q":
            break
        reply = handle_student(cmd)
        print("🤖", reply if reply else "(student command nahi thi — aage jati)")