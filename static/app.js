
// Smart Crop AI — App JS

// ── Image preview ──────────────────────────────────────────────
function previewImage(input) {
  const p = document.getElementById('preview');
  if (input.files && input.files[0]) {
    const r = new FileReader();
    r.onload = e => { p.src = e.target.result; p.style.display = 'block'; };
    r.readAsDataURL(input.files[0]);
  }
}

// ── Drag & drop ────────────────────────────────────────────────
function handleDrop(e) {
  e.preventDefault();
  const zone = document.getElementById('dropZone');
  if (zone) zone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) {
    const fi = document.getElementById('fileInput');
    const dt = new DataTransfer();
    dt.items.add(file);
    fi.files = dt.files;
    previewImage(fi);
  }
}
function handleDragOver(e) {
  e.preventDefault();
  const zone = document.getElementById('dropZone');
  if (zone) zone.classList.add('drag-over');
}
function handleDragLeave() {
  const zone = document.getElementById('dropZone');
  if (zone) zone.classList.remove('drag-over');
}

// ── Tabs ───────────────────────────────────────────────────────
function switchTab(id) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  const btn = document.querySelector('[data-tab="' + id + '"]');
  const panel = document.getElementById(id);
  if (btn) btn.classList.add('active');
  if (panel) panel.classList.add('active');
}

