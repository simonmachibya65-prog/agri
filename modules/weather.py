"""modules/weather.py — Weather data with offline cache"""
import json, random
from pathlib import Path
from datetime import datetime, timedelta

_CACHE_FILE = Path("data/offline_cache/weather.json")

def _default_weather():
    base_temp = 28 + random.uniform(-3, 3)
    return {
        "temperature": round(base_temp, 1),
        "humidity": random.randint(65, 85),
        "wind_speed": round(random.uniform(8, 20), 1),
        "rainfall_mm": round(random.uniform(0, 8), 1),
        "condition": random.choice(["Partly Cloudy", "Sunny", "Light Rain", "Overcast"]),
        "city": "Dar es Salaam",
        "forecast": [
            {
                "day": (datetime.now() + timedelta(days=i+1)).strftime("%a"),
                "condition": random.choice(["Sunny", "Partly Cloudy", "Light Rain"]),
                "temp_max": round(base_temp + random.uniform(-2, 4), 1),
                "temp_min": round(base_temp - random.uniform(3, 6), 1),
                "rain_mm": round(random.uniform(0, 10), 1),
            }
            for i in range(4)
        ],
    }

def get_weather(city: str = "Dar es Salaam") -> dict:
    try:
        if _CACHE_FILE.exists():
            data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "temperature" in data:
                return data
    except Exception:
        pass
    w = _default_weather()
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_FILE.write_text(json.dumps(w, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return w

def disease_risk_forecast(weather: dict) -> list:
    risks = []
    temp = weather.get("temperature", 25)
    humidity = weather.get("humidity", 70)
    rain = weather.get("rainfall_mm", 0)

    if humidity > 80 and temp > 20:
        risks.append({"disease": "Late Blight (Potato/Tomato)", "risk": "High",
                      "reason": f"High humidity ({humidity}%) favors Phytophthora spread"})
    if humidity > 70 and rain > 2:
        risks.append({"disease": "Bacterial Leaf Blight (Rice)", "risk": "High",
                      "reason": "Warm wet conditions ideal for Xanthomonas oryzae"})
    if 15 <= temp <= 25 and humidity > 75:
        risks.append({"disease": "Common Rust (Corn)", "risk": "Moderate",
                      "reason": f"Cool humid weather ({temp}°C) suits Puccinia sorghi"})
    if humidity < 60:
        risks.append({"disease": "Powdery Mildew", "risk": "Moderate",
                      "reason": "Dry conditions favor powdery mildew development"})
    if not risks:
        risks.append({"disease": "General disease pressure", "risk": "Low",
                      "reason": "Current conditions are not highly favorable for major diseases"})
    return risks

def irrigation_advice(weather: dict) -> str:
    rain = weather.get("rainfall_mm", 0)
    humidity = weather.get("humidity", 70)
    temp = weather.get("temperature", 25)

    if rain > 10:
        return "Heavy rainfall detected — skip irrigation for 2-3 days. Monitor for waterlogging."
    elif rain > 4:
        return "Moderate rain today — reduce irrigation by 50%. Check soil moisture before watering."
    elif humidity > 80:
        return "High humidity — irrigate in early morning only to prevent fungal disease spread."
    elif temp > 32:
        return "High temperature — irrigate in the evening to reduce evaporation and heat stress."
    else:
        return "Normal conditions — irrigate according to your standard schedule. Morning watering recommended."
