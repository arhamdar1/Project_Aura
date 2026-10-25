# ============================================================
# system_control.py — AURA ka "control panel" ⚙️
# Volume, brightness, WiFi, Bluetooth, battery, settings pages,
# lock / sleep / shutdown, screenshot, folders aur files kholna
# ============================================================

import asyncio            # WiFi/Bluetooth wala Windows API "async" hai
import glob               # OneDrive folders dhoondne ke liye
import os                 # files/folders kholne ke liye
import re                 # text mein words dhoondne ke liye
import subprocess         # Windows commands (shutdown, lock)
import threading          # thori der baad kaam karne ke liye (sleep)
from datetime import datetime

import pyautogui          # keyboard keys (Win + D, volume keys) + screenshot
import psutil             # battery info

# ---- Brightness (load na ho to AURA phir bhi chale) ----
try:
    import screen_brightness_control as sbc
    BRIGHTNESS_OK = True
except Exception:
    BRIGHTNESS_OK = False

# ---- Volume (pycaw) ----
try:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    PYCAW_OK = True
except Exception:
    PYCAW_OK = False

# ---- WiFi / Bluetooth (Windows Radio API) ----
try:
    from winrt.windows.devices.radios import Radio, RadioState
    RADIO_OK = True
except Exception:
    RADIO_OK = False


# ============================================================
# SETTINGS
# ============================================================
VOLUME_STEP = 10          # "volume up" par kitna barhe (%)
BRIGHTNESS_STEP = 10      # "brighter" par kitna barhe (%)
SHUTDOWN_DELAY = 30       # shutdown/restart se pehle kitne second (cancel ka mauqa)
HOME = os.path.expanduser("~")    # C:\Users\Arham Dar

WIFI_KIND = 1             # Windows mein WiFi radio ka number
BLUETOOTH_KIND = 3        # Windows mein Bluetooth radio ka number

UP_WORDS = ("up", "increase", "raise", "louder", "higher", "more", "brighter")
DOWN_WORDS = ("down", "decrease", "lower", "reduce", "quieter", "less",
              "dimmer", "dim", "darker")
DEVICE_WORDS = ("laptop", "computer", "pc", "system", "screen", "device", "windows")

# Settings pages: naam -> Windows settings link
SETTINGS_PAGES = {
    "bluetooth": "ms-settings:bluetooth",
    "wifi": "ms-settings:network-wifi",
    "network": "ms-settings:network",
    "internet": "ms-settings:network",
    "display": "ms-settings:display",
    "screen": "ms-settings:display",
    "sound": "ms-settings:sound",
    "volume": "ms-settings:sound",
    "battery": "ms-settings:batterysaver",
    "battery saver": "ms-settings:batterysaver",
    "energy saver": "ms-settings:batterysaver",
    "power": "ms-settings:powersleep",
    "night light": "ms-settings:nightlight",
    "airplane mode": "ms-settings:network-airplanemode",
    "hotspot": "ms-settings:network-mobilehotspot",
    "vpn": "ms-settings:network-vpn",
    "notifications": "ms-settings:notifications",
    "windows update": "ms-settings:windowsupdate",
    "update": "ms-settings:windowsupdate",
    "apps": "ms-settings:appsfeatures",
    "storage": "ms-settings:storagesense",
    "wallpaper": "ms-settings:personalization-background",
    "background": "ms-settings:personalization-background",
    "theme": "ms-settings:themes",
    "mouse": "ms-settings:mousetouchpad",
    "touchpad": "ms-settings:devices-touchpad",
    "keyboard": "ms-settings:typing",
    "privacy": "ms-settings:privacy",
    "date and time": "ms-settings:dateandtime",
    "time": "ms-settings:dateandtime",
    "language": "ms-settings:regionlanguage",
    "printer": "ms-settings:printers",
    "about": "ms-settings:about",
}

# Ye 3 cheezein Windows Python se seedha on/off nahi karne deti -> page kholenge
SETTINGS_ONLY_TOGGLES = {
    "battery saver": "ms-settings:batterysaver",
    "energy saver": "ms-settings:batterysaver",
    "night light": "ms-settings:nightlight",
    "airplane mode": "ms-settings:network-airplanemode",
}

