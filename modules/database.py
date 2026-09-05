"""modules/database.py — Database layer with MySQL + fallback"""
from datetime import datetime

_detections = []
_farms = []
_alerts = []
_health_logs = []
_chats = []
_users = []
_next_ids = {"detection": 1, "farm": 1, "alert": 1, "user": 1}

def init_db():
    raise Exception("MySQL not configured — using offline mode")

def ensure_demo_user():
    pass

def save_detection(user_id, farm_id, crop_name, disease, severity, confidence,
                   image, cause, solution, prevention, chemical_treatment="",
                   organic_treatment="", notes="", is_healthy=False,
                   confidence_pct=0, disease_display=""):
    rec = {
        "id": _next_ids["detection"],
        "user_id": user_id, "farm_id": farm_id,
        "crop_name": crop_name, "disease": disease,
        "severity": severity, "confidence": confidence,
        "image": image, "cause": cause, "solution": solution,
        "prevention": prevention,
        "chemical_treatment": chemical_treatment,
        "organic_treatment": organic_treatment,
        "notes": notes, "is_healthy": is_healthy,
        "confidence_pct": confidence_pct,
        "disease_display": disease_display,
        "detected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    _detections.insert(0, rec)
    _next_ids["detection"] += 1
    return rec["id"]

def get_detections(user_id=None, limit=200):
    if user_id is not None:
        return [d for d in _detections if d.get("user_id") == user_id][:limit]
    return _detections[:limit]

def get_disease_stats(user_id=None):
    dets = get_detections(user_id)
    stats = {}
    for d in dets:
        name = d.get("disease", "")
        stats[name] = stats.get(name, 0) + 1
    return [{"disease": k, "count": v} for k, v in sorted(stats.items(), key=lambda x: -x[1])]

def create_farm(user_id, name, location="", size="", crop_type=""):
    farm = {
        "id": _next_ids["farm"],
        "user_id": user_id, "name": name,
        "location": location, "size": size, "crop_type": crop_type,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    _farms.append(farm)
    _next_ids["farm"] += 1
    return farm["id"]

def get_farms(user_id=None):
    if user_id is not None:
        return [f for f in _farms if f.get("user_id") == user_id]
    return _farms

def create_alert(user_id, message, severity="medium", farm_id=None, alert_type="disease"):
    alert = {
        "id": _next_ids["alert"],
        "user_id": user_id, "farm_id": farm_id,
        "alert_type": alert_type, "message": message,
        "severity": severity, "is_read": False,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    _alerts.insert(0, alert)
    _next_ids["alert"] += 1
    return alert["id"]

def get_alerts(user_id=None, unread_only=False):
    result = _alerts
    if user_id is not None:
        result = [a for a in result if a.get("user_id") == user_id]
    if unread_only:
        result = [a for a in result if not a.get("is_read")]
    return result[:50]

def mark_alerts_read(user_id, alert_id=None):
    for a in _alerts:
        if a.get("user_id") == user_id:
            if alert_id is None or a.get("id") == alert_id:
                a["is_read"] = True

def log_health(user_id, score):
    _health_logs.append({
        "user_id": user_id, "score": score,
        "logged_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

def get_health_history(user_id, days=30):
    return [h for h in _health_logs if h.get("user_id") == user_id][-days:]

def save_chat(user_id, question, answer, disease=""):
    _chats.append({
        "user_id": user_id, "question": question,
        "answer": answer, "disease": disease,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

def get_chat_history(user_id, limit=50):
    return [c for c in _chats if c.get("user_id") == user_id][-limit:]
