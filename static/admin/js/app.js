'use strict';

/* ── Nomeda — Admin Panel ── */

// ── State ──
const state = {
  tab: 'dashboard',
  sessions: [],
  logs: [],
  logFilter: 'all',
  config: {},
  models: []
};

// ── DOM Cache ──
const $ = id => document.getElementById(id);

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
  initNav();
  loadDashboard();
});

// ── Tab Navigation ──
function initNav() {
  const nav = $('sidebarNav');
  nav.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
      nav.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const tab = btn.dataset.tab;
      state.tab = tab;
      document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
      const content = $('tab-' + tab);
      if (content) content.classList.add('active');

      // Lazy load
      switch (tab) {
        case 'dashboard': loadDashboard(); break;
        case 'config': loadConfig(); break;
        case 'history': loadHistory(); break;
        case 'logs': loadLogs(); break;
        case 'models': loadModels(); break;
      }
    });
  });
}

// ── Toast ──
function showToast(msg, type) {
  const t = $('toast');
  t.textContent = msg;
  t.className = 'toast show ' + (type || '');
  clearTimeout(t._hide);
  t._hide = setTimeout(() => { t.classList.remove('show'); }, 3000);
}

// ── API Helper ──
async function api(url, opts) {
  try {
    const res = await fetch(url, opts || {});
    if (!res.ok) {
      if (res.status === 404) return null;
      throw new Error(res.statusText);
    }
    return await res.json();
  } catch (e) {
    if (e.message === 'Failed to fetch') return null;
    console.warn('API error:', url, e.message);
    return null;
  }
}

// ── Format helpers ──
function fmtTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString();
}

function fmtDuration(sec) {
  if (!sec && sec !== 0) return '—';
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return m + 'm ' + s + 's';
}

function escapeHtml(str) {
  if (!str) return '';
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

// ════════════════════════════════════════════════════════════════
//  DASHBOARD
// ════════════════════════════════════════════════════════════════

async function loadDashboard() {
  const status = await api('/api/admin/status');

  if (!status) {
    $('dashStatus').textContent = 'Offline';
    $('dashStatus').className = 'badge badge-yellow';
    $('dashStatusDetail').textContent = 'Backend not reachable';
    $('dashSessions').textContent = '—';
    $('dashAvgDistress').textContent = '—';
    $('dashModels').textContent = '—';
    return;
  }

  $('dashStatus').textContent = status.running ? 'Running' : 'Idle';
  $('dashStatus').className = 'badge ' + (status.running ? 'badge-green' : 'badge-gray');
  $('dashStatusDetail').textContent = status.running ? 'Session active' : 'No active session';
  $('dashSessions').textContent = status.total_sessions || 0;
  $('dashAvgDistress').textContent = status.avg_distress !== undefined ? status.avg_distress : '—';
  $('dashModels').textContent = (status.models_ready || 0) + '/' + (status.models_total || 0);

  // Recent sessions table
  if (status.recent_sessions && status.recent_sessions.length > 0) {
    const tbody = $('dashRecentTable');
    tbody.innerHTML = status.recent_sessions.slice(0, 5).map(s =>
      '<tr><td>' + fmtTime(s.timestamp) + '</td><td>' + fmtDuration(s.duration) + '</td>' +
      '<td>' + escapeHtml(s.emotion || '—') + '</td><td>' + (s.distress || '—') + '</td>' +
      '<td>' + (s.messages || 0) + '</td></tr>'
    ).join('');
  }
}

// ════════════════════════════════════════════════════════════════
//  CONFIG
// ════════════════════════════════════════════════════════════════

async function loadConfig() {
  const cfg = await api('/api/admin/config');
  if (!cfg) {
    // Show defaults
    $('cfgLlmMode').value = 'local';
    $('cfgGroqKey').value = 'Not configured';
    $('cfgMaxTokens').value = '256';
    $('cfgTemp').value = '0.7';
    $('cfgTtsBackend').value = 'gemini';
    $('cfgTtsThreshold').value = '0';
    $('cfgCamSource').value = 'browser';
    $('cfgCamId').value = '0';
    return;
  }
  state.config = cfg;
  if ($('cfgLlmMode')) $('cfgLlmMode').value = cfg.llm_mode || 'local';
  if ($('cfgGroqKey')) $('cfgGroqKey').value = cfg.groq_key ? '••••••••' : 'Not set';
  if ($('cfgMaxTokens')) $('cfgMaxTokens').value = cfg.max_tokens || 256;
  if ($('cfgTemp')) $('cfgTemp').value = cfg.temperature || 0.7;
  if ($('cfgTtsBackend')) $('cfgTtsBackend').value = cfg.tts_backend || 'gemini';
  if ($('cfgTtsThreshold')) $('cfgTtsThreshold').value = cfg.tts_threshold || 0;
  if ($('cfgCamSource')) $('cfgCamSource').value = cfg.camera_source || 'browser';
  if ($('cfgCamId')) $('cfgCamId').value = cfg.camera_id || 0;
}

async function saveConfig() {
  const body = {
    llm_mode: $('cfgLlmMode').value,
    max_tokens: parseInt($('cfgMaxTokens').value) || 256,
    temperature: parseFloat($('cfgTemp').value) || 0.7,
    tts_backend: $('cfgTtsBackend').value,
    tts_threshold: parseInt($('cfgTtsThreshold').value) || 0,
    camera_source: $('cfgCamSource').value,
    camera_id: parseInt($('cfgCamId').value) || 0
  };

  const btn = document.querySelector('#tab-config .btn-primary');
  btn.disabled = true;
  btn.innerHTML = '<span class="loader" style="width:1rem;height:1rem"></span> Saving...';

  try {
    const res = await api('/api/admin/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    if (res !== null) {
      showToast('Configuration saved', 'success');
    } else {
      showToast('Saved locally (backend not available)', '');
    }
  } catch (e) {
    showToast('Save failed: ' + e.message, 'error');
  }

  btn.disabled = false;
  btn.innerHTML = '<svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg> Save';
}

// ════════════════════════════════════════════════════════════════
//  HISTORY
// ════════════════════════════════════════════════════════════════

async function loadHistory() {
  const tbody = $('historyTable');
  tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:2rem"><span class="loader" style="margin-right:0.5rem"></span>Loading...</td></tr>';

  const data = await api('/api/admin/history');
  if (!data || !data.sessions) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-dim);padding:2rem">No sessions found</td></tr>';
    state.sessions = [];
    return;
  }

  state.sessions = data.sessions || [];
  renderHistory();
}

