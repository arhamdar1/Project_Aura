# ==========================================================
# AURA - Live Weather (Open-Meteo)
# Free weather service, koi API key nahi chahiye.
# Shehar ka naam dhoond kar abhi ka mausam lata hai.
# ==========================================================

import re         # Jumle mein shehar ka naam dhoondne ke liye
import requests   # Internet se data mangwane ke liye

DEFAULT_CITY = "Lahore"   # Agar shehar na bataya ho to ye use hoga

# Open-Meteo mausam ko number mein batata hai. Ye unka matlab hai.
WEATHER_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "foggy", 48: "foggy",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain",
    71: "light snow", 73: "snow", 75: "heavy snow",
    80: "rain showers", 81: "rain showers", 82: "heavy rain showers",
    95: "a thunderstorm", 96: "a thunderstorm with hail", 99: "a thunderstorm with hail",
}

WEATHER_WORDS = ["weather", "temperature", "mausam"]


def is_weather_question(clean_text):
    """Kya ye sawaal mausam ke baare mein hai?"""
    words = clean_text.split()
    return any(word in words for word in WEATHER_WORDS)


def find_city(clean_text):
    """
    Jumle mein 'in / of / at / for' ke baad wala shehar dhoondta hai.
    Misaal: "what is the weather in karachi today" -> "karachi"
    """
    match = re.search(
        r"\b(?:in|of|at|for)\s+([a-z ]+?)(?:\s+(?:today|tonight|right now|now))?$",
        clean_text,
    )
    return match.group(1).strip() if match else None


def get_weather(clean_text):
    """
    Live mausam laata hai aur aik saaf jumla wapas karta hai.
    Kuch ghalat ho jaye to None (phir AURA Tavily try karegi).
    """
    city = find_city(clean_text) or DEFAULT_CITY

    try:
        # 1) Shehar ka naam -> uski location (latitude/longitude)
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1},
            timeout=10,
        ).json()

        if not geo.get("results"):
            print(f"   ⚠️ Shehar nahi mila: {city}")
            return None

        place = geo["results"][0]

        # 2) Location -> abhi ka mausam + aaj ka max/min
        data = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m",
                "daily": "temperature_2m_max,temperature_2m_min",
                "timezone": "auto",
                "forecast_days": 1,
            },
            timeout=10,
        ).json()

        now = data["current"]
        today = data["daily"]
        condition = WEATHER_CODES.get(now["weather_code"], "unknown conditions")

        # 3) Sab ko aik jumle mein jodo (Llama isay parh kar bolne layak jawab banayega)
        return (
            f"Live weather for {place['name']}, {place.get('country', '')}: "
            f"{now['temperature_2m']} degrees Celsius, feels like {now['apparent_temperature']}, "
            f"{condition}, humidity {now['relative_humidity_2m']} percent, "
            f"wind {now['wind_speed_10m']} km/h. "
            f"Today's high is {today['temperature_2m_max'][0]} and low is "
            f"{today['temperature_2m_min'][0]} degrees Celsius."
        )

    except Exception as error:
        print(f"   ⚠️ Weather fail: {error}")
        return None