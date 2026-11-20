import json
import urllib.request
import urllib.parse


def fetch_weather(lat: float, lon: float) -> dict | None:
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&current_weather=true"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        cw = data["current_weather"]
        return {"temp": round(cw["temperature"]), "code": cw["weathercode"]}
    except Exception:
        return None


def geocode_city(city: str) -> dict | None:
    try:
        q = urllib.parse.quote(city)
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={q}&count=1&language=ru"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        results = data.get("results")
        if not results:
            return None
        r0 = results[0]
        return {
            "lat": r0["latitude"],
            "lon": r0["longitude"],
            "city": r0.get("name", city),
        }
    except Exception:
        return None


WEATHER_EMOJI = {
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
    45: "🌫️", 48: "🌫️",
    51: "🌦️", 53: "🌦️", 55: "🌧️",
    61: "🌧️", 63: "🌧️", 65: "🌧️",
    71: "🌨️", 73: "🌨️", 75: "❄️",
    80: "🌦️", 81: "🌧️", 82: "⛈️",
    95: "⛈️", 96: "⛈️", 99: "⛈️",
}