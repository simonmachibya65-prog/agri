"""modules/monitoring.py — Health scoring, yield prediction, chart data"""
from datetime import datetime, timedelta
import random

_CROP_YIELDS = {
    "Maize": 4.0, "Corn": 4.0, "Potato": 18.0, "Tomato": 25.0,
    "Rice": 4.5, "Wheat": 3.5, "Apple": 20.0, "Grape": 8.0,
    "Soybean": 2.5, "Pepper": 12.0, "Peach": 10.0, "Orange": 15.0,
    "Cherry": 6.0, "Strawberry": 8.0, "Blueberry": 4.0, "Squash": 14.0,
    "Raspberry": 3.0,
}

_STAGES = {
    "Maize":  ["Germination", "Seedling", "Vegetative", "Tasseling", "Silking", "Maturity"],
    "Potato": ["Sprout", "Vegetative", "Tuber Initiation", "Bulking", "Maturation"],
    "Tomato": ["Seedling", "Vegetative", "Flowering", "Fruiting", "Harvest"],
    "Rice":   ["Germination", "Seedling", "Tillering", "Heading", "Ripening"],
    "Wheat":  ["Germination", "Tillering", "Jointing", "Heading", "Ripening"],
}
_DEFAULT_STAGES = ["Planting", "Vegetative", "Flowering", "Fruiting", "Harvest"]


def calculate_health_score(detections: list) -> int:
    if not detections:
        return 85
    total = len(detections)
    healthy = sum(1 for d in detections if "healthy" in d.get("disease", "").lower())
    ratio = healthy / total
    score = int(50 + ratio * 50)
    critical = sum(1 for d in detections if d.get("severity", "").lower() == "critical")
    score = max(10, score - critical * 5)
    return min(100, score)


def predict_yield(crop: str, health_score: int, hectares: float = 1.0) -> dict:
    baseline = _CROP_YIELDS.get(crop, 5.0)
    loss_pct = max(0, (100 - health_score) * 0.8)
    predicted = round(baseline * hectares * (1 - loss_pct / 100), 2)
    optimal = round(baseline * hectares, 2)
    return {
        "crop": crop,
        "predicted_tons": predicted,
        "optimal_tons": optimal,
        "loss_percent": round(loss_pct, 1),
        "health_score": health_score,
        "hectares": hectares,
    }


def get_growth_stages(crop: str) -> list:
    stages = _STAGES.get(crop, _DEFAULT_STAGES)
    current = random.randint(1, len(stages) - 1)
    return [{"stage": s, "active": i == current, "done": i < current}
            for i, s in enumerate(stages)]


def health_chart_data(months: int = 6) -> dict:
    labels, scores = [], []
    for i in range(months):
        d = datetime.now() - timedelta(days=30 * (months - i - 1))
        labels.append(d.strftime("%b"))
        scores.append(random.randint(60, 95))
    return {"labels": labels, "scores": scores}


def disease_frequency_chart() -> dict:
    diseases = ["Late Blight", "Bacterial Spot", "Common Rust", "Early Blight", "Powdery Mildew"]
    counts = [random.randint(1, 20) for _ in diseases]
    colors = ["#ef4444", "#f59e0b", "#3b82f6", "#8b5cf6", "#ec4899"]
    return {"labels": diseases, "counts": counts, "colors": colors}


def detection_timeline_chart(days: int = 14) -> dict:
    labels, counts = [], []
    for i in range(days):
        d = datetime.now() - timedelta(days=days - i - 1)
        labels.append(d.strftime("%m/%d"))
        counts.append(random.randint(0, 5))
    return {"labels": labels, "counts": counts}
