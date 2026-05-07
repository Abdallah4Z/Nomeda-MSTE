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

    var pipFeed = $('pipFeed');
    pipFeed.src = '/video_feed';
    pipFeed.style.display = '';
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

// ── Continuous Audio Streaming for Live SER ──
var audioCtx = null;
var audioStream = null;
var audioUploadTimer = null;

async function initLiveAudio() {
  try {
    audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    var src = audioCtx.createMediaStreamSource(audioStream);
    var processor = audioCtx.createScriptProcessor(4096, 1, 1);
    processor.onaudioprocess = function (e) {
      var input = e.inputBuffer.getChannelData(0);
      var buf = new ArrayBuffer(input.length * 2);
      var view = new Int16Array(buf);
      for (var i = 0; i < input.length; i++) {
        var s = Math.max(-1, Math.min(1, input[i]));
        view[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
      }
      var fd = new FormData();
      fd.append('audio', new Blob([buf], { type: 'audio/wav' }), 'chunk.raw');
      fetch('/api/browser-audio', { method: 'POST', body: fd }).catch(function () {});
    };
    src.connect(processor);
    processor.connect(audioCtx.destination);
    console.log('[Audio] Live SER streaming started');
  } catch (e) {
    console.warn('[Audio] Live mic not available:', e);
  }
}

function stopLiveAudio() {
  if (audioStream) { audioStream.getTracks().forEach(function (t) { t.stop(); }); audioStream = null; }
  if (audioCtx) { audioCtx.close(); audioCtx = null; }
}
var tlChart = null;

function initTimelineChart() {
  var canvas = document.getElementById('timelineChart');
  if (!canvas || typeof Chart === 'undefined') {
    // Retry in 1s if chart.js not yet loaded
    setTimeout(initTimelineChart, 1000);
    return;
  }
  if (tlChart) { tlChart.destroy(); tlChart = null; }
  tlChart = new Chart(canvas, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        { label: 'Face', data: [], borderColor: '#6366f1', backgroundColor: 'rgba(99,102,241,0.1)', borderWidth: 2, pointRadius: 0, tension: 0.3, fill: false, spanGaps: false },
        { label: 'Voice', data: [], borderColor: '#22d3ee', backgroundColor: 'rgba(34,211,238,0.1)', borderWidth: 2, pointRadius: 0, tension: 0.3, fill: false, spanGaps: false }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: true, labels: { color: '#aaa', font: { size: 9 }, boxWidth: 12 } } },
      scales: {
        x: { display: true, ticks: { color: '#555', font: { size: 7 }, maxTicksLimit: 6, maxRotation: 0 } },
        y: { min: 0, max: 7, ticks: { stepSize: 1, color: '#555', font: { size: 8 },
              callback: function(v) { return {0:'Ang',1:'Fer',2:'Dis',3:'Sad',4:'Neu',5:'Cal',6:'Hap',7:'Sur'}[v]||v; }
            }
        }
      },
      animation: { duration: 150 }
    }
  });
  console.log('[Timeline] Chart initialized');
}

var emotionValue = { 'angry':0,'anger':0,'fear':1,'disgust':2,'sad':3,'neutral':4,'calm':5,'happy':6,'surprised':7,
                     'Angry':0,'Anger':0,'Fear':1,'Disgust':2,'Sad':3,'Neutral':4,'Calm':5,'Happy':6,'Surprised':7,
                     'Anxious':1, 'No Face Detected':null, 'No Frame':null, 'Idle':null };

function updateTimeline(voiceEmotion, faceEmotion, distress) {
  // Always update live labels — even when timeline panel is closed
  var fl = document.getElementById('tlFaceLabel');
  var vl = document.getElementById('tlVoiceLabel');
  var fLabel = faceEmotion && faceEmotion !== 'Idle' ? faceEmotion : '--';
  var vLabel = voiceEmotion && voiceEmotion !== 'Idle' ? voiceEmotion : '--';
  if (fl) fl.innerHTML = '<span class="dot face"></span>Face: ' + fLabel;
  if (vl) vl.innerHTML = '<span class="dot voice"></span>Voice: ' + vLabel;

  if (!tlChart) return;
  var now = new Date().toLocaleTimeString();
  var v = emotionValue[voiceEmotion] !== undefined ? emotionValue[voiceEmotion] : null;
  var f = emotionValue[faceEmotion] !== undefined ? emotionValue[faceEmotion] : null;
  tlChart.data.labels.push(now);
  tlChart.data.datasets[0].data.push(f);
  tlChart.data.datasets[1].data.push(v);
  if (tlChart.data.labels.length > 60) {
    tlChart.data.labels.shift();
    tlChart.data.datasets[0].data.shift();
    tlChart.data.datasets[1].data.shift();
  }
  tlChart.update();
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
    initTimelineChart();
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

        // Update live SER badge
        var serLabel = document.getElementById('serLabel');
        if (serLabel && d.voice_emotion && d.voice_emotion !== 'Idle') {
          serLabel.textContent = 'Voice: ' + d.voice_emotion;
          serLabel.parentElement.classList.add('active');
        }

        // Always update timeline labels directly — even before chart is initialized
        var flEl = document.getElementById('tlFaceLabel');
        var vlEl = document.getElementById('tlVoiceLabel');
        var fLabel = d.video_emotion && d.video_emotion !== 'Idle' ? d.video_emotion : '--';
        var vLabel = d.voice_emotion && d.voice_emotion !== 'Idle' ? d.voice_emotion : '--';
        if (flEl) flEl.innerHTML = '<span class="dot face"></span>Face: ' + fLabel;
        if (vlEl) vlEl.innerHTML = '<span class="dot voice"></span>Voice: ' + vLabel;

        // Robot face: use video emotion, fall back to voice emotion
        var faceEmotion = d.video_emotion;
        if (!faceEmotion || faceEmotion === 'Idle' || faceEmotion === 'No Frame') {
          faceEmotion = d.voice_emotion;
        }
        if (faceEmotion && faceEmotion !== 'Idle' && typeof Face !== 'undefined') {
          Face.setEmotion(faceEmotion, d.distress);
        }

        // Update timeline chart
        updateTimeline(d.voice_emotion, d.video_emotion, d.distress);
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
