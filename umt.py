# ============================================================
# umt.py — AURA + UMT LMS 🎓🔗
# 1) LMS se assignments / quizzes khud fetch (Moodle API)
# 2) Nayi assignments deadlines mein auto add + bol kar batana
# 3) Deadline 24 ghante reh jaye to khud yaad dilana
# 4) "Open LMS" / "Open portal" -> browser khol kar khud login
# (Portal attendance: agla step, portal recording milne ke baad)
# Fix: login sirf VISIBLE boxes mein bharta hai (hidden "logintoken" nahi)
# ============================================================

import json               # cache file ke liye
import re                 # naam saaf karne ke liye
import threading          # auto sync aur browser background mein
import time
from datetime import date, datetime, timedelta

import keyring            # Windows Credential Manager (password yahan se)
import requests           # LMS API se baat

from daily_tools import clean, has, format_when
from student_tools import load_deadlines, save_deadlines


# ============================================================
# SETTINGS
# ============================================================
SERVICE = "AURA-UMT"                    # umt_setup.py wala hi naam
LMS_URL = "https://lms.umt.edu.pk"
PORTAL_URL = "https://online.umt.edu.pk"   # portal ka link alag ho to yahan badlein

PROFILE_DIR = "browser_profile"         # login yaad rakhne wala browser folder
CACHE_FILE = "lms_cache.json"           # kis cheez ki warning de chuke hain

SYNC_EVERY_HOURS = 3                    # har kitne ghante baad LMS check kare
FIRST_SYNC_DELAY = 20                   # AURA start hone ke kitne second baad pehli sync
WARN_HOURS = 24                         # deadline itne ghante reh jaye to yaad dilao
LOOKBACK_DAYS = 3                       # thori purani (late) assignments bhi dikhao

# Username box dhoondne ki tarteeb (pehle Moodle ka asal box)
USERNAME_SELECTORS = [
    "input#username",
    "input[name='username']",
    "input[type='email']",
    "input[name*='user' i]:not([type='hidden'])",
    "input[id*='user' i]:not([type='hidden'])",
    "input[type='text']",
]

_speaker = None
_sync_started = False
_browser_busy = False


def set_speaker(func):
    global _speaker
    _speaker = func


def _say(text):
    """Background se bolna (auto sync ki khabrein)."""
    print(f"\n🎓 AURA: {text}")
    if _speaker:
        try:
            _speaker(text)
        except Exception as e:
            print(f"   ⚠️ Bol nahi saki: {e}")


# ============================================================
# PART 1: LMS API (Moodle) 📚
# ============================================================
def get_token(force_new=False):
    """Saved token do. Expire ho gaya ho to dobara login kar ke naya lo."""
    token = keyring.get_password(SERVICE, "lms_token")
    if token and not force_new:
        return token

    user = keyring.get_password(SERVICE, "lms_username")
    password = keyring.get_password(SERVICE, "lms_password")
    if not user or not password:
        raise RuntimeError("I don't have your LMS login. Please run umt setup first.")

    data = requests.post(f"{LMS_URL}/login/token.php",
                         data={"username": user, "password": password,
                               "service": "moodle_mobile_app"}, timeout=20).json()
    if "token" not in data:
        raise RuntimeError(f"LMS login failed: {data.get('error', 'unknown error')}")
    keyring.set_password(SERVICE, "lms_token", data["token"])
    return data["token"]


def moodle(function, **params):
    """Moodle API call. Token purana ho to aik dafa naya le kar dobara try."""
    for attempt in (1, 2):
        token = get_token(force_new=(attempt == 2))
        data = requests.post(f"{LMS_URL}/webservice/rest/server.php",
                             data={"wstoken": token, "wsfunction": function,
                                   "moodlewsrestformat": "json", **params},
                             timeout=20).json()
        if isinstance(data, dict) and data.get("exception"):
            if data.get("errorcode") in ("invalidtoken", "accessexception") and attempt == 1:
                continue
            raise RuntimeError(f"LMS error: {data.get('message')}")
        return data
    return {}


def course_name(full_name):
    """'CC230 - Database Systems - Mohsin ... - D1 - OC' -> 'Database Systems'"""
    parts = [p.strip() for p in full_name.split(" - ")]
    return parts[1] if len(parts) > 1 else full_name.strip()


def clean_event_name(name):
    """'ASSIGNMENT 1 is due' -> 'Assignment 1'"""
    name = re.sub(r"\s+(?:is due|is due to be graded|closes|opens|due)$", "", name.strip(), flags=re.I)
    return name.title() if name.isupper() else name


