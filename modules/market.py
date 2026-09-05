"""modules/market.py — Market prices and economic analysis (Tanzania TSh)"""
import random

_PRICES = {
    "Maize":      {"price_per_kg": 450,  "unit": "kg",  "trend": "Rising",  "market": "Kariakoo"},
    "Rice":       {"price_per_kg": 1800, "unit": "kg",  "trend": "Stable",  "market": "Mwanza"},
    "Potato":     {"price_per_kg": 800,  "unit": "kg",  "trend": "Rising",  "market": "Arusha"},
    "Tomato":     {"price_per_kg": 600,  "unit": "kg",  "trend": "Falling", "market": "Kariakoo"},
    "Wheat":      {"price_per_kg": 900,  "unit": "kg",  "trend": "Stable",  "market": "Dodoma"},
    "Soybean":    {"price_per_kg": 1200, "unit": "kg",  "trend": "Rising",  "market": "Mbeya"},
    "Apple":      {"price_per_kg": 3500, "unit": "kg",  "trend": "Stable",  "market": "Dar es Salaam"},
    "Grape":      {"price_per_kg": 4000, "unit": "kg",  "trend": "Rising",  "market": "Dar es Salaam"},
    "Orange":     {"price_per_kg": 500,  "unit": "kg",  "trend": "Stable",  "market": "Morogoro"},
    "Pepper":     {"price_per_kg": 2500, "unit": "kg",  "trend": "Rising",  "market": "Kariakoo"},
    "Strawberry": {"price_per_kg": 8000, "unit": "kg",  "trend": "Rising",  "market": "Dar es Salaam"},
    "Corn":       {"price_per_kg": 450,  "unit": "kg",  "trend": "Stable",  "market": "Dodoma"},
    "Cherry":     {"price_per_kg": 9000, "unit": "kg",  "trend": "Stable",  "market": "Dar es Salaam"},
    "Peach":      {"price_per_kg": 3000, "unit": "kg",  "trend": "Stable",  "market": "Arusha"},
    "Blueberry":  {"price_per_kg": 12000,"unit": "kg",  "trend": "Rising",  "market": "Dar es Salaam"},
    "Squash":     {"price_per_kg": 400,  "unit": "kg",  "trend": "Stable",  "market": "Moshi"},
    "Raspberry":  {"price_per_kg": 10000,"unit": "kg",  "trend": "Rising",  "market": "Dar es Salaam"},
}

_ICONS = {
    "Maize": "🌽", "Rice": "🌾", "Potato": "🥔", "Tomato": "🍅",
    "Wheat": "🌾", "Soybean": "🫘", "Apple": "🍎", "Grape": "🍇",
    "Orange": "🍊", "Pepper": "🌶️", "Strawberry": "🍓", "Corn": "🌽",
    "Cherry": "🍒", "Peach": "🍑", "Blueberry": "🫐", "Squash": "🎃",
    "Raspberry": "🍇",
}


def get_market_info(crop: str) -> dict:
    info = _PRICES.get(crop, {"price_per_kg": 500, "unit": "kg", "trend": "Stable", "market": "Local"})
    return {**info, "currency": "TSh", "crop": crop, "icon": _ICONS.get(crop, "🌿")}


def get_all_prices() -> list:
    result = []
    for crop, info in _PRICES.items():
        result.append({
            "crop": crop,
            "icon": _ICONS.get(crop, "🌿"),
            "price_per_kg": info["price_per_kg"],
            "currency": "TSh",
            "trend": info["trend"],
            "market": info["market"],
            "trend_color": "#10b981" if info["trend"] == "Rising" else "#ef4444" if info["trend"] == "Falling" else "#6b7280",
        })
    return sorted(result, key=lambda x: -x["price_per_kg"])


def economic_impact(disease: str, yield_loss_pct: float, crop: str = "Maize",
                    hectares: float = 1.0) -> dict:
    info = _PRICES.get(crop, {"price_per_kg": 500})
    baseline = {"Maize": 4000, "Potato": 18000, "Tomato": 25000, "Rice": 4500}.get(crop, 5000)
    lost_kg = baseline * hectares * (yield_loss_pct / 100)
    lost_value = int(lost_kg * info["price_per_kg"])
    return {
        "crop": crop, "disease": disease,
        "yield_loss_kg": round(lost_kg, 1),
        "financial_loss_tsh": lost_value,
        "loss_percent": yield_loss_pct,
    }


# ── Transaction store (in-memory + file-backed) ───────────────────────────────
import json as _json, secrets as _secrets
from pathlib import Path as _Path
from datetime import datetime as _dt

_TX_FILE = _Path("data/transactions.json")
_TRANSACTIONS: list = []

def _load_transactions():
    global _TRANSACTIONS
    try:
        if _TX_FILE.exists():
            _TRANSACTIONS = _json.loads(_TX_FILE.read_text(encoding="utf-8"))
    except Exception:
        _TRANSACTIONS = []