# Aap ke folders: bolne wala naam -> Windows folder ka naam
USER_FOLDERS = {
    "downloads": "Downloads",
    "documents": "Documents",
    "desktop": "Desktop",
    "pictures": "Pictures",
    "music": "Music",
    "videos": "Videos",
}

# File dhoondte waqt ye folders skip (bohat bare / faltu)
SKIP_DIRS = {"node_modules", "venv", ".git", "__pycache__", "appdata", "$recycle.bin"}
MAX_DEPTH = 4             # folders ke andar kitna gehra dhoonde

# File ke naam se pehle/baad wale faltu words
FILLER_WORDS = {"the", "my", "a", "an", "called", "named", "please", "dot", "for", "me"}


# ============================================================
# HELPER FUNCTIONS
# ============================================================
def clean(text):
    """Text saaf karo: lowercase, punctuation hatao, aam spellings aik jaisi karo."""
    text = text.lower()
    text = text.replace("wi-fi", "wifi")
    text = re.sub(r"[^\w\s%]", " ", text)        # % rakho, baaqi symbols hatao
    text = text.replace("%", " percent")
    text = " ".join(text.split())
    text = text.replace("wi fi", "wifi").replace("blue tooth", "bluetooth")
    text = text.replace("screen shot", "screenshot").replace("shut down", "shutdown")
    return text


def has(text, *words):
    """Kya text mein in mein se koi poora word/phrase hai?"""
    return any(re.search(rf"\b{re.escape(w)}\b", text) for w in words)


def get_number(text):
    """Text mein se 0-100 ka number nikalo (jaise 'volume 40' -> 40)."""
    match = re.search(r"\b(\d{1,3})\b", text)
    if match:
        return max(0, min(100, int(match.group(1))))
    return None


def wants_off(text):
    return has(text, "off", "disable", "disconnect", "deactivate")


def wants_on(text):
    return has(text, "on", "enable", "connect", "activate")


def enum_value(x):
    """Windows enum ko simple number bana do."""
    return int(getattr(x, "value", x))


def folder_options(name):
    """Folder ki saari mumkin jagahein (OneDrive wali bhi)."""
    options = glob.glob(os.path.join(HOME, "OneDrive*", name))
    options.append(os.path.join(HOME, name))
    return [p for p in options if os.path.isdir(p)]


def find_user_folder(name):
    """Asli folder dhoondo (jis mein zyada cheezein hon, wohi asli hai)."""
    options = folder_options(name)
    if not options:
        return None

    def count(p):
        try:
            return len(os.listdir(p))
        except Exception:
            return 0

    return max(options, key=count)


# ============================================================
# 1) POWER: lock, sleep, shutdown, restart 🔒
# ============================================================
def handle_power(t):
    # Shutdown cancel
    if has(t, "cancel", "abort", "stop") and has(t, "shutdown", "restart"):
        result = subprocess.run(["shutdown", "/a"], capture_output=True, text=True)
        if result.returncode == 0:
            return "Shutdown cancelled."
        return "There was no shutdown to cancel."

    # Shutdown
    if has(t, "shutdown", "power off") and (has(t, *DEVICE_WORDS) or t.startswith("shutdown")):
        subprocess.run(["shutdown", "/s", "/t", str(SHUTDOWN_DELAY)])
        return f"Shutting down in {SHUTDOWN_DELAY} seconds. Say cancel shutdown to stop it."

    # Restart
    if has(t, "restart", "reboot") and has(t, *DEVICE_WORDS):
        subprocess.run(["shutdown", "/r", "/t", str(SHUTDOWN_DELAY)])
        return f"Restarting in {SHUTDOWN_DELAY} seconds. Say cancel restart to stop it."

    # Lock
    if has(t, "lock") and has(t, *DEVICE_WORDS):
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
        return "Locking the laptop."

    # Sleep (5 second baad, taake AURA pehle jawab bol sake)
    if has(t, "sleep") and (has(t, *DEVICE_WORDS) or has(t, "sleep mode")):
        threading.Timer(5, lambda: subprocess.run(
            ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])).start()
        return "Putting the laptop to sleep in 5 seconds."

    return None


