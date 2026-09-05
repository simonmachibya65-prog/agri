import pathlib

SHELL_FUNC = '''
NAV = [
    ("home",    "Home",        "/home",     "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"),
    ("scan",    "Scan",        "/scan",     "M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z M15 13a3 3 0 11-6 0 3 3 0 016 0z"),
    ("monitor", "Monitor",     "/monitor",  "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"),
    ("insights","Insights",    "/insights", "M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"),
    ("farms",   "Farms",       "/farms",    "M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"),
    ("reports", "Reports",     "/reports",  "M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"),
    ("alerts",  "Alerts",      "/alerts",   "M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"),
    ("market",  "Market",      "/market",   "M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"),
    ("expert",  "Expert Help", "/expert",   "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"),
    ("settings","Settings",    "/settings", "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z"),
]

def svg_icon(path_d, size=16, color="currentColor"):
    paths = path_d.split(" M ")
    d_attr = " M ".join(paths)
    return f\'\'\'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="{d_attr}"/></svg>\'\'\'

def shell(title, subtitle, body, active="", user=None, lang="en", alert_count=0):
    uname = (user.get("full_name") or user.get("username","User")) if user else "Guest"
    initials = uname[0].upper() if uname else "G"
    lang_toggle = "sw" if lang=="en" else "en"
    lang_label = "Swahili" if lang=="en" else "English"
    badge = f\'<span class="nav-badge">{alert_count}</span>\' if alert_count else ""

    nav_items = ""
    for key, label, href, icon_path in NAV:
        cls = "active" if active==key else ""
        extra = badge if key=="alerts" and alert_count else ""
        nav_items += f\'\'\'<a href="{href}" class="{cls}">
          <span class="nav-icon">{svg_icon(icon_path)}</span>
          <span>{label}</span>{extra}
        </a>\'\'\'

    return f\'\'\'<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title} — Smart Crop AI</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/style.css">
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
</head>
<body>
<div class="layout">
  <aside class="sidebar">
    <div class="sidebar-logo">
      <div class="sidebar-logo-icon">🌿</div>
      <div class="sidebar-logo-text">
        <h1>Smart Crop AI</h1>
        <p>Intelligent Agricultural System</p>
      </div>
    </div>
    <div class="sidebar-nav-label">Navigation Menu</div>
    <nav class="sidebar-nav">{nav_items}</nav>
    <div class="sidebar-footer">
      <a href="/logout">{svg_icon("M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1")} Sign Out</a>
    </div>
  </aside>
  <div class="main-wrap">
    <div class="topbar">
      <div class="topbar-left">
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
      <div class="topbar-right">
        <a href="?lang={lang_toggle}" class="lang-btn">{lang_label}</a>
        <button class="topbar-icon-btn" onclick="location.href=\'/alerts\'" title="Alerts">
          {svg_icon("M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9")}
          {\'<span class="dot"></span>\' if alert_count else ""}
        </button>
        <div class="topbar-avatar" title="{uname}">{initials}</div>
      </div>
    </div>
    <div class="page-content">{body}</div>
  </div>
</div>
<script src="/static/app.js"></script>
</body>
</html>\'\'\'
'''

pathlib.Path("modules/shell.py").write_text(SHELL_FUNC, encoding="utf-8")
print(f"shell.py: {pathlib.Path('modules/shell.py').stat().st_size} bytes")
