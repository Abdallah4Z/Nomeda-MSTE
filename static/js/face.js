'use strict';
/* Nomeda — Glowing Digital Face */

const Face = (function () {
  var W = 560, H = 480;
  var CYAN = '#00e5ff';
  var BG   = '#07070d';

  var LEX = 170, REX = 390, EY_BASE = 245;

  var DEFS = {
    normal: { hw:75, hh:80, cr:28, tb:  0, bb: 0, ey: 0, morph:0 },
    happy:  { hw:78, hh:  6, cr: 6, tb:100, bb: 0, ey:-6, morph:0 },
    sad:    { hw:75, hh:70, cr:25, tb:-70, bb: 8, ey:10, morph:0 },
    loved:  { hw:75, hh:80, cr:28, tb:  0, bb: 0, ey: 0, morph:1 }
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
    var mt = p.morph || 0;

    // Heart morph: top dips inward creating cleft, bottom extends to point
    var morphTop  = -mt * 70;  // top bows DOWN (heart cleft)
    var morphBot  =  mt * 55;  // bottom bows DOWN (heart point)
    var morphWide =  mt * 10;  // slight widening
    var morphR    =  mt * 8;   // more rounded top

    w += morphWide;
    var tb = p.tb + morphTop;
    var bb = p.bb + morphBot;
    r = Math.min(r + morphR, w, h);

    var L = cx - w, R = cx + w, T = cy - h, B = cy + h;

    ctx.beginPath();
    ctx.moveTo(L + r, T);
    ctx.quadraticCurveTo(cx, T - tb, R - r, T);
    ctx.quadraticCurveTo(R, T, R, T + r);
    ctx.lineTo(R, B - r);
    ctx.quadraticCurveTo(R, B, R - r, B);
    ctx.quadraticCurveTo(cx, B + bb, L + r, B);
    ctx.quadraticCurveTo(L, B, L, B - r);
    ctx.lineTo(L, T + r);
    ctx.quadraticCurveTo(L, T, L + r, T);
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

  function render() {
    if (!ctx) return;
    ctx.fillStyle = BG; ctx.fillRect(0,0,W,H);

    var p  = cur();
    var ey = EY_BASE + p.ey;

    var pulse = 1;
    if (exprName === 'normal' && progress > 0.99)
      pulse = 1 + Math.sin(idlePhase) * 0.04;

    var pp = Object.assign({}, p, {
      hw: p.hw * pulse,
      hh: p.hh * pulse,
      cr: Math.min(p.cr * pulse, p.hw * pulse, p.hh * pulse)
    });

    var bs = 1 - blinkProg;
    var ep = Object.assign({}, pp, { hh: pp.hh*bs, cr: Math.min(pp.cr, pp.hh*bs) });
    if (blinkProg > 0.4) ep.morph = lerp(ep.morph, 0, (blinkProg-0.4)*1.67);

    outline(function() { eyePath(LEX, ey, ep); });
    outline(function() { eyePath(REX, ey, ep); });

    glow(function() { eyePath(LEX, ey, ep); });
    glow(function() { eyePath(REX, ey, ep); });

    if (bs > 0.15 && ep.morph < 0.5)
      pupil(LEX, ey, ep), pupil(REX, ey, ep);
  }

  function update(dt) {
    if (progress < 1) progress = Math.min(1, progress + dt/animDur);

    idlePhase += dt * 0.0018;

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

  function bind(id, expr) {
    var el = document.getElementById(id);
    if (el) el.addEventListener('click', function() { api.setExpression(expr); });
  }

  function activeBtn(name) {
    var m = { normal:'faceNormalBtn', happy:'faceHappyBtn', sad:'faceSadBtn', loved:'faceLovedBtn' };
    document.querySelectorAll('.face-btn').forEach(function(b) { b.classList.remove('active'); });
    var id = m[name]; if (id) document.getElementById(id).classList.add('active');
  }

  var api = {};

  api.init = function(el) {
    canvas = el; ctx = canvas.getContext('2d');
    bind('faceNormalBtn','idle'); bind('faceHappyBtn','happy');
    bind('faceSadBtn','sad'); bind('faceLovedBtn','loved');
    var sl = document.getElementById('faceAnimSlider');
    var lb = document.getElementById('faceAnimVal');
    if (sl) sl.addEventListener('input', function() { animDur = +sl.value; if (lb) lb.textContent = sl.value+'ms'; });
    activeBtn('normal');
    if (!started) { started = true; requestAnimationFrame(function(ts) { lastTime = ts; loop(ts); }); }
  };

  var ALIAS = { idle:'normal', listening:'normal', thinking:'normal', happy:'happy', sad:'sad', concerned:'sad', surprised:'normal', loved:'loved' };

  api.setExpression = function(name) {
    var sn = ALIAS[name] || name;
    if (!DEFS[sn]) sn = 'normal';
    if (sn === exprName && progress >= 1) return;
    fromS = cur(); toS = Object.assign({}, DEFS[sn]);
    progress = 0; exprName = sn; activeBtn(sn);
  };

  api.setEmotion = function(emotion, distress) {
    var e = (emotion||'').toLowerCase();
    if (e==='happy'||e==='calm') api.setExpression('happy');
    else if (e==='sad'||e==='anxious') api.setExpression('sad');
    else if (e==='angry') api.setExpression('concerned');
    else api.setExpression('idle');
  };

  api.startTalking = function() { talking = true; talkPhase = 0; };
  api.stopTalking  = function() { talking = false; };

  return api;
})();