// ── Chat ───────────────────────────────────────────────────────
function sendChat(question) {
  const input = document.getElementById('chatInput');
  const q = question || (input ? input.value.trim() : '');
  if (!q) return;
  if (input) input.value = '';
  const box = document.getElementById('chatBox') || document.getElementById('chatMessages');
  if (!box) return;
  const now = new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
  box.innerHTML += '<div class="chat-msg user"><div class="chat-bubble">' + esc(q) + '</div><div class="chat-time">' + now + '</div></div>';
  box.scrollTop = box.scrollHeight;
  const disease = (document.getElementById('currentDisease') || {}).value || '';
  const lang = (document.getElementById('currentLang') || {}).value || 'en';
  fetch('/api/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({question: q, disease, lang})
  })
  .then(r => r.json())
  .then(d => {
    const t = new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
    box.innerHTML += '<div class="chat-msg bot"><div class="chat-bubble">' + esc(d.answer) + '</div><div class="chat-time">' + t + '</div></div>';
    box.scrollTop = box.scrollHeight;
  })
  .catch(() => {
    box.innerHTML += '<div class="chat-msg bot"><div class="chat-bubble">Sorry, could not connect. Please try again.</div></div>';
    box.scrollTop = box.scrollHeight;
  });
}
function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Charts ─────────────────────────────────────────────────────
function initCharts() {
  // Health trend chart
  const hCtx = document.getElementById('healthChart');
  if (hCtx && window._healthData) {
    new Chart(hCtx, {
      type: 'line',
      data: {
        labels: window._healthData.labels,
        datasets: [{
          label: 'Health Score',
          data: window._healthData.scores,
          borderColor: '#2d9e6b',
          backgroundColor: 'rgba(45,158,107,.12)',
          tension: 0.4, fill: true, pointRadius: 3,
          pointBackgroundColor: '#2d9e6b'
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: true,
        plugins: { legend: { display: false } },
        scales: {
          y: { min: 0, max: 100, grid: { color: '#f3f4f6' }, ticks: { font: { size: 11 } } },
          x: { grid: { display: false }, ticks: { font: { size: 11 } } }
        }
      }
    });
  }

  // Soil moisture chart
  const sCtx = document.getElementById('soilChart');
  if (sCtx && window._soilData) {
    new Chart(sCtx, {
      type: 'line',
      data: {
        labels: window._soilData.labels,
        datasets: [{
          label: 'Soil Moisture %',
          data: window._soilData.values,
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59,130,246,.08)',
          tension: 0.4, fill: true, pointRadius: 4,
          pointBackgroundColor: '#3b82f6'
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: true,
        plugins: { legend: { display: false } },
        scales: {
          y: { min: 0, max: 100, grid: { color: '#f3f4f6' }, ticks: { font: { size: 11 } } },
          x: { grid: { display: false }, ticks: { font: { size: 11 } } }
        }
      }
    });
  }

  // Disease bar chart
  const dCtx = document.getElementById('diseaseChart');
  if (dCtx && window._diseaseData) {
    new Chart(dCtx, {
      type: 'bar',
      data: {
        labels: window._diseaseData.labels,
        datasets: [{
          label: 'Detections',
          data: window._diseaseData.counts,
          backgroundColor: window._diseaseData.colors || '#2d9e6b',
          borderRadius: 4
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: true,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, grid: { color: '#f3f4f6' }, ticks: { font: { size: 11 } } },
          x: { grid: { display: false }, ticks: { font: { size: 10 }, maxRotation: 30 } }
        }
      }
    });
  }

  // Timeline chart
  const tCtx = document.getElementById('timelineChart');
  if (tCtx && window._timelineData) {
    new Chart(tCtx, {
      type: 'line',
      data: {
        labels: window._timelineData.labels,
        datasets: [{
          label: 'Scans',
          data: window._timelineData.counts,
          borderColor: '#2d9e6b',
          backgroundColor: 'rgba(45,158,107,.1)',
          tension: 0.3, fill: true
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: true,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, grid: { color: '#f3f4f6' }, ticks: { font: { size: 11 } } },
          x: { grid: { display: false }, ticks: { maxTicksLimit: 8, font: { size: 11 } } }
        }
      }
    });
  }

  // Crop performance bar chart (Reports)
  const cpCtx = document.getElementById('cropPerfChart');
  if (cpCtx && window._cropPerfData) {
    new Chart(cpCtx, {
      type: 'bar',
      data: {
        labels: window._cropPerfData.labels,
        datasets: [
          { label: 'Yield (t/ha)', data: window._cropPerfData.yield, backgroundColor: '#2d9e6b', borderRadius: 4 },
          { label: 'Health Score', data: window._cropPerfData.health, backgroundColor: '#3b82f6', borderRadius: 4 }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: true,
        plugins: { legend: { position: 'bottom', labels: { font: { size: 11 } } } },
        scales: {
          y: { beginAtZero: true, grid: { color: '#f3f4f6' }, ticks: { font: { size: 11 } } },
          x: { grid: { display: false }, ticks: { font: { size: 11 } } }
        }
      }
    });
  }

  // Disease distribution donut (Reports)
  const ddCtx = document.getElementById('diseaseDoughnut');
  if (ddCtx && window._donutData) {
    new Chart(ddCtx, {
      type: 'doughnut',
      data: {
        labels: window._donutData.labels,
        datasets: [{ data: window._donutData.values, backgroundColor: ['#ef4444','#f59e0b','#3b82f6','#2d9e6b','#8b5cf6'], borderWidth: 2 }]
      },
      options: {
        responsive: true, maintainAspectRatio: true,
        plugins: { legend: { position: 'right', labels: { font: { size: 11 }, padding: 12 } } },
        cutout: '60%'
      }
    });
  }
}

// ── Mark alert read ────────────────────────────────────────────
function markRead(id) {
  fetch('/api/alerts/' + id + '/read', { method: 'POST' })
    .then(() => { const el = document.getElementById('alert-' + id); if (el) el.style.opacity = '.5'; });
}

// ── Export report ──────────────────────────────────────────────
function exportReport() {
  window.open('/api/records', '_blank');
}

// ── Init ───────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initCharts();
  const ci = document.getElementById('chatInput');
  if (ci) ci.addEventListener('keydown', e => { if (e.key === 'Enter') sendChat(); });
  const fi = document.getElementById('fileInput');
  if (fi) fi.addEventListener('change', () => previewImage(fi));
});
