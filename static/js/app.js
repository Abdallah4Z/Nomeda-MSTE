'use strict';

/* ── Nomeda — Application Core ── */

// ── State ──
const state = {
  screen: 'checkin',
  session: {
    id: null,
    startTime: null,
    messages: [],
    emotionHistory: [],
    isRunning: false
  },
  ws: null,
  connected: false,
  selectedEmotion: null,
  pipVisible: true,
  currentAudio: null,
  sessionData: null,
  timerInterval: null,
  browserStream: null,
  browserVideo: null,
  browserCanvas: null,
  frameTimer: null,
  mediaRecorder: null,
  audioChunks: [],
  recordingStream: null,
  msgCounter: 0
};

// ── DOM Cache ──
function $(id) { return document.getElementById(id); }

// ── Init ──
document.addEventListener('DOMContentLoaded', function () {
  if (location.search.indexOf('reset') >= 0) {
    localStorage.removeItem('nomeda_skip_checkin');
  }
  var skip = localStorage.getItem('nomeda_skip_checkin') === 'true';
  if (skip) showChat();
  else showCheckin();
});

// ── Screen Routing ──
function showScreen(id) {
  document.querySelectorAll('.screen').forEach(function (el) { el.classList.remove('active'); });
  $(id).classList.add('active');
  state.screen = id.replace('screen-', '');
}

function showCheckin() {
  showScreen('screen-checkin');
  renderEmotionGrid();
  $('checkinText').value = '';
  $('continueBtn').disabled = true;
  $('checkinVoiceBtn').classList.remove('recording');
  var span = $('checkinVoiceBtn').querySelector('span');
  if (span) span.textContent = 'Hold to record';
  $('checkinVoiceStatus').classList.remove('visible');
  state.selectedEmotion = null;
  $('continueBtnText').textContent = 'Continue';
  $('endBtnText').textContent = 'End';
  $('endBtn').disabled = false;
  $('sendSummaryText').textContent = 'Send Summary';
  $('sendSummaryBtn').disabled = false;
  $('copyBtnText').textContent = 'Copy';
  $('copyBtn').classList.remove('copied');

  $('continueBtn').onclick = submitCheckin;
  $('skipBtn').onclick = skipCheckin;
  initCheckinVoice();
}

function skipCheckin() {
  localStorage.setItem('nomeda_skip_checkin', 'true');
  state.session.checkin = null;
  showChat();
}

function showChat() {
  showScreen('screen-chat');
  initChat();
}

function showSummary(data) {
  showScreen('screen-summary');
  renderSummary(data);
}

function goHome() {
  state.session = { id: null, startTime: null, messages: [], emotionHistory: [], isRunning: false };
  state.emotionHistory = [];
  state.msgCounter = 0;
  $('chatMessages').innerHTML =
    '<div class="chat-empty" id="chatEmpty">' +
    '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/></svg>' +
    '<p>Your session is ready. How are you feeling?</p></div>';
  $('timerDisplay').textContent = '00:00';
  showCheckin();
}

// ── Check-in Submit ──
async function submitCheckin() {
  var emotion = state.selectedEmotion;
  var text = $('checkinText').value.trim();
  $('continueBtn').disabled = true;
  $('continueBtnText').textContent = 'Starting...';

  state.session.checkin = { emotion: emotion, text: text };

  try {
    var res = await fetch('/api/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ checkin: { emotion: emotion, text: text } })
    });
    if (res.ok) {
      var data = await res.json();
      state.session.id = data.session_id || 'sess_' + Date.now();
    }
  } catch (e) {
    console.warn('Start session error (backend may not be ready):', e);
    state.session.id = 'sess_' + Date.now();
  }

  state.session.isRunning = true;
  showChat();
}