def fetch_lms_events():
    """LMS se pending assignments / quizzes ki list."""
    data = moodle("core_calendar_get_action_events_by_timesort",
                  timesortfrom=int(time.time()) - LOOKBACK_DAYS * 86400, limitnum=50)
    events = []
    for e in (data.get("events", []) if isinstance(data, dict) else []):
        due = datetime.fromtimestamp(e.get("timesort", 0))
        course = course_name((e.get("course") or {}).get("fullname", ""))
        name = clean_event_name(e.get("name", ""))
        nice = f"{course}, {name}" if course else name
        title = " ".join(re.sub(r"[^\w\s]", " ", f"{course} {name}").lower().split())
        events.append({
            "id": e.get("id"),
            "nice": nice,                                        # bolne ke liye
            "title": title,                                      # deadlines.json ke liye
            "due": due,
            "due_date": (due - timedelta(minutes=1)).date(),     # 12:00 AM = pichle din ki raat
        })
    events.sort(key=lambda x: x["due"])
    return events


def when_due(dt):
    """Deadline ko insani zubaan mein: 'tonight at midnight', 'tomorrow at 11:59 PM'..."""
    now = datetime.now()
    if dt <= now:
        return f"was due {format_when(dt)}"
    if dt.hour == 0 and dt.minute == 0:                # raat 12 baje wali deadlines
        d = (dt - timedelta(minutes=1)).date()
        today = date.today()
        if d == today:
            return "tonight at midnight"
        if d == today + timedelta(days=1):
            return "tomorrow night at midnight"
        return f"on {d.strftime('%A')}, {d.day} {d.strftime('%B')} at midnight"
    return format_when(dt)


# ============================================================
# PART 2: SYNC 🔄 (LMS -> deadlines.json + warnings)
# ============================================================
def load_cache():
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"warned": {}}


def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def sync_lms(announce=True):
    """
    LMS check karo:
    - nayi assignments deadlines mein daalo
    - submit / band ho chuki hata do
    - 24 ghante wali deadlines ki warning do
    """
    events = fetch_lms_events()
    now = datetime.now()

    items = load_deadlines()
    current_ids = {e["id"] for e in events}
    known_ids = {i.get("lms_id") for i in items if i.get("source") == "lms"}

    # Jo ab LMS par pending nahi (submit ho gayi), unhein hata do
    before = len(items)
    items = [i for i in items
             if not (i.get("source") == "lms" and i.get("lms_id") not in current_ids)]
    removed = before - len(items)

    # Nayi wali add karo
    new = [e for e in events if e["id"] not in known_ids]
    for e in new:
        items.append({
            "title": e["title"],
            "due": e["due_date"].isoformat(),
            "added": now.strftime("%Y-%m-%d %H:%M"),
            "source": "lms",
            "lms_id": e["id"],
        })
    save_deadlines(items)

    # Kya bolna hai
    cache = load_cache()
    warned = cache.setdefault("warned", {})
    messages = []
    if new:
        parts = "; ".join(f"{e['nice']}, due {when_due(e['due'])}" for e in new)
        messages.append(f"I found {len(new)} new item{'s' if len(new) > 1 else ''} on LMS: {parts}.")

    for e in events:
        left = e["due"] - now
        key = str(e["id"])
        if timedelta(0) < left <= timedelta(hours=WARN_HOURS) and key not in warned:
            warned[key] = now.isoformat()
            if e not in new:                        # nayi wali ka time pehle hi bata diya
                messages.append(f"Heads up! {e['nice']} is due {when_due(e['due'])}.")

    cache["warned"] = {k: v for k, v in warned.items() if k in {str(i) for i in current_ids}}
    cache["last_sync"] = now.isoformat()
    save_cache(cache)

    print(f"   🔄 LMS sync: {len(events)} pending, {len(new)} new, {removed} removed")
    if announce:
        for m in messages:
            _say(m)
    return events, new, removed


def _auto_sync_loop():
    time.sleep(FIRST_SYNC_DELAY)
    while True:
        try:
            sync_lms(announce=True)
        except Exception as e:
            print(f"   ⚠️ LMS auto sync fail: {e}")
        time.sleep(SYNC_EVERY_HOURS * 3600)


def start_auto_sync():
    """aura_core.py start par ye call karta hai."""
    global _sync_started
    if _sync_started:
        return
    if not keyring.get_password(SERVICE, "lms_username"):
        print("⚠️ UMT login saved nahi hai. Pehle chalayein: python umt_setup.py")
        return
    _sync_started = True
    threading.Thread(target=_auto_sync_loop, daemon=True).start()
    print(f"🔄 LMS auto sync on (har {SYNC_EVERY_HOURS} ghante)")


def list_lms():
    events = fetch_lms_events()
    if not events:
        return "You have no pending items on LMS. Nice work!"
    parts = [f"{e['nice']}, due {when_due(e['due'])}" for e in events[:6]]
    count = len(events)
    return f"You have {count} pending item{'s' if count > 1 else ''} on LMS: " + "; ".join(parts) + "."


def sync_reply():
    events, new, removed = sync_lms(announce=False)
    reply = f"LMS synced. You have {len(events)} pending item{'s' if len(events) != 1 else ''}"
    if new:
        reply += f", and {len(new)} of them {'are' if len(new) > 1 else 'is'} new"
    reply += "."
    if removed:
        reply += f" I removed {removed} that you already submitted."
    if events:
        e = events[0]
        reply += f" The next one is {e['nice']}, due {when_due(e['due'])}."
    return reply