function renderHistory() {
  const tbody = $('historyTable');
  const query = ($('historySearch').value || '').toLowerCase();
  const filter = $('historyFilter').value;

  let rows = state.sessions;
  if (query) rows = rows.filter(s => JSON.stringify(s).toLowerCase().includes(query));
  if (filter !== 'all') rows = rows.filter(s => (s.emotion || '').toLowerCase() === filter.toLowerCase());

  if (rows.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-dim);padding:2rem">No sessions match your filters</td></tr>';
    return;
  }

  tbody.innerHTML = rows.map(s =>
    '<tr>' +
      '<td>' + (s.date || fmtTime(s.timestamp).split(',')[0] || '—') + '</td>' +
      '<td>' + (s.time || (s.timestamp ? fmtTime(s.timestamp).split(',')[1] || '' : '') || '—') + '</td>' +
      '<td>' + fmtDuration(s.duration) + '</td>' +
      '<td>' + escapeHtml(s.emotion || '—') + '</td>' +
      '<td>' + (s.avg_distress !== undefined ? s.avg_distress : (s.distress || '—')) + '</td>' +
      '<td>' + (s.messages || 0) + '</td>' +
      '<td><button class="btn btn-sm btn-secondary" onclick="viewSession(\'' + (s.id || '') + '\')">View</button></td>' +
    '</tr>'
  ).join('');
}

function filterHistory() {
  renderHistory();
}

async function viewSession(id) {
  const modal = $('sessionModal');
  const title = $('sessionModalTitle');
  const body = $('sessionModalBody');
  modal.classList.add('open');
  title.textContent = 'Session #' + id;
  body.innerHTML = '<p style="color:var(--text-muted)"><span class="loader"></span> Loading...</p>';

  const data = await api('/api/admin/history/' + id);
  if (!data) {
    body.innerHTML = '<p style="color:var(--text-muted)">Session data not available (backend endpoint not ready)</p>';
    return;
  }

  let html = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;margin-bottom:1rem">';
  html += '<div class="stat-card"><div class="stat-label">Duration</div><div class="stat-value" style="font-size:1rem">' + fmtDuration(data.duration) + '</div></div>';
  html += '<div class="stat-card"><div class="stat-label">Emotion</div><div class="stat-value" style="font-size:1rem">' + escapeHtml(data.emotion || '—') + '</div></div>';
  html += '<div class="stat-card"><div class="stat-label">Distress</div><div class="stat-value" style="font-size:1rem">' + (data.avg_distress || data.distress || '—') + '</div></div>';
  html += '<div class="stat-card"><div class="stat-label">Messages</div><div class="stat-value" style="font-size:1rem">' + (data.messages || 0) + '</div></div>';
  html += '</div>';

  if (data.checkin) {
    html += '<div class="card-title">Check-in</div><p style="font-size:0.875rem;margin-bottom:0.75rem">Emotion: ' + escapeHtml(data.checkin.emotion || '—') + '</p>';
    if (data.checkin.text) html += '<p style="font-size:0.8125rem;color:var(--text-muted);margin-bottom:1rem">' + escapeHtml(data.checkin.text) + '</p>';
  }

  if (data.transcript && data.transcript.length > 0) {
    html += '<div class="card-title">Conversation</div>';
    html += '<div style="max-height:200px;overflow-y:auto;font-size:0.8125rem">';
    data.transcript.forEach(msg => {
      html += '<div style="padding:0.375rem 0;border-bottom:1px solid var(--border)">';
      html += '<span style="color:' + (msg.role === 'user' ? 'var(--accent-light)' : 'var(--cyan)') + ';font-weight:600">' + msg.role + ':</span> ';
      html += escapeHtml(msg.text);
      html += '</div>';
    });
    html += '</div>';
  }

  body.innerHTML = html;
}