// ── Checkin Voice ──
function initCheckinVoice() {
  initVoiceRecord($('checkinVoiceBtn'), async function (blob) {
    var fd = new FormData();
    fd.append('audio', blob, 'voice.webm');
    try {
      var res = await fetch('/api/voice-note', { method: 'POST', body: fd });
      if (res.ok) {
        var data = await res.json();
        if (data.transcript) {
          var ta = $('checkinText');
          ta.value = (ta.value + ' ' + data.transcript).trim();
        }
        var st = $('checkinVoiceStatus');
        st.textContent = data.emotion ? 'Voice: ' + data.emotion : 'Voice note added';
        st.classList.add('visible');
      }
    } catch (e) {
      $('checkinVoiceStatus').textContent = 'Voice note recorded';
      $('checkinVoiceStatus').classList.add('visible');
    }
  });
}

// ── Chat ──
async function initChat() {
  var checkin = state.session.checkin;
  if (checkin && checkin.emotion) {
    addMessage({
      role: 'user',
      text: checkin.text || 'Feeling ' + checkin.emotion,
      type: 'checkin',
      emotion: checkin.emotion,
      timestamp: new Date().toISOString()
    });
  }

  initCamera();
  connectWS();
  startTimer();
  initFace();
  initChatInput();
  initChatVoice();
  initTimeline();

  $('endBtn').onclick = endSession;
  $('summaryBtn').onclick = function () {
    if (state.sessionData) showSummary(state.sessionData);
  };
  $('pipToggle').onclick = function (e) {
    e.stopPropagation();
    state.pipVisible = false;
    $('videoPip').classList.add('collapsed');
  };
  $('videoPip').onclick = function () {
    if (!state.pipVisible) {
      state.pipVisible = true;
      $('videoPip').classList.remove('collapsed');
    }
  };
}

function initFace() {
  var el = $('robotFace');
  if (!el) return;
  try {
    Face.init(el);
    var ci = state.session.checkin;
    if (ci && ci.emotion) {
      Face.setEmotion(ci.emotion, 30);
    } else {
      Face.setExpression('idle');
    }
  } catch (e) {
    console.warn('Face init failed:', e);
  }
}

function initChatInput() {
  var inp = $('chatInput');
  var btn = $('sendBtn');

  inp.onfocus = function () { Face.setExpression('listening'); };
  inp.oninput = function () { btn.disabled = !inp.value.trim(); };
  inp.onkeydown = function (e) {
    if (e.key === 'Enter' && !e.shiftKey && inp.value.trim()) {
      e.preventDefault();
      sendMessage(inp.value.trim());
    }
  };
  btn.onclick = function () {
    if (inp.value.trim()) sendMessage(inp.value.trim());
  };
}

async function sendMessage(text) {
  $('chatInput').value = '';
  $('sendBtn').disabled = true;

  addMessage({ role: 'user', text: text, type: 'text', timestamp: new Date().toISOString() });
  showTyping();
  Face.setExpression('thinking');

  try {
    var res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text })
    });
    hideTyping();
    if (res.ok) {
      var data = await res.json();
      addMessage({
        role: 'ai',
        text: data.response || 'I\'m here with you.',
        fusion: { face: data.face_emotion, voice: data.voice_emotion, distress: data.distress },
        rag: data.rag_sources && data.rag_sources.length > 0 ? data.rag_sources[0].text : null,
        ttsAudio: data.tts_audio_url || data.tts_audio_b64 || null,
        timestamp: new Date().toISOString()
      });
      if (data.tts_audio_url || data.tts_audio_b64) {
        Face.setExpression('talking');
      } else {
        Face.setExpression('listening');
      }
    } else {
      Face.setExpression('listening');
    }
  } catch (e) {
    hideTyping();
    Face.setExpression('listening');
    console.warn('Chat error (backend endpoint may not exist yet):', e);
    addMessage({
      role: 'ai',
      text: 'I\'m here with you. Tell me more about how you\'re feeling.',
      fusion: { face: '\u2014', voice: '\u2014', distress: 0 },
      timestamp: new Date().toISOString()
    });
  }
}