# ============================================================
# 2) SCREENSHOT 📸 aur SHOW DESKTOP
# ============================================================
def handle_screenshot(t):
    if not has(t, "screenshot"):
        return None
    pictures = find_user_folder("Pictures") or HOME
    folder = os.path.join(pictures, "AURA Screenshots")
    os.makedirs(folder, exist_ok=True)                 # folder na ho to bana do
    name = datetime.now().strftime("screenshot_%Y-%m-%d_%H-%M-%S.png")
    pyautogui.screenshot(os.path.join(folder, name))
    return "Screenshot saved in your Pictures folder, inside AURA Screenshots."


def handle_show_desktop(t):
    if has(t, "show desktop", "minimize all", "minimise all", "minimize everything"):
        pyautogui.hotkey("win", "d")                   # Win + D
        return "Showing the desktop."
    return None


# ============================================================
# 3) SETTINGS PAGES ⚙️
# ============================================================
def handle_settings_page(t):
    if not has(t, "settings", "setting"):
        return None
    for name in sorted(SETTINGS_PAGES, key=len, reverse=True):   # lambe naam pehle
        if has(t, name):
            os.startfile(SETTINGS_PAGES[name])
            return f"Opening {name} settings."
    return None   # sirf "open settings" -> actions.py main settings kholega


def handle_settings_only_toggles(t):
    """Battery saver / night light / airplane mode: page kholo, switch user dabaye."""
    for name, uri in SETTINGS_ONLY_TOGGLES.items():
        if has(t, name) and (wants_on(t) or wants_off(t) or has(t, "turn", "switch")):
            os.startfile(uri)
            return (f"Windows does not let me switch {name} directly, "
                    f"so I opened its settings. Please click the switch.")
    return None


# ============================================================
# 4) WIFI aur BLUETOOTH 📶🎧
# ============================================================
async def _set_radio_async(kind_number, turn_on):
    """Windows Radio API se WiFi/Bluetooth on/off."""
    access = await Radio.request_access_async()
    if enum_value(access) != 1:                        # 1 = Allowed
        return "denied"

    radios = await Radio.get_radios_async()
    found = False
    for radio in radios:
        if enum_value(radio.kind) == kind_number:
            found = True
            await radio.set_state_async(RadioState(1 if turn_on else 2))   # 1 = On, 2 = Off
    return "ok" if found else "missing"


def set_radio(kind_number, turn_on, label, settings_uri):
    state_word = "on" if turn_on else "off"
    if RADIO_OK:
        try:
            result = asyncio.run(_set_radio_async(kind_number, turn_on))
            if result == "ok":
                return f"{label} turned {state_word}."
            if result == "missing":
                return f"I couldn't find a {label} adapter on this laptop."
            print(f"   ⚠️ Windows ne {label} control ki ijazat nahi di")
        except Exception as e:
            print(f"   ⚠️ Radio fail: {e}")
    # Seedha nahi hua -> settings page khol do
    os.startfile(settings_uri)
    return f"I couldn't switch {label} directly, so I opened {label} settings for you."


def handle_radios(t):
    if t.startswith("is "):            # "is wifi on?" sawal hai, command nahi
        return None
    if has(t, "wifi"):
        kind, label, uri = WIFI_KIND, "WiFi", "ms-settings:network-wifi"
    elif has(t, "bluetooth"):
        kind, label, uri = BLUETOOTH_KIND, "Bluetooth", "ms-settings:bluetooth"
    else:
        return None

    if wants_off(t):                   # "off" pehle check (warna "on" galti se match ho sakta hai)
        return set_radio(kind, False, label, uri)
    if wants_on(t):
        return set_radio(kind, True, label, uri)
    return None