def _save_transactions():
    try:
        _TX_FILE.parent.mkdir(parents=True, exist_ok=True)
        _TX_FILE.write_text(_json.dumps(_TRANSACTIONS[-500:], ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

_load_transactions()

_MARKET_LOCATIONS = {
    "Kariakoo": [
        {"name": "Kariakoo Central Market",  "city": "Dar es Salaam", "lat": -6.8160, "lng": 39.2803, "hours": "Mon–Sun 6am–8pm"},
        {"name": "Tandale Market",           "city": "Dar es Salaam", "lat": -6.7838, "lng": 39.2460, "hours": "Mon–Sun 6am–6pm"},
        {"name": "Buguruni Market",          "city": "Dar es Salaam", "lat": -6.8334, "lng": 39.2502, "hours": "Mon–Sun 6am–6pm"},
    ],
    "Dar es Salaam": [
        {"name": "Kariakoo Central Market",  "city": "Dar es Salaam", "lat": -6.8160, "lng": 39.2803, "hours": "Mon–Sun 6am–8pm"},
        {"name": "Ubungo Market",            "city": "Dar es Salaam", "lat": -6.7900, "lng": 39.2200, "hours": "Mon–Sun 5am–7pm"},
        {"name": "Mwenge Market",            "city": "Dar es Salaam", "lat": -6.7713, "lng": 39.2524, "hours": "Mon–Sun 6am–6pm"},
    ],
    "Arusha": [
        {"name": "Arusha Central Market",    "city": "Arusha",        "lat": -3.3731, "lng": 36.6940, "hours": "Mon–Sun 6am–7pm"},
        {"name": "Soko Kuu la Arusha",       "city": "Arusha",        "lat": -3.3669, "lng": 36.6823, "hours": "Mon–Sat 6am–6pm"},
        {"name": "Sakina Market",            "city": "Arusha",        "lat": -3.3589, "lng": 36.6673, "hours": "Mon–Sat 7am–5pm"},
    ],
    "Mwanza": [
        {"name": "Mwanza Central Market",    "city": "Mwanza",        "lat": -2.5164, "lng": 32.9175, "hours": "Mon–Sun 6am–7pm"},
        {"name": "Kirumba Market",           "city": "Mwanza",        "lat": -2.4982, "lng": 32.9044, "hours": "Mon–Sat 6am–5pm"},
    ],
    "Dodoma": [
        {"name": "Dodoma Central Market",    "city": "Dodoma",        "lat": -6.1722, "lng": 35.7395, "hours": "Mon–Sun 6am–6pm"},
        {"name": "Makulu Market",            "city": "Dodoma",        "lat": -6.1850, "lng": 35.7480, "hours": "Mon–Sat 6am–5pm"},
    ],
    "Mbeya": [
        {"name": "Mbeya Central Market",     "city": "Mbeya",         "lat": -8.9094, "lng": 33.4607, "hours": "Mon–Sun 6am–6pm"},
        {"name": "Uyole Market",             "city": "Mbeya",         "lat": -8.9301, "lng": 33.4713, "hours": "Mon–Sat 6am–5pm"},
    ],
    "Morogoro": [
        {"name": "Morogoro Central Market",  "city": "Morogoro",      "lat": -6.8241, "lng": 37.6605, "hours": "Mon–Sun 6am–6pm"},
        {"name": "Mwembe Market",            "city": "Morogoro",      "lat": -6.8190, "lng": 37.6540, "hours": "Mon–Sat 6am–5pm"},
    ],
    "Moshi": [
        {"name": "Moshi Market",             "city": "Moshi",         "lat": -3.3549, "lng": 37.3407, "hours": "Mon–Sun 6am–7pm"},
        {"name": "Kiboriloni Market",        "city": "Moshi",         "lat": -3.3670, "lng": 37.3540, "hours": "Mon–Sat 6am–5pm"},
    ],
    "Local": [
        {"name": "Nearest District Market",  "city": "Your area",     "lat": None,    "lng": None,    "hours": "Contact local authorities"},
        {"name": "Local Cooperative Buyer",  "city": "Your area",     "lat": None,    "lng": None,    "hours": "Varies"},
    ],
}

_CHECKLIST = {
    "default": [
        "Harvest at peak ripeness — check colour and firmness",
        "Sort and grade: remove damaged or diseased produce",
        "Clean and pack in appropriate containers or bags",
        "Label with weight and variety if possible",
        "Transport early morning to avoid heat damage",
        "Negotiate price before unloading at market",
        "Keep a record of quantity sold and price received",
    ],
    "Tomato":   ["Harvest when fully red but still firm", "Pack in shallow crates to avoid bruising",
                 "Sell within 2 days of harvest", "Avoid stacking more than 3 layers deep"],
    "Potato":   ["Cure in shade for 1–2 weeks before selling", "Remove soil gently — do not wash before sale",
                 "Pack in breathable sacks", "Avoid exposure to sunlight after harvest"],
    "Maize":    ["Dry to 13% moisture before selling", "Shell and bag in standard 100kg bags",
                 "Check for aflatoxin if storing more than 2 weeks", "Sell to certified grain buyers for best price"],
    "Rice":     ["Mill or sell as paddy based on buyer preference", "Dry thoroughly before bagging",
                 "Pack in 50kg or 100kg standard bags", "Negotiate with millers for better rates"],
}

def get_market_locations(market: str) -> list:
    return _MARKET_LOCATIONS.get(market, _MARKET_LOCATIONS["Local"])

def get_checklist(crop: str) -> list:
    return _CHECKLIST.get(crop, _CHECKLIST["default"])

def save_transaction(user_id, crop, quantity_kg, price_per_kg, total, method, phone, ref) -> dict:
    tx = {
        "id":           ref,
        "user_id":      user_id,
        "crop":         crop,
        "quantity_kg":  quantity_kg,
        "price_per_kg": price_per_kg,
        "total":        total,
        "method":       method,
        "phone":        phone,
        "status":       "Pending",
        "created_at":   _dt.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    _TRANSACTIONS.insert(0, tx)
    _save_transactions()
    return tx

def get_transactions(user_id=None, limit=50) -> list:
    if user_id is not None:
        return [t for t in _TRANSACTIONS if t.get("user_id") == user_id][:limit]
    return _TRANSACTIONS[:limit]
