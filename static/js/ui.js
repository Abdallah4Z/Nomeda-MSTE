'use strict';

/* ── Nomeda — UI Rendering ── */

// ── Emotion Definitions ──
const EMOTIONS = [
  {
    id: 'happy', label: 'Happy', color: '#34d399',
    svg: '<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="24" cy="24" r="20"/><circle cx="17" cy="20" r="2.5" fill="currentColor" stroke="none"/><circle cx="31" cy="20" r="2.5" fill="currentColor" stroke="none"/><path d="M14 30 Q24 38 34 30"/></svg>'
  },
  {
    id: 'neutral', label: 'Neutral', color: '#fbbf24',
    svg: '<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="24" cy="24" r="20"/><circle cx="17" cy="20" r="2.5" fill="currentColor" stroke="none"/><circle cx="31" cy="20" r="2.5" fill="currentColor" stroke="none"/><line x1="16" y1="31" x2="32" y2="31"/></svg>'
  },
  {
    id: 'sad', label: 'Sad', color: '#60a5fa',
    svg: '<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="24" cy="24" r="20"/><circle cx="17" cy="20" r="2.5" fill="currentColor" stroke="none"/><circle cx="31" cy="20" r="2.5" fill="currentColor" stroke="none"/><path d="M16 34 Q24 28 32 34"/><path d="M35 18 Q37 14 35 12" stroke-width="1.5"/></svg>'
  },
  {
    id: 'anxious', label: 'Anxious', color: '#fca5a5',
    svg: '<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="24" cy="24" r="20"/><circle cx="17" cy="20" r="2.5" fill="currentColor" stroke="none"/><circle cx="31" cy="20" r="2.5" fill="currentColor" stroke="none"/><path d="M14 32 Q18 28 22 32 Q26 36 30 32 Q34 28 38 32" stroke-width="1.5"/></svg>'
  },
  {
    id: 'angry', label: 'Angry', color: '#f87171',
    svg: '<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="24" cy="24" r="20"/><circle cx="17" cy="20" r="2.5" fill="currentColor" stroke="none"/><circle cx="31" cy="20" r="2.5" fill="currentColor" stroke="none"/><line x1="14" y1="14" x2="20" y2="18"/><line x1="34" y1="14" x2="28" y2="18"/><line x1="16" y1="32" x2="32" y2="32"/></svg>'
  },
  {
    id: 'calm', label: 'Calm', color: '#22d3ee',
    svg: '<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="24" cy="24" r="20"/><path d="M14 20 Q17 18 20 20" fill="none"/><path d="M28 20 Q31 18 34 20" fill="none"/><path d="M16 31 Q24 37 32 31"/></svg>'
  }
];

const EMOTION_COLOR_MAP = {};
EMOTIONS.forEach(e => { EMOTION_COLOR_MAP[e.id] = e.color; EMOTION_COLOR_MAP[e.label] = e.color; });
EMOTION_COLOR_MAP['Idle'] = '#7a7a8c';

