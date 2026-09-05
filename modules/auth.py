"""modules/auth.py — Authentication, sessions, rate limiting"""
import hashlib, secrets, re, time

_sessions = {}
_failed_attempts = {}
_users_db = {}
_next_uid = 1

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{h}"

def verify_password(password: str, stored: str) -> bool:
    try:
        salt, h = stored.split(":", 1)
        return hashlib.sha256((salt + password).encode()).hexdigest() == h
    except Exception:
        return False

def validate_password_strength(password: str):
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    return True, ""

def sanitize_input(text: str, max_len: int = 200) -> str:
    text = re.sub(r"<[^>]+>", "", str(text))
    return text[:max_len].strip()

def register_user(username: str, password: str, full_name: str = "",
                  phone: str = "", language: str = "en") -> int:
    global _next_uid
    username = username.lower().strip()
    if username in _users_db:
        raise ValueError("Username already taken")
    uid = _next_uid
    _users_db[username] = {
        "id": uid, "username": username,
        "password_hash": hash_password(password),
        "full_name": full_name, "phone": phone,
        "language": language, "role": "farmer",
    }
    _next_uid += 1
    return uid

def ensure_demo_user():
    if "demo" not in _users_db:
        register_user("demo", "demo123", "Demo Farmer", "", "en")

def login_user(username: str, password: str, ip: str = ""):
    username = username.lower().strip()
    user = _users_db.get(username)
    if not user:
        return None, "Invalid username or password"
    if not verify_password(password, user["password_hash"]):
        record_failed_attempt(username, ip)
        return None, "Invalid username or password"
    clear_attempts(username, ip)
    return {k: v for k, v in user.items() if k != "password_hash"}, ""

def create_session(user: dict) -> str:
    token = secrets.token_hex(32)
    _sessions[token] = {"user": user, "created": time.time()}
    return token

def get_session(token: str):
    if not token:
        return None
    s = _sessions.get(token)
    if not s:
        return None
    if time.time() - s["created"] > 86400:
        del _sessions[token]
        return None
    return s["user"]

def destroy_session(token: str):
    _sessions.pop(token, None)

def record_failed_attempt(username: str, ip: str):
    key = f"{username}:{ip}"
    if key not in _failed_attempts:
        _failed_attempts[key] = {"count": 0, "last": 0}
    _failed_attempts[key]["count"] += 1
    _failed_attempts[key]["last"] = time.time()

def clear_attempts(username: str, ip: str):
    _failed_attempts.pop(f"{username}:{ip}", None)

def check_rate_limit(username: str, ip: str):
    key = f"{username}:{ip}"
    info = _failed_attempts.get(key)
    if not info:
        return True, 0
    if info["count"] >= 5:
        wait = max(0, 300 - (time.time() - info["last"]))
        if wait > 0:
            return False, int(wait)
        clear_attempts(username, ip)
    return True, 0

def update_user(user_id: int, full_name: str = "", phone: str = "", language: str = ""):
    for u in _users_db.values():
        if u["id"] == user_id:
            if full_name: u["full_name"] = full_name
            if phone:     u["phone"] = phone
            if language:  u["language"] = language
            return True
    return False

def update_password(user_id: int, new_password: str):
    for u in _users_db.values():
        if u["id"] == user_id:
            u["password_hash"] = hash_password(new_password)
            return True
    return False

# seed demo on import
ensure_demo_user()