function initChatVoice() {
  initVoiceRecord($('chatVoiceBtn'), async function (blob) {
    var fd = new FormData();
    fd.append('audio', blob, 'voice.webm');
    try {
      var res = await fetch('/api/voice-note', { method: 'POST', body: fd });
      if (res.ok) {
        var data = await res.json();
        if (data.transcript) sendMessage(data.transcript);
      }
    } catch (e) { /* silent */ }
  });
}

function initTimeline() {
  $('timelineToggle').onclick = function () {
    $('timelineBar').classList.toggle('open');
  };
}

// ── TTS ──
function playTTS(msg) {
  if (state.currentAudio) { state.currentAudio.pause(); state.currentAudio = null; }
  if (!msg.ttsAudio) return;

  Face.startTalking();
  var btn = document.querySelector('.tts-btn[data-id="' + msg._id + '"]');
  try {
    var audio = new Audio(msg.ttsAudio);
    state.currentAudio = audio;
    if (btn) btn.classList.add('playing');
    audio.addEventListener('ended', function () {
      if (btn) btn.classList.remove('playing');
      state.currentAudio = null;
      Face.stopTalking();
      Face.setExpression('listening');
    });
    audio.addEventListener('error', function () {
      if (btn) btn.classList.remove('playing');
      state.currentAudio = null;
      Face.stopTalking();
    });
    audio.play().catch(function () {
      if (btn) btn.classList.remove('playing');
      Face.stopTalking();
    });
  } catch (e) {
    console.warn('TTS error:', e);
    Face.stopTalking();
  }
}

// ── Timer ──
function startTimer() {
  state.session.startTime = Date.now();
  if (state.timerInterval) clearInterval(state.timerInterval);
  state.timerInterval = setInterval(function () {
    var e = Math.floor((Date.now() - state.session.startTime) / 1000);
    $('timerDisplay').textContent = formatDuration(e);
  }, 1000);
}

function stopTimer() {
  if (state.timerInterval) { clearInterval(state.timerInterval); state.timerInterval = null; }
}

// ── End Session ──
async function endSession() {
  $('endBtn').disabled = true;
  $('endBtnText').textContent = 'Ending...';

  hideTyping();
  stopCamera();
  stopTimer();
  if (state.ws) { state.ws.close(); state.ws = null; }

  var summary = {
    session_id: state.session.id,
    duration_seconds: state.session.startTime ? Math.floor((Date.now() - state.session.startTime) / 1000) : 0,
    checkin: state.session.checkin,
    messages: state.session.messages,
    emotion_timeline: state.emotionHistory,
    stats: calcStats()
  };

  try {
    var res = await fetch('/api/session/end', { method: 'POST' });
    if (res.ok) {
      var data = await res.json();
      Object.assign(summary, data);
    }
  } catch (e) { /* use local summary */ }

  state.sessionData = summary;
  showSummary(summary);
}

function calcStats() {
  var userMsgs = state.session.messages.filter(function (m) { return m.role === 'user'; });
  var dists = state.emotionHistory.map(function (t) { return t.distress; }).filter(function (d) { return d !== undefined; });
  var avgDist = dists.length > 0 ? Math.round(dists.reduce(function (a, b) { return a + b; }, 0) / dists.length) : 0;

  var counts = {};
  state.emotionHistory.forEach(function (t) {
    if (t.face && t.face !== 'Idle') counts[t.face] = (counts[t.face] || 0) + 1;
  });
  var dominant = '\u2014';
  var max = 0;
  Object.entries(counts).forEach(function (entry) {
    if (entry[1] > max) { max = entry[1]; dominant = entry[0]; }
  });

  return { message_count: userMsgs.length, avg_distress: avgDist, dominant_emotion: dominant };
}

// ── Cleanup ──
window.addEventListener('beforeunload', function () {
  stopCamera();
  if (state.recordingStream) state.recordingStream.getTracks().forEach(function (t) { t.stop(); });
  if (state.ws) state.ws.close();
});
