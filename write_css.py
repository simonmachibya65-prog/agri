import pathlib

CSS = """:root{--g:#2d9e6b;--gd:#1a7a4a;--gl:#e8f5e9;--gbg:linear-gradient(135deg,#f0f7f0,#e8f5e9);--red:#ef4444;--ora:#f59e0b;--blu:#3b82f6;--t1:#1a1a1a;--t2:#6b7280;--t3:#9ca3af;--bd:#e5e7eb;--card:#fff;--sh:0 1px 3px rgba(0,0,0,.08);--r:12px;--rs:8px;--rx:6px;--sw:240px;--hh:64px;--ff:'Inter',-apple-system,sans-serif}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--ff);background:var(--gbg);color:var(--t1);min-height:100vh;font-size:14px;line-height:1.5}
a{text-decoration:none;color:inherit}
button,input,select,textarea{font-family:var(--ff)}
button{cursor:pointer}
.layout{display:flex;min-height:100vh}
.main-wrap{margin-left:var(--sw);flex:1;display:flex;flex-direction:column;min-height:100vh}
.page-content{padding:24px;flex:1}
.sidebar{width:var(--sw);background:#fff;border-right:1px solid var(--bd);position:fixed;top:0;left:0;bottom:0;z-index:100;display:flex;flex-direction:column;overflow-y:auto}
.sidebar-logo{padding:18px 16px 14px;border-bottom:1px solid var(--bd);display:flex;align-items:center;gap:10px}
.sidebar-logo-icon{width:36px;height:36px;background:var(--g);border-radius:8px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:18px;flex-shrink:0}
.sidebar-logo-text h1{font-size:13px;font-weight:700;color:var(--t1);line-height:1.2}
.sidebar-logo-text p{font-size:10px;color:var(--t2);margin-top:1px}
.sidebar-nav-label{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.08em;color:var(--t3);padding:14px 16px 4px}
.sidebar-nav a{display:flex;align-items:center;gap:10px;padding:10px 16px;color:var(--t2);font-size:13px;font-weight:500;transition:background .15s,color .15s}
.sidebar-nav a:hover{background:#f9fafb;color:var(--t1)}
.sidebar-nav a.active{background:var(--g);color:#fff;font-weight:600}
.sidebar-nav a .nav-icon{font-size:15px;width:20px;text-align:center;flex-shrink:0}
.sidebar-nav a .nav-badge{margin-left:auto;background:var(--red);color:#fff;font-size:10px;font-weight:700;padding:1px 6px;border-radius:10px}
.sidebar-footer{padding:14px 16px;border-top:1px solid var(--bd);margin-top:auto}
.sidebar-footer a{display:flex;align-items:center;gap:8px;color:var(--t2);font-size:13px}
.sidebar-footer a:hover{color:var(--red)}
.topbar{height:var(--hh);background:#fff;border-bottom:1px solid var(--bd);display:flex;align-items:center;justify-content:space-between;padding:0 24px;position:sticky;top:0;z-index:50}
.topbar-left h2{font-size:18px;font-weight:700;color:var(--t1)}
.topbar-left p{font-size:12px;color:var(--t2);margin-top:1px}
.topbar-right{display:flex;align-items:center;gap:10px}
.topbar-icon-btn{width:36px;height:36px;border-radius:50%;border:1px solid var(--bd);background:#fff;display:flex;align-items:center;justify-content:center;font-size:16px;cursor:pointer;position:relative;transition:background .15s}
.topbar-icon-btn:hover{background:#f9fafb}
.topbar-icon-btn .dot{position:absolute;top:6px;right:6px;width:8px;height:8px;background:var(--red);border-radius:50%;border:2px solid #fff}
.topbar-avatar{width:36px;height:36px;border-radius:50%;background:var(--g);display:flex;align-items:center;justify-content:center;color:#fff;font-size:14px;font-weight:600;cursor:pointer}
.lang-btn{padding:6px 12px;border-radius:6px;border:1px solid var(--bd);background:#fff;font-size:12px;color:var(--t2);cursor:pointer;transition:all .15s}
.lang-btn:hover{border-color:var(--g);color:var(--g)}
.card{background:var(--card);border-radius:var(--r);padding:20px;box-shadow:var(--sh);margin-bottom:16px}
.card-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}
.card-title{font-size:15px;font-weight:600;color:var(--t1)}
.card-subtitle{font-size:12px;color:var(--t2);margin-top:2px}
.card-link{font-size:12px;color:var(--g);font-weight:500;cursor:pointer}
.card-link:hover{text-decoration:underline}
.stat-card{background:var(--card);border-radius:var(--r);padding:20px;box-shadow:var(--sh)}
.stat-icon-box{width:44px;height:44px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:20px;margin-bottom:12px}
.stat-icon-box.green{background:#dcfce7}.stat-icon-box.blue{background:#dbeafe}.stat-icon-box.orange{background:#fef3c7}.stat-icon-box.red{background:#fee2e2}.stat-icon-box.purple{background:#ede9fe}
.stat-value{font-size:28px;font-weight:700;color:var(--t1);line-height:1}
.stat-label{font-size:12px;color:var(--t2);margin-top:4px}
.stat-delta{font-size:11px;margin-top:6px;display:flex;align-items:center;gap:3px}
.stat-delta.up{color:#10b981}.stat-delta.down{color:var(--red)}.stat-delta.neutral{color:var(--t2)}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.grid-3{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.grid-4{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}
.btn{display:inline-flex;align-items:center;gap:6px;padding:9px 18px;border-radius:var(--rx);font-size:13px;font-weight:600;border:none;cursor:pointer;transition:all .15s;white-space:nowrap}
.btn-primary{background:var(--g);color:#fff}.btn-primary:hover{background:var(--gd)}
.btn-secondary{background:#fff;color:var(--g);border:1.5px solid var(--g)}.btn-secondary:hover{background:var(--gl)}
.btn-danger{background:var(--red);color:#fff}.btn-danger:hover{background:#dc2626}
.btn-orange{background:var(--ora);color:#fff}.btn-orange:hover{background:#d97706}
.btn-blue{background:var(--blu);color:#fff}.btn-blue:hover{background:#2563eb}
.btn-ghost{background:transparent;color:var(--t2);border:1px solid var(--bd)}.btn-ghost:hover{background:#f9fafb;color:var(--t1)}
.btn-sm{padding:6px 12px;font-size:12px}.btn-lg{padding:12px 24px;font-size:15px}.btn-full{width:100%;justify-content:center}
.form-group{margin-bottom:14px}
.form-label{display:block;font-size:12px;font-weight:600;color:var(--t2);margin-bottom:5px;text-transform:uppercase;letter-spacing:.04em}
.form-input{width:100%;padding:10px 12px;border:1.5px solid var(--bd);border-radius:var(--rx);font-size:14px;color:var(--t1);background:#fff;transition:border-color .15s}
.form-input:focus{outline:none;border-color:var(--g);box-shadow:0 0 0 3px rgba(45,158,107,.1)}
.form-input::placeholder{color:var(--t3)}
.toggle-row{display:flex;align-items:center;justify-content:space-between;padding:14px 0;border-bottom:1px solid var(--bd)}
.toggle-row:last-child{border-bottom:none}
.toggle-info h4{font-size:13px;font-weight:600;color:var(--t1)}
.toggle-info p{font-size:12px;color:var(--t2);margin-top:2px}
.toggle{position:relative;width:44px;height:24px;flex-shrink:0}
.toggle input{opacity:0;width:0;height:0;position:absolute}
.toggle-slider{position:absolute;inset:0;background:#d1d5db;border-radius:12px;cursor:pointer;transition:background .2s}
.toggle-slider::before{content:'';position:absolute;width:18px;height:18px;left:3px;top:3px;background:#fff;border-radius:50%;transition:transform .2s;box-shadow:0 1px 3px rgba(0,0,0,.2)}
.toggle input:checked + .toggle-slider{background:var(--g)}
.toggle input:checked + .toggle-slider::before{transform:translateX(20px)}
.badge{display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600}
.badge-green{background:#dcfce7;color:#15803d}.badge-red{background:#fee2e2;color:#dc2626}.badge-orange{background:#fef3c7;color:#d97706}.badge-blue{background:#dbeafe;color:#1d4ed8}.badge-gray{background:#f3f4f6;color:#6b7280}
.progress{background:#e5e7eb;border-radius:4px;height:6px;overflow:hidden}
.progress-fill{height:100%;border-radius:4px;transition:width .4s ease}
.progress-fill.green{background:var(--g)}.progress-fill.orange{background:var(--ora)}.progress-fill.red{background:var(--red)}.progress-fill.blue{background:var(--blu)}
.alert-card{background:#fff;border-radius:var(--rs);padding:14px 16px;border-left:4px solid var(--bd);margin-bottom:10px;display:flex;align-items:flex-start;gap:12px;box-shadow:var(--sh)}
.alert-card.critical{border-left-color:var(--red);background:#fff9f9}.alert-card.warning{border-left-color:var(--ora);background:#fffbf0}.alert-card.info{border-left-color:var(--blu);background:#f0f7ff}.alert-card.success{border-left-color:var(--g);background:#f0fdf4}
.alert-icon{font-size:18px;flex-shrink:0;margin-top:1px}
.alert-body{flex:1}
.alert-title{font-size:13px;font-weight:600;color:var(--t1)}
.alert-desc{font-size:12px;color:var(--t2);margin-top:3px}
.alert-meta{font-size:11px;color:var(--t3);margin-top:6px;display:flex;align-items:center;gap:8px}
.alert-actions{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
.upload-zone{border:2px dashed #d1d5db;border-radius:var(--r);padding:40px 24px;text-align:center;cursor:pointer;transition:all .2s;background:#fafafa}
.upload-zone:hover,.upload-zone.drag-over{border-color:var(--g);background:var(--gl)}
.upload-zone input[type=file]{display:none}
.upload-icon{font-size:40px;margin-bottom:12px}
.upload-title{font-size:15px;font-weight:600;color:var(--t1);margin-bottom:4px}
.upload-sub{font-size:12px;color:var(--t2)}
#preview{max-width:100%;max-height:220px;border-radius:var(--rs);margin-top:16px;display:none}
.weather-card{background:linear-gradient(135deg,#1d4ed8 0%,#3b82f6 100%);border-radius:var(--r);padding:20px;color:#fff}
.weather-temp{font-size:48px;font-weight:700;line-height:1}
.weather-cond{font-size:14px;opacity:.85;margin-top:4px}
.weather-stats{display:flex;gap:20px;margin-top:16px;padding-top:16px;border-top:1px solid rgba(255,255,255,.2)}
.weather-stat{text-align:center;flex:1}
.weather-stat-icon{font-size:18px}
.weather-stat-val{font-size:13px;font-weight:600;margin-top:2px}
.weather-stat-lbl{font-size:10px;opacity:.7}
.forecast-row{display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.15);font-size:13px}
.forecast-row:last-child{border-bottom:none}
.chat-container{display:flex;flex-direction:column}
.chat-messages{height:360px;overflow-y:auto;padding:16px;background:#f9fafb;border-radius:var(--rs);border:1px solid var(--bd);margin-bottom:12px}
.chat-msg{margin-bottom:12px;display:flex;flex-direction:column}
.chat-msg.user{align-items:flex-end}.chat-msg.bot{align-items:flex-start}
.chat-bubble{max-width:75%;padding:10px 14px;border-radius:12px;font-size:13px;line-height:1.5}
.chat-msg.user .chat-bubble{background:var(--g);color:#fff;border-radius:12px 12px 2px 12px}
.chat-msg.bot .chat-bubble{background:#fff;color:var(--t1);border:1px solid var(--bd);border-radius:12px 12px 12px 2px}
.chat-time{font-size:10px;color:var(--t3);margin-top:3px}
.chat-input-row{display:flex;gap:8px}
.chat-input-row input{flex:1}
.quick-questions{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}
.quick-q-btn{padding:6px 12px;border-radius:20px;border:1px solid var(--bd);background:#fff;font-size:12px;color:var(--t2);cursor:pointer;transition:all .15s}
.quick-q-btn:hover{border-color:var(--g);color:var(--g);background:var(--gl)}
.expert-card{background:#fff;border-radius:var(--r);padding:16px;box-shadow:var(--sh);margin-bottom:12px}
.expert-header{display:flex;align-items:center;gap:12px;margin-bottom:12px}
.expert-avatar{width:44px;height:44px;border-radius:50%;background:var(--gl);display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0}
.expert-name{font-size:14px;font-weight:600;color:var(--t1)}
.expert-spec{font-size:12px;color:var(--t2)}
.expert-rating{font-size:12px;color:var(--t2);margin-top:2px}
.expert-status{font-size:11px;font-weight:600;padding:2px 8px;border-radius:10px;margin-left:auto}
.expert-status.available{background:#dcfce7;color:#15803d}.expert-status.busy{background:#fee2e2;color:#dc2626}
.expert-actions{display:flex;gap:8px}
.farm-card{background:#fff;border-radius:var(--r);padding:20px;box-shadow:var(--sh);margin-bottom:16px}
.farm-header{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:14px}
.farm-name{font-size:15px;font-weight:600;color:var(--t1)}
.farm-location{font-size:12px;color:var(--t2);margin-top:2px;display:flex;align-items:center;gap:4px}
.farm-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:14px}
.farm-stat-val{font-size:16px;font-weight:700;color:var(--t1)}
.farm-stat-lbl{font-size:11px;color:var(--t2);margin-top:2px}
.field-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:14px}
.field-item{background:#f9fafb;border-radius:var(--rx);padding:12px}
.field-id{font-size:11px;font-weight:700;color:var(--t2);margin-bottom:4px}
.field-crop{font-size:13px;font-weight:600;color:var(--t1)}
.field-size{font-size:11px;color:var(--t2);margin-top:2px}
.market-hero{background:linear-gradient(135deg,var(--g) 0%,var(--gd) 100%);border-radius:var(--r);padding:24px;color:#fff;margin-bottom:16px}
.market-hero-price{font-size:36px;font-weight:700;line-height:1}
.market-hero-label{font-size:13px;opacity:.85;margin-top:4px}
.crop-price-row{display:flex;align-items:center;padding:14px 0;border-bottom:1px solid var(--bd)}
.crop-price-row:last-child{border-bottom:none}
.crop-price-icon{width:36px;height:36px;border-radius:8px;background:var(--gl);display:flex;align-items:center;justify-content:center;font-size:18px;margin-right:12px;flex-shrink:0}
.crop-price-name{font-size:14px;font-weight:600;color:var(--t1);flex:1}
.crop-price-market{font-size:11px;color:var(--t2)}
.crop-price-val{font-size:15px;font-weight:700;color:var(--t1);text-align:right}
.crop-price-trend{font-size:11px;margin-top:2px;text-align:right}
.market-insight-card{background:#fff;border-radius:var(--rs);padding:14px 16px;border:1px solid var(--bd);margin-bottom:8px;display:flex;align-items:flex-start;gap:12px}
.market-insight-body{flex:1}
.market-insight-title{font-size:13px;font-weight:600;color:var(--t1)}
.market-insight-desc{font-size:12px;color:var(--t2);margin-top:3px}
.tabs{display:flex;border-bottom:2px solid var(--bd);margin-bottom:16px}
.tab-btn{padding:10px 16px;border:none;background:none;font-size:13px;font-weight:500;color:var(--t2);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px;transition:all .15s}
.tab-btn:hover{color:var(--t1)}.tab-btn.active{color:var(--g);border-bottom-color:var(--g);font-weight:600}
.tab-panel{display:none}.tab-panel.active{display:block}
.conf-bar{background:#e5e7eb;border-radius:4px;height:8px;overflow:hidden;margin-top:6px}
.conf-fill{height:100%;border-radius:4px;background:linear-gradient(90deg,#86efac,var(--g))}
.section-header{margin-bottom:20px}
.section-title{font-size:22px;font-weight:700;color:var(--t1)}
.section-sub{font-size:13px;color:var(--t2);margin-top:4px}
.table-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:13px}
thead th{background:#f9fafb;padding:10px 14px;text-align:left;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:var(--t2);border-bottom:1px solid var(--bd)}
tbody td{padding:12px 14px;border-bottom:1px solid var(--bd);color:var(--t1)}
tbody tr:hover td{background:#f9fafb}
tbody tr:last-child td{border-bottom:none}
.divider{border:none;border-top:1px solid var(--bd);margin:16px 0}
.text-green{color:var(--g)}.text-red{color:var(--red)}.text-orange{color:var(--ora)}.text-muted{color:var(--t2)}
.text-sm{font-size:12px}.text-xs{font-size:11px}.font-bold{font-weight:700}.font-semibold{font-weight:600}
.flex{display:flex}.flex-center{display:flex;align-items:center}.flex-between{display:flex;align-items:center;justify-content:space-between}
.gap-4{gap:4px}.gap-6{gap:6px}.gap-8{gap:8px}.gap-12{gap:12px}.gap-16{gap:16px}
.mt-4{margin-top:4px}.mt-8{margin-top:8px}.mt-12{margin-top:12px}.mt-16{margin-top:16px}
.mb-8{margin-bottom:8px}.mb-12{margin-bottom:12px}.mb-16{margin-bottom:16px}
.chip{display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:20px;font-size:11px;background:var(--gl);color:var(--gd)}
.back-link{display:inline-flex;align-items:center;gap:6px;color:var(--t2);font-size:13px;margin-bottom:16px}
.back-link:hover{color:var(--g)}
.empty-state{text-align:center;padding:40px 20px;color:var(--t2)}
.empty-state-icon{font-size:40px;margin-bottom:12px}
.empty-state-title{font-size:15px;font-weight:600;color:var(--t1);margin-bottom:6px}
.preview-img{max-width:100%;max-height:240px;border-radius:var(--rs);display:block;margin:0 auto 14px}
.auth-wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;background:var(--gbg)}
.auth-card{background:#fff;border-radius:16px;padding:36px 40px;width:100%;max-width:420px;box-shadow:0 8px 32px rgba(0,0,0,.12)}
.auth-logo{text-align:center;margin-bottom:28px}
.auth-logo-icon{width:56px;height:56px;background:var(--g);border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:28px;margin:0 auto 12px}
.auth-logo h2{font-size:20px;font-weight:700;color:var(--t1)}
.auth-logo p{font-size:13px;color:var(--t2);margin-top:4px}
.why-card{background:#fff;border-radius:var(--r);padding:20px;box-shadow:var(--sh);margin-bottom:12px}
.why-header{display:flex;align-items:center;gap:10px;margin-bottom:12px}
.why-title{font-size:14px;font-weight:600;color:var(--t1)}
.why-list{list-style:none;padding:0}
.why-list li{font-size:13px;color:var(--t2);padding:4px 0;display:flex;align-items:flex-start;gap:8px}
.why-list li::before{content:'•';color:var(--g);font-weight:700;flex-shrink:0}
.why-rec{background:var(--gl);border-radius:var(--rx);padding:10px 14px;margin-top:12px;font-size:12px;color:var(--gd);display:flex;align-items:center;gap:8px}
.ai-learning-card{background:linear-gradient(135deg,var(--g) 0%,var(--gd) 100%);border-radius:var(--r);padding:24px;color:#fff}
.ai-learning-title{font-size:16px;font-weight:700;margin-bottom:4px}
.ai-learning-sub{font-size:12px;opacity:.85;margin-bottom:16px}
.ai-learning-stats{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.ai-stat-val{font-size:28px;font-weight:700}
.ai-stat-lbl{font-size:12px;opacity:.8;margin-top:2px}
.urgent-card{background:linear-gradient(135deg,var(--blu) 0%,#1d4ed8 100%);border-radius:var(--r);padding:20px;color:#fff}
.urgent-icon{font-size:28px;margin-bottom:8px}
.urgent-title{font-size:15px;font-weight:700;margin-bottom:4px}
.urgent-sub{font-size:12px;opacity:.85;margin-bottom:14px}
.settings-section{background:#fff;border-radius:var(--r);padding:20px;box-shadow:var(--sh);margin-bottom:16px}
.settings-section-title{font-size:14px;font-weight:700;color:var(--t1);margin-bottom:16px;display:flex;align-items:center;gap:8px}
.settings-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.insights-metric{background:#fff;border-radius:var(--r);padding:20px;box-shadow:var(--sh)}
.insights-metric-label{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:var(--t2);margin-bottom:8px}
.insights-metric-val{font-size:28px;font-weight:700;color:var(--t1);line-height:1}
.insights-metric-sub{font-size:12px;color:var(--t2);margin-top:4px}
.insights-metric-bar{margin-top:12px}
@media(max-width:1024px){.grid-4{grid-template-columns:repeat(2,1fr)}.grid-3{grid-template-columns:repeat(2,1fr)}}
@media(max-width:768px){.sidebar{transform:translateX(-100%)}.main-wrap{margin-left:0}.grid-2,.grid-3,.grid-4{grid-template-columns:1fr}.page-content{padding:16px}}
"""

import pathlib
pathlib.Path("static/style.css").write_text(CSS, encoding="utf-8")
print(f"CSS written: {len(CSS)} chars, {pathlib.Path('static/style.css').stat().st_size} bytes")
