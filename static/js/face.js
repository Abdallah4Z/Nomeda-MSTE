'use strict';
/* ── Nomeda — Glowing OLED Digital Face ── */

const Face = (function () {
  var W = 560, H = 480;
  var CYAN    = '#00e5ff';
  var BG      = '#07070d';
  var OUTLINE = '#333344';

  var LEX = 180, REX = 380, EY_BASE = 240;

  var DEFS = {
    normal: { hw:100, hh:110, cr:30, tb:   0, bb: 0, ey: 0, ha:0, ea:1, morph:0, tilt:0 },
    happy:  { hw:100, hh:  6, cr: 8, tb: 120, bb: 0, ey:-8, ha:0, ea:1, morph:0, tilt:0 },
    sad:    { hw:100, hh:110, cr:30, tb: -90, bb:30, ey:15, ha:0, ea:1, morph:0, tilt:8 },
    loved:  { hw:100, hh:110, cr:30, tb:   0, bb: 0, ey: 0, ha:0, ea:1, morph:1, tilt:0 }
  };

  var canvas, ctx;
  var fromS, toS, progress = 1;
  var animDur = 800;
  var lastTime = 0;
  var loopStarted = false;

  var blinkTimer = 0, blinkProg = 0, blinking = false, blinkPhase = 0;
  var talking = false, talkPhase = 0;
  var expressionExtra = 0;
  var idlePulse = 0;
  var heartPulse = 0;

  var exprName = 'normal';

  function lerp(a, b, t) { return a + (b - a) * t; }
  function easeInOut(t) { return t < 0.5 ? 2*t*t : -1 + (4 - 2*t)*t; }
  function lerpS(a, b, t) {
    var o = {};
    for (var k in a) o[k] = lerp(a[k], b[k], t);
    return o;
  }
  function curState() {
    return lerpS(fromS, toS, easeInOut(Math.min(1, progress)));
  }

  var FILL_PASSES = [[50,0.10],[28,0.22],[14,0.46],[5,0.82],[1,1.00]];

  function glowFill(pathFn, alpha) {
    var am = alpha !== undefined ? alpha : 1;
    if (am < 0.01) return;
    FILL_PASSES.forEach(function(g) {
      ctx.save();
      ctx.globalAlpha = g[1] * am;
      ctx.shadowColor = CYAN;
      ctx.shadowBlur  = g[0];
      ctx.fillStyle   = CYAN;
      pathFn();
      ctx.fill();
      ctx.restore();
    });
  }

  function drawOutline(pathFn, alpha) {
    if (alpha < 0.01) return;
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.strokeStyle = OUTLINE;
    ctx.lineWidth = 1.5;
    ctx.shadowColor = 'transparent';
    ctx.shadowBlur = 0;
    pathFn();
    ctx.stroke();
    ctx.restore();
  }

  function eyePath(cx, cy, p, side) {
    var w = p.hw, h = p.hh, r = p.cr;
    var mt = p.morph || 0;

    var cleftD = mt * 65;
    var lobeUp = mt * 25;
    var pointD = mt * 55;
    var bulgeW = mt * 24;

    w += bulgeW;
    var tb = p.tb + lobeUp;
    var bb = p.bb + pointD;
    r = Math.min(r + mt * 10, w, h);

    var L = cx - w, R = cx + w, T = cy - h, B = cy + h;

    var tilt = p.tilt || 0;
    var outerDroop = tilt;
    var tiltL = (side < 0) ? outerDroop : 0;
    var tiltR = (side > 0) ? outerDroop : 0;

    var topRimL = T + tiltL;
    var topRimR = T + tiltR;

    ctx.beginPath();

    if (mt < 0.03) {
      ctx.moveTo(L + r, topRimL);
      ctx.quadraticCurveTo(cx, (topRimL + topRimR) / 2 - tb, R - r, topRimR);
    } else {
      var cleftY = T + cleftD;
      var lobeTop = T - lobeUp;

      ctx.moveTo(L + r, topRimL);
      ctx.bezierCurveTo(
        L + w * 0.22, topRimL - lobeUp * 0.9,
        cx - w * 0.14, cleftY * 0.15 + lobeTop * 0.85,
        cx, cleftY
      );
      ctx.bezierCurveTo(
        cx + w * 0.14, cleftY * 0.15 + lobeTop * 0.85,
        R - w * 0.22, topRimR - lobeUp * 0.9,
        R - r, topRimR
      );
    }

    ctx.quadraticCurveTo(R, topRimR, R, topRimR + r);
    ctx.lineTo(R, B - r);
    ctx.quadraticCurveTo(R, B, R - r, B);
    ctx.quadraticCurveTo(cx, B + bb, L + r, B);
    ctx.quadraticCurveTo(L, B, L, B - r);
    ctx.lineTo(L, topRimL + r);
    ctx.quadraticCurveTo(L, topRimL, L + r, topRimL);
    ctx.closePath();
  }

  function drawPupil(cx, cy, p) {
    var shift = p.ey * 0.3 + expressionExtra * 12;
    var px = cx + shift;
    var py = cy + shift * 0.5;
    var radius = Math.max(p.hh * 0.32, 2);
    var alpha = 0.65;
    var passes = [[16,0.15],[8,0.35],[3,0.65],[1,0.90]];
    passes.forEach(function(g) {
      ctx.save();
      ctx.globalAlpha = g[1] * alpha;
      ctx.shadowColor = CYAN;
      ctx.shadowBlur  = g[0];
      ctx.fillStyle   = CYAN;
      ctx.beginPath();
      ctx.arc(px, py, radius, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    });
  }

  function render() {
    if (!ctx) return;
    ctx.fillStyle = BG;
    ctx.fillRect(0, 0, W, H);

    var p  = curState();
    var ey = EY_BASE + p.ey;

    var pulseScale = 1;
    if (exprName === 'normal' && progress >= 0.99) {
      pulseScale = 1 + Math.sin(idlePulse) * 0.05;
    }
    var heartPulseScale = 1;
    if (p.morph > 0.5) {
      heartPulseScale = 1 + Math.sin(heartPulse) * 0.06;
    }
    var scale = pulseScale * heartPulseScale;

    var pp = Object.assign({}, p, {
      hw: p.hw * scale,
      hh: p.hh * scale,
      cr: Math.min(p.cr * scale, p.hw * scale, p.hh * scale)
    });

    var bs  = 1 - blinkProg;
    var bHH = pp.hh * bs;
    var ep  = Object.assign({}, pp, { hh: bHH, cr: Math.min(pp.cr, bHH) });
    if (blinkProg > 0.4) ep.morph = lerp(ep.morph, 0, (blinkProg - 0.4) * 1.67);

    var eyeAlpha = p.ea;

    if (eyeAlpha > 0.01) {
      drawOutline(function() { eyePath(LEX, ey, ep, -1); }, 0.35);
      drawOutline(function() { eyePath(REX, ey, ep, 1); }, 0.35);

      glowFill(function() { eyePath(LEX, ey, ep, -1); }, eyeAlpha);
      glowFill(function() { eyePath(REX, ey, ep, 1); }, eyeAlpha);
    }

    if (bs > 0.15 && eyeAlpha > 0.3 && ep.morph < 0.4) {
      drawPupil(LEX, ey, ep);
      drawPupil(REX, ey, ep);
    }
  }

  function update(dt) {
    if (progress < 1) progress = Math.min(1, progress + dt / animDur);

    idlePulse += dt * 0.0019;

    var p = curState();
    if (p.morph > 0.5) {
      heartPulse += dt * 0.004;
    } else {
      heartPulse = lerp(heartPulse, 0, dt * 0.003);
    }

    if (!blinking) {
      blinkTimer += dt;
      if (blinkTimer > 3000 + Math.random() * 2000) {
        blinking = true; blinkTimer = 0; blinkPhase = 0;
      }
    }
    if (blinking) {
      blinkPhase += dt;
      blinkProg = Math.max(0, Math.sin(Math.PI * blinkPhase / 140));
      if (blinkPhase >= 140) { blinking = false; blinkProg = 0; }
    }

    if (talking) {
      talkPhase += dt * 0.009;
      expressionExtra = Math.sin(talkPhase) * 0.7;
    } else {
      expressionExtra = lerp(expressionExtra, 0, dt * 0.004);
    }

    if (!talking && Math.abs(expressionExtra) < 0.001) expressionExtra = 0;
  }

  function loop(ts) {
    var dt = Math.min(ts - lastTime, 50);
    lastTime = ts;
    update(dt);
    render();
    requestAnimationFrame(loop);
  }

  function wireControls() {
    function bind(id, expr) {
      var el = document.getElementById(id);
      if (el) el.addEventListener('click', function() { api.setExpression(expr); });
    }
    bind('faceNormalBtn', 'idle');
    bind('faceHappyBtn',  'happy');
    bind('faceSadBtn',    'sad');
    bind('faceLovedBtn',  'loved');

    var sl  = document.getElementById('faceAnimSlider');
    var lbl = document.getElementById('faceAnimVal');
    if (sl) {
      sl.addEventListener('input', function() {
        animDur = +sl.value;
        if (lbl) lbl.textContent = sl.value + 'ms';
      });
    }
  }

  function setActiveBtn(name) {
    var map = { normal:'faceNormalBtn', happy:'faceHappyBtn', sad:'faceSadBtn', loved:'faceLovedBtn' };
    document.querySelectorAll('.face-btn').forEach(function(b) { b.classList.remove('active'); });
    var id = map[name];
    if (id) { var el = document.getElementById(id); if (el) el.classList.add('active'); }
  }

  var api = {};

  api.init = function(el) {
    canvas = el;
    ctx = canvas.getContext('2d', { alpha: false });
    fromS = Object.assign({}, DEFS.normal);
    toS   = Object.assign({}, DEFS.normal);
    progress = 1;
    exprName = 'normal';
    wireControls();
    setActiveBtn('normal');
    if (!loopStarted) {
      loopStarted = true;
      requestAnimationFrame(function(ts) { lastTime = ts; loop(ts); });
    }
  };

  var ALIASES = {
    idle:'normal', listening:'normal', thinking:'normal',
    happy:'happy', sad:'sad', concerned:'sad', surprised:'normal', loved:'loved'
  };

  api.setExpression = function(name) {
    var sn = ALIASES[name] || name;
    if (!DEFS[sn]) sn = 'normal';
    if (sn === exprName && progress >= 1) return;
    fromS = curState();
    toS   = Object.assign({}, DEFS[sn]);
    progress = 0;
    exprName = sn;
    setActiveBtn(sn);
  };

  api.setEmotion = function(emotion, distress) {
    var e = (emotion || '').toLowerCase();
    if (e === 'happy' || e === 'calm')       api.setExpression('happy');
    else if (e === 'sad' || e === 'anxious') api.setExpression('sad');
    else if (e === 'angry')                  api.setExpression('concerned');
    else                                     api.setExpression('idle');
  };

  api.startTalking = function() { talking = true;  talkPhase = 0; };
  api.stopTalking  = function() { talking = false; };

  return api;
})();
