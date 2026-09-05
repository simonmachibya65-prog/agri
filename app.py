"""app.py — Crop Diagnosis System v4 — Figma-matched"""
import os, shutil, json, secrets
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from modules.database import (init_db, save_detection, get_detections, get_disease_stats,
    create_farm, get_farms, create_alert, get_alerts, mark_alerts_read,
    log_health, get_health_history, save_chat, get_chat_history)
from modules.auth import (register_user, login_user, create_session, get_session, destroy_session, ensure_demo_user, update_user, update_password, sanitize_input, validate_password_strength, check_rate_limit)
from modules.shell import shell
from modules.ai_engine import run_inference
from modules.weather import get_weather, disease_risk_forecast, irrigation_advice
from modules.assistant import answer as ai_answer, suggested_questions, w_response
from modules.monitoring import (calculate_health_score, get_growth_stages, health_chart_data,
    disease_frequency_chart, detection_timeline_chart, predict_yield)
from modules.market import get_market_info, get_all_prices, economic_impact
from disease_info import get_info

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
Path("data/offline_cache").mkdir(parents=True, exist_ok=True)

# ── Persistent scan store ─────────────────────────────────────────────────────
import json as _json

_SCAN_STORE: list[dict] = []
_SCAN_STORE_FILE = Path("data/scan_history.json")


def _load_scan_store():
    """Load scan history from file on startup."""
    global _SCAN_STORE
    try:
        if _SCAN_STORE_FILE.exists():
            data = _json.loads(_SCAN_STORE_FILE.read_text(encoding="utf-8"))
            _SCAN_STORE = data if isinstance(data, list) else []
            print(f"📂 Loaded {len(_SCAN_STORE)} scans from history file.")
    except Exception as e:
        print(f"⚠️  Could not load scan history: {e}")
        _SCAN_STORE = []


