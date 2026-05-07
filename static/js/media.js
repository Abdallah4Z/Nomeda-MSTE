'use strict';

/* ── Nomeda — Media & Connection ── */

const WS_RECONNECT_DELAY = 2000;
const FRAME_INTERVAL = 66;

// ── Camera ──
async function initCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    state.browserStream = stream;
    const v = document.createElement('video');
    v.autoplay = true;
    v.muted = true;
    v.playsInline = true;
    v.srcObject = stream;
    state.browserVideo = v;
    state.browserCanvas = document.createElement('canvas');
    state.browserCanvas.width = 320;
    state.browserCanvas.height = 240;
    await v.play();

    $('pipFeed').src = '/video_feed?' + Date.now();
    $('pipFeed').style.display = '';
    $('pipPlaceholder').style.display = 'none';

    if (state.frameTimer) clearInterval(state.frameTimer);
    state.frameTimer = setInterval(sendFrame, FRAME_INTERVAL);
  } catch (e) {
    console.warn('Camera not available:', e);
  }
}

async function sendFrame() {
  if (!state.browserVideo || !state.browserCanvas || state.browserVideo.readyState < 2) return;
  const ctx = state.browserCanvas.getContext('2d');
  if (!ctx) return;
  ctx.drawImage(state.browserVideo, 0, 0, 320, 240);
  try {
    const blob = await new Promise(function (r) { state.browserCanvas.toBlob(r, 'image/jpeg', 0.7); });
    if (!blob) return;
    const fd = new FormData();
    fd.append('frame', blob, 'frame.jpg');
    await fetch('/api/browser-frame', { method: 'POST', body: fd });
  } catch (e) { /* silent */ }
}

function stopCamera() {
  if (state.frameTimer) { clearInterval(state.frameTimer); state.frameTimer = null; }
  if (state.browserStream) { state.browserStream.getTracks().forEach(function (t) { t.stop(); }); state.browserStream = null; }
  state.browserVideo = null;
  state.browserCanvas = null;
}

// ── Voice Recording ──
function initVoiceRecord(btnEl, onResult) {
  btnEl.onpointerdown = null;
  btnEl.onpointerup = null;
  btnEl.onpointerleave = null;

  let recording = false;

  function stop() {
    if (!recording) return;
    recording = false;
    btnEl.classList.remove('recording');
    var span = btnEl.querySelector('span');
    if (span) span.textContent = 'Hold to record';
    if (state.mediaRecorder && state.mediaRecorder.state !== 'inactive') {
      state.mediaRecorder.stop();
    }
  }

  btnEl.onpointerdown = async function (e) {
    e.preventDefault();
    if (recording) return;
    recording = true;
    btnEl.classList.add('recording');
    var span = btnEl.querySelector('span');
    if (span) span.textContent = 'Recording...';

    state.audioChunks = [];
    try {
      var stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      state.recordingStream = stream;
      var mt = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm';
      var mr = new MediaRecorder(stream, { mimeType: mt });
      state.mediaRecorder = mr;
      mr.ondataavailable = function (e) { if (e.data.size > 0) state.audioChunks.push(e.data); };
      mr.onstop = async function () {
        stream.getTracks().forEach(function (t) { t.stop(); });
        state.recordingStream = null;
        if (state.audioChunks.length === 0) return;
        var blob = new Blob(state.audioChunks, { type: 'audio/webm' });
        state.audioChunks = [];
        if (onResult) await onResult(blob);
      };
      mr.start();
    } catch (err) {
      console.error('Voice mic error:', err);
      btnEl.classList.remove('recording');
      if (span) span.textContent = 'Hold to record';
      recording = false;
    }
  };

  btnEl.onpointerup = stop;
  btnEl.onpointerleave = stop;
}

// ── WebSocket ──
function connectWS() {
  if (state.ws) try { state.ws.close(); } catch (e) { /* ignore */ }
  var proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  var ws = new WebSocket(proto + '//' + location.host + '/ws');
  state.ws = ws;

  ws.onopen = function () {
    state.connected = true;
    setHeaderStatus(true);
  };

  ws.onmessage = function (e) {
    try {
      var d = JSON.parse(e.data);
      state.session.isRunning = d.running;
      if (d.distress !== undefined) {
        state.emotionHistory.push({
          time: Date.now(),
          face: d.video_emotion || 'Idle',
          voice: d.voice_emotion || 'Idle',
          distress: Number(d.distress) || 0
        });
        if (state.emotionHistory.length > 200) state.emotionHistory.splice(0, 50);
        if (d.video_emotion && d.video_emotion !== 'Idle' && typeof Face !== 'undefined') {
          Face.setEmotion(d.video_emotion, d.distress);
        }
      }
    } catch (_) { /* ignore */ }
  };

  ws.onclose = function () {
    state.connected = false;
    setHeaderStatus(false);
    state.ws = null;
    setTimeout(connectWS, WS_RECONNECT_DELAY);
  };

  ws.onerror = function () { if (ws) ws.close(); };
}
