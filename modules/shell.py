
import json as _json

NAV_GROUPS = [
    ("FARM", [
        ("home",    "Home",        "/home",     "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"),
        ("scan",    "Scan",        "/scan",     "M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0118.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z M15 13a3 3 0 11-6 0 3 3 0 016 0z"),
        ("farms",   "Farms",       "/farms",    "M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"),
    ]),
    ("ANALYTICS", [
        ("monitor", "Monitor",     "/monitor",  "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"),
        ("insights","Insights",    "/insights", "M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"),
        ("reports", "Reports",     "/reports",  "M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"),
    ]),
    ("TOOLS", [
        ("alerts",  "Alerts",      "/alerts",   "M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"),
        ("market",  "Market",      "/market",   "M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"),
        ("expert",  "Expert Help", "/expert",   "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"),
    ]),
    ("ACCOUNT", [
        ("settings","Settings",    "/settings", "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z"),
    ]),
]

_DEFAULT_OPEN = {"FARM": True, "ANALYTICS": True, "TOOLS": True, "ACCOUNT": False}


def _svg(d, size=16):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
            f'stroke-linejoin="round"><path d="{ " M ".join(d.split(" M ")) }"/></svg>')

def shell(title, subtitle, body, active="", user=None, lang="en", alert_count=0):
    uname    = (user.get("full_name") or user.get("username", "User")) if user else "Guest"
    initials = uname[0].upper() if uname else "G"
    lang_lbl = "Swahili" if lang == "en" else "English"
    lang_tog = "sw"      if lang == "en" else "en"
    badge    = f'<span class="nb">{alert_count}</span>' if alert_count else ""

    # Which group owns the active page?
    active_group = ""
    for g, its in NAV_GROUPS:
        if any(k == active for k, *_ in its):
            active_group = g
            break

    # Build nav HTML
    nav_html = ""
    for grp, items in NAV_GROUPS:
        nav_html += f'<div class="ng" data-g="{grp}"><button class="ngh" onclick="tg(\'{grp}\')" type="button"><span class="ngl">{grp}</span><span class="chv">&#8250;</span></button><div class="ngi">'
        for key, lbl, href, icon_d in items:
            ac    = " active" if key == active else ""
            extra = badge if key == "alerts" and alert_count else ""
            nav_html += f'<a href="{href}" class="ni{ac}" data-tip="{lbl}" onclick="mnc()"><span class="nic">{_svg(icon_d)}</span><span class="nil">{lbl}</span>{extra}</a>'
        nav_html += '</div></div>'

    js_defs      = _json.dumps(_DEFAULT_OPEN)
    signout_icon = _svg("M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1")
    bell_icon    = _svg("M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9")
    alert_dot    = '<span class="adot"></span>' if alert_count else ""

    return f'''<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — Smart Crop AI</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/static/style.css">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
/* ════ NAV LAYOUT ════════════════════════════════════════════════════════════ */
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Inter',-apple-system,sans-serif;background:#f0f7f0;color:#1a1a1a;min-height:100vh}}
.app{{display:flex;min-height:100vh}}

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
#sb{{
  width:240px;min-width:240px;
  background:#fff;border-right:1px solid #e5e7eb;
  position:fixed;top:0;left:0;bottom:0;z-index:200;
  display:flex;flex-direction:column;overflow:hidden;
  transition:width .25s ease,transform .25s ease;
}}

/* Nav scroll area */
.sb-nav{{flex:1;overflow-y:auto;overflow-x:hidden;padding:8px 0;margin-top:4px}}
.sb-nav::-webkit-scrollbar{{width:4px}}
.sb-nav::-webkit-scrollbar-thumb{{background:#e5e7eb;border-radius:4px}}

/* Group */
.ng{{margin-bottom:2px}}
.ngh{{
  width:100%;display:flex;align-items:center;gap:6px;
  padding:9px 16px 5px;background:none;border:none;cursor:pointer;
  font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.09em;
  color:#9ca3af;transition:color .15s;
}}
.ngh:hover{{color:#6b7280}}
.ngl{{flex:1;text-align:left;white-space:nowrap;overflow:hidden}}
/* chevron rotates */
.chv{{
  font-size:16px;line-height:1;color:#9ca3af;flex-shrink:0;
  display:inline-block;transform:rotate(90deg);
  transition:transform .2s ease;
}}
.ng.open .chv{{transform:rotate(270deg)}}

/* Group items */
.ngi{{overflow:hidden;max-height:0;transition:max-height .25s ease}}
.ng.open .ngi{{max-height:400px}}

/* Nav item */
.ni{{
  display:flex;align-items:center;gap:10px;
  padding:9px 14px 9px 20px;color:#6b7280;font-size:13px;
  font-weight:500;text-decoration:none;
  border-left:3px solid transparent;
  transition:background .12s,color .12s,border-color .12s;
  white-space:nowrap;overflow:hidden;
}}
.ni:hover{{background:#f9fafb;color:#1a1a1a}}
.ni.active{{background:#f0fdf4;color:#1a7a4a;border-left-color:#2d9e6b;font-weight:600}}
.ni.active .nic svg{{stroke:#2d9e6b}}
.nic{{width:18px;display:flex;align-items:center;justify-content:center;flex-shrink:0}}
.nil{{flex:1;overflow:hidden;text-overflow:ellipsis}}
.nb{{
  margin-left:auto;background:#ef4444;color:#fff;
  font-size:10px;font-weight:700;padding:1px 6px;border-radius:10px;flex-shrink:0;
}}

/* Sidebar footer */
.sb-foot{{
  padding:12px 14px;border-top:1px solid #e5e7eb;flex-shrink:0;
}}
.sb-foot a{{
  display:flex;align-items:center;gap:10px;color:#6b7280;font-size:13px;
  font-weight:500;text-decoration:none;padding:8px 6px;border-radius:6px;
  white-space:nowrap;overflow:hidden;
  transition:background .12s,color .12s;
}}
.sb-foot a:hover{{background:#fff1f2;color:#dc2626}}

/* ── Collapsed state ─────────────────────────────────────────────────────── */
#sb.col{{width:60px;min-width:60px}}
#sb.col .sb-logo-text,
#sb.col .ngl,
#sb.col .chv,
#sb.col .nil,
#sb.col .nb,
#sb.col .sb-foot-lbl{{display:none!important}}
#sb.col .sb-logo{{justify-content:center;padding:0}}
#sb.col .ngh{{justify-content:center;padding:8px 0;cursor:default;pointer-events:none}}
#sb.col .ngi{{max-height:400px!important}}
#sb.col .ni{{justify-content:center;padding:10px 0;border-left:none;position:relative}}
#sb.col .ni.active{{background:#f0fdf4;border-left:none}}
#sb.col .ni.active::before{{
  content:'';position:absolute;left:0;top:4px;bottom:4px;
  width:3px;background:#2d9e6b;border-radius:0 3px 3px 0;
}}
#sb.col .nic{{width:100%;justify-content:center}}
#sb.col .sb-foot a{{justify-content:center;padding:10px 0}}

/* Tooltip on collapse */
#sb.col .ni::after,
#sb.col .sb-foot a::after{{
  content:attr(data-tip);
  position:absolute;left:68px;top:50%;transform:translateY(-50%);
  background:#1e293b;color:#fff;padding:5px 10px;border-radius:6px;
  font-size:12px;font-weight:500;white-space:nowrap;
  pointer-events:none;opacity:0;transition:opacity .15s;z-index:300;
}}
#sb.col .ni:hover::after,
#sb.col .sb-foot a:hover::after{{opacity:1}}

/* ── Mobile overlay ──────────────────────────────────────────────────────── */
#ov{{
  display:none;position:fixed;inset:0;
  background:rgba(0,0,0,.45);z-index:199;
  opacity:0;transition:opacity .25s;
}}
#ov.show{{display:block;opacity:1}}

/* ── Main wrap ───────────────────────────────────────────────────────────── */
#mw{{
  margin-left:240px;flex:1;display:flex;flex-direction:column;
  min-height:100vh;min-width:0;
  transition:margin-left .25s ease;
}}
#mw.col{{margin-left:60px}}

/* ── Topbar ──────────────────────────────────────────────────────────────── */
.topbar{{
  height:64px;background:#fff;border-bottom:1px solid #e5e7eb;
  display:flex;align-items:center;justify-content:space-between;
  padding:0 20px;position:sticky;top:0;z-index:50;flex-shrink:0;
}}
.tb-left{{display:flex;align-items:center;gap:10px}}
.tb-logo{{display:flex;align-items:center;gap:8px;flex-shrink:0}}
.tb-logo-icon{{width:30px;height:30px;background:#2d9e6b;border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:15px;flex-shrink:0}}
.tb-logo-text{{font-size:14px;font-weight:700;color:#1a1a1a;white-space:nowrap}}
.tb-divider{{width:1px;height:28px;background:#e5e7eb;flex-shrink:0;margin:0 4px}}
.tb-title h2{{font-size:16px;font-weight:700;color:#1a1a1a;line-height:1.2}}
.tb-title p{{font-size:11px;color:#9ca3af;margin-top:1px}}
.hbtn{{
  width:34px;height:34px;border-radius:8px;border:1px solid #e5e7eb;
  background:#fff;display:flex;align-items:center;justify-content:center;
  cursor:pointer;color:#6b7280;flex-shrink:0;transition:background .12s,color .12s;margin-left:4px;
}}
.hbtn:hover{{background:#f9fafb;color:#1a1a1a}}
.hbtn svg{{pointer-events:none}}
.tb-right{{display:flex;align-items:center;gap:8px}}
.lang-btn{{padding:6px 12px;border-radius:6px;border:1px solid #e5e7eb;background:#fff;font-size:12px;color:#6b7280;cursor:pointer;text-decoration:none;transition:all .12s}}
.lang-btn:hover{{border-color:#2d9e6b;color:#2d9e6b}}
.bell-btn{{width:36px;height:36px;border-radius:50%;border:1px solid #e5e7eb;background:#fff;display:flex;align-items:center;justify-content:center;cursor:pointer;position:relative;transition:background .12s}}
.bell-btn:hover{{background:#f9fafb}}
.adot{{position:absolute;top:6px;right:6px;width:8px;height:8px;background:#ef4444;border-radius:50%;border:2px solid #fff}}
.avatar{{width:36px;height:36px;border-radius:50%;background:#2d9e6b;display:flex;align-items:center;justify-content:center;color:#fff;font-size:14px;font-weight:600;cursor:pointer;flex-shrink:0}}

/* ── Page + Footer ───────────────────────────────────────────────────────── */
.page-content{{padding:24px;flex:1}}
.app-footer{{height:44px;background:#fff;border-top:1px solid #e5e7eb;display:flex;align-items:center;justify-content:center;gap:10px;font-size:12px;color:#9ca3af;flex-shrink:0}}
.app-footer strong{{color:#2d9e6b;font-weight:700}}
.footer-div{{color:#e5e7eb;font-size:16px}}

/* ── Mobile (<768px) ─────────────────────────────────────────────────────── */
@media(max-width:767px){{
  #sb{{transform:translateX(-100%);width:260px!important;min-width:260px!important}}
  #sb.mob-open{{transform:translateX(0)}}
  #sb.col{{width:260px!important;min-width:260px!important}}
  #mw,#mw.col{{margin-left:0!important}}
  .page-content{{padding:16px}}
  /* un-collapse labels on mobile drawer */
  #sb.mob-open .sb-logo-text,
  #sb.mob-open .ngl,#sb.mob-open .chv,
  #sb.mob-open .nil,#sb.mob-open .nb,
  #sb.mob-open .sb-foot-lbl{{display:initial!important}}
  #sb.mob-open .sb-logo{{justify-content:flex-start;padding:0 14px}}
  #sb.mob-open .ngh{{justify-content:flex-start;padding:9px 16px 5px;pointer-events:auto}}
  #sb.mob-open .ni{{justify-content:flex-start;padding:9px 14px 9px 20px}}
  #sb.mob-open .nic{{width:18px}}
  #sb.mob-open .sb-foot a{{justify-content:flex-start;padding:8px 6px}}
  #sb.mob-open .ni::after,#sb.mob-open .sb-foot a::after{{display:none}}
}}
</style>
</head>
<body>
<div id="ov" onclick="closeSB()"></div>
<div class="app">

<!-- SIDEBAR -->
<aside id="sb">
  <nav class="sb-nav">{nav_html}</nav>
  <div class="sb-foot">
    <a href="/logout" data-tip="Sign Out">
      {signout_icon}
      <span class="sb-foot-lbl">Sign Out</span>
    </a>
  </div>
</aside>

<!-- MAIN -->
<div class="main-wrap" id="mw">
  <div class="topbar">
    <div class="tb-left">
      <div class="tb-logo">
        <div class="tb-logo-icon">🌿</div>
        <span class="tb-logo-text">Smart Crop AI</span>
      </div>
      <div class="tb-divider"></div>
      <div class="tb-title">
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
      <button class="hbtn" id="hbtn" onclick="togSB()" title="Toggle sidebar" type="button">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
          <line x1="3" y1="6" x2="21" y2="6"/>
          <line x1="3" y1="12" x2="21" y2="12"/>
          <line x1="3" y1="18" x2="21" y2="18"/>
        </svg>
      </button>
    </div>
    <div class="tb-right">
      <a href="?lang={lang_tog}" class="lang-btn">{lang_lbl}</a>
      <button class="bell-btn" onclick="location.href='/alerts'" title="Alerts">
        {bell_icon}{alert_dot}
      </button>
      <div class="avatar" title="{uname}">{initials}</div>
    </div>
  </div>

  <div class="page-content">{body}</div>

  <footer class="app-footer">
    <span>Designed &amp; Developed by <strong>Masalago</strong></span>
    <span class="footer-div">·</span>
    <span>Smart Crop AI &copy; 2026</span>
  </footer>
</div>
</div>

<script src="/static/app.js"></script>
<script>
(function(){{
  var sb      = document.getElementById('sb');
  var mw      = document.getElementById('mw');
  var ov      = document.getElementById('ov');
  var isMob   = window.innerWidth < 768;
  var isOpen  = true;
  var groups  = {{}};
  var defs    = {js_defs};
  var actGrp  = "{active_group}";

  /* ── Load saved state ── */
  try {{
    var s = JSON.parse(localStorage.getItem('_cnav') || '{{}}');
    if (s.open !== undefined) isOpen = s.open;
    if (s.g)    groups = s.g;
  }} catch(e) {{}}

  if (isMob) isOpen = false;

  function save() {{
    try {{ localStorage.setItem('_cnav', JSON.stringify({{open:isOpen,g:groups}})); }} catch(e) {{}}
  }}

  /* ── Apply sidebar state ── */
  function apSB() {{
    if (isMob) {{
      sb.classList.remove('col');
      mw.classList.remove('col');
      if (isOpen) {{
        sb.classList.add('mob-open');
        ov.classList.add('show');
      }} else {{
        sb.classList.remove('mob-open');
        ov.classList.remove('show');
      }}
    }} else {{
      ov.classList.remove('show');
      sb.classList.remove('mob-open');
      if (isOpen) {{
        sb.classList.remove('col');
        mw.classList.remove('col');
      }} else {{
        sb.classList.add('col');
        mw.classList.add('col');
      }}
    }}
  }}

  /* ── Toggle sidebar ── */
  window.togSB = function() {{
    isOpen = !isOpen;
    apSB();
    save();
  }};
  window.closeSB = function() {{
    isOpen = false;
    apSB();
    save();
  }};

  /* ── Apply group open/close ── */
  function apGrp(el, open) {{
    if (open) el.classList.add('open');
    else      el.classList.remove('open');
  }}

  /* ── Toggle group ── */
  window.tg = function(name) {{
    if (name === actGrp) return; // active group always open
    var el   = document.querySelector('.ng[data-g="' + name + '"]');
    if (!el) return;
    var open = !el.classList.contains('open');
    groups[name] = open;
    apGrp(el, open);
    save();
  }};

  /* ── Close on nav link (mobile) ── */
  window.mnc = function() {{
    if (isMob) {{ isOpen=false; apSB(); save(); }}
  }};

  /* ── Init all groups ── */
  document.querySelectorAll('.ng').forEach(function(el) {{
    var name = el.getAttribute('data-g');
    var open;
    if (name === actGrp)              open = true;
    else if (groups[name] !== undefined) open = groups[name];
    else                              open = defs[name] !== undefined ? defs[name] : true;
    apGrp(el, open);
  }});

  apSB();

  window.addEventListener('resize', function() {{
    isMob = window.innerWidth < 768;
    apSB();
  }});
}})();
</script>
</body>
</html>'''
