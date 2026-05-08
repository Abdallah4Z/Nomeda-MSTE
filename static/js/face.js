'use strict';
/* Nomeda — Glowing Digital Face v2 */

const Face = (function () {
  var W = 560, H = 480;
  var CYAN = '#00e5ff';
  var BG   = '#07070d';

  var LEX = 170, REX = 390, EY_BASE = 245;

  var DEFS = {
    normal:   { hw:70, hh:75, cr:26, tb:  0, bb: 0, ey: 0, ha:0, ea:1, mb:0, bw:50, bh:8, bt:0 },
    happy:    { hw:72, hh: 6, cr: 6, tb: 95, bb: 0, ey:-5, ha:0, ea:1, mb:1, bw:55, bh:4, bt:-5 },
    sad:      { hw:70, hh:65, cr:24, tb:-65, bb: 8, ey:10, ha:0, ea:1, mb:2, bw:45, bh:6, bt:5 },
    angry:    { hw:68, hh:72, cr:25, tb:  0, bb:-4, ey: 2, ha:0, ea:1, mb:3, bw:40, bh:5, bt:-8 },
    loved:    { hw:70, hh:75, cr:26, tb:  0, bb: 0, ey: 0, ha:1, ea:0, mb:0, bw:50, bh:8, bt:0 },
    surprised:{ hw:80, hh:80, cr:30, tb:  0, bb: 0, ey: 0, ha:0, ea:1, mb:4, bw:40, bh:3, bt:0 },
    afraid:   { hw:66, hh:70, cr:22, tb:-30, bb: 5, ey:15, ha:0, ea:1, mb:2, bw:38, bh:5, bt:3 },
  };

  var canvas, ctx;
  var fromS = Object.assign({}, DEFS.normal);
  var toS   = Object.assign({}, DEFS.normal);
  var progress = 1;
  var animDur = 700;
  var lastTime = 0;
  var started = false;
  var exprName = 'normal';

  var blinkTimer = 0, blinkProg = 0, blinking = false, blinkPhase = 0;
  var talking = false, talkPhase = 0;
  var exprExtra = 0;
  var idlePhase = 0;
  var heartBeat = 0;
  var listening = false;
  var listenPhase = 0;

  function lerp(a,b,t) { return a + (b-a)*t; }
  function ease(t) { return t<0.5 ? 2*t*t : -1+(4-2*t)*t; }

  function cur() {
    var o = {}, t = ease(Math.min(1, progress));
    for (var k in fromS) o[k] = lerp(fromS[k], toS[k], t);
    return o;
  }

  var PASSES = [[50,0.10],[28,0.22],[14,0.46],[5,0.82],[1,1.00]];

  function glow(pathFn, a) {
    if ((a||1) < 0.01) return;
    PASSES.forEach(function(g) {
      ctx.save();
      ctx.globalAlpha = g[1] * (a||1);
      ctx.shadowColor = CYAN; ctx.shadowBlur = g[0];
      ctx.fillStyle = CYAN;
      pathFn(); ctx.fill(); ctx.restore();
    });
  }

  function eyePath(cx, cy, p) {
    var w = p.hw, h = p.hh, r = Math.min(p.cr, w, h);
    var L = cx - w, R = cx + w, T = cy - h, B = cy + h;
    ctx.beginPath();
    ctx.moveTo(L + r, T);
    ctx.quadraticCurveTo(cx, T - p.tb, R - r, T);
    ctx.quadraticCurveTo(R, T, R, T + r);
    ctx.lineTo(R, B - r);
    ctx.quadraticCurveTo(R, B, R - r, B);
    ctx.quadraticCurveTo(cx, B + p.bb, L + r, B);
    ctx.quadraticCurveTo(L, B, L, B - r);
    ctx.lineTo(L, T + r);
    ctx.quadraticCurveTo(L, T, L + r, T);
    ctx.closePath();
  }

  function browPath(cx, cy, bw, bh, tilt) {
    var y = cy - 95 + tilt;
    ctx.beginPath();
    ctx.moveTo(cx - bw, y + bh);
    ctx.quadraticCurveTo(cx, y - bh, cx + bw, y + bh);
  }

  function mouthPath(cx, cy, mw, mh, shape) {
    var y = cy + 105;
    ctx.beginPath();
    if (shape === 1) {
      ctx.quadraticCurveTo(cx, y - mh * 2.5, cx + mw, y);
    } else if (shape === 2) {
      ctx.quadraticCurveTo(cx, y + mh, cx + mw, y);
    } else if (shape === 3) {
      ctx.moveTo(cx - mw, y + 2);
      ctx.quadraticCurveTo(cx, y - 2, cx + mw, y + 2);
    } else if (shape === 4) {
      ctx.arc(cx, y, mh * 1.2, 0, Math.PI * 2);
    } else {
      ctx.quadraticCurveTo(cx, y + 1, cx + mw, y);
    }
  }

  function heartPath(cx, cy, s) {
    ctx.beginPath();
    ctx.moveTo(cx, cy + s * 0.85);
    ctx.bezierCurveTo(cx - s*0.1, cy + s*0.5, cx - s*1.1, cy + s*0.05, cx - s*0.85, cy - s*0.45);
    ctx.bezierCurveTo(cx - s*0.55, cy - s*1.0, cx, cy - s*0.6, cx, cy - s*0.1);
    ctx.bezierCurveTo(cx, cy - s*0.6, cx + s*0.55, cy - s*1.0, cx + s*0.85, cy - s*0.45);
    ctx.bezierCurveTo(cx + s*1.1, cy + s*0.05, cx + s*0.1, cy + s*0.5, cx, cy + s*0.85);
    ctx.closePath();
  }

  function pupil(cx, cy, p) {
    var sx = p.ey*0.3 + exprExtra*8;
    var px = cx + sx, py = cy + sx*0.5;
    var rad = Math.max(p.hh*0.32, 2);
    var pas = [[16,0.15],[8,0.35],[3,0.65],[1,0.90]];
    pas.forEach(function(g) {
      ctx.save();
      ctx.globalAlpha = g[1]*0.65;
      ctx.shadowColor = CYAN; ctx.shadowBlur = g[0];
      ctx.fillStyle = CYAN;
      ctx.beginPath(); ctx.arc(px, py, rad, 0, Math.PI*2); ctx.fill();
      ctx.restore();
    });
  }

  function outline(pathFn) {
    ctx.save();
    ctx.strokeStyle = '#555560'; ctx.lineWidth = 1.5;
    ctx.shadowColor = 'transparent'; ctx.shadowBlur = 0;
    ctx.globalAlpha = 0.30;
    pathFn(); ctx.stroke(); ctx.restore();
  }

  function out(fn) { outline(fn); }
  function g(fn, a) { glow(fn, a); }

  function render() {
    if (!ctx) return;
    ctx.fillStyle = BG; ctx.fillRect(0,0,W,H);

    var p  = cur();
    var ey = EY_BASE + p.ey;

    var pulse = 1;
    if (exprName === 'normal' && progress > 0.99)
      pulse = 1 + Math.sin(idlePhase) * 0.04;

    var sway = 0;
    if (listening) sway = Math.sin(listenPhase) * 3;

    var pp = Object.assign({}, p, {
      hw: p.hw * pulse, hh: p.hh * pulse,
      cr: Math.min(p.cr * pulse, p.hw * pulse, p.hh * pulse)
    });

    var bs = 1 - blinkProg;
    var ep = Object.assign({}, pp, { hh: pp.hh*bs, cr: Math.min(pp.cr, pp.hh*bs) });

    var bw = p.bw, bh = p.bh, bt = p.bt;
    var ley = ey - 95 + bt + sway * 0.3;
    var rey = ey - 95 + bt - sway * 0.3;
    out(function() { browPath(LEX, ley, bw, bh, bt); });
    out(function() { browPath(REX, rey, bw, bh, bt); });
    g(function() { browPath(LEX, ley, bw, bh, bt); }, 0.5);
    g(function() { browPath(REX, rey, bw, bh, bt); }, 0.5);

    var mouthOpen = talking ? 0.5 + 0.5 * Math.abs(Math.sin(talkPhase * 1.5)) : 0;
    var mw = p.bw * 0.7;
    var mh = p.bh * (0.5 + mouthOpen * 2);
    var mx = (LEX + REX) / 2 + sway;
    out(function() { mouthPath(mx, ey, mw, mh, p.mb); });
    g(function() { mouthPath(mx, ey, mw, mh, p.mb); }, 0.6);

    var eyeAlpha = p.ea;
    if (p.ha > 0.01 && eyeAlpha > 0.5) eyeAlpha = lerp(eyeAlpha, 0, p.ha);

    if (eyeAlpha > 0.01) {
      out(function() { eyePath(LEX + sway, ey, ep); });
      out(function() { eyePath(REX + sway, ey, ep); });
      g(function() { eyePath(LEX + sway, ey, ep); }, eyeAlpha);
      g(function() { eyePath(REX + sway, ey, ep); }, eyeAlpha);
      if (bs > 0.15 && p.ha < 0.3) {
        pupil(LEX + sway, ey, ep);
        pupil(REX + sway, ey, ep);
      }
    }

    if (p.ha > 0.01) {
      var beat = 1 + Math.sin(heartBeat) * 0.06;
      var hs = 55 * beat;
      var ha = Math.min(1, p.ha);
      out(function() { heartPath(LEX + sway, ey - 5, hs); });
      out(function() { heartPath(REX + sway, ey - 5, hs); });
      g(function() { heartPath(LEX + sway, ey - 5, hs); }, ha);
      g(function() { heartPath(REX + sway, ey - 5, hs); }, ha);
    }
  }

  function update(dt) {
    if (progress < 1) progress = Math.min(1, progress + dt/animDur);
    idlePhase += dt * 0.0018;
    if (listening) listenPhase += dt * 0.003;

    var p = cur();
    if (p.ha > 0.01) heartBeat += dt * 0.005;
    else heartBeat = lerp(heartBeat, 0, dt*0.003);

    if (!blinking) {
      blinkTimer += dt;
      if (blinkTimer > 3200 + Math.random()*2200)
        { blinking = true; blinkTimer = 0; blinkPhase = 0; }
    }
    if (blinking) {
      blinkPhase += dt;
      blinkProg = Math.max(0, Math.sin(Math.PI*blinkPhase/140));
      if (blinkPhase >= 140) { blinking = false; blinkProg = 0; }
    }

    if (talking)
      { talkPhase += dt*0.009; exprExtra = Math.sin(talkPhase)*0.7; }
    else
      { exprExtra = lerp(exprExtra, 0, dt*0.004); }
    if (!talking && Math.abs(exprExtra) < 0.001) exprExtra = 0;
  }

  function loop(ts) {
    var dt = Math.min(ts - lastTime, 50); lastTime = ts;
    update(dt); render();
    requestAnimationFrame(loop);
  }

  var api = {};

  api.init = function(el) {
    canvas = el; ctx = canvas.getContext('2d');
    if (!started) { started = true; requestAnimationFrame(function(ts) { lastTime = ts; loop(ts); }); }
  };

  var ALIAS = {
    idle: 'normal', listening: 'normal', thinking: 'normal',
    happy: 'happy', calm: 'happy',
    sad: 'sad', anxious: 'sad',
    angry: 'angry', fear: 'afraid', frightened: 'afraid',
    surprised: 'surprised', shock: 'surprised',
    loved: 'loved'
  };

  api.setExpression = function(name) {
    var sn = ALIAS[name] || name;
    if (!DEFS[sn]) sn = 'normal';
    if (sn === exprName && progress >= 1) return;
    fromS = cur(); toS = Object.assign({}, DEFS[sn]);
    progress = 0; exprName = sn;
  };

  api.setEmotion = function(emotion, distress) {
    var e = (emotion||'').toLowerCase();
    var d = Number(distress) || 0;
    if (d > 70) {
      api.setExpression('afraid');
    } else if (e === 'happy' || e === 'calm') {
      api.setExpression('happy');
    } else if (e === 'sad' || e === 'anxious') {
      api.setExpression('sad');
    } else if (e === 'angry') {
      api.setExpression('angry');
    } else if (e === 'surprised' || e === 'shock') {
      api.setExpression('surprised');
    } else if (e === 'fear' || e === 'frightened') {
      api.setExpression('afraid');
    } else {
      api.setExpression('normal');
    }
  };

  api.setListening = function(v) {
    listening = v;
    if (v) listenPhase = 0;
  };

  api.startTalking = function() {
    talking = true;
    talkPhase = 0;
    listening = false;
  };

  api.stopTalking  = function() {
    talking = false;
  };

  return api;
})();
