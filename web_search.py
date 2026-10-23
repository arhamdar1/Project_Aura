# ==========================================================
# AURA - Phase 2.2: Web Search (Tavily + Live Weather)
# Faisla karti hai ke kab internet chahiye, aur taza maloomat laati hai.
# ==========================================================

import os                                          # .env se key parhne ke liye
from dotenv import load_dotenv                     # .env file load karne ke liye
from tavily import TavilyClient                    # Tavily search
from actions import clean_text                     # Text saaf karne wala function
from weather import is_weather_question, get_weather  # 🆕 Live weather

# .env file parho aur key nikalo
load_dotenv()
API_KEY = os.getenv("TAVILY_API_KEY")
tavily = TavilyClient(api_key=API_KEY) if API_KEY else None

# Ye alfaaz sun kar AURA samjhegi ke "taza info chahiye"
SEARCH_TRIGGERS = [
    "search", "search for", "google", "look up", "find out",
    "today", "tonight", "tomorrow", "yesterday", "right now",
    "this week", "this month", "this year", "latest", "current", "recent",
    "weather", "temperature", "news", "price", "rate", "score",
    "match", "who won", "result", "stock", "update",
]


def needs_search(text):
    """True = internet chahiye, False = Llama apne dimagh se jawab de."""
    padded = f" {clean_text(text)} "
    return any(f" {word} " in padded for word in SEARCH_TRIGGERS)


def search_web(query):
    """
    Taza maloomat laata hai:
      - Mausam ka sawaal -> Open-Meteo (live, free)
      - Baqi sab         -> Tavily search
    Kuch ghalat ho jaye to None, taake AURA crash na ho.
    """
    clean = clean_text(query)

    # 1) 🆕 Mausam ka sawaal? Pehle asal weather service try karo
    if is_weather_question(clean):
        weather = get_weather(clean)
        if weather:
            print("   ☀️ Live data: Open-Meteo")
            return weather
        # Weather fail hua to neeche Tavily try hoga

    # 2) Tavily search
    if tavily is None:
        print("⚠️  Tavily API key nahi mili. .env file check karein.")
        return None

    # 🆕 News ke sawaal par Tavily ki khaas news search use karo
    topic = "news" if "news" in clean.split() else "general"

    try:
        response = tavily.search(
            query=query,
            max_results=3,
            include_answer=True,   # 🆕 Tavily ek chhota tayyar jawab bhi dega
            topic=topic,
        )
    except Exception as error:
        print(f"⚠️  Search fail ho gayi: {error}")
        return None

    parts = []

    # Tavily ka tayyar jawab sab se upar rakho (sab se kaam ki cheez)
    if response.get("answer"):
        parts.append(f"Quick answer: {response['answer']}")

    for result in response.get("results", []):
        print(f"   🔗 {result['url']}")
        parts.append(f"Source: {result['title']}\n{result['content'][:1000]}")

    return "\n\n".join(parts) if parts else None