// ── Helpers ──
function escapeHtml(str) {
  if (!str) return '';
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

function formatTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatDuration(sec) {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
}

function getEmotionColor(label) {
  return EMOTION_COLOR_MAP[label] || '#7a7a8c';
}

// ── Emotion Grid ──
function renderEmotionGrid() {
  const grid = $('emotionGrid');
  grid.innerHTML = EMOTIONS.map(e =>
    '<div class="emotion-card" data-emotion="' + e.id + '">' +
      '<div class="emotion-color" style="color:' + e.color + '">' + e.svg + '</div>' +
      '<span class="emotion-label">' + e.label + '</span>' +
    '</div>'
  ).join('');

  grid.querySelectorAll('.emotion-card').forEach(card => {
    card.addEventListener('click', function () {
      grid.querySelectorAll('.emotion-card').forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      state.selectedEmotion = card.dataset.emotion;
      $('continueBtn').disabled = false;
    });
  });
}

// ── Messages ──
function addMessage(msg) {
  msg._id = ++state.msgCounter;
  state.session.messages.push(msg);
  renderMsg(msg);
  scrollBottom();
  const empty = $('chatEmpty');
  if (empty) empty.style.display = 'none';
}

function renderMsg(msg) {
  const c = $('chatMessages');
  const div = document.createElement('div');
  div.className = 'msg msg-' + msg.role;

  if (msg.role === 'user') {
    div.innerHTML =
      '<div class="msg-bubble">' +
        '<div class="msg-text">' + escapeHtml(msg.text) + '</div>' +
        '<div class="msg-meta">' +
          (msg.type === 'voice'
            ? '<svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>'
            : '') +
          (msg.emotion ? '<span style="color:' + getEmotionColor(msg.emotion) + '">' + msg.emotion + '</span>' : '') +
          '<span>' + formatTime(msg.timestamp) + '</span>' +
        '</div>' +
      '</div>' +
      '<div class="msg-avatar user">' +
        '<svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>' +
      '</div>';
  } else {
    div.innerHTML =
      '<div class="msg-avatar ai">' +
        '<svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a4 4 0 014 4v6a4 4 0 01-4 4 4 4 0 01-4-4V6a4 4 0 014-4z"/><path d="M12 16v4"/></svg>' +
      '</div>' +
      '<div class="msg-bubble">' +
        '<div class="ai-text">' + escapeHtml(msg.text) + '</div>' +
        buildFusion(msg.fusion) +
        (msg.rag ? '<div class="rag-card"><svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 016.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/></svg><span>' + escapeHtml(msg.rag) + '</span></div>' : '') +
        (msg.ttsAudio ? '<button class="tts-btn" data-id="' + msg._id + '"><svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>Listen</button>' : '') +
        '<div class="msg-meta"><span>' + formatTime(msg.timestamp) + '</span></div>' +
      '</div>';

    const tb = div.querySelector('.tts-btn');
    if (tb) {
      tb.addEventListener('click', function () {
        playTTS(msg);
      });
    }
  }

  c.appendChild(div);
}

function buildFusion(f) {
  if (!f) return '';
  let html = '<div class="fusion-bar">';
  if (f.face) {
    html += '<span class="fusion-chip">' +
      '<svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/></svg>' +
      escapeHtml(f.face) + '</span>';
  }
  if (f.voice) {
    html += '<span class="fusion-chip">' +
      '<svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>' +
      escapeHtml(f.voice) + '</span>';
  }
  if (f.distress !== undefined) {
    const d = Number(f.distress);
    const dc = d < 40 ? 'var(--success)' : d < 70 ? 'var(--warning)' : 'var(--danger)';
    html += '<span class="fusion-chip" style="color:' + dc + '">Distress: ' + d + '</span>';
  }
  html += '</div>';
  return html;
}

function scrollBottom() {
  const c = $('chatMessages');
  c.scrollTop = c.scrollHeight;
}

function showTyping() {
  const c = $('chatMessages');
  const d = document.createElement('div');
  d.className = 'msg msg-ai';
  d.id = 'typingIndicator';
  d.innerHTML =
    '<div class="msg-avatar ai">' +
    '<svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a4 4 0 014 4v6a4 4 0 01-4 4 4 4 0 01-4-4V6a4 4 0 014-4z"/><path d="M12 16v4"/></svg>' +
    '</div>' +
    '<div class="msg-bubble"><div style="display:flex;gap:4px;padding:0.25rem 0">' +
      '<span style="width:6px;height:6px;border-radius:50%;background:var(--text-dim);animation:bounce 1.2s infinite"></span>' +
      '<span style="width:6px;height:6px;border-radius:50%;background:var(--text-dim);animation:bounce 1.2s 0.2s infinite"></span>' +
      '<span style="width:6px;height:6px;border-radius:50%;background:var(--text-dim);animation:bounce 1.2s 0.4s infinite"></span>' +
    '</div></div>';
  c.appendChild(d);
  scrollBottom();
}

function hideTyping() {
  const el = $('typingIndicator');
  if (el) el.remove();
}

// ── Summary ──
function renderSummary(data) {
  const st = data.stats || {};
  $('statDuration').textContent = formatDuration(data.duration_seconds || 0);
  $('statMessages').textContent = st.message_count || 0;
  $('statAvgDistress').textContent = st.avg_distress || 0;
  $('statDominant').textContent = st.dominant_emotion || '\u2014';
  $('jsonPreview').textContent = JSON.stringify(data, null, 2);

  $('copyBtn').onclick = function () {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2)).then(function () {
      $('copyBtnText').textContent = 'Copied!';
      $('copyBtn').classList.add('copied');
      setTimeout(function () {
        $('copyBtnText').textContent = 'Copy';
        $('copyBtn').classList.remove('copied');
      }, 2000);
    });
  };

  $('sendSummaryBtn').onclick = async function () {
    const email = $('emailInput').value.trim();
    if (!email) { $('emailInput').focus(); return; }
    $('sendSummaryBtn').disabled = true;
    $('sendSummaryText').textContent = 'Sending...';
    try {
      await fetch('/api/session/send-summary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email, summary: data })
      });
      $('sendSummaryText').textContent = 'Sent!';
    } catch (e) {
      $('sendSummaryBtn').disabled = false;
      $('sendSummaryText').textContent = 'Send Summary';
    }
  };

  $('downloadBtn').onclick = async function () {
    $('downloadBtn').disabled = true;
    $('downloadBtnText').textContent = 'Generating...';

    try {
      var res = await fetch('/api/session/report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ summary: data })
      });
      var result = await res.json();
      var content = '';

      if (result.report) {
        content = 'Session Report\n' +
          '==============\n\n' +
          result.report + '\n\n' +
          '---\n' +
          'Generated by AI Therapist. ' + new Date().toLocaleString() + '\n' +
          'https://github.com/AnomalyCo/Nomeda-MSTE\n';
      } else {
        content = JSON.stringify(data, null, 2);
      }

      var blob = new Blob([content], { type: result.report ? 'text/plain' : 'application/json' });
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = result.report
        ? 'session-report-' + (data.session_id || 'summary') + '.txt'
        : 'session-data-' + (data.session_id || 'summary') + '.json';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      $('downloadBtnText').textContent = result.report ? 'Downloaded' : 'Downloaded (Raw)';
    } catch (e) {
      var blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = 'session-data-' + (data.session_id || 'summary') + '.json';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      $('downloadBtnText').textContent = 'Downloaded (Raw)';
    }

    setTimeout(function () {
      $('downloadBtn').disabled = false;
      $('downloadBtnText').textContent = 'Download Report';
    }, 3000);
  };

  $('homeBtn').onclick = goHome;
}

// ── Header Status ──
function setHeaderStatus(connected) {
  const dot = $('headerStatusDot');
  const txt = $('headerStatusText');
  dot.className = 'status-dot' + (connected ? ' live' : '');
  txt.textContent = connected ? 'Live' : 'Connecting';
}