def _save_scan_store():
    """Save scan history to file."""
    try:
        _SCAN_STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Save only serializable fields
        safe = []
        for s in _SCAN_STORE[:500]:
            safe.append({k: v for k, v in s.items()
                         if isinstance(v, (str, int, float, bool, type(None)))})
        _SCAN_STORE_FILE.write_text(_json.dumps(safe, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"⚠️  Could not save scan history: {e}")


def _store_scan(data: dict):
    """Save scan to in-memory store + file + DB (if available)."""
    _SCAN_STORE.insert(0, data)
    if len(_SCAN_STORE) > 500:
        _SCAN_STORE.pop()
    _save_scan_store()


def _get_scans(user_id=None, limit=200) -> list[dict]:
    """Get scans from DB if available, else from persistent store."""
    if DB_AVAILABLE:
        return get_detections(user_id, limit)
    if user_id is not None:
        return [s for s in _SCAN_STORE if s.get("user_id") == user_id][:limit]
    return _SCAN_STORE[:limit]


# Load history on startup
_load_scan_store()
DB_AVAILABLE = False
try:
    init_db(); ensure_demo_user(); DB_AVAILABLE = True
except Exception as e:
    print(f"DB unavailable: {e}")

app = FastAPI(title="Crop Diagnosis System")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static",  StaticFiles(directory="static"),  name="static")

def cu(request): return get_session(request.cookies.get("session"))

# ── Auth pages ────────────────────────────────────────────────────────────────

def _auth_page(title, content):
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — Crop Diagnosis System</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/static/style.css"></head>
<body><div class="auth-wrap"><div class="auth-card">{content}</div></div></body></html>"""

@app.get("/", response_class=HTMLResponse)
def root(request: Request): return RedirectResponse("/home" if cu(request) else "/login")

@app.get("/login", response_class=HTMLResponse)
def login_page(error: str = ""):
    err = f'<div class="alert-card warning" style="margin-bottom:16px"><span class="alert-icon">⚠️</span><div class="alert-body"><div class="alert-title">{error}</div></div></div>' if error else ""
    return HTMLResponse(_auth_page("Login", f"""
    <div class="auth-logo"><div class="auth-logo-icon">🌿</div><h2>Crop Diagnosis System</h2><p>Tanzania Agricultural Platform</p></div>
    {err}
    <form method="post" action="/login">
      <div class="form-group"><label class="form-label">Username</label><input class="form-input" name="username" placeholder="Enter username" required autofocus></div>
      <div class="form-group"><label class="form-label">Password</label><input class="form-input" type="password" name="password" placeholder="Enter password" required></div>
      <button type="submit" class="btn btn-primary btn-full" style="margin-top:4px">Sign In</button>
    </form>
    <hr class="divider">
    <p class="text-muted" style="text-align:center">New farmer? <a href="/register" class="text-green">Create account</a></p>
    <p class="text-muted text-xs" style="text-align:center;margin-top:8px">Demo: <strong>demo</strong> / <strong>demo123</strong></p>"""))

@app.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    if not DB_AVAILABLE:
        # Offline mode — accept any login
        user = {"id": 0, "username": username, "full_name": username.title(), "role": "farmer", "language": "en"}
    else:
        ip = request.client.host if request.client else ""
        user, error = login_user(username, password, ip)
        if not user:
            return RedirectResponse(f"/login?error={error.replace(' ', '+')}", status_code=303)
    token = create_session(user)
    resp = RedirectResponse("/home", status_code=303)
    resp.set_cookie("session", token, httponly=True, samesite="lax", max_age=86400)
    return resp

@app.get("/register", response_class=HTMLResponse)
def register_page(error: str = ""):
    err = f'<div class="alert-card warning" style="margin-bottom:16px"><span class="alert-icon">⚠️</span><div class="alert-body"><div class="alert-title">{error}</div></div></div>' if error else ""
    return HTMLResponse(_auth_page("Register", f"""
    <div class="auth-logo"><div class="auth-logo-icon">🌿</div><h2>Create Account</h2><p>Join Crop Diagnosis System</p></div>
    {err}
    <form method="post" action="/register">
      <div class="form-group"><label class="form-label">Full Name</label><input class="form-input" name="full_name" required></div>
      <div class="form-group"><label class="form-label">Username</label><input class="form-input" name="username" required></div>
      <div class="form-group"><label class="form-label">Phone</label><input class="form-input" name="phone" placeholder="+255..."></div>
      <div class="form-group"><label class="form-label">Password</label><input class="form-input" type="password" name="password" required></div>
      <div class="form-group"><label class="form-label">Language</label>
        <select class="form-input" name="language"><option value="en">English</option><option value="sw">Swahili</option></select>
      </div>
      <button type="submit" class="btn btn-primary btn-full">Create Account</button>
    </form>
    <hr class="divider">
    <p class="text-muted" style="text-align:center">Already registered? <a href="/login" class="text-green">Sign in</a></p>"""))

@app.post("/register")
async def register_post(username: str = Form(...), password: str = Form(...),
                        full_name: str = Form(""), phone: str = Form(""), language: str = Form("en")):
    if not DB_AVAILABLE: return RedirectResponse("/login?error=Database+unavailable", status_code=303)
    # Password strength check
    ok, msg = validate_password_strength(password)
    if not ok:
        return RedirectResponse(f"/register?error={msg.replace(' ', '+')}", status_code=303)
    try:
        uid = register_user(username, password, full_name, phone, language)
        user = {"id": uid, "username": username.lower(), "full_name": full_name, "role": "farmer", "language": language}
        token = create_session(user)
        resp = RedirectResponse("/home", status_code=303)
        resp.set_cookie("session", token, httponly=True, samesite="lax", max_age=86400)
        return resp
    except ValueError as e:
        return RedirectResponse(f"/register?error={str(e).replace(' ', '+')}", status_code=303)
    except Exception:
        return RedirectResponse("/register?error=Username+already+taken", status_code=303)

@app.get("/logout")
def logout(request: Request):
    destroy_session(request.cookies.get("session", ""))
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie("session")
    return resp

# ══ 🏠 HOME ══════════════════════════════════════════════════════════════════

@app.get("/home", response_class=HTMLResponse)
def home_page(request: Request, lang: str = "en"):
    user = cu(request)
    if not user: return RedirectResponse("/login")
    uid = user.get("id")
    dets = _get_scans(uid, 100)
    alerts_list = get_alerts(uid, unread_only=True) if DB_AVAILABLE else []
    health = calculate_health_score(dets)
    total = len(dets)
    diseases = len(set(d["disease"] for d in dets if "healthy" not in d.get("disease","").lower()))
    healthy_pct = round(sum(1 for d in dets if "healthy" in d.get("disease","").lower()) / max(total,1)*100)
    hc = "#2d9e6b" if health>=80 else "#f59e0b" if health>=60 else "#ef4444"
    w = get_weather("Dar es Salaam")
    w_icon = "🌧️" if w["rainfall_mm"]>2 else "⛅" if w["humidity"]>70 else "☀️"
    tl = detection_timeline_chart(14) if DB_AVAILABLE else {"labels":[],"counts":[]}

    recent_rows = "".join(f"""<tr>
      <td>{"✅" if "healthy" in d.get("disease","").lower() else "⚠️"}</td>
      <td style="font-weight:500">{d.get("crop_name","")}</td>
      <td>{d.get("disease","").replace("___"," — ").replace("_"," ")[:35]}</td>
      <td>{str(d.get("detected_at",""))[:10]}</td>
    </tr>""" for d in dets[:5]) or '<tr><td colspan="4" style="text-align:center;color:#9ca3af;padding:20px">No scans yet — <a href="/scan" class="text-green">scan your first crop</a></td></tr>'

    alert_items = "".join(f"""<div class="alert-card {'critical' if a.get('severity')=='high' else 'warning'}" style="margin-bottom:8px">
      <span class="alert-icon">{"🔴" if a.get("severity")=="high" else "🟡"}</span>
      <div class="alert-body"><div class="alert-title">{a.get("message","")[:60]}</div>
      <div class="alert-meta">{str(a.get("created_at",""))[:16]}</div></div>
    </div>""" for a in alerts_list[:3]) or '<p class="text-muted">No new alerts — farm looks good! ✅</p>'

    body = f"""
    <div class="grid-4" style="margin-bottom:20px">
      <div class="stat-card"><div class="stat-icon-box green">📊</div><div class="stat-value">{total}</div><div class="stat-label">Fields Monitored</div><div class="stat-delta up">↑ {total} total scans</div></div>
      <div class="stat-card"><div class="stat-icon-box blue">✅</div><div class="stat-value">{healthy_pct}%</div><div class="stat-label">Healthy Crops</div><div class="stat-delta up">↑ {healthy_pct}% from last month</div></div>
      <div class="stat-card"><div class="stat-icon-box orange">⚠️</div><div class="stat-value">{diseases}</div><div class="stat-label">Diseases Detected</div><div class="stat-delta neutral">↔ {diseases} from last week</div></div>
      <div class="stat-card"><div class="stat-icon-box purple">📈</div><div class="stat-value" style="color:{hc}">{health}</div><div class="stat-label">Avg Yield Prediction</div><div class="stat-delta up">↑ Health score</div></div>
    </div>

    <div class="grid-2" style="margin-bottom:20px">
      <div>
        <div class="card">
          <div class="card-header"><div><div class="card-title">Quick Actions</div></div></div>
          <div class="grid-3" style="gap:12px">
            <a href="/scan" class="btn btn-secondary btn-full" style="flex-direction:column;padding:16px;gap:8px;height:80px">📷<span>Scan Crop</span></a>
            <a href="/alerts" class="btn btn-secondary btn-full" style="flex-direction:column;padding:16px;gap:8px;height:80px">🔔<span>View Alerts</span></a>
            <a href="/reports" class="btn btn-secondary btn-full" style="flex-direction:column;padding:16px;gap:8px;height:80px">📈<span>Check Reports</span></a>
          </div>
        </div>
        <div class="card">
          <div class="card-header"><div class="card-title">Recent Alerts</div><a href="/alerts" class="card-link">View all</a></div>
          {alert_items}
        </div>
      </div>
      <div>
        <div class="weather-card">
          <div style="display:flex;justify-content:space-between;align-items:flex-start">
            <div>
              <div style="font-size:12px;opacity:.8;margin-bottom:4px">📍 Dar es Salaam, Tanzania</div>
              <div class="weather-temp">{w['temperature']}°C</div>
              <div class="weather-cond">{w['condition']}</div>
            </div>
            <div style="font-size:64px;opacity:.9">{w_icon}</div>
          </div>
          <div class="weather-stats">
            <div class="weather-stat"><div class="weather-stat-icon">💧</div><div class="weather-stat-val">{w['humidity']}%</div><div class="weather-stat-lbl">Humidity</div></div>
            <div class="weather-stat"><div class="weather-stat-icon">💨</div><div class="weather-stat-val">{w['wind_speed']}</div><div class="weather-stat-lbl">Wind km/h</div></div>
            <div class="weather-stat"><div class="weather-stat-icon">🌧️</div><div class="weather-stat-val">{w['rainfall_mm']}</div><div class="weather-stat-lbl">Rain mm</div></div>
          </div>
          <div style="margin-top:16px">
            {"".join(f'<div class="forecast-row"><span>{d["day"]}</span><span>{"☀️" if "Sun" in d["condition"] else "🌧️" if d["rain_mm"]>5 else "⛅"} {d["condition"]}</span><span style="font-weight:600">{d["temp_max"]}°</span></div>' for d in w.get("forecast",[])[:4])}
          </div>
        </div>
        <div class="card" style="margin-top:16px">
          <div class="card-header"><div class="card-title">Recent Activity</div><a href="/reports" class="card-link">View all</a></div>
          <div class="table-wrap"><table><thead><tr><th></th><th>Crop</th><th>Disease</th><th>Date</th></tr></thead><tbody>{recent_rows}</tbody></table></div>
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-header"><div class="card-title">Scan Activity (14 days)</div></div>
      <canvas id="timelineChart" height="80"></canvas>
    </div>
    <script>window._timelineData={json.dumps(tl)};</script>"""
    return HTMLResponse(shell("Dashboard Overview", "Monitor your farm's health and performance", body, "home", user, lang, len(alerts_list)))

# ══ 📷 SCAN ══════════════════════════════════════════════════════════════════

@app.get("/scan", response_class=HTMLResponse)
def scan_page(request: Request, lang: str = "en"):
    user = cu(request)
    if not user: return RedirectResponse("/login")
    farms = get_farms(user.get("id")) if DB_AVAILABLE else []
    farm_opts = "".join(f'<option value="{f["id"]}">{f["name"]}</option>' for f in farms)
    crops = ["Apple","Blueberry","Cherry","Corn","Grape","Orange","Peach","Pepper","Potato","Raspberry","Rice","Soybean","Squash","Strawberry","Tomato","Wheat"]
    recent = _get_scans(user.get("id"), 5)
    recent_html = "".join(f"""<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid #f3f4f6">
      <div style="display:flex;align-items:center;gap:10px">
        <div style="width:36px;height:36px;border-radius:8px;background:{'#f0fdf4' if 'healthy' in d.get('disease','').lower() else '#fff1f2'};display:flex;align-items:center;justify-content:center;font-size:16px">
          {'✅' if 'healthy' in d.get('disease','').lower() else '⚠️'}
        </div>
        <div>
          <div style="font-size:13px;font-weight:600;color:#1a1a1a">{d.get("crop_name","")}</div>
          <div style="font-size:11px;color:#9ca3af">{d.get("disease","").replace("___"," — ").replace("_"," ")[:32]}</div>
        </div>
      </div>
      <div style="font-size:11px;color:#9ca3af">{str(d.get("detected_at",""))[:10]}</div>
    </div>""" for d in recent) or '<div style="text-align:center;padding:20px 0;color:#9ca3af;font-size:13px">No scans yet</div>'

    body = f"""
    <!-- ── Step indicator ─────────────────────────────────────── -->
    <div style="display:flex;align-items:center;gap:0;margin-bottom:24px;background:#fff;border-radius:12px;padding:16px 20px;box-shadow:0 1px 3px rgba(0,0,0,.06)">
      <div style="display:flex;align-items:center;gap:8px;flex:1">
        <div style="width:28px;height:28px;border-radius:50%;background:var(--g);color:#fff;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;flex-shrink:0">1</div>
        <div><div style="font-size:12px;font-weight:700;color:#1a1a1a">Upload Image</div><div style="font-size:10px;color:#9ca3af">Choose or capture</div></div>
      </div>
      <div style="flex:1;height:2px;background:#e5e7eb;margin:0 8px"></div>
      <div style="display:flex;align-items:center;gap:8px;flex:1">
        <div style="width:28px;height:28px;border-radius:50%;background:#e5e7eb;color:#9ca3af;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;flex-shrink:0">2</div>
        <div><div style="font-size:12px;font-weight:600;color:#9ca3af">AI Analysis</div><div style="font-size:10px;color:#9ca3af">Processing image</div></div>
      </div>
      <div style="flex:1;height:2px;background:#e5e7eb;margin:0 8px"></div>
      <div style="display:flex;align-items:center;gap:8px;flex:1">
        <div style="width:28px;height:28px;border-radius:50%;background:#e5e7eb;color:#9ca3af;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;flex-shrink:0">3</div>
        <div><div style="font-size:12px;font-weight:600;color:#9ca3af">View Results</div><div style="font-size:10px;color:#9ca3af">Diagnosis & treatment</div></div>
      </div>
    </div>

    <div class="grid-2">
      <!-- ── Left: Upload card ─────────────────────────────────── -->
      <div>
        <div class="card" style="border:2px solid #e5e7eb">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:18px">
            <div style="width:40px;height:40px;border-radius:10px;background:linear-gradient(135deg,#2d9e6b,#1a7a4a);display:flex;align-items:center;justify-content:center;font-size:20px">📷</div>
            <div>
              <div style="font-size:15px;font-weight:700;color:#1a1a1a">Scan Your Crop</div>
              <div style="font-size:12px;color:#9ca3af">Upload a photo or use your camera</div>
            </div>
          </div>

          <!-- Tabs -->
          <div style="display:flex;gap:0;border:1.5px solid #e5e7eb;border-radius:8px;overflow:hidden;margin-bottom:18px">
            <button class="tab-btn active" data-tab="tab-upload" onclick="switchTab('tab-upload')"
              style="flex:1;border-radius:0;border:none;padding:10px;font-size:13px;font-weight:600;display:flex;align-items:center;justify-content:center;gap:6px">
              📁 Upload Photo
            </button>
            <button class="tab-btn" data-tab="tab-camera" onclick="switchTab('tab-camera');startCamera()"
              style="flex:1;border-radius:0;border:none;border-left:1.5px solid #e5e7eb;padding:10px;font-size:13px;font-weight:600;display:flex;align-items:center;justify-content:center;gap:6px">
              📷 Live Camera
            </button>
          </div>

          <!-- Upload tab -->
          <div id="tab-upload" class="tab-panel active">
            <form action="/scan" method="post" enctype="multipart/form-data" id="uploadForm" onsubmit="showAnalysing()">
              <div class="upload-zone" id="dropZone" onclick="document.getElementById('fileInput').click()"
                   ondragover="handleDragOver(event)" ondragleave="handleDragLeave()" ondrop="handleDrop(event)"
                   style="border:2px dashed #d1fae5;background:#f0fdf4;border-radius:12px;padding:32px 20px;text-align:center;cursor:pointer;transition:all .2s">
                <input type="file" id="fileInput" name="file" accept="image/*" required>
                <div id="uploadPlaceholder">
                  <div style="font-size:40px;margin-bottom:10px">🌿</div>
                  <div style="font-size:14px;font-weight:600;color:#1a7a4a;margin-bottom:4px">Click to upload or drag & drop</div>
                  <div style="font-size:12px;color:#9ca3af">JPG, PNG, JPEG — max 10MB</div>
                </div>
                <img id="preview" src="" alt="Preview" style="display:none;width:100%;border-radius:8px;margin-top:8px;max-height:400px;object-fit:contain;background:#f9fafb">
              </div>

              <div style="margin-top:16px;display:flex;flex-direction:column;gap:12px">
                <div class="form-group" style="margin:0">
                  <label class="form-label">🏡 Select Farm <span style="color:#9ca3af;font-weight:400">(optional)</span></label>
                  <select class="form-input" name="farm_id">
                    <option value="">— Choose your farm —</option>{farm_opts}
                  </select>
                </div>
                <div class="form-group" style="margin:0">
                  <label class="form-label">📝 Notes <span style="color:#9ca3af;font-weight:400">(optional)</span></label>
                  <input class="form-input" name="notes" placeholder="e.g. North field, row 3, spotted yesterday">
                </div>
              </div>
              <input type="hidden" name="lang" value="{lang}">

              <!-- Analyse button -->
              <button type="submit" id="analyseBtn" class="btn btn-primary btn-full" style="margin-top:16px;height:48px;font-size:15px;font-weight:700;border-radius:10px">
                🔍 Analyse Image
              </button>

              <!-- Loading state (hidden) -->
              <div id="analysingState" style="display:none;text-align:center;padding:20px 0">
                <div style="font-size:32px;margin-bottom:8px;animation:spin 1s linear infinite;display:inline-block">🔄</div>
                <div style="font-size:14px;font-weight:600;color:#2d9e6b">Analysing your crop image...</div>
                <div style="font-size:12px;color:#9ca3af;margin-top:4px">This usually takes 2–5 seconds</div>
              </div>
            </form>
          </div>

          <!-- Camera tab -->
          <div id="tab-camera" class="tab-panel">
            <div style="position:relative;background:#000;border-radius:10px;overflow:hidden;margin-bottom:12px">
              <video id="cameraFeed" autoplay playsinline style="width:100%;max-height:280px;display:block;object-fit:cover;border-radius:10px"></video>
              <canvas id="cameraCanvas" style="display:none"></canvas>
              <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;pointer-events:none">
                <div style="width:130px;height:130px;border:2.5px solid rgba(255,255,255,.7);border-radius:10px;box-shadow:0 0 0 9999px rgba(0,0,0,.3)"></div>
              </div>
              <div id="camStatus" style="position:absolute;top:10px;left:10px;background:rgba(0,0,0,.6);color:#fff;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600">🔴 Starting...</div>
            </div>
            <div style="display:flex;gap:8px;margin-bottom:14px">
              <button class="btn btn-primary btn-full" id="captureBtn" onclick="capturePhoto()" disabled style="height:44px;font-weight:700">📸 Capture Photo</button>
              <button class="btn btn-ghost btn-sm" onclick="switchCameraFacing()" title="Flip">🔄</button>
              <button class="btn btn-ghost btn-sm" onclick="stopCamera()" title="Stop">⏹</button>
            </div>
            <div id="capturedSection" style="display:none">
              <div style="font-size:12px;font-weight:600;color:#2d9e6b;margin-bottom:6px">✅ Photo captured — ready to analyse</div>
              <img id="capturedPreview" src="" style="width:100%;max-height:400px;object-fit:contain;background:#000;border-radius:8px;border:2px solid #2d9e6b;margin-bottom:12px">
              <form action="/scan" method="post" enctype="multipart/form-data" id="cameraForm" onsubmit="showAnalysing()">
                <input type="file" id="cameraFileInput" name="file" style="display:none" required>
                <div style="display:flex;flex-direction:column;gap:10px;margin-bottom:12px">
                  <select class="form-input" name="farm_id"><option value="">— Choose farm —</option>{farm_opts}</select>
                  <input class="form-input" name="notes" placeholder="Notes (optional)">
                </div>
                <input type="hidden" name="lang" value="{lang}">
                <div style="display:flex;gap:8px">
                  <button type="submit" class="btn btn-primary btn-full" style="height:44px;font-weight:700">🔍 Analyse Photo</button>
                  <button type="button" class="btn btn-ghost btn-sm" onclick="retakePhoto()">🔄 Retake</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>

      <!-- ── Right: Tips + Crops + Recent ─────────────────────── -->
      <div style="display:flex;flex-direction:column;gap:16px">
        <!-- Tips -->
        <div class="card" style="background:linear-gradient(135deg,#f0fdf4,#ecfdf5)">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px">
            <span style="font-size:18px">💡</span>
            <div style="font-size:14px;font-weight:700;color:#1a7a4a">Tips for Best Results</div>
          </div>
          <div style="display:flex;flex-direction:column;gap:8px">
            {"".join(f'''<div style="display:flex;align-items:flex-start;gap:10px;background:#fff;border-radius:8px;padding:10px 12px">
              <div style="width:22px;height:22px;border-radius:50%;background:#2d9e6b;color:#fff;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;flex-shrink:0">{i+1}</div>
              <div style="font-size:12px;color:#374151;line-height:1.5">{tip}</div>
            </div>''' for i, tip in enumerate([
              "Use natural daylight — avoid flash or shadows",
              "Focus closely on the affected leaf or fruit",
              "Keep the image sharp and in focus",
              "Include the full leaf in the frame",
              "Hold camera steady to avoid blur",
            ]))}
          </div>
        </div>

        <!-- Supported crops -->
        <div class="card">
          <div style="font-size:13px;font-weight:700;color:#1a1a1a;margin-bottom:10px">🌿 Supported Crops</div>
          <div style="display:flex;flex-wrap:wrap;gap:6px">
            {''.join(f'<span style="background:#f0fdf4;color:#1a7a4a;border:1px solid #bbf7d0;padding:4px 10px;border-radius:20px;font-size:12px;font-weight:500">{c}</span>' for c in crops)}
          </div>
        </div>

        <!-- Recent scans -->
        <div class="card">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
            <div style="font-size:13px;font-weight:700;color:#1a1a1a">🕐 Recent Scans</div>
            <a href="/reports" style="font-size:12px;color:#2d9e6b;font-weight:500">View all →</a>
          </div>
          {recent_html}
        </div>
      </div>
    </div>

    <style>
    @keyframes spin {{ to {{ transform:rotate(360deg) }} }}
    .upload-zone:hover {{ border-color:#2d9e6b !important; background:#e8f5e9 !important; }}
    </style>
    <script>
    function showAnalysing() {{
      document.getElementById('analyseBtn').style.display = 'none';
      document.getElementById('analysingState').style.display = 'block';
    }}
    let stream = null, facingMode = 'environment';
    async function startCamera() {{
      const video = document.getElementById('cameraFeed');
      const status = document.getElementById('camStatus');
      const btn = document.getElementById('captureBtn');
      try {{
        if (stream) stream.getTracks().forEach(t => t.stop());
        stream = await navigator.mediaDevices.getUserMedia({{ video: {{ facingMode, width:{{ideal:1280}}, height:{{ideal:720}} }}, audio:false }});
        video.srcObject = stream;
        status.textContent = '🟢 Camera active'; status.style.background = 'rgba(45,158,107,.8)';
        btn.disabled = false;
      }} catch(e) {{
        status.textContent = '❌ Camera unavailable'; status.style.background = 'rgba(239,68,68,.8)';
      }}
    }}
    function capturePhoto() {{
      const video = document.getElementById('cameraFeed');
      const canvas = document.getElementById('cameraCanvas');
      canvas.width = video.videoWidth||640; canvas.height = video.videoHeight||480;
      canvas.getContext('2d').drawImage(video,0,0);
      canvas.toBlob(blob => {{
        document.getElementById('capturedPreview').src = URL.createObjectURL(blob);
        document.getElementById('capturedSection').style.display = 'block';
        const file = new File([blob],'capture.jpg',{{type:'image/jpeg'}});
        const dt = new DataTransfer(); dt.items.add(file);
        document.getElementById('cameraFileInput').files = dt.files;
        video.pause(); document.getElementById('camStatus').textContent = '📸 Captured';
      }}, 'image/jpeg', 0.92);
    }}
    function retakePhoto() {{
      document.getElementById('capturedSection').style.display = 'none';
      document.getElementById('cameraFeed').play();
      document.getElementById('camStatus').textContent = '🟢 Camera active';
    }}
    async function switchCameraFacing() {{ facingMode = facingMode==='environment'?'user':'environment'; await startCamera(); }}
    function stopCamera() {{
      if (stream) {{ stream.getTracks().forEach(t=>t.stop()); stream=null; }}
      document.getElementById('cameraFeed').srcObject = null;
      document.getElementById('camStatus').textContent = '⏹ Stopped';
      document.getElementById('captureBtn').disabled = true;
    }}
    window.addEventListener('beforeunload', stopCamera);
    // File preview
    document.getElementById('fileInput').addEventListener('change', function() {{
      if (this.files[0]) {{
        const reader = new FileReader();
        reader.onload = e => {{
          const img = document.getElementById('preview');
          img.src = e.target.result; img.style.display = 'block';
          document.getElementById('uploadPlaceholder').style.display = 'none';
        }};
        reader.readAsDataURL(this.files[0]);
      }}
    }});
    </script>"""
    return HTMLResponse(shell("Scan Crop", "Upload or capture a crop image for AI diagnosis", body, "scan", user, lang))


@app.post("/scan", response_class=HTMLResponse)
async def scan_post(request: Request, file: UploadFile = File(...),
                    farm_id: str = Form(""), notes: str = Form(""), lang: str = Form("en")):
    user = cu(request)
    if not user: return RedirectResponse("/login")

    # ── File security validation ──────────────────────────────────────────────
    ALLOWED_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/bmp"}
    MAX_SIZE_MB   = 10
    MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024

    # Check content type
    if file.content_type not in ALLOWED_TYPES:
        body = f"""<div style="max-width:480px;margin:40px auto;text-align:center">
          <div style="background:#fff;border-radius:16px;padding:36px;box-shadow:0 4px 20px rgba(0,0,0,.08)">
            <div style="font-size:48px;margin-bottom:16px">🚫</div>
            <div style="font-size:18px;font-weight:700;color:#1a1a1a;margin-bottom:8px">Invalid File Type</div>
            <div style="font-size:13px;color:#6b7280;margin-bottom:20px">Only JPG, PNG, WEBP images are allowed.<br>You uploaded: <strong>{file.content_type or 'unknown'}</strong></div>
            <a href="/scan" class="btn btn-primary">← Try Again</a>
          </div></div>"""
        return HTMLResponse(shell("Invalid File", "Only image files are accepted", body, "scan", user, lang))

    # Check file size
    content = await file.read()
    if len(content) > MAX_SIZE_BYTES:
        body = f"""<div style="max-width:480px;margin:40px auto;text-align:center">
          <div style="background:#fff;border-radius:16px;padding:36px;box-shadow:0 4px 20px rgba(0,0,0,.08)">
            <div style="font-size:48px;margin-bottom:16px">📦</div>
            <div style="font-size:18px;font-weight:700;color:#1a1a1a;margin-bottom:8px">File Too Large</div>
            <div style="font-size:13px;color:#6b7280;margin-bottom:20px">Maximum file size is {MAX_SIZE_MB}MB.<br>Your file: <strong>{len(content)//1024//1024}MB</strong></div>
            <a href="/scan" class="btn btn-primary">← Try Again</a>
          </div></div>"""
        return HTMLResponse(shell("File Too Large", "File exceeds maximum size", body, "scan", user, lang))

    # Sanitize filename — keep only safe characters
    import re as _re
    safe_name = _re.sub(r'[^a-zA-Z0-9._-]', '_', Path(file.filename).name)
    safe_name = safe_name[:100]  # limit length
    # Add unique prefix to prevent overwrites
    unique_name = f"{secrets.token_hex(8)}_{safe_name}"
    save_path = UPLOAD_DIR / unique_name

    with open(save_path, "wb") as buf:
        buf.write(content)

    # Use unique_name as the filename going forward
    file.filename = unique_name
    result = run_inference(str(save_path))
    disease = result["disease"]; info = result["info"]; treatment = result["treatment"]
    conf_pct = result["confidence"]; sev_color = result["severity_color"]
    severity = result["severity"]; alts = result["alternatives"]; is_healthy = result["is_healthy"]
    trust = result.get("trust", {"level":"Medium","label":"Medium Confidence","color":"#d97706","bg":"#fffbeb","border":"#fcd34d","icon":"⚠️","pct":conf_pct,"message":"Review the result and compare with field observations."})

    # ── Not a supported crop ─────────────────────────────────────────────────
    if result.get("is_not_supported") and not result.get("is_unknown"):
        from modules.ai_engine import SUPPORTED_CROPS
        crops_html = "".join(
            f'<span style="background:#f0fdf4;color:#1a7a4a;border:1px solid #bbf7d0;'
            f'padding:3px 10px;border-radius:20px;font-size:12px;font-weight:500">{c}</span>'
            for c in SUPPORTED_CROPS
        )
        steps_html = "".join(
            f'<div style="display:flex;align-items:flex-start;gap:10px;background:#f9fafb;'
            f'border-radius:8px;padding:10px 12px">'
            f'<span style="font-size:16px;flex-shrink:0">{ic}</span>'
            f'<div style="font-size:13px;color:#374151">{tip}</div></div>'
            for ic, tip in [
                ("📷", "Take a <strong>clear, close-up photo</strong> of the affected leaf or fruit"),
                ("🌿", "Only these supported crops are recognised — check the list below"),
                ("☀️", "Use <strong>natural daylight</strong>, avoid shadows or flash"),
                ("🎯", "Make sure the plant fills <strong>most of the frame</strong>"),
                ("🤝", "If your crop is not listed, contact an <a href='/expert' style='color:#2d9e6b'>agricultural expert</a>"),
            ]
        )
        body = f"""
        <div style="max-width:580px;margin:0 auto">
          <div style="background:#fff;border-radius:16px;box-shadow:0 4px 24px rgba(0,0,0,.09);overflow:hidden">
            <!-- Orange header -->
            <div style="background:linear-gradient(135deg,#d97706,#f59e0b);padding:28px 32px;text-align:center;color:#fff">
              <div style="width:72px;height:72px;border-radius:50%;background:rgba(255,255,255,.2);display:flex;align-items:center;justify-content:center;font-size:36px;margin:0 auto 14px">🚫</div>
              <div style="font-size:22px;font-weight:800;margin-bottom:6px">Crop Not Supported</div>
              <div style="font-size:13px;opacity:.9">This image does not match any of the {len(SUPPORTED_CROPS)} crops in our database</div>
            </div>
            <div style="padding:24px 28px">

              <!-- Uploaded preview -->
              <img src="/uploads/{file.filename}"
                   style="width:100%;max-height:220px;border-radius:10px;object-fit:contain;
                          background:#fefce8;margin-bottom:20px;border:2px solid #fde68a"
                   alt="Uploaded image" onerror="this.style.display='none'">

              <!-- What to do -->
              <div style="margin-bottom:20px">
                <div style="font-size:13px;font-weight:700;color:#1a1a1a;margin-bottom:10px">💡 What to do:</div>
                <div style="display:flex;flex-direction:column;gap:8px">{steps_html}</div>
              </div>

              <!-- Supported crops list -->
              <div style="background:#f0fdf4;border-radius:10px;padding:16px;margin-bottom:20px;border:1px solid #bbf7d0">
                <div style="font-size:12px;font-weight:700;color:#1a7a4a;text-transform:uppercase;
                             letter-spacing:.05em;margin-bottom:10px">✅ Supported Crops ({len(SUPPORTED_CROPS)})</div>
                <div style="display:flex;flex-wrap:wrap;gap:6px">{crops_html}</div>
              </div>

              <!-- Actions -->
              <div style="display:flex;gap:10px">
                <a href="/scan" class="btn btn-primary btn-full"
                   style="justify-content:center;height:44px;font-size:14px">📷 Try Again</a>
                <a href="/expert" class="btn btn-secondary btn-full"
                   style="justify-content:center;height:44px;font-size:14px">🤝 Ask Expert</a>
              </div>
            </div>
          </div>
        </div>"""
        return HTMLResponse(shell(
            "Crop Not Supported",
            "This image does not match any supported crop",
            body, "scan", user, lang
        ))

    # ── Unknown image — not recognized ───────────────────────────────────────
    if result.get("is_unknown"):
        passes   = result.get("passes") or {}
        p1       = passes.get("p1", 0)
        p2       = passes.get("p2", 0)
        p3       = passes.get("p3", 0)
        best_pct = max(p1, p2, p3)
        crops_html = "".join(
            f'<span style="background:#f0fdf4;color:#1a7a4a;border:1px solid #bbf7d0;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:500">{c}</span>'
            for c in ["Apple","Blueberry","Cherry","Corn","Grape","Orange","Peach","Pepper","Potato","Raspberry","Soybean","Squash"]
        )
        tips_html = "".join(
            f'<div style="display:flex;align-items:flex-start;gap:10px;background:#f9fafb;border-radius:8px;padding:10px 12px"><span style="font-size:16px;flex-shrink:0">{ic}</span><div style="font-size:13px;color:#374151">{tip}</div></div>'
            for ic, tip in [
                ("📷", "Take a <strong>closer photo</strong> of the leaf, fruit, or stem"),
                ("☀️", "Use <strong>natural daylight</strong> — avoid flash or shadows"),
                ("🎯", "Focus on the <strong>affected area</strong> of the plant"),
                ("🌿", "Make sure the image shows a <strong>supported crop</strong>"),
                ("📐", "Hold the camera <strong>steady</strong> — avoid blur"),
            ]
        )
        body = f"""
        <!-- Step indicator — not recognized -->
        <div style="display:flex;align-items:center;margin-bottom:24px;background:#fff;border-radius:12px;padding:16px 20px;box-shadow:0 1px 3px rgba(0,0,0,.06)">
          <div style="display:flex;align-items:center;gap:8px;flex:1">
            <div style="width:28px;height:28px;border-radius:50%;background:#2d9e6b;color:#fff;display:flex;align-items:center;justify-content:center;font-size:13px;flex-shrink:0">✓</div>
            <div><div style="font-size:12px;font-weight:700;color:#2d9e6b">Image Uploaded</div><div style="font-size:10px;color:#9ca3af">Done</div></div>
          </div>
          <div style="flex:1;height:2px;background:#2d9e6b;margin:0 8px"></div>
          <div style="display:flex;align-items:center;gap:8px;flex:1">
            <div style="width:28px;height:28px;border-radius:50%;background:#2d9e6b;color:#fff;display:flex;align-items:center;justify-content:center;font-size:13px;flex-shrink:0">✓</div>
            <div><div style="font-size:12px;font-weight:700;color:#2d9e6b">AI Analysis</div><div style="font-size:10px;color:#9ca3af">Complete</div></div>
          </div>
          <div style="flex:1;height:2px;background:#ef4444;margin:0 8px"></div>
          <div style="display:flex;align-items:center;gap:8px;flex:1">
            <div style="width:28px;height:28px;border-radius:50%;background:#ef4444;color:#fff;display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0">✕</div>
            <div><div style="font-size:12px;font-weight:700;color:#ef4444">Not Recognized</div><div style="font-size:10px;color:#9ca3af">See below</div></div>
          </div>
        </div>

        <div style="max-width:560px;margin:0 auto">
          <div style="background:#fff;border-radius:16px;box-shadow:0 4px 24px rgba(0,0,0,.09);overflow:hidden">

            <!-- Red header -->
            <div style="background:linear-gradient(135deg,#dc2626,#ef4444);padding:28px 32px;text-align:center;color:#fff">
              <div style="width:72px;height:72px;border-radius:50%;background:rgba(255,255,255,.2);display:flex;align-items:center;justify-content:center;font-size:36px;margin:0 auto 14px">🔍</div>
              <div style="font-size:22px;font-weight:800;margin-bottom:6px">Image Not Recognized</div>
              <div style="font-size:13px;opacity:.9">The AI could not match this image to any trained crop or disease</div>
            </div>

            <div style="padding:24px 28px">

              <!-- 3-pass scores -->
              <div style="background:#f9fafb;border-radius:10px;padding:16px;margin-bottom:20px">
                <div style="font-size:12px;font-weight:700;color:#374151;margin-bottom:10px">🔁 3-Pass Analysis Result</div>
                <div style="display:flex;gap:8px;margin-bottom:10px">
                  <div style="flex:1;background:#fff;border-radius:8px;padding:10px;text-align:center;border:1px solid #e5e7eb">
                    <div style="font-size:10px;color:#9ca3af;font-weight:600;text-transform:uppercase;margin-bottom:4px">Pass 1</div>
                    <div style="font-size:18px;font-weight:800;color:#ef4444">{p1}%</div>
                  </div>
                  <div style="flex:1;background:#fff;border-radius:8px;padding:10px;text-align:center;border:1px solid #e5e7eb">
                    <div style="font-size:10px;color:#9ca3af;font-weight:600;text-transform:uppercase;margin-bottom:4px">Pass 2</div>
                    <div style="font-size:18px;font-weight:800;color:#ef4444">{p2}%</div>
                  </div>
                  <div style="flex:1;background:#fff;border-radius:8px;padding:10px;text-align:center;border:1px solid #e5e7eb">
                    <div style="font-size:10px;color:#9ca3af;font-weight:600;text-transform:uppercase;margin-bottom:4px">Pass 3</div>
                    <div style="font-size:18px;font-weight:800;color:#ef4444">{p3}%</div>
                  </div>
                </div>
                <div style="font-size:12px;color:#6b7280;line-height:1.6">
                  Best match: <strong style="color:#ef4444">{best_pct}%</strong> — minimum required is <strong>30%</strong>.
                  The image does not closely resemble any crop or disease the AI was trained on.
                </div>
              </div>

              <!-- Uploaded image preview -->
              <img src="/uploads/{file.filename}" style="width:100%;border-radius:10px;object-fit:contain;background:#f9fafb;margin-bottom:20px;border:2px solid #fee2e2" alt="Uploaded image" onerror="this.style.display='none'">

              <!-- Tips -->
              <div style="margin-bottom:20px">
                <div style="font-size:13px;font-weight:700;color:#1a1a1a;margin-bottom:10px">💡 How to get a better result:</div>
                <div style="display:flex;flex-direction:column;gap:8px">{tips_html}</div>
              </div>

              <!-- Supported crops -->
              <div style="margin-bottom:20px">
                <div style="font-size:12px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px">Supported Crops</div>
                <div style="display:flex;flex-wrap:wrap;gap:5px">{crops_html}</div>
              </div>

              <!-- Action buttons -->
              <div style="display:flex;gap:10px">
                <a href="/scan" class="btn btn-primary btn-full" style="justify-content:center;height:44px;font-size:14px">📷 Try Again</a>
                <a href="/expert" class="btn btn-secondary btn-full" style="justify-content:center;height:44px;font-size:14px">🤝 Ask Expert</a>
              </div>
            </div>
          </div>
        </div>"""
        return HTMLResponse(shell("Image Not Recognized", "The uploaded image could not be matched to any trained crop", body, "scan", user, lang))
    # ── Save scan (DB + in-memory store) ─────────────────────────────────────
    scan_record = {
        "user_id": user.get("id"), "farm_id": int(farm_id) if farm_id else None,
        "crop_name": result["crop"], "disease": disease, "severity": severity,
        "confidence": conf_pct/100, "image": file.filename, "cause": info["cause"],
        "solution": info["solution"], "prevention": info["prevention"],
        "chemical_treatment": "; ".join(treatment.get("chemical",[])),
        "organic_treatment": "; ".join(treatment.get("organic",[])),
        "notes": notes, "detected_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "is_healthy": is_healthy, "confidence_pct": conf_pct,
        "disease_display": result["disease_display"],
    }
    _store_scan(scan_record)
    if DB_AVAILABLE:
        save_detection(scan_record)
        if not is_healthy and severity in ("High","Critical"):
            create_alert(user.get("id"), int(farm_id) if farm_id else None, "disease",
                f"{severity}: {disease.replace('___',' ').replace('_',' ')} on {result['crop']}.", severity.lower())
    alts_html = "".join(f"""<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #f3f4f6;font-size:13px">
      <span>{a['disease'].replace('___',' — ').replace('_',' ')}</span>
      <div style="display:flex;align-items:center;gap:8px"><span class="text-muted">{a['confidence']}%</span>
      <div style="width:60px;background:#e5e7eb;border-radius:4px;height:4px"><div style="width:{a['confidence']}%;background:#2d9e6b;height:4px;border-radius:4px"></div></div></div>
    </div>""" for a in alts) or '<p class="text-muted">High confidence — no significant alternatives.</p>'
    steps_html = "".join(f"<li style='margin-bottom:8px;font-size:13px;color:#374151'>{s}</li>" for s in treatment.get("steps",[]))
    chem_html = "".join(f"<li style='margin-bottom:8px;font-size:13px;color:#374151'>{c}</li>" for c in treatment.get("chemical",[]))
    org_html = "".join(f"<li style='margin-bottom:8px;font-size:13px;color:#374151'>{o}</li>" for o in treatment.get("organic",[]))
    sugg_html = "".join(f'<button class="quick-q-btn" onclick="sendChat(\'{q}\')">{q}</button>' for q in suggested_questions(disease, lang))
    status_icon = "✅" if is_healthy else "❌"

    # ── W-Response + Crop Doctor data ─────────────────────────────────────────
    from modules.assistant import w_response as get_wr
    wr = get_wr(disease, lang, notes or "your field")

    # Role-based WHO action
    role = (user.get("role") or "farmer").lower()
    if role == "admin":
        who_action = "Admin: Review system-wide disease spread and update alert thresholds."
    elif role == "expert":
        who_action = f"Agronomist: Provide expert consultation. {wr['who']}"
    else:
        who_action = wr["who"]

    # W cards config
    w_cards = [
        ("❓", "WHAT",  "Diagnosis & Identification", wr["what"],  "#dbeafe", "#1d4ed8",
         f"Crop type: <strong>{result['crop']}</strong> &nbsp;|&nbsp; Disease: <strong>{result['disease_display']}</strong> &nbsp;|&nbsp; Confidence: <strong>{conf_pct}%</strong>"),
        ("📍", "WHERE", "Location Intelligence",      wr["where"], "#dcfce7", "#15803d",
         f"Field: <strong>{notes or 'Scanned field'}</strong> &nbsp;|&nbsp; Severity zone: <strong>{severity}</strong>"),
        ("⏰", "WHEN",  "Timing & Prediction",        wr["when"],  "#fef3c7", "#d97706",
         f"Harvest prediction: based on current health score <strong>{calculate_health_score([])}</strong>"),
        ("🤔", "WHY",   "Cause Analysis",             wr["why"],   "#fee2e2", "#dc2626",
         f"Severity: <span style='font-weight:700;color:{sev_color}'>{severity}</span>"),
        ("👨‍🌾", "WHO",  "Action & Responsibility",    who_action,  "#ede9fe", "#7c3aed",
         f"Role: <strong>{role.title()}</strong> &nbsp;|&nbsp; Action required: <strong>{'No' if is_healthy else 'Yes — Immediately'}</strong>"),
    ]

    w_html = ""
    for emoji, label, sublabel, text, bg, color, meta in w_cards:
        w_html += f"""
        <div style="background:{bg};border-radius:10px;padding:16px 18px;margin-bottom:10px;border-left:4px solid {color}">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
            <span style="font-size:22px">{emoji}</span>
            <div>
              <div style="font-size:13px;font-weight:700;color:{color};text-transform:uppercase;letter-spacing:.06em">{label}</div>
              <div style="font-size:11px;color:#6b7280">{sublabel}</div>
            </div>
          </div>
          <div style="font-size:13px;color:#1a1a1a;line-height:1.6;margin-bottom:6px">{text}</div>
          <div style="font-size:11px;color:#6b7280">{meta}</div>
        </div>"""

    # ── Pre-compute all variables used in f-string (no nested dicts) ──────────
    passes   = result.get("passes") or {}
    p1       = passes.get("p1", conf_pct)
    p2       = passes.get("p2", conf_pct)
    p3       = passes.get("p3", conf_pct)
    img_warn = result.get("image_warning", "")
    img_warn_html = (f'<span style="font-size:11px;background:#fef3c7;padding:2px 9px;border-radius:20px;color:#d97706">⚠️ {img_warn}</span>'
                     if img_warn else "")
    t_bg     = trust["bg"]
    t_border = trust["border"]
    t_icon   = trust["icon"]
    t_color  = trust["color"]
    t_label  = trust["label"]
    t_pct    = trust["pct"]
    t_msg    = trust["message"]
    hero_bg  = "linear-gradient(135deg,#1a7a4a,#2d9e6b)" if is_healthy else "linear-gradient(135deg,#b45309,#f59e0b)"
    hero_icon = "✅" if is_healthy else "⚠️"
    hero_badge = "✅ Healthy Crop" if is_healthy else "❌ Disease Detected"
    sum_bg   = "#f0fdf4" if is_healthy else "#fff7ed"
    sum_bdr  = "#86efac" if is_healthy else "#fcd34d"
    sum_col  = "#15803d" if is_healthy else "#d97706"
    sum_head = "✅ Your crop is healthy!" if is_healthy else "⚠️ Action Required"
    act_when = "Monitor" if is_healthy else ("Now" if severity in ("Severe","Critical") else "2–3 days")
    st_col   = "#2d9e6b" if is_healthy else "#ef4444"
    st_lbl   = "Healthy ✅" if is_healthy else "Affected ❌"
    conf_col = "#2d9e6b" if conf_pct >= 70 else ("#f59e0b" if conf_pct >= 50 else "#ef4444")
    alts_section = alts_html if alts else '<div style="font-size:13px;color:#9ca3af;text-align:center;padding:10px 0">High confidence — no significant alternatives.</div>'
    disease_short = result["disease_display"].split(" — ")[-1]
    plain_sum = result.get("plain_summary", "")

    body = f"""
    <!-- ── Step indicator (completed) ──────────────────────────── -->
    <div style="display:flex;align-items:center;gap:0;margin-bottom:24px;background:#fff;border-radius:12px;padding:16px 20px;box-shadow:0 1px 3px rgba(0,0,0,.06)">
      <div style="display:flex;align-items:center;gap:8px;flex:1">
        <div style="width:28px;height:28px;border-radius:50%;background:#2d9e6b;color:#fff;display:flex;align-items:center;justify-content:center;font-size:13px;flex-shrink:0">✓</div>
        <div><div style="font-size:12px;font-weight:700;color:#2d9e6b">Image Uploaded</div><div style="font-size:10px;color:#9ca3af">Done</div></div>
      </div>
      <div style="flex:1;height:2px;background:#2d9e6b;margin:0 8px"></div>
      <div style="display:flex;align-items:center;gap:8px;flex:1">
        <div style="width:28px;height:28px;border-radius:50%;background:#2d9e6b;color:#fff;display:flex;align-items:center;justify-content:center;font-size:13px;flex-shrink:0">✓</div>
        <div><div style="font-size:12px;font-weight:700;color:#2d9e6b">AI Analysis</div><div style="font-size:10px;color:#9ca3af">Complete</div></div>
      </div>
      <div style="flex:1;height:2px;background:#2d9e6b;margin:0 8px"></div>
      <div style="display:flex;align-items:center;gap:8px;flex:1">
        <div style="width:28px;height:28px;border-radius:50%;background:#2d9e6b;color:#fff;display:flex;align-items:center;justify-content:center;font-size:13px;flex-shrink:0">✓</div>
        <div><div style="font-size:12px;font-weight:700;color:#2d9e6b">Results Ready</div><div style="font-size:10px;color:#9ca3af">See below</div></div>
      </div>
    </div>

    <!-- ── Result hero banner ────────────────────────────────────── -->
    <div style="background:{hero_bg};border-radius:14px;padding:22px 24px;margin-bottom:16px;color:#fff;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:14px">
      <div style="display:flex;align-items:center;gap:14px">
        <div style="width:56px;height:56px;border-radius:12px;background:rgba(255,255,255,.2);display:flex;align-items:center;justify-content:center;font-size:28px;flex-shrink:0">{hero_icon}</div>
        <div>
          <div style="font-size:11px;opacity:.8;text-transform:uppercase;letter-spacing:.08em;margin-bottom:3px">Diagnosis Result</div>
          <div style="font-size:20px;font-weight:800;line-height:1.2">{result['disease_display']}</div>
          <div style="font-size:13px;opacity:.85;margin-top:4px">🌿 {result['crop']} &nbsp;·&nbsp; 🎯 {conf_pct}% confidence &nbsp;·&nbsp; 📊 {severity} severity</div>
        </div>
      </div>
      <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px">
        <span style="background:rgba(255,255,255,.25);padding:6px 16px;border-radius:20px;font-size:13px;font-weight:700">{hero_badge}</span>
        <a href="/scan" style="color:rgba(255,255,255,.8);font-size:12px;text-decoration:none">← Scan another crop</a>
      </div>
    </div>

    <!-- ── AI Trust panel ────────────────────────────────────────── -->
    <div style="background:{t_bg};border:1.5px solid {t_border};border-radius:12px;padding:14px 18px;margin-bottom:20px">
      <div style="display:flex;align-items:flex-start;gap:12px">
        <div style="font-size:26px;flex-shrink:0">{t_icon}</div>
        <div style="flex:1">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:5px;flex-wrap:wrap">
            <span style="font-size:13px;font-weight:800;color:{t_color}">{t_label}</span>
            <span style="font-size:12px;color:#6b7280">AI matched at <strong style="color:{t_color}">{t_pct}%</strong></span>
            <div style="flex:1;min-width:100px;background:#e5e7eb;border-radius:6px;height:7px;overflow:hidden">
              <div style="width:{t_pct}%;height:7px;background:{t_color};border-radius:6px"></div>
            </div>
          </div>
          <div style="font-size:12px;color:#374151;line-height:1.6;margin-bottom:8px">{t_msg}</div>
          <div style="display:flex;gap:6px;flex-wrap:wrap">
            <span style="font-size:11px;background:rgba(0,0,0,.06);padding:2px 9px;border-radius:20px;color:#6b7280">Pass 1: {p1}%</span>
            <span style="font-size:11px;background:rgba(0,0,0,.06);padding:2px 9px;border-radius:20px;color:#6b7280">Pass 2: {p2}%</span>
            <span style="font-size:11px;background:rgba(0,0,0,.06);padding:2px 9px;border-radius:20px;color:#6b7280">Pass 3: {p3}%</span>
            {img_warn_html}
          </div>
        </div>
      </div>
    </div>

    <!-- ── Main result grid ──────────────────────────────────────── -->
    <div class="grid-2" style="margin-bottom:20px">

      <!-- Left column -->
      <div style="display:flex;flex-direction:column;gap:16px">

        <!-- Scanned image card -->
        <div class="card">
          <div style="font-size:13px;font-weight:700;color:#1a1a1a;margin-bottom:12px">📷 Scanned Image</div>
          <img src="/uploads/{file.filename}" style="width:100%;border-radius:10px;object-fit:contain;background:#f9fafb;margin-bottom:12px" alt="Scanned crop">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
            <span style="font-size:12px;color:#6b7280">AI Confidence</span>
            <span style="font-size:13px;font-weight:700;color:{conf_col}">{conf_pct}%</span>
          </div>
          <div style="background:#e5e7eb;border-radius:6px;height:8px;overflow:hidden;margin-bottom:14px">
            <div style="width:{conf_pct}%;height:100%;background:{conf_col};border-radius:6px"></div>
          </div>
          <div style="display:flex;gap:8px;margin-top:14px">
            <a href="/insights?disease={disease}" class="btn btn-primary btn-sm" style="flex:1;justify-content:center">🧠 Deep Analysis</a>
            <a href="/expert?disease={disease}" class="btn btn-secondary btn-sm" style="flex:1;justify-content:center">🤝 Ask Expert</a>
          </div>
        </div>

        <!-- Quick summary -->
        <div class="card" style="background:{sum_bg};border:1.5px solid {sum_bdr}">
          <div style="font-size:13px;font-weight:700;color:{sum_col};margin-bottom:12px">{sum_head}</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px">
            <div style="background:#fff;border-radius:8px;padding:12px;text-align:center">
              <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#9ca3af;margin-bottom:4px">Crop</div>
              <div style="font-size:15px;font-weight:800;color:#1a1a1a">{result['crop']}</div>
            </div>
            <div style="background:#fff;border-radius:8px;padding:12px;text-align:center">
              <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#9ca3af;margin-bottom:4px">Severity</div>
              <div style="font-size:15px;font-weight:800;color:{sev_color}">{severity}</div>
            </div>
            <div style="background:#fff;border-radius:8px;padding:12px;text-align:center">
              <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#9ca3af;margin-bottom:4px">Act When</div>
              <div style="font-size:13px;font-weight:700;color:#1a1a1a">{act_when}</div>
            </div>
            <div style="background:#fff;border-radius:8px;padding:12px;text-align:center">
              <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#9ca3af;margin-bottom:4px">Status</div>
              <div style="font-size:13px;font-weight:700;color:{st_col}">{st_lbl}</div>
            </div>
          </div>
          <div style="font-size:13px;color:#374151;line-height:1.7;background:#fff;border-radius:8px;padding:12px">
            <strong>What to do:</strong> {info['solution']}
          </div>
        </div>

        <!-- Other possibilities -->
        <div class="card">
          <div style="font-size:13px;font-weight:700;color:#1a1a1a;margin-bottom:12px">🔬 Other Possibilities</div>
          {alts_section}
        </div>
      </div>

      <!-- Right column -->
      <div style="display:flex;flex-direction:column;gap:16px">

        <!-- Treatment plan -->
        <div class="card">
          <div style="font-size:13px;font-weight:700;color:#1a1a1a;margin-bottom:14px">💊 Treatment Plan</div>
          <div style="display:flex;gap:0;border:1.5px solid #e5e7eb;border-radius:8px;overflow:hidden;margin-bottom:14px">
            <button class="tab-btn active" data-tab="t-steps" onclick="switchTab('t-steps')" style="flex:1;border-radius:0;border:none;padding:9px;font-size:12px;font-weight:600">📋 Steps</button>
            <button class="tab-btn" data-tab="t-chem" onclick="switchTab('t-chem')" style="flex:1;border-radius:0;border:none;border-left:1px solid #e5e7eb;padding:9px;font-size:12px;font-weight:600">🧪 Chemical</button>
            <button class="tab-btn" data-tab="t-org" onclick="switchTab('t-org')" style="flex:1;border-radius:0;border:none;border-left:1px solid #e5e7eb;padding:9px;font-size:12px;font-weight:600">🌿 Organic</button>
          </div>
          <div id="t-steps" class="tab-panel active">
            <ol style="padding-left:18px;margin:0">
              {steps_html or '<li style="color:#9ca3af;font-size:13px">No steps available.</li>'}
            </ol>
          </div>
          <div id="t-chem" class="tab-panel">
            <ul style="padding-left:18px;margin:0">
              {chem_html or '<li style="color:#9ca3af;font-size:13px">No chemical treatment listed.</li>'}
            </ul>
          </div>
          <div id="t-org" class="tab-panel">
            <ul style="padding-left:18px;margin:0">
              {org_html or '<li style="color:#9ca3af;font-size:13px">No organic treatment listed.</li>'}
            </ul>
          </div>
        </div>

        <!-- Cause & Prevention -->
        <div class="card">
          <div style="font-size:13px;font-weight:700;color:#1a1a1a;margin-bottom:12px">🔍 Cause & Prevention</div>
          <div style="background:#fff7ed;border-radius:8px;padding:12px;margin-bottom:10px;border-left:3px solid #f59e0b">
            <div style="font-size:11px;font-weight:700;text-transform:uppercase;color:#d97706;margin-bottom:5px">🤔 Why it happened</div>
            <div style="font-size:13px;color:#374151;line-height:1.6">{info['cause']}</div>
          </div>
          <div style="background:#fef3c7;border-radius:8px;padding:12px;margin-bottom:10px;border-left:3px solid #d97706">
            <div style="font-size:11px;font-weight:700;text-transform:uppercase;color:#d97706;margin-bottom:5px">⏰ When it occurs</div>
            <div style="font-size:13px;color:#374151;line-height:1.6">{info.get('when','Unknown')}</div>
          </div>
          <div style="background:#fee2e2;border-radius:8px;padding:12px;margin-bottom:10px;border-left:3px solid #ef4444">
            <div style="font-size:11px;font-weight:700;text-transform:uppercase;color:#dc2626;margin-bottom:5px">📡 How it spreads</div>
            <div style="font-size:13px;color:#374151;line-height:1.6">{info.get('how','Unknown')}</div>
          </div>
          <div style="background:#eff6ff;border-radius:8px;padding:12px;margin-bottom:10px;border-left:3px solid #3b82f6">
            <div style="font-size:11px;font-weight:700;text-transform:uppercase;color:#1d4ed8;margin-bottom:5px">🎯 Who is affected</div>
            <div style="font-size:13px;color:#374151;line-height:1.6">{info.get('who','Unknown')}</div>
          </div>
          <div style="background:#f0fdf4;border-radius:8px;padding:12px;border-left:3px solid #2d9e6b">
            <div style="font-size:11px;font-weight:700;text-transform:uppercase;color:#15803d;margin-bottom:5px">🛡️ How to prevent</div>
            <div style="font-size:13px;color:#374151;line-height:1.6">{info['prevention']}</div>
          </div>
        </div>

        <!-- W-Response intelligence -->
        <div class="card">
          <div style="font-size:13px;font-weight:700;color:#1a1a1a;margin-bottom:4px">🧠 AI Intelligence Report</div>
          <div style="font-size:11px;color:#9ca3af;margin-bottom:14px">5-dimension analysis of your crop</div>
          {w_html}
        </div>
      </div>
    </div>

    <!-- ── Plain language summary ─────────────────────────────────── -->
    <div style="background:{sum_bg};border:1.5px solid {sum_bdr};border-radius:12px;padding:18px 20px;margin-bottom:20px">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
        <span style="font-size:18px">💬</span>
        <div style="font-size:13px;font-weight:700;color:{sum_col}">Plain Language Summary</div>
      </div>
      <div style="font-size:13px;color:#374151;line-height:1.8;white-space:pre-line">{plain_sum}</div>
    </div>

    <!-- ── AI Chat ────────────────────────────────────────────────── -->
    <div class="card">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;flex-wrap:wrap;gap:8px">
        <div>
          <div style="font-size:14px;font-weight:700;color:#1a1a1a">💬 Ask About This Crop</div>
          <div style="font-size:11px;color:#9ca3af">Answers are based on your scanned image only</div>
        </div>
        <span style="background:#f0fdf4;color:#15803d;border:1px solid #86efac;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600">📷 Image-Driven AI</span>
      </div>
      <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:10px 14px;margin-bottom:12px;font-size:12px;color:#15803d;display:flex;align-items:center;gap:8px">
        <span>🌿</span>
        <span>Detected: <strong>{result['crop']}</strong> — <strong>{disease_short}</strong> &nbsp;·&nbsp; {conf_pct}% match</span>
      </div>
      <input type="hidden" id="currentDisease" value="{disease}">
      <input type="hidden" id="currentLang" value="{lang}">
      <div class="quick-questions" style="margin-bottom:12px">{sugg_html}</div>
      <div class="chat-container">
        <div class="chat-messages" id="chatBox">
          <div class="chat-msg bot">
            <div class="chat-bubble" style="white-space:pre-line">📷 Image analysed. Here is what I found:

🌿 Crop:       {result['crop']}
🦠 Disease:    {disease_short}
⚠️  Status:     {st_lbl}
📊 Severity:   {severity}
🎯 Confidence: {conf_pct}%

Ask me anything about this crop or disease.</div>
            <div class="chat-time">Now</div>
          </div>
        </div>
        <div class="chat-input-row">
          <input class="form-input" id="chatInput" placeholder="e.g. How do I treat this? What caused it? Is it contagious?">
          <button class="btn btn-primary" onclick="sendChat()">Send ➤</button>
        </div>
      </div>
    </div>"""
    return HTMLResponse(shell("Diagnosis Result", f"{result['crop']} — {disease_short}", body, "scan", user, lang))

# ══ 📊 MONITOR ════════════════════════════════════════════════════════════════

@app.get("/monitor", response_class=HTMLResponse)
def monitor_page(request: Request, lang: str = "en"):
    user = cu(request)
    if not user: return RedirectResponse("/login")
    dets = _get_scans(user.get("id"), 200)
    health = calculate_health_score(dets)
    hc = "#2d9e6b" if health>=80 else "#f59e0b" if health>=60 else "#ef4444"

    # Real crop counts from scan history
    crop_counts = {}
    disease_counts = {}
    for d in dets:
        c = d.get("crop_name","Unknown")
        crop_counts[c] = crop_counts.get(c,0)+1
        if "healthy" not in d.get("disease","").lower():
            dis = d.get("disease","").replace("___"," — ").replace("_"," ")[:30]
            disease_counts[dis] = disease_counts.get(dis,0)+1

    top_crop = max(crop_counts, key=crop_counts.get) if crop_counts else "Maize"
    yield_pred = predict_yield(top_crop, health, 2.0)
    hc_data = health_chart_data(1) if DB_AVAILABLE else {"labels":["Jan","Feb","Mar","Apr","May","Jun"],"scores":[45,50,55,60,65,75]}

    # Scan history per crop
    crop_rows = ""
    for crop, count in sorted(crop_counts.items(), key=lambda x: -x[1])[:6]:
        crop_dets = [d for d in dets if d.get("crop_name")==crop]
        crop_health = calculate_health_score(crop_dets)
        ch = "#2d9e6b" if crop_health>=80 else "#f59e0b" if crop_health>=60 else "#ef4444"
        diseased = sum(1 for d in crop_dets if "healthy" not in d.get("disease","").lower())
        crop_rows += f"""<div style="margin-bottom:14px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
            <div>
              <div style="font-size:13px;font-weight:600">🌿 {crop}</div>
              <div style="font-size:11px;color:#9ca3af">{count} scans · {diseased} disease{'s' if diseased!=1 else ''} detected</div>
            </div>
            <span style="font-size:13px;font-weight:700;color:{ch}">{crop_health}%</span>
          </div>
          <div class="progress"><div class="progress-fill {'green' if crop_health>=80 else 'orange' if crop_health>=60 else 'red'}" style="width:{crop_health}%"></div></div>
        </div>"""

    if not crop_rows:
        crop_rows = '<div style="text-align:center;padding:20px;color:#9ca3af;font-size:13px">No scan data yet — <a href="/scan" style="color:#2d9e6b">scan your first crop</a></div>'

    # Recent disease detections
    recent_diseases = [d for d in dets[:20] if "healthy" not in d.get("disease","").lower()]
    disease_rows = "".join(f"""<div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid #f3f4f6">
      <div style="width:36px;height:36px;border-radius:8px;background:#fff1f2;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0">🦠</div>
      <div style="flex:1">
        <div style="font-size:12px;font-weight:600;color:#1a1a1a">{d.get('crop_name','')}</div>
        <div style="font-size:11px;color:#9ca3af">{d.get('disease','').replace('___',' — ').replace('_',' ')[:35]}</div>
      </div>
      <div style="text-align:right">
        <div style="font-size:11px;font-weight:600;color:#ef4444">{d.get('severity','—')}</div>
        <div style="font-size:10px;color:#9ca3af">{str(d.get('detected_at',''))[:10]}</div>
      </div>
    </div>""" for d in recent_diseases[:5]) or '<div style="text-align:center;padding:16px;color:#9ca3af;font-size:13px">No diseases detected ✅</div>'

    total_scans = len(dets)
    healthy_count = sum(1 for d in dets if "healthy" in d.get("disease","").lower())
    diseased_count = total_scans - healthy_count
    healthy_pct = round(healthy_count/max(total_scans,1)*100)

    body = f"""
    <!-- Stats row -->
    <div class="grid-4" style="margin-bottom:20px">
      <div class="stat-card"><div class="stat-icon-box green">💚</div><div class="stat-value" style="color:{hc}">{health}</div><div class="stat-label">Health Score</div><div class="stat-delta up">Overall farm health</div></div>
      <div class="stat-card"><div class="stat-icon-box blue">🌾</div><div class="stat-value">{len(crop_counts)}</div><div class="stat-label">Crops Monitored</div><div class="stat-delta up">{total_scans} total scans</div></div>
      <div class="stat-card"><div class="stat-icon-box green">✅</div><div class="stat-value">{healthy_pct}%</div><div class="stat-label">Healthy Crops</div><div class="stat-delta up">{healthy_count} of {total_scans} scans</div></div>
      <div class="stat-card"><div class="stat-icon-box red">⚠️</div><div class="stat-value">{diseased_count}</div><div class="stat-label">Diseases Detected</div><div class="stat-delta {'down' if diseased_count>0 else 'up'}">{'Needs attention' if diseased_count>0 else 'All clear'}</div></div>
    </div>

    <div class="grid-2">
      <div>
        <!-- Health trend chart -->
        <div class="card">
          <div class="card-header"><div class="card-title">📈 Health Score Trend</div><a href="/reports" class="card-link">View history</a></div>
          <canvas id="healthChart" height="160"></canvas>
        </div>

        <!-- Crop health breakdown -->
        <div class="card">
          <div class="card-header"><div class="card-title">🌿 Crop Health Breakdown</div></div>
          {crop_rows}
        </div>
      </div>

      <div>
        <!-- Yield prediction -->
        <div class="card" style="background:linear-gradient(135deg,#1a7a4a,#2d9e6b);color:#fff;margin-bottom:16px">
          <div style="font-size:12px;opacity:.8;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px">📦 Yield Prediction — {top_crop}</div>
          <div style="font-size:36px;font-weight:800;line-height:1">{yield_pred['predicted_tons']}t</div>
          <div style="font-size:13px;opacity:.85;margin-top:4px">per hectare · {100-yield_pred['loss_percent']}% of optimal</div>
          <div style="background:rgba(255,255,255,.2);border-radius:6px;height:6px;margin-top:12px;overflow:hidden">
            <div style="width:{100-yield_pred['loss_percent']}%;height:6px;background:#fff;border-radius:6px"></div>
          </div>
          <div style="display:flex;justify-content:space-between;margin-top:8px;font-size:11px;opacity:.8">
            <span>Yield loss: {yield_pred['loss_percent']}%</span>
            <span>Optimal: {yield_pred['optimal_tons']}t</span>
          </div>
        </div>

        <!-- Recent disease detections -->
        <div class="card">
          <div class="card-header"><div class="card-title">🦠 Recent Disease Detections</div><a href="/reports" class="card-link">View all</a></div>
          {disease_rows}
        </div>

        <!-- Quick actions -->
        <div class="card">
          <div class="card-header"><div class="card-title">⚡ Quick Actions</div></div>
          <div style="display:flex;flex-direction:column;gap:8px">
            <a href="/scan" class="btn btn-primary btn-full" style="justify-content:center">📷 Scan a Crop Now</a>
            <a href="/insights" class="btn btn-secondary btn-full" style="justify-content:center">🧠 View AI Insights</a>
            <a href="/reports" class="btn btn-ghost btn-full" style="justify-content:center">📈 Full Report</a>
          </div>
        </div>
      </div>
    </div>
    <script>window._healthData={json.dumps(hc_data)};</script>"""
    return HTMLResponse(shell("Monitor Crops", "Track crop health, yield predictions, and disease history", body, "monitor", user, lang))


# ══ 🧠 INSIGHTS ═══════════════════════════════════════════════════════════════

@app.get("/insights", response_class=HTMLResponse)
def insights_page(request: Request, disease: str = "", lang: str = "en"):
    user = cu(request)
    if not user: return RedirectResponse("/login")
    w = get_weather("Dar es Salaam")
    risks = disease_risk_forecast(w)
    irr = irrigation_advice(w)
    dets = _get_scans(user.get("id"), 200)
    health = calculate_health_score(dets)
    total = len(dets)

    # Real top crop from scan history
    crop_counts = {}
    for d in dets:
        c = d.get("crop_name","Maize")
        crop_counts[c] = crop_counts.get(c,0)+1
    top_crop = max(crop_counts, key=crop_counts.get) if crop_counts else "Maize"
    yield_pred = predict_yield(top_crop, health, 2.0)

    # Real disease risk from actual detections
    recent_diseases = [d for d in dets[:30] if "healthy" not in d.get("disease","").lower()]
    risk_level = "High" if len(recent_diseases) >= 5 else "Moderate" if len(recent_diseases) >= 2 else "Low"
    risk_color = "#ef4444" if risk_level=="High" else "#f59e0b" if risk_level=="Moderate" else "#2d9e6b"
    risk_pct   = 80 if risk_level=="High" else 50 if risk_level=="Moderate" else 20

    # Real disease frequency from scan history
    disease_freq = {}
    for d in dets:
        if "healthy" not in d.get("disease","").lower():
            key = d.get("disease","").replace("___"," — ").replace("_"," ")[:30]
            disease_freq[key] = disease_freq.get(key,0)+1
    top_diseases = sorted(disease_freq.items(), key=lambda x:-x[1])[:5]

    disease_list = "".join(f"""<div style="display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid #f3f4f6">
      <div style="font-size:13px;color:#374151">{name}</div>
      <div style="display:flex;align-items:center;gap:8px">
        <div style="width:80px;background:#e5e7eb;border-radius:4px;height:6px;overflow:hidden">
          <div style="width:{min(count/max(len(dets),1)*100*5,100):.0f}%;height:6px;background:#ef4444;border-radius:4px"></div>
        </div>
        <span style="font-size:12px;font-weight:600;color:#ef4444">{count}x</span>
      </div>
    </div>""" for name, count in top_diseases) or '<div style="text-align:center;padding:16px;color:#9ca3af;font-size:13px">No diseases detected yet ✅</div>'

    # W-based disease analysis (if disease param provided)
    why_cards = ""
    if disease:
        from modules.assistant import w_response as get_wr
        wr = get_wr(disease, lang)
        why_cards = f"""
        <div style="background:linear-gradient(135deg,#1a7a4a,#2d9e6b);border-radius:12px;padding:20px 24px;margin-bottom:20px;color:#fff">
          <div style="font-size:11px;opacity:.8;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px">🧠 AI Analysis — {disease.replace('___',' — ').replace('_',' ')}</div>
          <div style="font-size:16px;font-weight:700">5-Dimension Diagnosis</div>
        </div>
        <div class="grid-2" style="margin-bottom:20px;gap:12px">
          <div style="background:#dbeafe;border-radius:10px;padding:16px;border-left:4px solid #1d4ed8">
            <div style="font-size:11px;font-weight:700;color:#1d4ed8;text-transform:uppercase;margin-bottom:6px">❓ WHAT — Diagnosis</div>
            <div style="font-size:13px;color:#1a1a1a;line-height:1.6">{wr['what']}</div>
          </div>
          <div style="background:#dcfce7;border-radius:10px;padding:16px;border-left:4px solid #15803d">
            <div style="font-size:11px;font-weight:700;color:#15803d;text-transform:uppercase;margin-bottom:6px">📍 WHERE — Location</div>
            <div style="font-size:13px;color:#1a1a1a;line-height:1.6">{wr['where']}</div>
          </div>
          <div style="background:#fef3c7;border-radius:10px;padding:16px;border-left:4px solid #d97706">
            <div style="font-size:11px;font-weight:700;color:#d97706;text-transform:uppercase;margin-bottom:6px">⏰ WHEN — Timing</div>
            <div style="font-size:13px;color:#1a1a1a;line-height:1.6">{wr['when']}</div>
          </div>
          <div style="background:#fee2e2;border-radius:10px;padding:16px;border-left:4px solid #dc2626">
            <div style="font-size:11px;font-weight:700;color:#dc2626;text-transform:uppercase;margin-bottom:6px">🤔 WHY — Root Cause</div>
            <div style="font-size:13px;color:#1a1a1a;line-height:1.6">{wr['why']}</div>
          </div>
        </div>
        <div style="background:#ede9fe;border-radius:10px;padding:16px;border-left:4px solid #7c3aed;margin-bottom:20px">
          <div style="font-size:11px;font-weight:700;color:#7c3aed;text-transform:uppercase;margin-bottom:6px">👨‍🌾 WHO — Action</div>
          <div style="font-size:13px;color:#1a1a1a;line-height:1.6">{wr['who']}</div>
        </div>"""

    # Weather-based risk cards
    risk_cards = "".join(f"""<div style="background:#fff;border-radius:10px;padding:14px;border:1px solid #e5e7eb;margin-bottom:8px">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
        <div style="font-size:13px;font-weight:600;color:#1a1a1a">{r.get('disease','Disease')}</div>
        <span style="background:{'#fee2e2' if r.get('risk')=='High' else '#fef3c7' if r.get('risk')=='Moderate' else '#f0fdf4'};color:{'#dc2626' if r.get('risk')=='High' else '#d97706' if r.get('risk')=='Moderate' else '#15803d'};padding:2px 10px;border-radius:20px;font-size:11px;font-weight:700">{r.get('risk','Low')}</span>
      </div>
      <div style="font-size:12px;color:#6b7280">{r.get('reason','Based on current weather conditions')}</div>
    </div>""" for r in risks[:4]) or '<div style="font-size:13px;color:#9ca3af;text-align:center;padding:12px">No risk data available</div>'

    body = f"""
    {why_cards}

    <!-- Key metrics -->
    <div class="grid-3" style="margin-bottom:20px">
      <div class="insights-metric">
        <div class="insights-metric-label">Yield Prediction — {top_crop}</div>
        <div class="insights-metric-val">{yield_pred['predicted_tons']}t/ha</div>
        <div class="insights-metric-sub">{100-yield_pred['loss_percent']}% of optimal · {yield_pred['loss_percent']}% loss</div>
        <div class="insights-metric-bar"><div class="progress"><div class="progress-fill green" style="width:{100-yield_pred['loss_percent']}%"></div></div></div>
      </div>
      <div class="insights-metric">
        <div class="insights-metric-label">Disease Risk Level</div>
        <div class="insights-metric-val" style="color:{risk_color}">{risk_level}</div>
        <div class="insights-metric-sub">{len(recent_diseases)} diseases in last {total} scans</div>
        <div class="insights-metric-bar"><div class="progress"><div class="progress-fill {'red' if risk_level=='High' else 'orange' if risk_level=='Moderate' else 'green'}" style="width:{risk_pct}%"></div></div></div>
      </div>
      <div class="insights-metric">
        <div class="insights-metric-label">Overall Health Score</div>
        <div class="insights-metric-val" style="color:{'#2d9e6b' if health>=80 else '#f59e0b' if health>=60 else '#ef4444'}">{health}%</div>
        <div class="insights-metric-sub">Based on {total} scans</div>
        <div class="insights-metric-bar"><div class="progress"><div class="progress-fill {'green' if health>=80 else 'orange' if health>=60 else 'red'}" style="width:{health}%"></div></div></div>
      </div>
    </div>

    <div class="grid-2">
      <div>
        <!-- Disease frequency from real data -->
        <div class="card">
          <div class="card-header"><div class="card-title">🦠 Most Frequent Diseases</div><a href="/reports" class="card-link">Full history</a></div>
          {disease_list}
        </div>

        <!-- Irrigation advice -->
        <div class="card" style="background:linear-gradient(135deg,#dbeafe,#eff6ff);border:1px solid #bfdbfe">
          <div style="font-size:13px;font-weight:700;color:#1d4ed8;margin-bottom:8px">💧 Irrigation Advice</div>
          <div style="font-size:13px;color:#374151;line-height:1.7">{irr}</div>
          <div style="margin-top:10px;font-size:12px;color:#6b7280">
            💧 Humidity: {w['humidity']}% &nbsp;·&nbsp; 🌧️ Rain: {w['rainfall_mm']}mm &nbsp;·&nbsp; 🌡️ Temp: {w['temperature']}°C
          </div>
        </div>
      </div>

      <div>
        <!-- Weather-based disease risk -->
        <div class="card">
          <div class="card-header"><div class="card-title">🌦️ Weather-Based Disease Risk</div></div>
          {risk_cards}
        </div>

        <!-- Preventive advice -->
        <div class="card" style="background:linear-gradient(135deg,#f0fdf4,#dcfce7);border:1px solid #86efac">
          <div style="font-size:13px;font-weight:700;color:#15803d;margin-bottom:10px">🛡️ Preventive Recommendations</div>
          {"".join(f'<div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:8px;font-size:13px;color:#374151"><span style="color:#2d9e6b;flex-shrink:0">✓</span>{tip}</div>' for tip in [
            "Scout fields every 3–5 days for early disease signs",
            "Remove and destroy infected plant material immediately",
            "Avoid overhead irrigation — use drip irrigation where possible",
            "Rotate crops each season to break disease cycles",
            "Apply preventive fungicide before rainy season",
          ])}
        </div>

        <!-- AI stats -->
        <div class="ai-learning-card">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
            <span style="font-size:20px">🤖</span>
            <div class="ai-learning-title">AI Analysis Summary</div>
          </div>
          <div class="ai-learning-sub">Based on your {total} scans in the Crop Diagnosis System</div>
          <div class="ai-learning-stats">
            <div><div class="ai-stat-val">{total}</div><div class="ai-stat-lbl">Images Analysed</div></div>
            <div><div class="ai-stat-val">{len(crop_counts)}</div><div class="ai-stat-lbl">Crop Types</div></div>
          </div>
        </div>
      </div>
    </div>"""
    return HTMLResponse(shell("AI Insights", "Disease predictions, risk analysis, and preventive recommendations", body, "insights", user, lang))

# ══ 🌾 FARMS ══════════════════════════════════════════════════════════════════

@app.get("/farms", response_class=HTMLResponse)
def farms_page(request: Request, lang: str = "en"):
    user = cu(request)
    if not user: return RedirectResponse("/login")
    farms = get_farms(user.get("id")) if DB_AVAILABLE else []

    # Demo farms if none exist
    demo_farms = [
        {"id":1,"name":"Shamba la Kijani","location":"Arusha, Kaskazini","size_acres":4,"health":100,"crops":["Mahindi","Ngano"],"status":"Healthy"},
        {"id":2,"name":"Mashamba ya Alfajiri","location":"Mbeya, Nyanda za Juu Kusini","size_acres":6,"health":75,"crops":["Mpunga","Maharage"],"status":"Warning"},
        {"id":3,"name":"Mavuno ya Dhahabu","location":"Morogoro, Mashariki","size_acres":10,"health":100,"crops":["Ngano","Soya"],"status":"Healthy"},
    ]
    display_farms = farms if farms else demo_farms

    farm_cards = ""
    for f in display_farms:
        h = f.get("health", 85)
        hcolor = "#2d9e6b" if h>=80 else "#f59e0b" if h>=60 else "#ef4444"
        status = f.get("status","Healthy")
        farm_cards += f"""<div class="farm-card">
          <div class="farm-header">
            <div>
              <div class="farm-name">🌿 {f.get('name','Farm')}</div>
              <div class="farm-location">📍 {f.get('location','N/A')}</div>
            </div>
            <div style="display:flex;gap:6px">
              <button class="btn btn-secondary btn-sm" onclick="location.href='/scan'">Scan</button>
              <button class="btn btn-ghost btn-sm" onclick="openEditFarm(this)" data-id="{f.get('id','')}" data-name="{f.get('name','')}" data-location="{f.get('location','')}">Edit</button>
            </div>
          </div>
          <div class="farm-stats">
            <div class="farm-stat-item"><div class="farm-stat-val">{f.get('size_acres','—')}</div><div class="farm-stat-lbl">Size (ha)</div></div>
            <div class="farm-stat-item"><div class="farm-stat-val">{len(f.get('crops',[1,2]))}</div><div class="farm-stat-lbl">Crops</div></div>
            <div class="farm-stat-item"><div class="farm-stat-val" style="color:{hcolor}">{h}%</div><div class="farm-stat-lbl">Health</div></div>
          </div>
          <div class="progress"><div class="progress-fill {'green' if h>=80 else 'orange' if h>=60 else 'red'}" style="width:{h}%"></div></div>
        </div>"""

    # Field details section
    field_items = "".join(f"""<div class="field-item">
      <div class="field-id">Field {chr(65+i)}-{j+1}</div>
      <div class="field-crop">{crop}</div>
      <div class="field-size">{size} ha</div>
      <div class="progress" style="margin-top:6px"><div class="progress-fill {'green' if h>=80 else 'orange' if h>=60 else 'red'}" style="width:{h}%"></div></div>
      <div class="text-xs" style="color:{'#2d9e6b' if h>=80 else '#f59e0b' if h>=60 else '#ef4444'};margin-top:3px;font-weight:600">{h}%</div>
    </div>""" for i, (crop, size, h, j) in enumerate([("Wheat","2.5ha",81,0),("Corn","2.0ha",75,1),("Wheat","1.8ha",63,2),("Rice","2.1ha",72,3),("Barley","1.9ha",82,4)]))

    body = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
      <div><div class="section-title">Manage Farms</div><div class="section-sub">View and manage your farm locations and crop data</div></div>
      <button class="btn btn-primary" onclick="document.getElementById('addFarmModal').style.display='flex'">➕ Add Farm</button>
    </div>

    <div class="grid-2">{farm_cards}</div>

    <div class="card">
      <div class="card-header"><div class="card-title">📍 Field Details — Shamba la Kijani</div></div>
      <div class="field-grid">{field_items}</div>
    </div>

    <!-- Add Farm Modal -->
    <div id="addFarmModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:200;align-items:center;justify-content:center">
      <div style="background:#fff;border-radius:16px;padding:28px;width:100%;max-width:480px;box-shadow:0 20px 60px rgba(0,0,0,.2)">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
          <div style="font-size:16px;font-weight:700">Add New Farm</div>
          <button onclick="document.getElementById('addFarmModal').style.display='none'" style="background:none;border:none;font-size:20px;cursor:pointer;color:#6b7280">✕</button>
        </div>
        <form method="post" action="/farms">
          <div class="settings-grid">
            <div class="form-group"><label class="form-label">Farm Name *</label><input class="form-input" name="name" placeholder="e.g. North Farm" required></div>
            <div class="form-group"><label class="form-label">Location</label><input class="form-input" name="location" placeholder="e.g. Dodoma, Singida"></div>
            <div class="form-group"><label class="form-label">Size (acres)</label><input class="form-input" name="size" type="number" step="0.1" placeholder="2.5"></div>
            <div class="form-group"><label class="form-label">Main Crop</label><select class="form-input" name="crop_type">{''.join(f'<option>{c}</option>' for c in ["Maize","Potato","Wheat","Rice","Soybean","Other"])}</select></div>
            <div class="form-group"><label class="form-label">GPS Latitude</label><input class="form-input" name="lat" type="number" step="0.0001" placeholder="-0.3031"></div>
            <div class="form-group"><label class="form-label">GPS Longitude</label><input class="form-input" name="lon" type="number" step="0.0001" placeholder="36.0800"></div>
          </div>
          <div style="display:flex;gap:10px;margin-top:8px">
            <button type="submit" class="btn btn-primary">Add Farm</button>
            <button type="button" class="btn btn-ghost" onclick="document.getElementById('addFarmModal').style.display='none'">Cancel</button>
          </div>
        </form>
      </div>
    <!-- Edit Farm Modal -->
    <div id="editFarmModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:200;align-items:center;justify-content:center">
      <div style="background:#fff;border-radius:16px;padding:28px;width:100%;max-width:440px;box-shadow:0 20px 60px rgba(0,0,0,.2)">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
          <div style="font-size:16px;font-weight:700">✏️ Edit Farm</div>
          <button onclick="document.getElementById('editFarmModal').style.display='none'" style="background:none;border:none;font-size:20px;cursor:pointer;color:#6b7280">✕</button>
        </div>
        <div class="form-group"><label class="form-label">Farm Name</label><input class="form-input" id="editFarmName" placeholder="Farm name"></div>
        <div class="form-group"><label class="form-label">Location</label><input class="form-input" id="editFarmLocation" placeholder="e.g. Arusha, Kaskazini"></div>
        <div style="display:flex;gap:10px;margin-top:8px">
          <button class="btn btn-primary" onclick="saveEditFarm()">💾 Save Changes</button>
          <button class="btn btn-ghost" onclick="document.getElementById('editFarmModal').style.display='none'">Cancel</button>
        </div>
      </div>
    </div>
    <script>
    function openEditFarm(btn) {{
      document.getElementById('editFarmName').value = btn.dataset.name || '';
      document.getElementById('editFarmLocation').value = btn.dataset.location || '';
      document.getElementById('editFarmModal').style.display = 'flex';
    }}
    function saveEditFarm() {{
      document.getElementById('editFarmModal').style.display = 'none';
      const msg = document.createElement('div');
      msg.className = 'alert-card success';
      msg.style.cssText = 'position:fixed;top:80px;right:20px;z-index:999;min-width:260px';
      msg.innerHTML = '<span class="alert-icon">✅</span><div class="alert-body"><div class="alert-title">Farm updated successfully.</div></div>';
      document.body.appendChild(msg);
      setTimeout(() => msg.remove(), 3000);
    }}
    </script>"""
    return HTMLResponse(shell("Manage Farms", "View and manage your farm locations and crop data", body, "farms", user, lang))

@app.post("/farms")
async def farms_post(request: Request, name: str = Form(...), location: str = Form(""),
                     size: str = Form(""), lat: str = Form(""), lon: str = Form(""), crop_type: str = Form("")):
    user = cu(request)
    if not user: return RedirectResponse("/login")
    if DB_AVAILABLE:
        create_farm(user.get("id"), name, location,
                    float(lat) if lat else None, float(lon) if lon else None, float(size) if size else None)
    return RedirectResponse("/farms", status_code=303)

# ══ 📈 REPORTS ════════════════════════════════════════════════════════════════

@app.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request, lang: str = "en"):
    user = cu(request)
    if not user: return RedirectResponse("/login")
    uid = user.get("id")
    dets = _get_scans(uid, 500)
    total = len(dets)
    healthy = sum(1 for d in dets if "healthy" in d.get("disease","").lower())
    diseased = total - healthy
    avg_conf = round(sum(float(d.get("confidence",0) if d.get("confidence",0) <= 1 else d.get("confidence",0)/100) for d in dets) / max(total,1) * 100, 1)
    dc = disease_frequency_chart() if DB_AVAILABLE else {"labels":["Leaf Rust","Stem Rot","Blight","Powdery Mildew"],"counts":[35,25,20,20],"colors":["#ef4444","#f59e0b","#3b82f6","#2d9e6b"]}
    tl = detection_timeline_chart(30) if DB_AVAILABLE else {"labels":[],"counts":[]}

    # ── Scan history cards with images ────────────────────────────────────────
    def sev_color(s):
        return {"High":"#ef4444","Critical":"#dc2626","Moderate":"#f59e0b","Low":"#2d9e6b","None":"#2d9e6b"}.get(s,"#9ca3af")

    scan_cards = ""
    for d in dets[:50]:
        img = d.get("image","")
        crop = d.get("crop_name","Unknown")
        disease_raw = d.get("disease","")
        disease_label = disease_raw.replace("___"," — ").replace("_"," ")
        is_h = "healthy" in disease_raw.lower()
        sev = d.get("severity","—")
        sc = sev_color(sev)
        conf_val = d.get("confidence", 0)
        conf_pct = round(float(conf_val)*100 if float(conf_val) <= 1 else float(conf_val), 1)
        date_str = str(d.get("detected_at",""))[:16]
        notes = d.get("notes","") or ""
        solution = d.get("solution","") or ""
        cause = d.get("cause","") or ""
        prevention = d.get("prevention","") or ""
        chem = d.get("chemical_treatment","") or ""
        org = d.get("organic_treatment","") or ""
        img_html = f'<img src="/uploads/{img}" style="width:100%;max-height:180px;object-fit:contain;background:#f9fafb;border-radius:8px 8px 0 0" alt="{crop}" onerror="this.style.display=\'none\'">' if img else f'<div style="width:100%;height:140px;background:linear-gradient(135deg,#f0fdf4,#dcfce7);border-radius:8px 8px 0 0;display:flex;align-items:center;justify-content:center;font-size:40px">🌿</div>'

        scan_cards += f"""
        <div style="background:#fff;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.07);overflow:hidden;border:1px solid #e5e7eb;transition:box-shadow .2s" onmouseover="this.style.boxShadow='0 6px 20px rgba(0,0,0,.12)'" onmouseout="this.style.boxShadow='0 2px 8px rgba(0,0,0,.07)'">
          {img_html}
          <div style="padding:12px">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
              <span style="font-size:13px;font-weight:700;color:#1a1a1a">{crop}</span>
              <span style="background:{'#f0fdf4' if is_h else '#fff1f2'};color:{'#15803d' if is_h else '#dc2626'};border:1px solid {'#86efac' if is_h else '#fca5a5'};padding:2px 8px;border-radius:20px;font-size:10px;font-weight:700">{'✅ Healthy' if is_h else '❌ Affected'}</span>
            </div>
            <div style="font-size:11px;color:#6b7280;margin-bottom:8px;line-height:1.4">{disease_label[:45]}{'...' if len(disease_label)>45 else ''}</div>
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
              <span style="font-size:11px;color:{sc};font-weight:600;background:{sc}18;padding:2px 8px;border-radius:10px">{sev}</span>
              <span style="font-size:11px;color:#9ca3af">🎯 {conf_pct}%</span>
            </div>
            <div style="background:#e5e7eb;border-radius:4px;height:4px;margin-bottom:8px">
              <div style="width:{conf_pct}%;height:4px;background:{'#2d9e6b' if conf_pct>=70 else '#f59e0b' if conf_pct>=50 else '#ef4444'};border-radius:4px"></div>
            </div>
            <div style="font-size:10px;color:#9ca3af;margin-bottom:10px">🕐 {date_str}{' · 📝 '+notes[:20] if notes else ''}</div>
            <button onclick="showDetail(this)" data-crop="{crop}" data-disease="{disease_label}" data-sev="{sev}" data-conf="{conf_pct}" data-date="{date_str}" data-img="{img}" data-cause="{cause[:200]}" data-solution="{solution[:200]}" data-prevention="{prevention[:200]}" data-chem="{chem[:200]}" data-org="{org[:200]}" data-notes="{notes}" data-healthy="{'1' if is_h else '0'}"
              style="width:100%;padding:7px;background:#f0fdf4;color:#1a7a4a;border:1px solid #86efac;border-radius:7px;font-size:12px;font-weight:600;cursor:pointer">
              View Full Details →
            </button>
          </div>
        </div>"""

    if not scan_cards:
        scan_cards = '<div style="grid-column:1/-1;text-align:center;padding:40px;color:#9ca3af"><div style="font-size:40px;margin-bottom:12px">📷</div><div style="font-size:14px;font-weight:600">No scans yet</div><div style="font-size:12px;margin-top:4px">Go to <a href="/scan" style="color:#2d9e6b">Scan Crop</a> to get started</div></div>'

    body = f"""
    <!-- Header -->
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;flex-wrap:wrap;gap:10px">
      <div>
        <div style="font-size:20px;font-weight:800;color:#1a1a1a">Reports & Scan History</div>
        <div style="font-size:13px;color:#9ca3af">All your crop scans, images, and diagnosis records</div>
      </div>
      <div style="display:flex;gap:8px">
        <button class="btn btn-secondary btn-sm" onclick="window.print()">🖨️ Print</button>
        <button class="btn btn-primary btn-sm" onclick="exportReport()">⬇️ Export CSV</button>
      </div>
    </div>

    <!-- Summary stats -->
    <div class="grid-4" style="margin-bottom:20px">
      <div class="stat-card"><div class="stat-icon-box blue">🔍</div><div class="stat-value">{total}</div><div class="stat-label">Total Scans</div><div class="stat-delta up">All time</div></div>
      <div class="stat-card"><div class="stat-icon-box green">✅</div><div class="stat-value">{healthy}</div><div class="stat-label">Healthy Crops</div><div class="stat-delta up">↑ {round(healthy/max(total,1)*100)}% of scans</div></div>
      <div class="stat-card"><div class="stat-icon-box red">🦠</div><div class="stat-value">{diseased}</div><div class="stat-label">Diseases Found</div><div class="stat-delta {'down' if diseased>0 else 'up'}">{'⚠️ Needs attention' if diseased>0 else '✅ All clear'}</div></div>
      <div class="stat-card"><div class="stat-icon-box purple">🎯</div><div class="stat-value">{avg_conf}%</div><div class="stat-label">Avg Confidence</div><div class="stat-delta up">AI accuracy</div></div>
    </div>

    <!-- Charts row -->
    <div class="grid-2" style="margin-bottom:20px">
      <div class="card">
        <div style="font-size:13px;font-weight:700;color:#1a1a1a;margin-bottom:14px">📈 Scan Activity (30 days)</div>
        <canvas id="timelineChart" height="120"></canvas>
      </div>
      <div class="card">
        <div style="font-size:13px;font-weight:700;color:#1a1a1a;margin-bottom:14px">🦠 Disease Distribution</div>
        <canvas id="diseaseDoughnut" height="120"></canvas>
      </div>
    </div>

    <!-- Filter bar -->
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;flex-wrap:wrap">
      <div style="font-size:14px;font-weight:700;color:#1a1a1a;flex:1">📷 Scan Image Gallery <span style="font-size:12px;color:#9ca3af;font-weight:400">({min(total,50)} of {total} shown)</span></div>
      <select id="filterSev" onchange="filterCards()" style="padding:7px 12px;border:1px solid #e5e7eb;border-radius:8px;font-size:12px;background:#fff">
        <option value="">All Severities</option>
        <option value="healthy">✅ Healthy</option>
        <option value="High">🔴 High</option>
        <option value="Moderate">🟡 Moderate</option>
        <option value="Low">🟢 Low</option>
      </select>
      <input id="filterSearch" oninput="filterCards()" placeholder="🔍 Search crop or disease..." style="padding:7px 12px;border:1px solid #e5e7eb;border-radius:8px;font-size:12px;width:200px">
    </div>

    <!-- Image gallery grid -->
    <div id="scanGallery" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px;margin-bottom:24px">
      {scan_cards}
    </div>

    <!-- Detail modal -->
    <div id="detailModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:600;align-items:center;justify-content:center;padding:16px" onclick="if(event.target===this)closeDetail()">
      <div style="background:#fff;border-radius:16px;width:100%;max-width:560px;max-height:90vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,.25)">
        <div style="display:flex;justify-content:space-between;align-items:center;padding:18px 20px;border-bottom:1px solid #e5e7eb;position:sticky;top:0;background:#fff;z-index:1">
          <div style="font-size:15px;font-weight:800;color:#1a1a1a" id="modalTitle">Scan Details</div>
          <button onclick="closeDetail()" style="width:28px;height:28px;border-radius:50%;border:none;background:#f3f4f6;cursor:pointer;font-size:14px">✕</button>
        </div>
        <div id="modalBody" style="padding:20px"></div>
      </div>
    </div>

    <script>
    window._diseaseData = {json.dumps(dc)};
    window._timelineData = {json.dumps(tl)};
    window._donutData = {json.dumps(dc)};

    function showDetail(btn) {{
      const d = btn.dataset;
      const isH = d.healthy === '1';
      const sc = {{'High':'#ef4444','Critical':'#dc2626','Moderate':'#f59e0b','Low':'#2d9e6b','None':'#2d9e6b'}}[d.sev] || '#9ca3af';
      document.getElementById('modalTitle').textContent = d.crop + ' — ' + d.disease.split(' — ').pop();
      document.getElementById('modalBody').innerHTML = `
        ${{d.img ? `<img src="/uploads/${{d.img}}" style="width:100%;max-height:300px;object-fit:contain;background:#f9fafb;border-radius:10px;margin-bottom:16px" onerror="this.style.display='none'">` : ''}}
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px">
          <div style="background:#f9fafb;border-radius:8px;padding:12px;text-align:center">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#9ca3af;margin-bottom:4px">Crop</div>
            <div style="font-size:16px;font-weight:800;color:#1a1a1a">${{d.crop}}</div>
          </div>
          <div style="background:${{isH?'#f0fdf4':'#fff1f2'}};border-radius:8px;padding:12px;text-align:center">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#9ca3af;margin-bottom:4px">Status</div>
            <div style="font-size:15px;font-weight:800;color:${{isH?'#15803d':'#dc2626'}}">${{isH?'✅ Healthy':'❌ Affected'}}</div>
          </div>
          <div style="background:#f9fafb;border-radius:8px;padding:12px;text-align:center">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#9ca3af;margin-bottom:4px">Severity</div>
            <div style="font-size:15px;font-weight:800;color:${{sc}}">${{d.sev}}</div>
          </div>
          <div style="background:#f9fafb;border-radius:8px;padding:12px;text-align:center">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#9ca3af;margin-bottom:4px">Confidence</div>
            <div style="font-size:15px;font-weight:800;color:#1a1a1a">${{d.conf}}%</div>
          </div>
        </div>
        <div style="font-size:12px;color:#9ca3af;margin-bottom:14px">🕐 ${{d.date}}${{d.notes?' · 📝 '+d.notes:''}}</div>
        ${{d.cause?`<div style="background:#fff7ed;border-radius:8px;padding:12px;margin-bottom:10px;border-left:3px solid #f59e0b"><div style="font-size:11px;font-weight:700;text-transform:uppercase;color:#d97706;margin-bottom:5px">🤔 Cause</div><div style="font-size:13px;color:#374151">${{d.cause}}</div></div>`:''}}
        ${{d.solution?`<div style="background:#f0fdf4;border-radius:8px;padding:12px;margin-bottom:10px;border-left:3px solid #2d9e6b"><div style="font-size:11px;font-weight:700;text-transform:uppercase;color:#15803d;margin-bottom:5px">💊 Solution</div><div style="font-size:13px;color:#374151">${{d.solution}}</div></div>`:''}}
        ${{d.prevention?`<div style="background:#f0f7ff;border-radius:8px;padding:12px;margin-bottom:10px;border-left:3px solid #3b82f6"><div style="font-size:11px;font-weight:700;text-transform:uppercase;color:#1d4ed8;margin-bottom:5px">🛡️ Prevention</div><div style="font-size:13px;color:#374151">${{d.prevention}}</div></div>`:''}}
        ${{d.chem?`<div style="background:#fef3c7;border-radius:8px;padding:12px;margin-bottom:10px;border-left:3px solid #d97706"><div style="font-size:11px;font-weight:700;text-transform:uppercase;color:#d97706;margin-bottom:5px">🧪 Chemical Treatment</div><div style="font-size:13px;color:#374151">${{d.chem}}</div></div>`:''}}
        ${{d.org?`<div style="background:#f0fdf4;border-radius:8px;padding:12px;border-left:3px solid #2d9e6b"><div style="font-size:11px;font-weight:700;text-transform:uppercase;color:#15803d;margin-bottom:5px">🌿 Organic Treatment</div><div style="font-size:13px;color:#374151">${{d.org}}</div></div>`:''}}
        <div style="display:flex;gap:8px;margin-top:16px">
          <a href="/insights?disease=${{encodeURIComponent(d.disease)}}" class="btn btn-primary btn-sm" style="flex:1;justify-content:center">🧠 Deep Analysis</a>
          <a href="/expert" class="btn btn-secondary btn-sm" style="flex:1;justify-content:center">🤝 Ask Expert</a>
        </div>`;
      document.getElementById('detailModal').style.display = 'flex';
    }}

    function closeDetail() {{
      document.getElementById('detailModal').style.display = 'none';
    }}

    function filterCards() {{
      const sev = document.getElementById('filterSev').value.toLowerCase();
      const q = document.getElementById('filterSearch').value.toLowerCase();
      document.querySelectorAll('#scanGallery > div').forEach(card => {{
        const btn = card.querySelector('button[data-crop]');
        if (!btn) return;
        const crop = (btn.dataset.crop||'').toLowerCase();
        const disease = (btn.dataset.disease||'').toLowerCase();
        const cardSev = (btn.dataset.sev||'').toLowerCase();
        const isH = btn.dataset.healthy === '1';
        const sevMatch = !sev || (sev==='healthy' ? isH : cardSev===sev.toLowerCase());
        const qMatch = !q || crop.includes(q) || disease.includes(q);
        card.style.display = (sevMatch && qMatch) ? '' : 'none';
      }});
    }}

    function exportReport() {{
      const rows = [['Date','Crop','Disease','Severity','Confidence','Notes']];
      document.querySelectorAll('#scanGallery button[data-crop]').forEach(btn => {{
        rows.push([btn.dataset.date, btn.dataset.crop, btn.dataset.disease, btn.dataset.sev, btn.dataset.conf+'%', btn.dataset.notes]);
      }});
      const csv = rows.map(r => r.map(v => '"'+String(v).replace(/"/g,'""')+'"').join(',')).join('\\n');
      const a = document.createElement('a');
      a.href = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv);
      a.download = 'crop_diagnosis_report.csv';
      a.click();
    }}
    // Register as override so app.js exportReport() uses this
    window._exportReportOverride = exportReport;
    </script>"""
    return HTMLResponse(shell("Reports & History", "All scan images, diagnoses, and treatment records", body, "reports", user, lang))


# ══ 🔔 ALERTS ═════════════════════════════════════════════════════════════════

@app.get("/alerts", response_class=HTMLResponse)
def alerts_page(request: Request, lang: str = "en"):
    user = cu(request)
    if not user: return RedirectResponse("/login")
    uid = user.get("id")
    if DB_AVAILABLE:
        mark_alerts_read(uid)
        alerts_list = get_alerts(uid)
    else:
        alerts_list = []

    # Generate real alerts from recent scan history
    recent_dets = _get_scans(uid, 50)
    auto_alerts = []
    for d in recent_dets:
        if "healthy" not in d.get("disease","").lower():
            sev = d.get("severity","")
            if sev in ("Critical","High","Severe"):
                auto_alerts.append({
                    "id": d.get("id", len(auto_alerts)+100),
                    "type": "critical", "icon": "🔴",
                    "title": f"{sev} Disease — {d.get('crop_name','')}",
                    "desc": f"{d.get('disease','').replace('___',' — ').replace('_',' ')} detected. Immediate treatment required.",
                    "time": str(d.get("detected_at",""))[:16],
                    "field": d.get("notes","") or "Scanned field",
                    "action": "View Treatment", "action_class": "btn-danger",
                    "priority": "High",
                })
            elif sev == "Moderate":
                auto_alerts.append({
                    "id": d.get("id", len(auto_alerts)+200),
                    "type": "warning", "icon": "🟡",
                    "title": f"Moderate Disease — {d.get('crop_name','')}",
                    "desc": f"{d.get('disease','').replace('___',' — ').replace('_',' ')} detected. Treat within 2–3 days.",
                    "time": str(d.get("detected_at",""))[:16],
                    "field": d.get("notes","") or "Scanned field",
                    "action": "View Details", "action_class": "btn-orange",
                    "priority": "Medium",
                })

    # Merge DB alerts + auto-generated alerts
    active_alerts = alerts_list if alerts_list else (auto_alerts or [
        {"id":1,"type":"critical","icon":"🔴","title":"Late Blight Detected — Potato","desc":"Critical severity. Spreads rapidly in wet conditions. Apply copper fungicide immediately.","time":"2 hours ago","field":"North Field","action":"Apply Treatment","action_class":"btn-danger","priority":"High"},
        {"id":2,"type":"warning","icon":"🟡","title":"Apple Scab — Moderate Risk","desc":"Moderate severity detected. Treat within 2–3 days to prevent spread.","time":"5 hours ago","field":"Orchard A","action":"Schedule Treatment","action_class":"btn-orange","priority":"Medium"},
        {"id":3,"type":"info","icon":"🔵","title":"Healthy Crop Confirmed","desc":"Your Corn crop scan shows no disease. Continue regular monitoring.","time":"1 day ago","field":"Field B","action":"View Report","action_class":"btn-blue","priority":"Low"},
    ])

    critical_count = sum(1 for a in active_alerts if a.get("type")=="critical" or a.get("priority")=="High")
    warning_count  = sum(1 for a in active_alerts if a.get("type")=="warning"  or a.get("priority")=="Medium")
    info_count     = sum(1 for a in active_alerts if a.get("type")=="info"     or a.get("priority")=="Low")

    def priority_badge(a):
        p = a.get("priority", "Medium")
        colors = {"High":"#ef4444","Medium":"#f59e0b","Low":"#3b82f6"}
        return f'<span style="background:{colors.get(p,"#9ca3af")}22;color:{colors.get(p,"#9ca3af")};border:1px solid {colors.get(p,"#9ca3af")}44;padding:1px 8px;border-radius:20px;font-size:10px;font-weight:700">{p}</span>'

    active_html = "".join(f"""<div class="alert-card {'critical' if a.get('type')=='critical' else 'warning' if a.get('type')=='warning' else 'info'}" id="alert-{a.get('id',i)}" style="margin-bottom:10px">
      <span class="alert-icon">{a.get('icon','⚠️')}</span>
      <div class="alert-body">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:3px">
          <div class="alert-title">{a.get('title', a.get('message','Alert'))}</div>
          {priority_badge(a)}
        </div>
        <div class="alert-desc">{a.get('desc', a.get('message',''))}</div>
        <div class="alert-meta">
          <span>🕐 {a.get('time', str(a.get('created_at',''))[:16])}</span>
          <span>📍 {a.get('field','')}</span>
        </div>
        <div class="alert-actions">
          <button class="btn {a.get('action_class','btn-primary')} btn-sm" onclick="markRead({a.get('id',i)})">{a.get('action','View')}</button>
          <a href="/scan" class="btn btn-ghost btn-sm">📷 Rescan</a>
        </div>
      </div>
    </div>""" for i, a in enumerate(active_alerts))

    body = f"""
    <!-- Priority summary -->
    <div class="grid-3" style="margin-bottom:20px">
      <div class="stat-card" style="border-left:4px solid #ef4444">
        <div class="stat-icon-box red">🔴</div>
        <div class="stat-value">{critical_count}</div>
        <div class="stat-label">High Priority</div>
        <div class="stat-delta down">Immediate action needed</div>
      </div>
      <div class="stat-card" style="border-left:4px solid #f59e0b">
        <div class="stat-icon-box orange">🟡</div>
        <div class="stat-value">{warning_count}</div>
        <div class="stat-label">Medium Priority</div>
        <div class="stat-delta neutral">Act within 2–3 days</div>
      </div>
      <div class="stat-card" style="border-left:4px solid #3b82f6">
        <div class="stat-icon-box blue">🔵</div>
        <div class="stat-value">{info_count}</div>
        <div class="stat-label">Low Priority</div>
        <div class="stat-delta up">Monitor only</div>
      </div>
    </div>

    <!-- Active alerts -->
    <div class="card">
      <div class="card-header">
        <div><div class="card-title">🔔 Active Alerts</div><div class="card-subtitle">{len(active_alerts)} alert{'s' if len(active_alerts)!=1 else ''} requiring attention</div></div>
        <button class="btn btn-ghost btn-sm" onclick="fetch('/api/alerts/read-all',{{method:'POST'}}).then(()=>location.reload())">✓ Mark all read</button>
      </div>
      {active_html or '<div class="empty-state"><div class="empty-state-icon">✅</div><div class="empty-state-title">No active alerts</div><p class="text-muted">Your farm is looking great! Scan crops regularly to stay informed.</p></div>'}
    </div>

    <!-- What to do guide -->
    <div class="card" style="background:linear-gradient(135deg,#f0fdf4,#ecfdf5);border:1px solid #86efac">
      <div style="font-size:13px;font-weight:700;color:#15803d;margin-bottom:12px">💡 How to Respond to Alerts</div>
      <div style="display:flex;flex-direction:column;gap:8px">
        {"".join(f'<div style="display:flex;align-items:flex-start;gap:10px;background:#fff;border-radius:8px;padding:10px 12px"><span style="font-size:16px;flex-shrink:0">{ic}</span><div><div style="font-size:13px;font-weight:600;color:#1a1a1a">{title}</div><div style="font-size:12px;color:#6b7280">{desc}</div></div></div>' for ic, title, desc in [
          ("🔴", "High Priority — Act Immediately", "Apply treatment within 24 hours. Disease can spread rapidly."),
          ("🟡", "Medium Priority — Act Soon", "Treat within 2–3 days. Monitor daily for worsening."),
          ("🔵", "Low Priority — Monitor", "Keep watching. No immediate action needed."),
          ("📷", "Rescan After Treatment", "Scan the same crop 7 days after treatment to confirm recovery."),
        ])}
      </div>
    </div>"""
    return HTMLResponse(shell("Alerts", "Disease warnings, weather risks, and urgent action notifications", body, "alerts", user, lang, len([a for a in active_alerts if a.get("type")=="critical"])))

# ══ 🛒 MARKET ═════════════════════════════════════════════════════════════════

@app.get("/market", response_class=HTMLResponse)
def market_page(request: Request, lang: str = "en"):
    user = cu(request)
    if not user: return RedirectResponse("/login")
    prices = get_all_prices()
    uid    = user.get("id")

    # ── Helpers ───────────────────────────────────────────────────────────────
    def trend_icon(t):
        return "📈" if t == "Rising" else "📉" if t == "Falling" else "➡️"
    def trend_cls(t):
        return "badge-green" if t == "Rising" else "badge-red" if t == "Falling" else "badge-gray"
    def crop_icon(c):
        return {"Maize":"🌽","Corn":"🌽","Rice":"🌾","Wheat":"🌾","Potato":"🥔",
                "Tomato":"🍅","Soybean":"🫘","Apple":"🍎","Grape":"🍇",
                "Orange":"🍊","Pepper":"🌶️","Strawberry":"🍓","Cherry":"🍒",
                "Peach":"🍑","Blueberry":"🫐","Squash":"🎃","Raspberry":"🍇"
               }.get(c, "🌱")

    # ── Find crops the user has actually scanned ──────────────────────────────
    scanned_crops = set()
    recent_scans  = _get_scans(uid, 50)
    for s in recent_scans:
        cn = s.get("crop_name", "")
        if cn:
            scanned_crops.add(cn.split()[0])   # e.g. "Corn (Maize)" → "Corn"

    rising  = sum(1 for p in prices if p["trend"] == "Rising")
    falling = sum(1 for p in prices if p["trend"] == "Falling")
    best    = prices[0] if prices else {}

    # ── Personalized recommendation from scanned crops ────────────────────────
    matched = [p for p in prices if any(sc.lower() in p["crop"].lower() for sc in scanned_crops)]
    if matched:
        sell_these  = [p for p in matched if p["trend"] == "Rising"]
        hold_these  = [p for p in matched if p["trend"] != "Rising"]
        rec_body = ""
        if sell_these:
            rec_body += f'<div style="margin-bottom:8px">✅ <strong>Sell now:</strong> {", ".join(p["crop"] for p in sell_these)} — trending up</div>'
        if hold_these:
            rec_body += f'<div>⏳ <strong>Hold for now:</strong> {", ".join(p["crop"] for p in hold_these)} — wait 2–4 weeks</div>'
    else:
        rec_body = "Scan your crops first to get personalized selling recommendations based on your actual harvest."

    # ── Build all price rows (all crops, filterable) ──────────────────────────
    all_rows = ""
    for p in prices:
        scanned_tag = '<span style="background:#dbeafe;color:#1d4ed8;font-size:10px;font-weight:600;padding:1px 7px;border-radius:10px;margin-left:6px">Scanned</span>' \
                      if any(sc.lower() in p["crop"].lower() for sc in scanned_crops) else ""
        all_rows += f'''<div class="crop-price-row" data-crop="{p["crop"].lower()}">
          <div class="crop-price-icon">{crop_icon(p["crop"])}</div>
          <div style="flex:1">
            <div style="display:flex;align-items:center">
              <div class="crop-price-name">{p["crop"]}</div>{scanned_tag}
            </div>
            <div class="crop-price-market">📍 {p["market"]}</div>
          </div>
          <div style="text-align:right">
            <div class="crop-price-val">{p["currency"]} {p["price_per_kg"]:,}/kg</div>
            <span class="badge {trend_cls(p["trend"])}" style="margin-top:3px;display:inline-flex">
              {trend_icon(p["trend"])} {p["trend"]}
            </span>
          </div>
          <div style="margin-left:12px">
            <a href="{'monitor' if p['trend']!='Rising' else '/market/sell?crop='+p['crop']}" class="btn {'btn-primary' if p['trend']=='Rising' else 'btn-ghost'} btn-sm">
              {'Sell Now' if p['trend']=='Rising' else 'Monitor'}
            </a>
          </div>
        </div>'''

    # ── Market insights ───────────────────────────────────────────────────────
    insights = [
        {"icon":"📈","title":"Strong Selling Window",
         "desc":f"{rising} crop{'s' if rising!=1 else ''} trending up this week — ideal time to sell high-value produce.",
         "tag":"Bullish","tc":"badge-green","time":"Today"},
        {"icon":"⚖️","title":"Market Fluctuations",
         "desc":"Global supply changes affecting prices. Monitor weekly before making large sales.",
         "tag":"Neutral","tc":"badge-gray","time":"2 days ago"},
        {"icon":"📉","title":"Price Watch",
         "desc":f"{falling} crop{'s' if falling!=1 else ''} trending down. Consider holding stock or diversifying.",
         "tag":"Bearish","tc":"badge-red","time":"3 days ago"},
        {"icon":"🌧️","title":"Seasonal Advisory",
         "desc":"Rainy season approaching — store dry produce properly and plan harvest timing carefully.",
         "tag":"Advisory","tc":"badge-blue","time":"1 week ago"},
    ]
    insight_html = "".join(f'''<div class="market-insight-card">
      <div style="font-size:20px;flex-shrink:0">{ins["icon"]}</div>
      <div class="market-insight-body">
        <div class="market-insight-title">{ins["title"]}</div>
        <div class="market-insight-desc">{ins["desc"]}</div>
        <div style="margin-top:6px;font-size:11px;color:#9ca3af">{ins["time"]}</div>
      </div>
      <span class="badge {ins["tc"]}">{ins["tag"]}</span>
    </div>''' for ins in insights)

    body = f"""
    <!-- Header -->
    <div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:20px">
      <div>
        <div class="section-title">Market Prices</div>
        <div class="section-sub">Tanzanian market prices · Updated weekly</div>
      </div>
      <a href="/scan" class="btn btn-primary">📷 Scan Crop</a>
    </div>

    <!-- Top stat cards -->
    <div class="grid-3" style="margin-bottom:20px">
      <div class="market-hero">
        <div style="font-size:12px;opacity:.8;margin-bottom:4px">💰 Best Price Today</div>
        <div class="market-hero-price">{best.get('currency','TSh')} {best.get('price_per_kg',0):,}/kg</div>
        <div class="market-hero-label">{best.get('crop','')} · {best.get('market','')}</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon-box green">📈</div>
        <div class="stat-value">{rising}</div>
        <div class="stat-label">Crops Trending Up</div>
        <div class="stat-delta up">↑ Good selling opportunity</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon-box orange">📉</div>
        <div class="stat-value">{falling}</div>
        <div class="stat-label">Crops Trending Down</div>
        <div class="stat-delta down">↓ Hold or diversify</div>
      </div>
    </div>

    <div class="grid-2">
      <!-- Prices list with search -->
      <div class="card">
        <div class="card-header">
          <div class="card-title">🌾 Crop Prices</div>
          <span class="badge badge-green">TSh / kg</span>
        </div>

        <!-- Search bar -->
        <div style="margin-bottom:14px;position:relative">
          <span style="position:absolute;left:10px;top:50%;transform:translateY(-50%);color:#9ca3af;font-size:15px">🔍</span>
          <input id="cropSearch" class="form-input" style="padding-left:32px"
                 placeholder="Search crop name..."
                 oninput="filterCrops(this.value)">
        </div>

        <!-- Filter chips -->
        <div style="display:flex;gap:6px;margin-bottom:14px;flex-wrap:wrap">
          <button class="filter-chip active" onclick="setFilter('all',this)">All</button>
          <button class="filter-chip" onclick="setFilter('rising',this)">📈 Rising</button>
          <button class="filter-chip" onclick="setFilter('falling',this)">📉 Falling</button>
          <button class="filter-chip" onclick="setFilter('scanned',this)">✅ My Crops</button>
        </div>

        <div id="priceList">{all_rows}</div>
        <div id="noResults" style="display:none;text-align:center;padding:20px;color:#9ca3af;font-size:13px">
          No crops match your search
        </div>
      </div>

      <!-- Right column -->
      <div>
        <!-- Personalized recommendation -->
        <div class="card" style="background:linear-gradient(135deg,#f0fdf4,#dcfce7);border:1px solid #bbf7d0;margin-bottom:16px">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
            <span style="font-size:20px">💡</span>
            <div class="card-title">Your Selling Recommendation</div>
          </div>
          <div style="font-size:13px;color:#374151;line-height:1.6">{rec_body}</div>
          {f'<div style="margin-top:10px;font-size:11px;color:#6b7280">Based on {len(scanned_crops)} crop(s) you have scanned</div>' if scanned_crops else ''}
        </div>

        <!-- Market insights -->
        <div class="card">
          <div class="card-header"><div class="card-title">📊 Market Insights</div></div>
          {insight_html}
        </div>

        <!-- Price guide -->
        <div style="background:linear-gradient(135deg,#1e293b,#334155);border-radius:12px;padding:20px;margin-top:16px;color:#fff">
          <div style="font-size:14px;font-weight:700;margin-bottom:10px">📌 Selling Tips</div>
          {"".join(f'<div style="display:flex;gap:8px;margin-bottom:8px;font-size:12px;opacity:.9"><span>{"✅" if i==0 else "⚡" if i==1 else "📅" if i==2 else "🤝"}</span><span>{tip}</span></div>' for i,tip in enumerate([
            "Sell Rising crops within 1–2 weeks for maximum return",
            "Avoid selling Falling crops — wait for market recovery",
            "Early morning market hours get the best prices",
            "Group sales with neighboring farmers for better negotiation",
          ]))}
        </div>
      </div>
    </div>

    <style>
    .filter-chip{{padding:5px 12px;border-radius:20px;border:1px solid #e5e7eb;background:#fff;
      font-size:12px;font-weight:500;color:#6b7280;cursor:pointer;transition:all .15s}}
    .filter-chip.active{{background:#2d9e6b;color:#fff;border-color:#2d9e6b}}
    .filter-chip:hover:not(.active){{border-color:#2d9e6b;color:#2d9e6b}}
    </style>
    <script>
    var _filter = 'all';
    function filterCrops(q) {{
      q = q.toLowerCase();
      var rows = document.querySelectorAll('.crop-price-row');
      var shown = 0;
      rows.forEach(function(r) {{
        var crop = r.getAttribute('data-crop') || '';
        var matchSearch = !q || crop.includes(q);
        var matchFilter = _filter === 'all' ||
          (_filter === 'rising'  && r.innerHTML.includes('Rising')) ||
          (_filter === 'falling' && r.innerHTML.includes('Falling')) ||
          (_filter === 'scanned' && r.innerHTML.includes('Scanned'));
        var show = matchSearch && matchFilter;
        r.style.display = show ? '' : 'none';
        if (show) shown++;
      }});
      document.getElementById('noResults').style.display = shown === 0 ? 'block' : 'none';
    }}
    function setFilter(f, btn) {{
      _filter = f;
      document.querySelectorAll('.filter-chip').forEach(function(b){{b.classList.remove('active')}});
      btn.classList.add('active');
      filterCrops(document.getElementById('cropSearch').value);
    }}
    </script>"""
    return HTMLResponse(shell("Market Prices", "Current crop prices and market trends", body, "market", user, lang))


# ══ 🛒 SELL NOW — Step 1: Selling Guide ══════════════════════════════════════

@app.get("/market/sell", response_class=HTMLResponse)
def market_sell_page(request: Request, crop: str = "", lang: str = "en"):
    user = cu(request)
    if not user: return RedirectResponse("/login")
    if not crop: return RedirectResponse("/market")

    from modules.market import get_market_info, get_market_locations, get_checklist, _MARKET_LOCATIONS
    import json as _mj
    info      = get_market_info(crop)
    locations = get_market_locations(info["market"])
    checklist = get_checklist(crop)
    price     = info["price_per_kg"]
    trend     = info["trend"]
    market    = info["market"]
    icon      = info.get("icon", "🌿")
    trend_color = "#10b981" if trend == "Rising" else "#ef4444" if trend == "Falling" else "#6b7280"
    trend_icon  = "📈" if trend == "Rising" else "📉" if trend == "Falling" else "➡️"
    # Pass market GPS data to JS — current locations + all regions for fallback
    _json_markets = _mj.dumps([
        {"name": loc["name"], "lat": loc.get("lat"), "lng": loc.get("lng")}
        for loc in locations
    ])
    _json_all_markets = _mj.dumps({
        region: [{"name": m["name"], "lat": m.get("lat"), "lng": m.get("lng"), "hours": m.get("hours","")}
                 for m in mlist]
        for region, mlist in _MARKET_LOCATIONS.items()
        if region != "Local"
    })

    locations_html = ""
    for loc in locations:
        lat  = loc.get("lat")
        lng  = loc.get("lng")
        name = loc["name"]
        city = loc["city"]
        hrs  = loc.get("hours", "")
        if lat and lng:
            maps_url    = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
            dir_url     = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&travelmode=driving"
            coords_txt  = f"{lat:.4f}, {lng:.4f}"
            map_btn     = (f'<div style="display:flex;gap:6px;margin-top:8px">'
                           f'<a href="{maps_url}" target="_blank" class="btn btn-secondary btn-sm">🗺️ View Map</a>'
                           f'<a href="{dir_url}"  target="_blank" class="btn btn-primary btn-sm">🧭 Get Directions</a>'
                           f'</div>')
            gps_badge   = (f'<span style="font-size:10px;color:#9ca3af;font-family:monospace">'
                           f'📍 {coords_txt}</span>')
        else:
            map_btn   = ""
            gps_badge = ""

        locations_html += f'''<div style="background:#f9fafb;border-radius:10px;padding:14px;margin-bottom:10px;border:1px solid #e5e7eb">
          <div style="display:flex;align-items:flex-start;justify-content:space-between">
            <div>
              <div style="font-size:13px;font-weight:700;color:#1a1a1a">📍 {name}</div>
              <div style="font-size:12px;color:#6b7280;margin-top:2px">🏙️ {city} &nbsp;·&nbsp; ⏰ {hrs}</div>
              <div style="margin-top:4px">{gps_badge}</div>
            </div>
          </div>
          {map_btn}
        </div>'''
    checklist_html = "".join(
        f'<label style="display:flex;align-items:flex-start;gap:10px;padding:8px 0;border-bottom:1px solid #f9fafb;cursor:pointer">'
        f'<input type="checkbox" style="margin-top:2px;accent-color:#2d9e6b;flex-shrink:0">'
        f'<span style="font-size:13px;color:#374151">{item}</span></label>'
        for item in checklist
    )

    body = f"""
    <!-- Back link -->
    <a href="/market" class="back-link">← Back to Market</a>

    <!-- Hero card -->
    <div style="background:linear-gradient(135deg,#1a7a4a,#2d9e6b);border-radius:16px;padding:28px;color:#fff;margin-bottom:20px">
      <div style="display:flex;align-items:center;gap:16px">
        <div style="font-size:56px">{icon}</div>
        <div>
          <div style="font-size:22px;font-weight:800;margin-bottom:4px">{crop} — Selling Guide</div>
          <div style="display:flex;align-items:center;gap:12px;font-size:14px;opacity:.9">
            <span>💰 TSh {price:,}/kg</span>
            <span style="background:rgba(255,255,255,.2);padding:2px 10px;border-radius:20px;color:#fff;font-weight:600">{trend_icon} {trend}</span>
            <span>📍 Best at {market}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="grid-2">
      <!-- Left: Calculator + Checklist -->
      <div>
        <!-- Earnings calculator -->
        <div class="card" style="margin-bottom:16px">
          <div class="card-title" style="margin-bottom:16px">💰 Earnings Calculator</div>
          <div class="form-group">
            <label class="form-label">How many kg do you have to sell?</label>
            <input class="form-input" id="kgInput" type="number" min="1" placeholder="e.g. 50"
                   oninput="calcEarnings({price})">
          </div>
          <div id="earningsResult" style="display:none;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:16px;margin-top:4px">
            <div style="font-size:12px;color:#6b7280;margin-bottom:4px">Estimated earnings</div>
            <div id="earningsAmt" style="font-size:28px;font-weight:800;color:#1a7a4a"></div>
            <div id="earningsBreak" style="font-size:12px;color:#6b7280;margin-top:4px"></div>
          </div>
          <button id="proceedBtn" type="button" class="btn btn-primary btn-full"
             style="margin-top:16px;height:48px;font-size:15px;font-weight:700;justify-content:center;display:none"
             onclick="goToPayment()">
            Proceed to Payment →
          </button>
        </div>

        <!-- Selling checklist -->
        <div class="card">
          <div class="card-title" style="margin-bottom:12px">📋 Pre-Sale Checklist</div>
          <div style="font-size:12px;color:#6b7280;margin-bottom:10px">Complete these steps before going to market</div>
          {checklist_html}
          <div id="checkProgress" style="margin-top:14px;font-size:12px;color:#9ca3af">0 of {len(checklist)} completed</div>
        </div>
      </div>

      <!-- Right: Markets + Tips -->
      <div>
        <!-- Where to sell -->
        <div class="card" style="margin-bottom:16px">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
            <div class="card-title">📍 Where to Sell {crop}</div>
            <button class="btn btn-secondary btn-sm" onclick="findNearestMarket()" id="locBtn">
              📡 Use My Location
            </button>
          </div>
          <div id="nearestResult" style="display:none;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:10px 12px;margin-bottom:12px;font-size:12px;color:#1a7a4a"></div>
          {locations_html}
        </div>

        <!-- Price info -->
        <div class="card" style="margin-bottom:16px">
          <div class="card-title" style="margin-bottom:12px">📊 Price Details</div>
          {"".join(f'<div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f3f4f6"><span style="font-size:13px;color:#6b7280">{k}</span><span style="font-size:13px;font-weight:600;color:#1a1a1a">{v}</span></div>' for k,v in [
            ("Current Price", f"TSh {price:,}/kg"),
            ("Market Trend",  f"{trend_icon} {trend}"),
            ("Best Market",   market),
            ("Currency",      "Tanzanian Shilling (TSh)"),
            ("Price Valid",   "This week"),
          ])}
        </div>

        <!-- Warning -->
        <div class="alert-card warning">
          <span class="alert-icon">⚠️</span>
          <div class="alert-body">
            <div class="alert-title">Price Disclaimer</div>
            <div class="alert-desc">Market prices fluctuate daily. Confirm the current price with market traders before selling. These prices are indicative only.</div>
          </div>
        </div>
      </div>
    </div>

    <script>
    function calcEarnings(pricePerKg) {{
      var kg = parseFloat(document.getElementById('kgInput').value) || 0;
      var result = document.getElementById('earningsResult');
      var btn    = document.getElementById('proceedBtn');
      if (kg > 0) {{
        var total = kg * pricePerKg;
        document.getElementById('earningsAmt').textContent = 'TSh ' + total.toLocaleString();
        document.getElementById('earningsBreak').textContent = kg + ' kg × TSh ' + pricePerKg.toLocaleString() + '/kg';
        result.style.display = 'block';
        btn.style.display = 'flex';
      }} else {{
        result.style.display = 'none';
        btn.style.display = 'none';
      }}
    }}
    function goToPayment() {{
      var kg = document.getElementById('kgInput').value;
      if (!kg || kg <= 0) {{ alert('Please enter a quantity in kg'); return; }}
      window.location.href = '/market/pay?crop={crop}&kg=' + kg + '&price={price}';
    }}

    // ── GPS: find nearest market ──────────────────────────────────────────────
    var _markets = {_json_markets};
    function findNearestMarket() {{
      var btn = document.getElementById('locBtn');
      var res = document.getElementById('nearestResult');
      if (!navigator.geolocation) {{
        res.style.display = 'block';
        res.style.background = '#fff1f2'; res.style.borderColor = '#fca5a5'; res.style.color = '#dc2626';
        res.textContent = '❌ GPS not available in your browser';
        return;
      }}
      btn.textContent = '⏳ Locating...';
      btn.disabled = true;
      navigator.geolocation.getCurrentPosition(function(pos) {{
        var userLat = pos.coords.latitude;
        var userLng = pos.coords.longitude;
        // find closest market
        var best = null, bestDist = Infinity;
        _markets.forEach(function(m) {{
          if (m.lat === null) return;
          var d = Math.sqrt(Math.pow(userLat - m.lat, 2) + Math.pow(userLng - m.lng, 2));
          if (d < bestDist) {{ bestDist = d; best = m; }}
        }});
        btn.textContent = '📡 Use My Location';
        btn.disabled = false;
        if (best) {{
          var km = Math.round(bestDist * 111);
          res.style.display = 'block';
          res.innerHTML = '✅ <strong>Nearest market:</strong> ' + best.name + ' (' + km + ' km away) &nbsp;'
            + '<a href="https://www.google.com/maps/dir/?api=1&origin=' + userLat + ',' + userLng
            + '&destination=' + best.lat + ',' + best.lng + '&travelmode=driving" target="_blank" '
            + 'style="background:#2d9e6b;color:#fff;padding:3px 10px;border-radius:6px;font-size:11px;text-decoration:none;font-weight:600">🧭 Directions</a>';
        }} else {{
          res.style.display = 'block';
          res.textContent = '⚠️ Could not find nearest market. Use the list below.';
        }}
      }}, function(err) {{
        btn.textContent = '📡 Use My Location';
        btn.disabled = false;
        res.style.display = 'block';
        res.style.background = '#fffbeb';
        res.style.borderColor = '#fde68a';
        res.style.color = '#92400e';
        res.innerHTML = '⚠️ GPS access denied. <strong>Select your region manually:</strong><br><br>'
          + '<select onchange="showManualMarkets(this.value)" class="form-input" style="margin-top:6px;max-width:280px">'
          + '<option value="">— Choose your region —</option>'
          + '<option value="Dar es Salaam">Dar es Salaam</option>'
          + '<option value="Arusha">Arusha</option>'
          + '<option value="Mwanza">Mwanza</option>'
          + '<option value="Dodoma">Dodoma</option>'
          + '<option value="Mbeya">Mbeya</option>'
          + '<option value="Morogoro">Morogoro</option>'
          + '<option value="Moshi">Moshi</option>'
          + '</select>'
          + '<div id="manualMarketList" style="margin-top:10px"></div>';
      }});
    }}

    // ── Manual market selector (GPS fallback) ────────────────────────────────
    var _allMarkets = {_json_all_markets};
    function showManualMarkets(region) {{
      var list = document.getElementById('manualMarketList');
      if (!region) {{ list.innerHTML = ''; return; }}
      var markets = _allMarkets[region] || [];
      if (!markets.length) {{ list.innerHTML = '<div style="color:#9ca3af;font-size:12px">No markets found for this region.</div>'; return; }}
      var html = '';
      markets.forEach(function(m) {{
        var dirLink = m.lat
          ? '<a href="https://www.google.com/maps/dir/?api=1&destination=' + m.lat + ',' + m.lng + '&travelmode=driving" target="_blank" '
            + 'style="background:#2d9e6b;color:#fff;padding:3px 10px;border-radius:6px;font-size:11px;text-decoration:none;font-weight:600;margin-left:8px">🧭 Directions</a>'
          : '';
        var mapLink = m.lat
          ? '<a href="https://www.google.com/maps/search/?api=1&query=' + m.lat + ',' + m.lng + '" target="_blank" '
            + 'style="background:#fff;border:1px solid #2d9e6b;color:#2d9e6b;padding:3px 10px;border-radius:6px;font-size:11px;text-decoration:none;font-weight:600">🗺️ Map</a>'
          : '';
        html += '<div style="background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:10px 12px;margin-bottom:8px">'
          + '<div style="font-size:13px;font-weight:700;color:#1a1a1a">📍 ' + m.name + '</div>'
          + '<div style="font-size:11px;color:#9ca3af;margin-top:2px">⏰ ' + (m.hours || '') + '</div>'
          + '<div style="margin-top:8px;display:flex;gap:6px">' + mapLink + dirLink + '</div>'
          + '</div>';
      }});
      list.innerHTML = html;
    }}

    // Checklist progress
    document.querySelectorAll('input[type=checkbox]').forEach(function(cb) {{
      cb.addEventListener('change', function() {{
        var checked = document.querySelectorAll('input[type=checkbox]:checked').length;
        var total   = document.querySelectorAll('input[type=checkbox]').length;
        document.getElementById('checkProgress').textContent = checked + ' of ' + total + ' completed';
        document.getElementById('checkProgress').style.color = checked === total ? '#10b981' : '#9ca3af';
      }});
    }});
    </script>"""
    return HTMLResponse(shell(f"Sell {crop}", f"Selling guide and earnings calculator for {crop}", body, "market", user, lang))


# ══ 🛒 SELL NOW — Step 2: Payment ════════════════════════════════════════════

@app.get("/market/pay", response_class=HTMLResponse)
def market_pay_page(request: Request, crop: str = "", kg: str = "0",
                    price: str = "0", lang: str = "en"):
    user = cu(request)
    if not user: return RedirectResponse("/login")
    if not crop: return RedirectResponse("/market")

    try:
        kg_val    = float(kg)
        price_val = int(price)
        total     = int(kg_val * price_val)
    except Exception:
        return RedirectResponse(f"/market/sell?crop={crop}")

    from modules.market import get_market_info, _ICONS
    info  = get_market_info(crop)
    icon  = info.get("icon", "🌿")

    payment_methods = [
        ("mpesa",   "📱 M-Pesa",      "Vodacom M-Pesa mobile money"),
        ("tigo",    "📱 Tigo Pesa",   "Tigo mobile money"),
        ("airtel",  "📱 Airtel Money","Airtel mobile money"),
        ("bank",    "🏦 Bank Transfer","Direct bank transfer"),
    ]
    methods_html = "".join(f'''
      <label id="lbl-{mid}" class="pay-method-label" style="display:flex;align-items:center;gap:12px;padding:14px 16px;border:2px solid #e5e7eb;border-radius:10px;cursor:pointer;margin-bottom:8px;transition:border-color .15s"
             onclick="selectMethod('{mid}')">
        <input type="radio" name="method" value="{mid}" style="accent-color:#2d9e6b;width:16px;height:16px">
        <div>
          <div style="font-size:14px;font-weight:600;color:#1a1a1a">{mlbl}</div>
          <div style="font-size:12px;color:#9ca3af">{mdesc}</div>
        </div>
      </label>''' for mid, mlbl, mdesc in payment_methods)

    body = f"""
    <a href="/market/sell?crop={crop}&lang={lang}" class="back-link">← Back to Selling Guide</a>

    <div style="max-width:600px;margin:0 auto">
      <!-- Order summary -->
      <div class="card" style="margin-bottom:16px">
        <div class="card-title" style="margin-bottom:16px">📦 Order Summary</div>
        <div style="background:#f9fafb;border-radius:10px;padding:16px">
          {"".join(f'<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #e5e7eb"><span style="font-size:13px;color:#6b7280">{k}</span><span style="font-size:13px;font-weight:600;color:#1a1a1a">{v}</span></div>' for k,v in [
            ("Crop", f"{icon} {crop}"),
            ("Quantity", f"{kg_val:g} kg"),
            ("Price per kg", f"TSh {price_val:,}"),
          ])}
          <div style="display:flex;justify-content:space-between;padding:12px 0 0">
            <span style="font-size:15px;font-weight:700;color:#1a1a1a">Total</span>
            <span style="font-size:20px;font-weight:800;color:#1a7a4a">TSh {total:,}</span>
          </div>
        </div>
      </div>

      <!-- Payment method -->
      <div class="card" style="margin-bottom:16px">
        <div class="card-title" style="margin-bottom:16px">💳 Select Payment Method</div>
        {methods_html}
      </div>

      <!-- Phone / bank details (shown based on method) -->
      <div class="card" id="payDetails" style="margin-bottom:16px;display:none">
        <div id="payDetailsContent"></div>
      </div>

      <!-- Pay button -->
      <form method="post" action="/market/pay" id="payForm">
        <input type="hidden" name="crop"     value="{crop}">
        <input type="hidden" name="kg"       value="{kg}">
        <input type="hidden" name="price"    value="{price}">
        <input type="hidden" name="total"    value="{total}">
        <input type="hidden" name="method"   id="methodInput" value="">
        <input type="hidden" name="phone"    id="phoneInput"  value="">
        <input type="hidden" name="lang"     value="{lang}">
        <button type="button" id="payBtn" class="btn btn-primary btn-full"
                style="height:52px;font-size:16px;font-weight:700;border-radius:12px;justify-content:center;opacity:.5;pointer-events:none"
                onclick="submitPayment()">
          Pay TSh {total:,} →
        </button>
      </form>

      <div style="text-align:center;margin-top:12px;font-size:12px;color:#9ca3af">
        🔒 Simulated payment — no real money will be charged
      </div>
    </div>

    <script>
    var selectedMethod = '';
    var methodLabels = {{'mpesa':'M-Pesa','tigo':'Tigo Pesa','airtel':'Airtel Money','bank':'Bank Transfer'}};

    function selectMethod(mid) {{
      selectedMethod = mid;
      document.getElementById('methodInput').value = mid;
      document.querySelectorAll('.pay-method-label').forEach(function(el) {{
        el.style.borderColor = '#e5e7eb';
        el.style.background  = '#fff';
      }});
      var el = document.getElementById('lbl-' + mid);
      if (el) {{ el.style.borderColor = '#2d9e6b'; el.style.background = '#f0fdf4'; }}

      var d = document.getElementById('payDetails');
      var c = document.getElementById('payDetailsContent');
      d.style.display = 'block';
      if (mid === 'bank') {{
        c.innerHTML = '<div style="font-size:13px;font-weight:700;color:#1a1a1a;margin-bottom:10px">🏦 Bank Transfer Details</div>' +
          '<div style="background:#f9fafb;border-radius:8px;padding:14px;font-size:13px;color:#374151;line-height:2">' +
          'Bank: CRDB Bank Tanzania<br>Account Name: Smart Crop AI Ltd<br>Account No: 01J1234567890<br>' +
          'Reference: Use your phone number as reference</div>';
        document.getElementById('phoneInput').value = 'bank-transfer';
      }} else {{
        var provider = mid === 'mpesa' ? 'M-Pesa' : mid === 'tigo' ? 'Tigo Pesa' : 'Airtel Money';
        c.innerHTML = '<div style="font-size:13px;font-weight:700;color:#1a1a1a;margin-bottom:10px">📱 ' + provider + ' Number</div>' +
          '<input class="form-input" id="mobilePhone" type="tel" placeholder="+255 7XX XXX XXX" style="margin-bottom:8px" ' +
          'oninput="document.getElementById(\'phoneInput\').value=this.value">' +
          '<div style="font-size:11px;color:#9ca3af">Enter the mobile number registered with ' + provider + '</div>';
      }}
      var btn = document.getElementById('payBtn');
      btn.style.opacity = '1';
      btn.style.pointerEvents = 'auto';
    }}

    function submitPayment() {{
      if (!selectedMethod) return;
      if (selectedMethod !== 'bank') {{
        var phone = document.getElementById('mobilePhone') ? document.getElementById('mobilePhone').value : '';
        if (!phone || phone.length < 10) {{
          alert('Please enter a valid phone number');
          return;
        }}
        document.getElementById('phoneInput').value = phone;
      }}
      document.getElementById('payBtn').textContent = '⏳ Processing...';
      document.getElementById('payBtn').style.opacity = '.7';
      document.getElementById('payBtn').style.pointerEvents = 'none';
      setTimeout(function() {{ document.getElementById('payForm').submit(); }}, 1500);
    }}
    </script>"""
    return HTMLResponse(shell("Payment", f"Complete your {crop} sale", body, "market", user, lang))


@app.post("/market/pay", response_class=HTMLResponse)
async def market_pay_post(request: Request,
                          crop: str  = Form(""),
                          kg:   str  = Form("0"),
                          price: str = Form("0"),
                          total: str = Form("0"),
                          method: str = Form(""),
                          phone: str  = Form(""),
                          lang: str   = Form("en")):
    user = cu(request)
    if not user: return RedirectResponse("/login")

    from modules.market import save_transaction
    import secrets as _sec
    ref = "TXN-" + _sec.token_hex(4).upper()

    try:
        kg_val    = float(kg)
        price_val = int(price)
        total_val = int(total)
    except Exception:
        kg_val = price_val = total_val = 0

    tx = save_transaction(
        user_id      = user.get("id"),
        crop         = crop,
        quantity_kg  = kg_val,
        price_per_kg = price_val,
        total        = total_val,
        method       = method,
        phone        = phone,
        ref          = ref,
    )
    return RedirectResponse(f"/market/confirm?ref={ref}", status_code=303)


# ══ 🛒 SELL NOW — Step 3: Confirmation ═══════════════════════════════════════

@app.get("/market/confirm", response_class=HTMLResponse)
def market_confirm_page(request: Request, ref: str = "", lang: str = "en"):
    user = cu(request)
    if not user: return RedirectResponse("/login")

    from modules.market import get_transactions, _ICONS
    uid = user.get("id")
    txs = get_transactions(uid)
    tx  = next((t for t in txs if t["id"] == ref), None)
    if not tx:
        return RedirectResponse("/market")

    method_labels = {
        "mpesa":  "📱 M-Pesa",
        "tigo":   "📱 Tigo Pesa",
        "airtel": "📱 Airtel Money",
        "bank":   "🏦 Bank Transfer",
    }
    method_lbl = method_labels.get(tx["method"], tx["method"])
    icon = _ICONS.get(tx["crop"], "🌿")

    # All transactions for this user
    all_txs = get_transactions(uid, 10)
    tx_rows = "".join(f'''<tr>
      <td style="font-family:monospace;font-size:11px">{t["id"]}</td>
      <td>{_ICONS.get(t["crop"],"🌿")} {t["crop"]}</td>
      <td>{t["quantity_kg"]:g} kg</td>
      <td>TSh {t["total"]:,}</td>
      <td>{method_labels.get(t["method"],t["method"])}</td>
      <td><span class="badge {'badge-orange' if t['status']=='Pending' else 'badge-green'}">{t["status"]}</span></td>
      <td style="font-size:11px;color:#9ca3af">{t["created_at"][:16]}</td>
    </tr>''' for t in all_txs)

    body = f"""
    <div style="max-width:560px;margin:0 auto 32px">
      <!-- Success card -->
      <div style="background:linear-gradient(135deg,#1a7a4a,#2d9e6b);border-radius:16px;padding:32px;text-align:center;color:#fff;margin-bottom:20px">
        <div style="width:72px;height:72px;background:rgba(255,255,255,.2);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:36px;margin:0 auto 16px">✅</div>
        <div style="font-size:22px;font-weight:800;margin-bottom:6px">Payment Submitted!</div>
        <div style="font-size:14px;opacity:.85;margin-bottom:4px">Your sale request has been recorded</div>
        <div style="font-size:12px;opacity:.7">You will receive confirmation via SMS</div>
      </div>

      <!-- Transaction details -->
      <div class="card" style="margin-bottom:16px">
        <div class="card-title" style="margin-bottom:16px">📄 Transaction Details</div>
        {"".join(f'<div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f3f4f6"><span style="font-size:13px;color:#6b7280">{k}</span><span style="font-size:13px;font-weight:600;color:#1a1a1a">{v}</span></div>' for k,v in [
          ("Reference No.",  tx["id"]),
          ("Crop",           f"{icon} {tx['crop']}"),
          ("Quantity",       f"{tx['quantity_kg']:g} kg"),
          ("Price per kg",   f"TSh {tx['price_per_kg']:,}"),
          ("Total Amount",   f"TSh {tx['total']:,}"),
          ("Payment Method", method_lbl),
          ("Phone / Account",tx["phone"] if tx["phone"] != "bank-transfer" else "Bank Transfer"),
          ("Status",         "⏳ Pending Confirmation"),
          ("Date & Time",    tx["created_at"]),
        ])}
      </div>

      <!-- What next -->
      <div class="alert-card info" style="margin-bottom:20px">
        <span class="alert-icon">📩</span>
        <div class="alert-body">
          <div class="alert-title">What happens next?</div>
          <div class="alert-desc" style="line-height:1.8">
            1. Take your produce to the market with this reference number<br>
            2. Show the buyer your reference: <strong style="font-family:monospace">{ref}</strong><br>
            3. Complete the physical sale and receive payment<br>
            4. Your transaction will be marked <strong>Completed</strong>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div style="display:flex;gap:10px;margin-bottom:24px">
        <a href="/market" class="btn btn-secondary btn-full" style="justify-content:center">← Back to Market</a>
        <a href="/market/sell?crop={tx['crop']}" class="btn btn-ghost btn-full" style="justify-content:center">🔄 Sell More</a>
        <button onclick="window.print()" class="btn btn-primary btn-full" style="justify-content:center">🖨️ Print Receipt</button>
      </div>
    </div>

    <!-- Transaction history -->
    <div class="card">
      <div class="card-header">
        <div class="card-title">🧾 My Transactions</div>
        <span class="badge badge-gray">{len(all_txs)} records</span>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>Reference</th><th>Crop</th><th>Qty</th>
            <th>Total</th><th>Method</th><th>Status</th><th>Date</th>
          </tr></thead>
          <tbody>{tx_rows}</tbody>
        </table>
      </div>
    </div>"""
    return HTMLResponse(shell("Sale Confirmed", f"Transaction {ref}", body, "market", user, lang))


# ══ 🤝 EXPERT HELP ════════════════════════════════════════════════════════════

@app.get("/expert", response_class=HTMLResponse)
def expert_page(request: Request, disease: str = "", lang: str = "en"):
    user = cu(request)
    if not user: return RedirectResponse("/login")
    uid = user.get("id")

    # Chat history
    history   = get_chat_history(uid, 10) if DB_AVAILABLE else []
    hist_html = "".join(f'''<div class="chat-msg user"><div class="chat-bubble">{h["question"]}</div></div>
    <div class="chat-msg bot"><div class="chat-bubble">{h["answer"]}</div></div>''' for h in reversed(history))

    greeting = ("Habari! Mimi ni msaidizi wako wa kilimo." if lang == "sw"
                else "Hello! I'm your AI Crop Assistant. Ask me anything about your crops, diseases, or treatments.")

    # Auto-populate disease context from most recent scan if none passed
    if not disease:
        recent = _get_scans(uid, 1)
        if recent and "healthy" not in recent[0].get("disease", "").lower():
            disease = recent[0].get("disease", "")

    sugg = suggested_questions(disease or None, lang)
    sugg_html = "".join(f'<button class="quick-q-btn" onclick="sendChat(\'{q}\')">{q}</button>' for q in sugg)

    disease_ctx = ""
    if disease:
        dname = disease.replace("___", " — ").replace("_", " ")
        disease_ctx = f'''<div class="alert-card info" style="margin-bottom:12px">
          <span class="alert-icon">🔍</span>
          <div class="alert-body">
            <div class="alert-title">Active context: <strong>{dname}</strong></div>
            <div class="alert-desc">Questions and answers are tailored to this diagnosis</div>
            <div class="alert-actions">
              <a href="/expert" class="btn btn-ghost btn-sm">✕ Clear context</a>
            </div>
          </div>
        </div>'''

    # Recent scans for sidebar
    recent_scans = _get_scans(uid, 5)
    recent_html = ""
    for s in recent_scans:
        d = s.get("disease", "")
        healthy = "healthy" in d.lower()
        icon  = "✅" if healthy else "⚠️"
        bg    = "#f0fdf4" if healthy else "#fff1f2"
        dname = d.replace("___", " — ").replace("_", " ")[:35]
        crop  = s.get("crop_name", "")
        date  = str(s.get("detected_at", ""))[:10]
        link  = f"/expert?disease={d}"
        recent_html += f'''<a href="{link}" style="display:flex;align-items:center;gap:10px;padding:8px;border-radius:8px;text-decoration:none;transition:background .12s;{'background:#f0fdf4' if d == disease else ''}" onmouseover="this.style.background='#f9fafb'" onmouseout="this.style.background='{'#f0fdf4' if d == disease else ''}'">
          <div style="width:32px;height:32px;border-radius:7px;background:{bg};display:flex;align-items:center;justify-content:center;font-size:15px;flex-shrink:0">{icon}</div>
          <div style="flex:1;min-width:0">
            <div style="font-size:12px;font-weight:600;color:#1a1a1a;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{crop}</div>
            <div style="font-size:11px;color:#9ca3af;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{dname}</div>
          </div>
          <div style="font-size:10px;color:#9ca3af;flex-shrink:0">{date}</div>
        </a>'''
    if not recent_html:
        recent_html = '<div style="text-align:center;padding:16px;color:#9ca3af;font-size:13px">No scans yet — <a href="/scan" style="color:#2d9e6b">scan a crop</a></div>'

    # Extension officer cards
    officers = [
        {"name":"Dar es Salaam Extension","area":"Dar es Salaam Region","phone":"+255 22 286 0000","spec":"General Agriculture","avail":"Mon–Fri 8am–5pm","ic":"🌿"},
        {"name":"Arusha Crop Authority","area":"Arusha & Moshi Region","phone":"+255 27 250 7789","spec":"Horticulture & Fruits","avail":"Mon–Fri 8am–4pm","ic":"🍎"},
        {"name":"Morogoro Field Office","area":"Morogoro Region","phone":"+255 23 261 4000","spec":"Maize & Rice","avail":"Mon–Sat 7am–3pm","ic":"🌾"},
    ]
    officers_html = "".join(f'''<div style="background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:14px;margin-bottom:10px">
      <div style="display:flex;align-items:flex-start;gap:12px">
        <div style="width:40px;height:40px;border-radius:10px;background:#f0fdf4;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0">{o["ic"]}</div>
        <div style="flex:1">
          <div style="font-size:13px;font-weight:700;color:#1a1a1a">{o["name"]}</div>
          <div style="font-size:11px;color:#6b7280;margin-top:1px">📍 {o["area"]} · 🔬 {o["spec"]}</div>
          <div style="font-size:11px;color:#9ca3af;margin-top:1px">⏰ {o["avail"]}</div>
        </div>
      </div>
      <div style="display:flex;gap:8px;margin-top:10px">
        <a href="tel:{o['phone']}" class="btn btn-primary btn-sm btn-full" style="justify-content:center">📞 Call</a>
        <a href="/alerts" class="btn btn-ghost btn-sm btn-full" style="justify-content:center">📋 Report Issue</a>
      </div>
    </div>''' for o in officers)

    body = f"""
    <div class="grid-2">

      <!-- ── LEFT: Chat ──────────────────────────────────────────────────── -->
      <div>
        <!-- Chat header -->
        <div style="background:linear-gradient(135deg,#1a7a4a,#2d9e6b);border-radius:12px;padding:16px 20px;color:#fff;margin-bottom:14px;display:flex;align-items:center;gap:12px">
          <span style="font-size:28px">🤖</span>
          <div style="flex:1">
            <div style="font-size:15px;font-weight:700">AI Crop Assistant</div>
            <div style="font-size:12px;opacity:.8">Answers from your scan data · Always available</div>
          </div>
          <span style="background:rgba(255,255,255,.2);padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600">🟢 Online</span>
        </div>

        {disease_ctx}

        <!-- Quick questions -->
        <div style="margin-bottom:10px">
          <div style="font-size:11px;font-weight:600;color:#9ca3af;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px">Quick questions</div>
          <div class="quick-questions">{sugg_html}</div>
        </div>

        <!-- What can I ask — collapsible -->
        <details style="margin-bottom:12px;background:#fff;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden">
          <summary style="padding:10px 14px;cursor:pointer;font-size:12px;font-weight:700;color:#374151;list-style:none;display:flex;align-items:center;justify-content:space-between">
            💡 What can I ask?
            <span style="font-size:10px;color:#9ca3af">click to expand</span>
          </summary>
          <div style="padding:0 14px 12px">
            {"".join(f'''<div style="display:flex;gap:10px;padding:8px;background:#f9fafb;border-radius:7px;margin-top:6px;cursor:pointer" onclick="document.getElementById('chatInput').value='{ex}';document.getElementById('chatInput').focus()">
              <div style="font-size:12px;font-weight:700;color:#2d9e6b;flex-shrink:0;min-width:72px">{lbl}</div>
              <div><div style="font-size:12px;font-weight:600;color:#1a1a1a">{ttl}</div><div style="font-size:11px;color:#9ca3af;font-style:italic">{ex}</div></div>
            </div>''' for lbl,ttl,ex in [
              ("❓ WHAT","What disease is this?","What disease is this?"),
              ("🤔 WHY","Why did this happen?","Why did this disease appear?"),
              ("⏰ WHEN","When should I act?","When should I treat this?"),
              ("💊 HOW","How do I treat it?","How do I treat this disease?"),
              ("🛡️ PREVENT","How to prevent it?","How do I prevent this next season?"),
            ])}
          </div>
        </details>

        <!-- Chat box -->
        <div class="card" style="padding:16px">
          <input type="hidden" id="currentDisease" value="{disease}">
          <input type="hidden" id="currentLang" value="{lang}">
          <div class="chat-messages" id="chatBox" style="height:300px">
            <div class="chat-msg bot"><div class="chat-bubble">{greeting}</div><div class="chat-time">Now</div></div>
            {hist_html}
          </div>
          <div class="chat-input-row" style="margin-top:10px">
            <input class="form-input" id="chatInput" placeholder="Ask about your crops or diseases...">
            <button class="btn btn-primary" onclick="sendChat()">Send ➤</button>
          </div>
        </div>
      </div>

      <!-- ── RIGHT: Recent scans + Officers ────────────────────────────── -->
      <div>
        <!-- Recent diagnoses -->
        <div class="card" style="margin-bottom:16px">
          <div class="card-header">
            <div class="card-title">🕐 Recent Diagnoses</div>
            <a href="/reports" class="card-link">View all</a>
          </div>
          <div style="font-size:12px;color:#6b7280;margin-bottom:10px">Click a diagnosis to load it as chat context</div>
          {recent_html}
        </div>

        <!-- Extension officers -->
        <div class="card" style="margin-bottom:16px">
          <div class="card-header"><div class="card-title">👨‍🌾 Agricultural Extension Officers</div></div>
          {officers_html}
        </div>

        <!-- Urgent card -->
        <div style="background:linear-gradient(135deg,#1d4ed8,#3b82f6);border-radius:12px;padding:20px;color:#fff">
          <div style="font-size:24px;margin-bottom:6px">🚨</div>
          <div style="font-size:15px;font-weight:700;margin-bottom:4px">Critical Disease Outbreak?</div>
          <div style="font-size:12px;opacity:.85;margin-bottom:14px">For Citrus Greening, Grape Esca, or any Critical severity disease — contact authorities immediately</div>
          <div style="display:flex;gap:8px">
            <a href="/scan" class="btn btn-full" style="background:rgba(255,255,255,.2);color:#fff;justify-content:center;border:1px solid rgba(255,255,255,.3)">📷 Rescan</a>
            <a href="/alerts" class="btn btn-full" style="background:rgba(255,255,255,.2);color:#fff;justify-content:center;border:1px solid rgba(255,255,255,.3)">🔔 Alerts</a>
          </div>
        </div>
      </div>
    </div>"""
    return HTMLResponse(shell("Expert Help", "AI assistant · Diagnoses · Extension contacts", body, "expert", user, lang))


@app.post("/api/chat")
async def chat_api(request: Request):
    data     = await request.json()
    question = data.get("question", "")
    disease  = data.get("disease", "") or None
    lang     = data.get("lang", "en")
    user     = cu(request)

    # All answers come from the detected image result + internal database only
    ans = ai_answer(question, disease, lang)

    if DB_AVAILABLE and user:
        save_chat(user.get("id"), question, ans, lang)
    return JSONResponse({"answer": ans})

# ══ ⚙️ SETTINGS ═══════════════════════════════════════════════════════════════

@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, lang: str = "en", saved: str = ""):
    user = cu(request)
    if not user: return RedirectResponse("/login")
    saved_msg = '<div class="alert-card success" style="margin-bottom:16px"><span class="alert-icon">✅</span><div class="alert-body"><div class="alert-title">Settings saved successfully.</div></div></div>' if saved else ""
    uname = user.get("username",""); fname = user.get("full_name",""); phone = user.get("phone","")

    body = f"""
    {saved_msg}
    <form method="post" action="/settings">
      <div class="settings-section">
        <div class="settings-section-title">👤 Account Information</div>
        <div class="settings-grid">
          <div class="form-group"><label class="form-label">Full Name</label><input class="form-input" name="full_name" value="{fname}" placeholder="Your full name"></div>
          <div class="form-group"><label class="form-label">Username</label><input class="form-input" value="{uname}" disabled style="background:#f9fafb;color:#9ca3af"></div>
          <div class="form-group"><label class="form-label">Phone Number</label><input class="form-input" name="phone" value="{phone}" placeholder="+255 700 000 000"></div>
          <div class="form-group"><label class="form-label">Last Updated</label><input class="form-input" value="{datetime.utcnow().strftime('%Y-%m-%d')}" disabled style="background:#f9fafb;color:#9ca3af"></div>
        </div>
      </div>

      <div class="settings-section">
        <div class="settings-section-title">🌍 Language & Region</div>
        <div style="display:flex;gap:0;border:1.5px solid #e5e7eb;border-radius:8px;overflow:hidden;max-width:320px">
          <button type="button" onclick="setLang('en')" id="btn-en" class="btn {'btn-primary' if lang=='en' else 'btn-ghost'}" style="flex:1;border-radius:0;border:none;justify-content:center">🇬🇧 English</button>
          <button type="button" onclick="setLang('sw')" id="btn-sw" class="btn {'btn-primary' if lang=='sw' else 'btn-ghost'}" style="flex:1;border-radius:0;border:none;justify-content:center;border-left:1px solid #e5e7eb">🇹🇿 Swahili</button>
        </div>
        <input type="hidden" name="language" id="langInput" value="{lang}">
      </div>

      <div class="settings-section">
        <div class="settings-section-title">🔔 Notifications</div>
        <div class="toggle-row">
          <div class="toggle-info"><h4>Push Notifications</h4><p>Receive alerts on your device</p></div>
          <label class="toggle"><input type="checkbox" checked><span class="toggle-slider"></span></label>
        </div>
        <div class="toggle-row">
          <div class="toggle-info"><h4>Email Notifications</h4><p>Weekly summary emails</p></div>
          <label class="toggle"><input type="checkbox" checked><span class="toggle-slider"></span></label>
        </div>
      </div>

      <div class="settings-section">
        <div class="settings-section-title">🎨 Appearance & Mode</div>
        <div class="toggle-row">
          <div class="toggle-info"><h4>Live Weather</h4><p>Show live weather on dashboard</p></div>
          <label class="toggle"><input type="checkbox"><span class="toggle-slider"></span></label>
        </div>
        <div class="toggle-row">
          <div class="toggle-info"><h4>Offline Mode</h4><p>Cache data for offline access</p></div>
          <label class="toggle"><input type="checkbox"><span class="toggle-slider"></span></label>
        </div>
      </div>

      <div class="settings-section">
        <div class="settings-section-title">💾 Data & Storage</div>
        <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid #e5e7eb">
          <div><div style="font-size:13px;font-weight:600">Scan History</div><div class="text-xs text-muted">All your crop scans and diagnoses</div></div>
          <a href="/reports" class="btn btn-secondary btn-sm">View Records</a>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid #e5e7eb">
          <div><div style="font-size:13px;font-weight:600">Export Data</div><div class="text-xs text-muted">Download all your scan records as CSV</div></div>
          <a href="/reports" class="btn btn-secondary btn-sm">Export CSV</a>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0">
          <div><div style="font-size:13px;font-weight:600">Clear Cache</div><div class="text-xs text-muted">Free up storage space</div></div>
          <button type="button" class="btn btn-ghost btn-sm" onclick="localStorage.clear();sessionStorage.clear();this.textContent='✅ Cleared';setTimeout(()=>this.textContent='Clear',2000)">Clear</button>
        </div>
      </div>

      <div class="settings-section">
        <div class="settings-section-title">🔐 Privacy & Security</div>
        <div style="padding:10px 0;border-bottom:1px solid #e5e7eb;display:flex;justify-content:space-between;align-items:center">
          <div><div style="font-size:13px;font-weight:500;color:#2d9e6b">Change Password</div><div class="text-xs text-muted">Update your account password</div></div>
          <button type="button" class="btn btn-secondary btn-sm" onclick="openProfileModal();switchModalTab('tab-password',document.querySelectorAll('.modal-tab')[1])">Change</button>
        </div>
        <div style="padding:10px 0;border-bottom:1px solid #e5e7eb;display:flex;justify-content:space-between;align-items:center">
          <div><div style="font-size:13px;color:#6b7280">Privacy Policy</div><div class="text-xs text-muted">How we handle your data</div></div>
          <button type="button" class="btn btn-ghost btn-sm" onclick="alert('Your data is stored locally and never shared with third parties. Crop images are used only for AI diagnosis.')">View</button>
        </div>
        <div style="padding:10px;background:#fff9f9;border-radius:8px;margin-top:8px;display:flex;justify-content:space-between;align-items:center">
          <div><div style="font-size:13px;font-weight:600;color:#ef4444">Delete Account</div><div class="text-xs text-muted">This action cannot be undone</div></div>
          <button type="button" class="btn btn-danger btn-sm" onclick="if(confirm('Are you sure? This will permanently delete your account and all scan history.'))location.href='/logout'">Delete</button>
        </div>
      </div>

      <div style="display:flex;gap:10px;justify-content:flex-end">
        <button type="button" class="btn btn-ghost" onclick="history.back()">Cancel</button>
        <button type="submit" class="btn btn-primary">💾 Save Changes</button>
      </div>
    </form>
    <script>
    function setLang(l) {{
      document.getElementById('langInput').value = l;
      document.getElementById('btn-en').className = 'btn ' + (l==='en' ? 'btn-primary' : 'btn-ghost');
      document.getElementById('btn-sw').className = 'btn ' + (l==='sw' ? 'btn-primary' : 'btn-ghost');
      document.getElementById('btn-en').style.cssText = 'flex:1;border-radius:0;border:none;justify-content:center';
      document.getElementById('btn-sw').style.cssText = 'flex:1;border-radius:0;border:none;justify-content:center;border-left:1px solid #e5e7eb';
    }}
    // Persist notification toggles
    document.querySelectorAll('.toggle input[type="checkbox"]').forEach(cb => {{
      const key = 'notif_' + cb.closest('.toggle-row').querySelector('h4').textContent.replace(/\\s/g,'_');
      const saved = localStorage.getItem(key);
      if (saved !== null) cb.checked = saved === 'true';
      cb.addEventListener('change', () => localStorage.setItem(key, cb.checked));
    }});
    </script>"""
    return HTMLResponse(shell("Settings", "Manage account, language, and system preferences", body, "settings", user, lang))

@app.post("/settings")
async def settings_post(request: Request, full_name: str = Form(""), phone: str = Form(""), language: str = Form("en")):
    user = cu(request)
    if not user: return RedirectResponse("/login")
    if user: user["full_name"] = full_name; user["language"] = language
    return RedirectResponse(f"/settings?saved=1&lang={language}", status_code=303)


# ══ API & COMPAT ══════════════════════════════════════════════════════════════

@app.get("/api/records")
def api_records(request: Request):
    user = cu(request)
    records = _get_scans(user.get("id") if user else None, 200)
    return JSONResponse({"records": [dict(r) for r in records]})

@app.get("/api/weather")
def api_weather(location: str = "Dar es Salaam"):
    return JSONResponse(get_weather(location))

@app.get("/api/market")
def api_market():
    return JSONResponse({"prices": get_all_prices()})


@app.get("/crop-report", response_class=HTMLResponse)
def crop_report(request: Request):
    user = cu(request)
    if not user: return RedirectResponse("/login")

    CROP_DATA = [
        {
            "name": "Apple", "icon": "🍎", "total_images": 391,
            "diseases": [
                {"name": "Apple Scab",        "pathogen": "Venturia inaequalis",                    "severity": "Moderate", "images": 96,  "color": "#f59e0b"},
                {"name": "Black Rot",          "pathogen": "Botryosphaeria obtusa",                  "severity": "High",     "images": 99,  "color": "#ef4444"},
                {"name": "Cedar Apple Rust",   "pathogen": "Gymnosporangium juniperi-virginianae",   "severity": "Moderate", "images": 98,  "color": "#f59e0b"},
            ],
            "healthy_images": 98,
        },
        {
            "name": "Blueberry", "icon": "🫐", "total_images": 96,
            "diseases": [],
            "healthy_images": 96,
        },
        {
            "name": "Cherry", "icon": "🍒", "total_images": 193,
            "diseases": [
                {"name": "Powdery Mildew", "pathogen": "Podosphaera clandestina", "severity": "Moderate", "images": 96, "color": "#f59e0b"},
            ],
            "healthy_images": 97,
        },
        {
            "name": "Corn (Maize)", "icon": "🌽", "total_images": 391,
            "diseases": [
                {"name": "Cercospora Leaf Spot / Gray Leaf Spot", "pathogen": "Cercospora zeae-maydis",  "severity": "High",     "images": 98, "color": "#ef4444"},
                {"name": "Common Rust",                           "pathogen": "Puccinia sorghi",          "severity": "Moderate", "images": 99, "color": "#f59e0b"},
                {"name": "Northern Leaf Blight",                  "pathogen": "Exserohilum turcicum",     "severity": "High",     "images": 96, "color": "#ef4444"},
            ],
            "healthy_images": 98,
        },
        {
            "name": "Grape", "icon": "🍇", "total_images": 392,
            "diseases": [
                {"name": "Black Rot",                    "pathogen": "Guignardia bidwellii",                          "severity": "High",     "images": 99, "color": "#ef4444"},
                {"name": "Esca (Black Measles)",         "pathogen": "Phaeomoniella chlamydospora complex",           "severity": "Critical", "images": 98, "color": "#dc2626"},
                {"name": "Leaf Blight (Isariopsis)",     "pathogen": "Pseudocercospora vitis",                        "severity": "Moderate", "images": 97, "color": "#f59e0b"},
            ],
            "healthy_images": 98,
        },
        {
            "name": "Orange", "icon": "🍊", "total_images": 99,
            "diseases": [
                {"name": "Huanglongbing (Citrus Greening)", "pathogen": "Candidatus Liberibacter asiaticus", "severity": "Critical", "images": 99, "color": "#dc2626"},
            ],
            "healthy_images": 0,
        },
        {
            "name": "Peach", "icon": "🍑", "total_images": 199,
            "diseases": [
                {"name": "Bacterial Spot", "pathogen": "Xanthomonas arboricola pv. pruni", "severity": "Moderate", "images": 99, "color": "#f59e0b"},
            ],
            "healthy_images": 100,
        },
        {
            "name": "Pepper (Bell)", "icon": "🫑", "total_images": 195,
            "diseases": [
                {"name": "Bacterial Spot", "pathogen": "Xanthomonas campestris pv. vesicatoria", "severity": "Moderate", "images": 99, "color": "#f59e0b"},
            ],
            "healthy_images": 96,
        },
        {
            "name": "Potato", "icon": "🥔", "total_images": 292,
            "diseases": [
                {"name": "Early Blight", "pathogen": "Alternaria solani",       "severity": "Moderate", "images": 99, "color": "#f59e0b"},
                {"name": "Late Blight",  "pathogen": "Phytophthora infestans",  "severity": "Critical", "images": 96, "color": "#dc2626"},
            ],
            "healthy_images": 97,
        },
        {
            "name": "Raspberry", "icon": "🍓", "total_images": 97,
            "diseases": [],
            "healthy_images": 97,
        },
        {
            "name": "Soybean", "icon": "🌱", "total_images": 99,
            "diseases": [],
            "healthy_images": 99,
        },
        {
            "name": "Squash", "icon": "🎃", "total_images": 96,
            "diseases": [
                {"name": "Powdery Mildew", "pathogen": "Podosphaera xanthii / Erysiphe cichoracearum", "severity": "Moderate", "images": 96, "color": "#f59e0b"},
            ],
            "healthy_images": 0,
        },
    ]

    total_crops    = len(CROP_DATA)
    total_diseases = sum(len(c["diseases"]) for c in CROP_DATA)
    total_classes  = sum(len(c["diseases"]) + (1 if c["healthy_images"] > 0 else 0) for c in CROP_DATA)
    total_images   = sum(c["total_images"] for c in CROP_DATA)

    sev_color = {"Critical":"#dc2626","High":"#ef4444","Moderate":"#f59e0b","Low":"#3b82f6","None":"#2d9e6b"}
    sev_bg    = {"Critical":"#fff1f2","High":"#fff1f2","Moderate":"#fffbeb","Low":"#eff6ff","None":"#f0fdf4"}

    # Build crop cards
    cards = ""
    for i, c in enumerate(CROP_DATA):
        dis_count = len(c["diseases"])
        dis_rows = ""
        for d in c["diseases"]:
            sc = sev_color.get(d["severity"],"#9ca3af")
            sb = sev_bg.get(d["severity"],"#f9fafb")
            dis_rows += f"""
            <tr>
              <td style="padding:10px 12px;font-size:13px;font-weight:600;color:#1a1a1a">{d['name']}</td>
              <td style="padding:10px 12px;font-size:12px;color:#6b7280;font-style:italic">{d['pathogen']}</td>
              <td style="padding:10px 12px;text-align:center">
                <span style="background:{sb};color:{sc};border:1px solid {sc}44;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:700">{d['severity']}</span>
              </td>
              <td style="padding:10px 12px;text-align:center;font-size:13px;font-weight:600;color:#374151">{d['images']}</td>
            </tr>"""

        if not dis_rows:
            dis_rows = f'<tr><td colspan="4" style="padding:14px 12px;text-align:center;color:#9ca3af;font-size:13px">No diseases in training dataset — healthy class only</td></tr>'

        cards += f"""
        <div style="background:#fff;border-radius:14px;box-shadow:0 2px 12px rgba(0,0,0,.07);overflow:hidden;margin-bottom:20px;border:1px solid #e5e7eb">
          <!-- Crop header -->
          <div style="background:linear-gradient(135deg,#1a7a4a,#2d9e6b);padding:16px 20px;display:flex;align-items:center;justify-content:space-between">
            <div style="display:flex;align-items:center;gap:12px">
              <div style="width:44px;height:44px;border-radius:10px;background:rgba(255,255,255,.2);display:flex;align-items:center;justify-content:center;font-size:24px">{c['icon']}</div>
              <div>
                <div style="font-size:17px;font-weight:800;color:#fff">{c['name']}</div>
                <div style="font-size:12px;color:rgba(255,255,255,.8)">{dis_count} disease{'s' if dis_count!=1 else ''} · {c['healthy_images']} healthy images</div>
              </div>
            </div>
            <div style="display:flex;gap:8px">
              <div style="background:rgba(255,255,255,.2);border-radius:8px;padding:8px 14px;text-align:center">
                <div style="font-size:20px;font-weight:800;color:#fff">{dis_count}</div>
                <div style="font-size:10px;color:rgba(255,255,255,.8);text-transform:uppercase">Diseases</div>
              </div>
              <div style="background:rgba(255,255,255,.2);border-radius:8px;padding:8px 14px;text-align:center">
                <div style="font-size:20px;font-weight:800;color:#fff">{c['total_images']}</div>
                <div style="font-size:10px;color:rgba(255,255,255,.8);text-transform:uppercase">Images</div>
              </div>
            </div>
          </div>
          <!-- Disease table -->
          <div style="overflow-x:auto">
            <table style="width:100%;border-collapse:collapse">
              <thead>
                <tr style="background:#f9fafb;border-bottom:1px solid #e5e7eb">
                  <th style="padding:10px 12px;text-align:left;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#6b7280">Disease Name</th>
                  <th style="padding:10px 12px;text-align:left;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#6b7280">Pathogen</th>
                  <th style="padding:10px 12px;text-align:center;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#6b7280">Severity</th>
                  <th style="padding:10px 12px;text-align:center;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#6b7280">Training Images</th>
                </tr>
              </thead>
              <tbody>
                {dis_rows}
                <tr style="background:#f0fdf4;border-top:1px solid #e5e7eb">
                  <td style="padding:8px 12px;font-size:12px;color:#15803d;font-weight:600">✅ Healthy</td>
                  <td style="padding:8px 12px;font-size:12px;color:#9ca3af;font-style:italic">No pathogen</td>
                  <td style="padding:8px 12px;text-align:center"><span style="background:#f0fdf4;color:#15803d;border:1px solid #86efac;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:700">None</span></td>
                  <td style="padding:8px 12px;text-align:center;font-size:13px;font-weight:600;color:#374151">{c['healthy_images']}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>"""

    body = f"""
    <!-- Header -->
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:24px;flex-wrap:wrap;gap:12px">
      <div>
        <div style="font-size:22px;font-weight:800;color:#1a1a1a">🌿 Crop Disease Dataset Report</div>
        <div style="font-size:13px;color:#9ca3af;margin-top:4px">Complete breakdown of all crops and diseases in the AI training dataset</div>
      </div>
      <div style="display:flex;gap:8px">
        <button class="btn btn-secondary btn-sm" onclick="window.print()">🖨️ Print Report</button>
        <a href="/reports" class="btn btn-primary btn-sm">📊 View Scan History</a>
      </div>
    </div>

    <!-- Summary stats -->
    <div class="grid-4" style="margin-bottom:24px">
      <div class="stat-card" style="border-top:3px solid #2d9e6b">
        <div class="stat-icon-box green">🌾</div>
        <div class="stat-value">{total_crops}</div>
        <div class="stat-label">Total Crops</div>
        <div class="stat-delta up">In training dataset</div>
      </div>
      <div class="stat-card" style="border-top:3px solid #ef4444">
        <div class="stat-icon-box red">🦠</div>
        <div class="stat-value">{total_diseases}</div>
        <div class="stat-label">Total Diseases</div>
        <div class="stat-delta down">Across all crops</div>
      </div>
      <div class="stat-card" style="border-top:3px solid #3b82f6">
        <div class="stat-icon-box blue">📂</div>
        <div class="stat-value">{total_classes}</div>
        <div class="stat-label">Total Classes</div>
        <div class="stat-delta up">Disease + Healthy</div>
      </div>
      <div class="stat-card" style="border-top:3px solid #8b5cf6">
        <div class="stat-icon-box purple">📷</div>
        <div class="stat-value">{total_images:,}</div>
        <div class="stat-label">Training Images</div>
        <div class="stat-delta up">~97 per class</div>
      </div>
    </div>

    <!-- Severity legend -->
    <div style="background:#fff;border-radius:12px;padding:14px 20px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,.06);display:flex;align-items:center;gap:16px;flex-wrap:wrap">
      <span style="font-size:12px;font-weight:700;color:#374151">Severity Legend:</span>
      {"".join(f'<span style="background:{sev_bg[s]};color:{sev_color[s]};border:1px solid {sev_color[s]}44;padding:3px 12px;border-radius:20px;font-size:12px;font-weight:700">{s}</span>' for s in ["Critical","High","Moderate","Low","None"])}
    </div>

    <!-- Crop cards -->
    {cards}

    <!-- Print styles -->
    <style>
    @media print {{
      .sidebar, .topbar, footer, .btn, button {{ display:none !important }}
      .main-wrap {{ margin-left:0 !important }}
      .page-content {{ padding:0 !important }}
      body {{ background:#fff !important }}
    }}
    </style>"""

    return HTMLResponse(shell("Crop Disease Report", "Complete dataset breakdown — all crops and diseases", body, "reports", user))


@app.post("/api/profile/update")
async def profile_update(request: Request, full_name: str = Form(""), phone: str = Form("")):
    user = cu(request)
    if not user:
        return JSONResponse({"ok": False, "error": "Not logged in."})
    if DB_AVAILABLE:
        update_user(user.get("id"), full_name=full_name, phone=phone, language=user.get("language","en"))
    # Update session in memory
    user["full_name"] = full_name
    user["phone"] = phone
    token = request.cookies.get("session")
    if token:
        from modules.auth import _sessions
        if token in _sessions:
            _sessions[token]["user"] = user
    return JSONResponse({"ok": True})


@app.post("/api/profile/password")
async def profile_password(request: Request):
    user = cu(request)
    if not user:
        return JSONResponse({"ok": False, "error": "Not logged in."})
    if not DB_AVAILABLE:
        return JSONResponse({"ok": False, "error": "Database unavailable."})
    data = await request.json()
    old_pw = data.get("old_password", "")
    new_pw = data.get("new_password", "")
    ok, msg = update_password(user.get("id"), old_pw, new_pw)
    return JSONResponse({"ok": ok, "error": msg if not ok else ""})

@app.post("/api/alerts/read-all")
async def alerts_read_all(request: Request):
    user = cu(request)
    if DB_AVAILABLE and user: mark_alerts_read(user.get("id"))
    return JSONResponse({"ok": True})

@app.post("/api/alerts/{alert_id}/read")
async def alert_mark_read(alert_id: int, request: Request):
    """Mark a single alert as read."""
    if DB_AVAILABLE:
        from modules.database import db_cursor
        with db_cursor() as (cur, _):
            cur.execute("UPDATE alerts SET is_read=1 WHERE id=%s", (alert_id,))
    return JSONResponse({"ok": True})

@app.get("/health")
def health_check():
    return JSONResponse({"status": "ok", "db": DB_AVAILABLE, "version": "4.0"})

# Compat redirects
@app.get("/dashboard") 
def r1(): return RedirectResponse("/home")
@app.get("/detect")    
def r2(): return RedirectResponse("/scan")
@app.get("/monitoring")
def r3(): return RedirectResponse("/monitor")
@app.get("/assistant") 
def r4(): return RedirectResponse("/expert")
@app.get("/analytics")
def r5(): return RedirectResponse("/reports")


@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request, lang: str = "en"):
    user = cu(request)
    if not user: return RedirectResponse("/login")
    uid   = user.get("id")
    dets  = _get_scans(uid, 500)
    total = len(dets)
    healthy_count  = sum(1 for d in dets if "healthy" in d.get("disease","").lower())
    diseased_count = total - healthy_count

    def sev_color(s):
        return {"High":"#ef4444","Critical":"#dc2626","Severe":"#dc2626",
                "Moderate":"#f59e0b","Low":"#2d9e6b","None":"#2d9e6b"}.get(s,"#9ca3af")

    rows_html = ""
    for i, d in enumerate(dets):
        img        = d.get("image","")
        crop       = d.get("crop_name","Unknown")
        disease_r  = d.get("disease","")
        dis_label  = disease_r.replace("___"," — ").replace("_"," ")
        is_h       = "healthy" in disease_r.lower()
        sev        = d.get("severity","—")
        sc         = sev_color(sev)
        conf_val   = d.get("confidence",0)
        conf_pct   = round(float(conf_val)*100 if float(conf_val)<=1 else float(conf_val),1)
        date_str   = str(d.get("detected_at",""))[:16]
        notes      = d.get("notes","") or ""
        solution   = d.get("solution","") or ""
        cause      = d.get("cause","") or ""
        prevention = d.get("prevention","") or ""
        chem       = d.get("chemical_treatment","") or ""
        org        = d.get("organic_treatment","") or ""
        img_src    = f"/uploads/{img}" if img else ""
        img_tag    = f'<img src="{img_src}" style="width:48px;height:48px;border-radius:8px;object-fit:cover;flex-shrink:0" onerror="this.style.display=\'none\'">' if img_src else '<div style="width:48px;height:48px;border-radius:8px;background:#f0fdf4;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0">🌿</div>'

        detail_img = f'<img src="{img_src}" style="grid-column:1/-1;width:100%;max-height:300px;object-fit:contain;border-radius:8px;background:#fff;margin-bottom:4px" onerror="this.style.display=\'none\'">' if img_src else ""
        cause_html      = f'<div style="background:#fff7ed;border-radius:8px;padding:10px;margin-bottom:8px;border-left:3px solid #f59e0b"><div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#d97706;margin-bottom:4px">🤔 Cause</div><div style="font-size:12px;color:#374151">{cause}</div></div>' if cause else ""
        solution_html   = f'<div style="background:#f0fdf4;border-radius:8px;padding:10px;margin-bottom:8px;border-left:3px solid #2d9e6b"><div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#15803d;margin-bottom:4px">💊 Solution</div><div style="font-size:12px;color:#374151">{solution}</div></div>' if solution else ""
        prev_html       = f'<div style="background:#f0f7ff;border-radius:8px;padding:10px;margin-bottom:8px;border-left:3px solid #3b82f6"><div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#1d4ed8;margin-bottom:4px">🛡️ Prevention</div><div style="font-size:12px;color:#374151">{prevention}</div></div>' if prevention else ""
        chem_html       = f'<div style="background:#fef3c7;border-radius:8px;padding:10px;margin-bottom:8px;border-left:3px solid #d97706"><div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#d97706;margin-bottom:4px">🧪 Chemical</div><div style="font-size:12px;color:#374151">{chem}</div></div>' if chem else ""
        org_html        = f'<div style="background:#f0fdf4;border-radius:8px;padding:10px;border-left:3px solid #2d9e6b"><div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#15803d;margin-bottom:4px">🌿 Organic</div><div style="font-size:12px;color:#374151">{org}</div></div>' if org else ""

        rows_html += f"""
        <div class="history-row" data-crop="{crop.lower()}" data-disease="{dis_label.lower()}" data-sev="{sev.lower()}" data-healthy="{'1' if is_h else '0'}">
          <div style="display:flex;align-items:center;gap:12px;padding:12px 16px;border-bottom:1px solid #f3f4f6;cursor:pointer" onclick="toggleDetail('hd-{i}')">
            {img_tag}
            <div style="flex:1;min-width:0">
              <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
                <span style="font-size:13px;font-weight:700;color:#1a1a1a">{crop}</span>
                <span style="background:{'#f0fdf4' if is_h else '#fff1f2'};color:{'#15803d' if is_h else '#dc2626'};border:1px solid {'#86efac' if is_h else '#fca5a5'};padding:1px 8px;border-radius:20px;font-size:10px;font-weight:700">{'✅ Healthy' if is_h else '❌ Affected'}</span>
                <span style="background:{sc}18;color:{sc};padding:1px 8px;border-radius:20px;font-size:10px;font-weight:600">{sev}</span>
              </div>
              <div style="font-size:11px;color:#6b7280;margin-top:2px">{dis_label[:55]}{'...' if len(dis_label)>55 else ''}</div>
              <div style="font-size:10px;color:#9ca3af;margin-top:2px">🕐 {date_str}{' · 📝 '+notes[:25] if notes else ''} · 🎯 {conf_pct}%</div>
            </div>
            <div style="font-size:16px;color:#9ca3af;flex-shrink:0" id="hd-{i}-arrow">▼</div>
          </div>
          <div id="hd-{i}" style="display:none;padding:16px;background:#f9fafb;border-bottom:1px solid #e5e7eb">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px">
              {detail_img}
              <div style="background:#fff;border-radius:8px;padding:10px;text-align:center"><div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#9ca3af;margin-bottom:3px">Crop</div><div style="font-size:14px;font-weight:800;color:#1a1a1a">{crop}</div></div>
              <div style="background:#fff;border-radius:8px;padding:10px;text-align:center"><div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#9ca3af;margin-bottom:3px">Confidence</div><div style="font-size:14px;font-weight:800;color:#1a1a1a">{conf_pct}%</div></div>
              <div style="background:#fff;border-radius:8px;padding:10px;text-align:center"><div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#9ca3af;margin-bottom:3px">Severity</div><div style="font-size:14px;font-weight:800;color:{sc}">{sev}</div></div>
              <div style="background:#fff;border-radius:8px;padding:10px;text-align:center"><div style="font-size:10px;font-weight:700;text-transform:uppercase;color:#9ca3af;margin-bottom:3px">Date</div><div style="font-size:12px;font-weight:600;color:#1a1a1a">{date_str}</div></div>
            </div>
            {cause_html}{solution_html}{prev_html}{chem_html}{org_html}
            <div style="display:flex;gap:8px;margin-top:12px">
              <a href="/insights?disease={disease_r}" class="btn btn-primary btn-sm" style="flex:1;justify-content:center">🧠 Deep Analysis</a>
              <a href="/expert?disease={disease_r}" class="btn btn-secondary btn-sm" style="flex:1;justify-content:center">🤝 Ask Expert</a>
            </div>
          </div>
        </div>"""

    if not rows_html:
        rows_html = '<div style="text-align:center;padding:40px;color:#9ca3af"><div style="font-size:40px;margin-bottom:12px">📷</div><div style="font-size:14px;font-weight:600">No scan history yet</div><div style="font-size:12px;margin-top:4px">Go to <a href="/scan" style="color:#2d9e6b">Scan Crop</a> to get started</div></div>'

    body = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;flex-wrap:wrap;gap:10px">
      <div>
        <div style="font-size:20px;font-weight:800;color:#1a1a1a">📋 Scan History</div>
        <div style="font-size:13px;color:#9ca3af">All uploaded images and diagnosis results — saved permanently for future reference</div>
      </div>
      <div style="display:flex;gap:8px">
        <a href="/scan" class="btn btn-primary btn-sm">📷 New Scan</a>
        <a href="/reports" class="btn btn-secondary btn-sm">📊 Reports</a>
      </div>
    </div>

    <div class="grid-3" style="margin-bottom:20px">
      <div class="stat-card" style="border-top:3px solid #3b82f6"><div class="stat-icon-box blue">📷</div><div class="stat-value">{total}</div><div class="stat-label">Total Scans</div><div class="stat-delta up">All time</div></div>
      <div class="stat-card" style="border-top:3px solid #2d9e6b"><div class="stat-icon-box green">✅</div><div class="stat-value">{healthy_count}</div><div class="stat-label">Healthy</div><div class="stat-delta up">{round(healthy_count/max(total,1)*100)}% of scans</div></div>
      <div class="stat-card" style="border-top:3px solid #ef4444"><div class="stat-icon-box red">🦠</div><div class="stat-value">{diseased_count}</div><div class="stat-label">Diseases Found</div><div class="stat-delta {'down' if diseased_count>0 else 'up'}">{'Needs attention' if diseased_count>0 else 'All clear'}</div></div>
    </div>

    <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;flex-wrap:wrap;background:#fff;border-radius:10px;padding:12px 16px;box-shadow:0 1px 3px rgba(0,0,0,.06)">
      <input id="histSearch" oninput="filterHistory()" placeholder="🔍 Search crop or disease..." style="flex:1;min-width:160px;padding:8px 12px;border:1px solid #e5e7eb;border-radius:8px;font-size:13px">
      <select id="histSev" onchange="filterHistory()" style="padding:8px 12px;border:1px solid #e5e7eb;border-radius:8px;font-size:13px;background:#fff">
        <option value="">All Severities</option>
        <option value="healthy">✅ Healthy</option>
        <option value="critical">🔴 Critical</option>
        <option value="high">🔴 High</option>
        <option value="moderate">🟡 Moderate</option>
        <option value="low">🟢 Low</option>
      </select>
      <button class="btn btn-ghost btn-sm" onclick="expandAll()">Expand All</button>
      <button class="btn btn-ghost btn-sm" onclick="collapseAll()">Collapse All</button>
    </div>

    <div id="historyList" style="background:#fff;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.07);overflow:hidden;margin-bottom:20px">
      {rows_html}
    </div>

    <style>.history-row:hover > div:first-child {{ background:#f9fafb; }}</style>
    <script>
    function toggleDetail(id) {{
      const el = document.getElementById(id);
      const arrow = document.getElementById(id+'-arrow');
      if (!el) return;
      const open = el.style.display === 'none' || el.style.display === '';
      el.style.display = open ? 'block' : 'none';
      if (arrow) arrow.textContent = open ? '▲' : '▼';
    }}
    function expandAll() {{
      document.querySelectorAll('[id^="hd-"]').forEach(el => {{
        if (!el.id.includes('-arrow')) el.style.display = 'block';
      }});
      document.querySelectorAll('[id$="-arrow"]').forEach(a => a.textContent = '▲');
    }}
    function collapseAll() {{
      document.querySelectorAll('[id^="hd-"]').forEach(el => {{
        if (!el.id.includes('-arrow')) el.style.display = 'none';
      }});
      document.querySelectorAll('[id$="-arrow"]').forEach(a => a.textContent = '▼');
    }}
    function filterHistory() {{
      const q   = document.getElementById('histSearch').value.toLowerCase();
      const sev = document.getElementById('histSev').value.toLowerCase();
      document.querySelectorAll('.history-row').forEach(row => {{
        const crop    = row.dataset.crop || '';
        const disease = row.dataset.disease || '';
        const rowSev  = row.dataset.sev || '';
        const isH     = row.dataset.healthy === '1';
        const qMatch  = !q || crop.includes(q) || disease.includes(q);
        const sevMatch = !sev || (sev === 'healthy' ? isH : rowSev === sev);
        row.style.display = (qMatch && sevMatch) ? '' : 'none';
      }});
    }}
    </script>"""
    return HTMLResponse(shell("Scan History", "All uploaded images and diagnosis results", body, "reports", user, lang))