# ============================================================
# 5) BATTERY 🔋
# ============================================================
def handle_battery(t):
    if not has(t, "battery"):
        return None
    if not has(t, "percent", "percentage", "level", "status", "how much", "left",
               "charge", "charging", "remaining", "check") and t not in ("battery", "my battery"):
        return None

    b = psutil.sensors_battery()
    if b is None:
        return "I couldn't read the battery on this device."

    percent = round(b.percent)
    if b.power_plugged:
        if percent >= 100:
            return "Battery is full and plugged in."
        return f"Battery is at {percent} percent and charging."

    msg = f"Battery is at {percent} percent and not charging."
    if b.secsleft not in (psutil.POWER_TIME_UNLIMITED, psutil.POWER_TIME_UNKNOWN) and b.secsleft > 0:
        hours, minutes = divmod(b.secsleft // 60, 60)
        msg += f" About {hours} hours and {minutes} minutes left."
    return msg


# ============================================================
# 6) VOLUME 🔊
# ============================================================
def get_volume_control():
    """Speaker ka volume control lao (pycaw ke naye aur purane dono versions)."""
    speakers = AudioUtilities.GetSpeakers()
    if hasattr(speakers, "EndpointVolume"):            # naya pycaw
        return speakers.EndpointVolume
    interface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)   # purana pycaw
    return cast(interface, POINTER(IAudioEndpointVolume))


