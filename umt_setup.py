# ============================================================
# umt_setup.py — UMT login save karna + LMS test 🔐
# Sirf aik dafa chalani hai. Password Windows Credential Manager
# mein encrypted save hota hai (code ya GitHub par kabhi nahi).
# ============================================================

import getpass            # password type karte waqt screen par nazar nahi aata
import time
import keyring            # Windows Credential Manager
import requests           # LMS se baat karne ke liye

SERVICE = "AURA-UMT"      # Credential Manager mein is naam se save hoga

# Aap jo LMS link use karte hain. Agar "newlms.umt.edu.pk" hai to yahan badal dein.
LMS_URL = "https://lms.umt.edu.pk"


def save_credentials(kind, label):
    """Username + password Credential Manager mein save karo."""
    print(f"\n🔐 {label} login")
    user = input("   Username (roll number / email): ").strip()
    if not user:
        return False
    password = getpass.getpass("   Password (type karte waqt nazar nahi aayega, Enter dabayein): ")
    keyring.set_password(SERVICE, f"{kind}_username", user)
    keyring.set_password(SERVICE, f"{kind}_password", password)
    print(f"   ✅ {label} login save ho gaya (Windows Credential Manager mein)")
    return True


def moodle_call(token, function, **params):
    """Moodle API ko call karo."""
    data = {"wstoken": token, "wsfunction": function, "moodlewsrestformat": "json", **params}
    return requests.post(f"{LMS_URL}/webservice/rest/server.php", data=data, timeout=20).json()


def test_lms():
    print(f"\n🧪 LMS test: {LMS_URL}")
    user = keyring.get_password(SERVICE, "lms_username")
    password = keyring.get_password(SERVICE, "lms_password")
    if not user or not password:
        print("   ❌ LMS login save nahi hai")
        return

    # Step A: Moodle mobile app wala token lo
    try:
        r = requests.post(f"{LMS_URL}/login/token.php",
                          data={"username": user, "password": password,
                                "service": "moodle_mobile_app"}, timeout=20)
        data = r.json()
    except Exception as e:
        print(f"   ❌ LMS se jawab nahi aaya: {e}")
        print("   👉 Shayad link ghalat hai, ya LMS API band hai. Screenshot bhejein.")
        return

    if "token" not in data:
        print(f"   ❌ Token nahi mila. Error code: {data.get('errorcode')}")
        print(f"      Message: {data.get('error')}")
        print("   👉 Is ka screenshot bhejein, main dekh kar batata hoon.")
        return

    token = data["token"]
    keyring.set_password(SERVICE, "lms_token", token)
    print("   ✅ Token mil gaya! LMS API kaam kar raha hai 🎉")

    # Step B: Aap ka naam (check ke liye)
    info = moodle_call(token, "core_webservice_get_site_info")
    print(f"   👤 Site: {info.get('sitename')} | Naam: {info.get('fullname')}")

    # Step C: Agle 30 din ki assignments / deadlines
    events = moodle_call(token, "core_calendar_get_action_events_by_timesort",
                         timesortfrom=int(time.time()), limitnum=20)
    items = events.get("events", []) if isinstance(events, dict) else []
    print(f"   📚 Upcoming items mile: {len(items)}")
    for e in items[:5]:
        due = time.strftime("%d %b %Y %I:%M %p", time.localtime(e.get("timesort", 0)))
        course = (e.get("course") or {}).get("fullname", "")
        print(f"      • {e.get('name')}  |  {course}  |  {due}")
    if isinstance(events, dict) and events.get("exception"):
        print(f"   ⚠️ Calendar error: {events.get('message')}")


if __name__ == "__main__":
    print("=" * 55)
    print("   AURA — UMT login setup")
    print("=" * 55)

    save_credentials("lms", "LMS")

    same = input("\n❓ Kya Student Portal ka username/password bhi yehi hai? (y/n): ").strip().lower()
    if same == "y":
        keyring.set_password(SERVICE, "portal_username", keyring.get_password(SERVICE, "lms_username"))
        keyring.set_password(SERVICE, "portal_password", keyring.get_password(SERVICE, "lms_password"))
        print("   ✅ Portal ke liye bhi same login save ho gaya")
    else:
        save_credentials("portal", "Student Portal")

    test_lms()
    print("\n✅ Setup khatam. Terminal ka screenshot bhej dein (password kahin nazar nahi aayega).")