# ============================================================
# PART 3: AUTO LOGIN BROWSER 🔐
# ============================================================
def _find_visible(page, selectors):
    """Selectors ki list mein se pehla NAZAR AANE wala box do (hidden wale skip)."""
    for sel in selectors:
        box = page.locator(f"{sel}:visible").first
        try:
            if box.count() > 0:
                return box
        except Exception:
            continue
    return None


def _try_login(page, user, password):
    """Page par login form ho to bhar do. Wapas: kya hua (text)."""
    pw_box = page.locator("input[type='password']:visible").first
    try:
        pw_box.wait_for(state="visible", timeout=8000)
    except Exception:
        return "login form nahi mila (shayad pehle se logged in hain)"

    user_box = _find_visible(page, USERNAME_SELECTORS)
    if user_box is None:
        return "username wala box nahi mila, khud login kar lein"

    try:
        user_box.fill(user, timeout=5000)
        pw_box.fill(password, timeout=5000)
        pw_box.press("Enter")
        return "✅ username aur password bhar kar login daba diya"
    except Exception as e:
        first_line = str(e).splitlines()[0]
        return f"bhar nahi saka ({first_line}), khud login kar lein"


def _browser_thread(kind):
    global _browser_busy
    try:
        from playwright.sync_api import sync_playwright
        user = keyring.get_password(SERVICE, f"{kind}_username")
        password = keyring.get_password(SERVICE, f"{kind}_password")
        url = f"{LMS_URL}/my/" if kind == "lms" else PORTAL_URL

        with sync_playwright() as p:
            # "persistent" = cookies yaad rehti hain, agli dafa shayad login ki zaroorat hi na pade
            ctx = p.chromium.launch_persistent_context(
                PROFILE_DIR, headless=False, no_viewport=True, args=["--start-maximized"])
            page = ctx.pages[0] if ctx.pages else ctx.new_page()

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                print(f"   🔐 {kind.upper()} login: {_try_login(page, user, password)}")
            except Exception as e:
                # Login fail ho to bhi browser khula rahe, taake aap khud kar sakein
                print(f"   ⚠️ {kind.upper()} auto login nahi hua: {str(e).splitlines()[0]}")

            # Browser tab tak khula rakho jab tak aap khud band na karein
            try:
                while ctx.pages:
                    ctx.pages[0].wait_for_timeout(1000)
            except Exception:
                pass
            try:
                ctx.close()
            except Exception:
                pass
    except Exception as e:
        print(f"   ❌ Browser error: {str(e).splitlines()[0]}")
    finally:
        _browser_busy = False


def open_logged_in(kind):
    global _browser_busy
    label = "LMS" if kind == "lms" else "the student portal"
    if _browser_busy:
        return "The UMT browser window is already open."
    if not keyring.get_password(SERVICE, f"{kind}_username"):
        return "I don't have your UMT login. Please run umt setup first."
    _browser_busy = True
    threading.Thread(target=_browser_thread, args=(kind,), daemon=True).start()
    return f"Opening {label} and logging you in."


# ============================================================
# MAIN FUNCTION: aura_core.py isi ko call karta hai
# ============================================================
def handle_umt(text):
    t = clean(text)
    if not t:
        return None

    about_lms = has(t, "lms", "moodle")
    about_portal = has(t, "portal", "student portal")
    about_attendance = has(t, "attendance")
    if not (about_lms or about_portal or about_attendance):
        return None
    if has(t, "close", "exit", "quit"):
        return None   # "close lms" -> actions.py tab band karega

    try:
        # ---- "Open LMS" / "Log in to portal" ----
        if has(t, "open", "login", "log in", "sign in", "launch", "go to", "take me to"):
            if about_lms:
                return open_logged_in("lms")
            if about_portal:
                return open_logged_in("portal")

        # ---- Attendance (agla step) ----
        if about_attendance:
            return ("I can't read your attendance yet. Please send the portal recording "
                    "so I can finish this feature.")

        # ---- "Check my LMS" / "Sync LMS" ----
        if about_lms and has(t, "sync", "refresh", "update", "fetch", "check", "reload"):
            return sync_reply()

        # ---- "What's due on LMS" / "Any new assignments on LMS" ----
        if about_lms:
            return list_lms()

    except RuntimeError as e:
        return str(e)
    except requests.exceptions.RequestException:
        return "I couldn't reach LMS. Please check your internet connection."
    return None


# ============================================================
# TEST MODE: python umt.py
# ============================================================
if __name__ == "__main__":
    print("🧪 Test mode — command likhein (band karne ke liye 'q')")
    while True:
        cmd = input("\n⌨️  Command: ")
        if cmd.strip().lower() == "q":
            break
        reply = handle_umt(cmd)
        print("🤖", reply if reply else "(UMT command nahi thi — aage jati)")