def handle_volume(t):
    if not has(t, "volume", "mute", "unmute", "louder", "quieter", "sound"):
        return None

    vol = None
    if PYCAW_OK:
        try:
            vol = get_volume_control()
        except Exception as e:
            print(f"   ⚠️ pycaw fail, keyboard keys use karenge: {e}")

    # Mute / unmute
    if has(t, "unmute"):
        if vol:
            vol.SetMute(0, None)
        else:
            pyautogui.press("volumemute")
        return "Sound unmuted."
    if has(t, "mute"):
        if vol:
            vol.SetMute(1, None)
        else:
            pyautogui.press("volumemute")
        return "Sound muted."

    going_up = has(t, *UP_WORDS)
    going_down = has(t, *DOWN_WORDS)
    number = get_number(t)

    # pycaw na chale to sirf keyboard ki volume keys (har press = 2%)
    if vol is None:
        if going_up:
            pyautogui.press("volumeup", presses=VOLUME_STEP // 2)
            return "Volume up."
        if going_down:
            pyautogui.press("volumedown", presses=VOLUME_STEP // 2)
            return "Volume down."
        return None

    current = round(vol.GetMasterVolumeLevelScalar() * 100)

    if has(t, "max", "maximum", "full"):
        new = 100
    elif number is not None and has(t, "by"):          # "increase volume by 20"
        new = current - number if going_down else current + number
    elif number is not None:                           # "set volume to 40"
        new = number
    elif going_down:
        new = current - VOLUME_STEP
    elif going_up:
        new = current + VOLUME_STEP
    elif has(t, "current volume", "volume level", "how loud"):
        return f"The volume is at {current} percent."
    else:
        return None

    new = max(0, min(100, new))
    vol.SetMute(0, None)                               # volume badlo to mute khatam
    vol.SetMasterVolumeLevelScalar(new / 100, None)
    return f"Volume set to {new} percent."


# ============================================================
# 7) BRIGHTNESS 🔆
# ============================================================
def handle_brightness(t):
    if not has(t, "brightness", "brighter", "dimmer", "dim", "darker"):
        return None
    if not BRIGHTNESS_OK:
        return "Brightness control is not installed. Please run pip install screen brightness control."

    current = sbc.get_brightness(display=0)[0]
    number = get_number(t)
    going_up = has(t, *UP_WORDS)
    going_down = has(t, *DOWN_WORDS)

    if has(t, "max", "maximum", "full"):
        new = 100
    elif number is not None and has(t, "by"):
        new = current - number if going_down else current + number
    elif number is not None:
        new = number
    elif going_down:
        new = current - BRIGHTNESS_STEP
    elif going_up:
        new = current + BRIGHTNESS_STEP
    else:
        return f"Brightness is at {current} percent."

    new = max(0, min(100, new))
    sbc.set_brightness(new, display=0)
    return f"Brightness set to {new} percent."


# ============================================================
# 8) FOLDERS 📁
# ============================================================
def handle_folders(t):
    # Sirf "open downloads" / "open my documents folder" jaisa ho
    # (taake "open youtube videos" galti se Videos folder na khole)
    names = "|".join(USER_FOLDERS)
    match = re.search(rf"\b(open|show)\s+(my\s+|the\s+)?({names})(\s+folder)?$", t)
    if not match:
        return None
    key = match.group(3)
    path = find_user_folder(USER_FOLDERS[key])
    if not path:
        return f"I couldn't find your {key} folder."
    os.startfile(path)
    return f"Opening your {key} folder."


# ============================================================
# 9) FILES DHOONDNA aur KHOLNA 📄
# ============================================================
def normalize_name(name):
    """'Final_Report-v2.pdf' -> 'final report v2 pdf'"""
    return " ".join(re.sub(r"[._\-()\[\]]", " ", name.lower()).split())


def search_items(query_words, want_folder=False):
    """Desktop, Documents, Downloads, Pictures, Music, Videos mein dhoondo."""
    roots = []
    for folder_name in USER_FOLDERS.values():
        for p in folder_options(folder_name):
            if p not in roots:
                roots.append(p)

    matches = []
    for root in roots:
        base_depth = root.rstrip(os.sep).count(os.sep)
        for dirpath, dirnames, filenames in os.walk(root):
            # Faltu aur chhupe folders skip
            dirnames[:] = [d for d in dirnames
                           if d.lower() not in SKIP_DIRS and not d.startswith(".")]
            if dirpath.count(os.sep) - base_depth >= MAX_DEPTH:
                dirnames[:] = []                       # is se zyada gehra mat jao

            for item in (dirnames if want_folder else filenames):
                norm = normalize_name(item)
                if all(word in norm for word in query_words):
                    matches.append(os.path.join(dirpath, item))
    return matches


def extract_query(t, kind):
    """'open my resume file' / 'open file called resume' -> ['resume']"""
    patterns = [
        rf"\b(?:open|find|show)\s+(?:the\s+|my\s+|a\s+)?{kind}\s+(?:called\s+|named\s+)?(.+)",
        rf"\b(?:open|find|show)\s+(?:the\s+|my\s+|a\s+)?(.+?)\s+{kind}\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, t)
        if match:
            words = [w for w in match.group(1).split() if w not in FILLER_WORDS]
            if words:
                return words
    return None


def handle_files(t):
    for kind in ("file", "folder"):
        if not has(t, kind):
            continue
        query = extract_query(t, kind)
        if not query:
            continue

        print(f"   🔎 Dhoond rahe hain: {' '.join(query)}")
        matches = search_items(query, want_folder=(kind == "folder"))
        if not matches:
            return f"I couldn't find a {kind} named {' '.join(query)}."

        # Kayi milein to sab se naya (recent) wala kholo
        def modified(p):
            try:
                return os.path.getmtime(p)
            except Exception:
                return 0

        best = max(matches, key=modified)
        print(f"   📄 Mil gaya: {best}")
        os.startfile(best)
        return f"Opening {os.path.basename(best)}."
    return None


# ============================================================
# MAIN FUNCTION: aura_core.py isi ko call karta hai
# Jawab (text) wapas karta hai, ya None agar ye system command nahi thi
# ============================================================
HANDLERS = [
    handle_power,
    handle_screenshot,
    handle_show_desktop,
    handle_settings_page,
    handle_settings_only_toggles,
    handle_radios,
    handle_battery,
    handle_volume,
    handle_brightness,
    handle_folders,
    handle_files,
]


def handle_system(text):
    t = clean(text)
    if not t:
        return None
    for handler in HANDLERS:
        try:
            reply = handler(t)
        except Exception as e:
            print(f"   ❌ {handler.__name__} error: {e}")
            return "Sorry, I couldn't do that."
        if reply:
            return reply
    return None


# ============================================================
# TEST MODE: python system_control.py
# ============================================================
if __name__ == "__main__":
    print("🧪 Test mode — command likhein (band karne ke liye 'q')")
    while True:
        cmd = input("\n⌨️  Command: ")
        if cmd.strip().lower() == "q":
            break
        reply = handle_system(cmd)
        print("🤖", reply if reply else "(system command nahi thi — aage jati)")