function closeSessionModal() {
  $('sessionModal').classList.remove('open');
}

// ════════════════════════════════════════════════════════════════
//  LOGS
// ════════════════════════════════════════════════════════════════

async function loadLogs() {
  const viewer = $('logViewer');
  viewer.innerHTML = '<div class="log-line log-info"><span class="loader"></span> Loading...</div>';

  const data = await api('/api/admin/logs?level=' + state.logFilter);
  if (!data || !data.logs) {
    viewer.innerHTML = '<div class="log-line log-info"><span class="log-time">[--:--:--]</span> Log endpoint not available</div>';
    state.logs = [];
    return;
  }

  state.logs = data.logs || [];
  renderLogs();
}

function renderLogs() {
  const viewer = $('logViewer');
  const filtered = state.logs.filter(l => state.logFilter === 'all' || l.level === state.logFilter);

  if (filtered.length === 0) {
    viewer.innerHTML = '<div class="log-line log-info"><span class="log-time">[--:--:--]</span> No log entries</div>';
    return;
  }

  viewer.innerHTML = filtered.slice(-200).map(l =>
    '<div class="log-line log-' + (l.level || 'info') + '">' +
      '<span class="log-time">[' + (l.time || l.timestamp || '--:--:--') + ']</span>' +
      escapeHtml(l.message || '') +
    '</div>'
  ).join('');
  viewer.scrollTop = viewer.scrollHeight;
}

function setLogFilter(level, btn) {
  state.logFilter = level;
  document.querySelectorAll('.log-filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderLogs();
}

function clearLogs() {
  state.logs = [];
  $('logViewer').innerHTML = '<div class="log-line log-info"><span class="log-time">[--:--:--]</span> Cleared</div>';
}

// ════════════════════════════════════════════════════════════════
//  MODELS
// ════════════════════════════════════════════════════════════════

async function loadModels() {
  const container = $('modelsContainer');
  container.innerHTML = '<div class="empty-state"><span class="loader"></span><p>Loading models...</p></div>';

  const data = await api('/api/admin/models');
  if (!data || !data.models) {
    container.innerHTML = '<div class="empty-state"><svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg><p>Model status endpoint not available</p></div>';
    state.models = [];
    return;
  }

  state.models = data.models || [];
  renderModels();
}

function renderModels() {
  const container = $('modelsContainer');
  if (state.models.length === 0) {
    container.innerHTML = '<div class="empty-state"><p>No models configured</p></div>';
    return;
  }

  container.innerHTML = state.models.map(m => {
    const statusClass = m.status === 'ready' ? 'ready' : m.status === 'loading' ? 'loading' : 'error';
    const badgeClass = m.status === 'ready' ? 'badge-green' : m.status === 'loading' ? 'badge-yellow' : 'badge-red';
    const badgeText = m.status === 'ready' ? 'Ready' : m.status === 'loading' ? 'Loading' : 'Error';
    return '<div class="model-card">' +
      '<div class="model-icon ' + statusClass + '">' +
        (m.status === 'ready'
          ? '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>'
          : m.status === 'loading'
          ? '<span class="loader"></span>'
          : '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>') +
      '</div>' +
      '<div class="model-info">' +
        '<div class="model-name">' + escapeHtml(m.name || 'Unknown') + '</div>' +
        '<div class="model-desc">' + escapeHtml(m.description || '') + '</div>' +
      '</div>' +
      '<div class="model-status"><span class="badge ' + badgeClass + '">' + badgeText + '</span></div>' +
    '</div>';
  }).join('');
}

// ════════════════════════════════════════════════════════════════
//  GLOBAL
// ════════════════════════════════════════════════════════════════

function refreshAll() {
  loadDashboard();
  showToast('Refreshed', 'success');
}
