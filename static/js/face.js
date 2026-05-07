'use strict';
/* ── Nomeda — Glowing OLED Digital Face ── */

const Face = (function () {
  var W = 280, H = 190;
  var CYAN = '#00e5ff';
  var BG   = '#000000';

  // Geometry: eye centers, mouth anchor
  var LEX = 90, REX = 190, EY_BASE = 88;
  var MX = 140, MY = 152;

  // State params:
  //   hw  = eye half-width
  //   hh  = eye half-height
  //   cr  = corner radius (rounded-rect corners)
  //   tb  = top-edge bulge: >0 bows upward (arch), <0 bows inward/downward (drooping lid)
  //   bb  = bottom-edge bulge: >0 bows downward (extra fullness)
  //   ey  = eye center Y offset from EY_BASE
  //   mc  = mouth control offset: <0 = smile (ctrl above), >0 = frown (ctrl below)
  //   mw  = mouth half-width
  //   ha  = heart alpha  (0-1, for "loved")
  //   ea  = regular-eye alpha (0-1)
  var DEFS = {
    //                       eyes ──────────────────────    mouth ──────  fx ─────
    normal: { hw:22, hh:20, cr:9,  tb:  0, bb:0, ey: 0,  mc:  0, mw:48, ha:0, ea:1 },
    happy:  { hw:24, hh: 4, cr:4,  tb: 24, bb:0, ey:-2,  mc:-36, mw:52, ha:0, ea:1 },
    sad:    { hw:22, hh:16, cr:8,  tb:-18, bb:3, ey: 2,  mc: 36, mw:50, ha:0, ea:1 },
    loved:  { hw:22, hh:20, cr:9,  tb:  0, bb:0, ey: 0,  mc:-30, mw:46, ha:1, ea:0 }
  };
  // happy: tiny hh + large positive tb → flat bottom, top arches up strongly = ^ ^
  // sad:   negative tb → top edge bows downward (heavy eyelid droops over the eye)
  // loved: same eye shape as normal (replaced by hearts via ha), big smile (mc=-30)

  var canvas, ctx;
  var fromS, toS, progress = 1;
  var animDur = 600;
  var lastTime = 0;
  var loopStarted = false;

  // Blink state
  var blinkTimer = 0, blinkProg = 0, blinking = false, blinkPhase = 0;
  // Talk state
  var talking = false, talkPhase = 0;

  var exprName = 'normal';

  // ── Math helpers ──
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

  // ── Glow draw helpers ──
  var FILL_PASSES = [[50,0.10],[28,0.22],[14,0.46],[5,0.82],[1,1.00]];
  var STR_PASSES  = [[50,0.10],[28,0.20],[14,0.44],[5,0.80],[1,1.00]];

  function glowFill(pathFn, alpha) {
    var am = alpha !== undefined ? alpha : 1;
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

  function glowStroke(pathFn, lw, alpha) {
    var am = alpha !== undefined ? alpha : 1;
    var extras = [10, 5, 2, 1, 0];
    STR_PASSES.forEach(function(g, i) {
      ctx.save();
      ctx.globalAlpha = g[1] * am;
      ctx.shadowColor = CYAN;
      ctx.shadowBlur  = g[0];
      ctx.strokeStyle = CYAN;
      ctx.lineWidth   = lw + extras[i];
      ctx.lineCap     = 'round';
      pathFn();
      ctx.stroke();
      ctx.restore();
    });
  }

  // ── Eye path: rounded rectangle with optional top/bottom edge bulge ──
  //
  //  tb > 0  → top edge bows UP   (arched / happy ^ shape)
  //  tb < 0  → top edge bows DOWN (lid droops into eye / sad shape)
  //  bb > 0  → bottom edge bows DOWN (slightly fuller lower lid)
  //
  function eyePath(cx, cy, p) {
    var w = p.hw, h = p.hh, r = p.cr;
    // clamp corner radius so it never exceeds the half-dimensions
    r = Math.min(r, w, h);
    var L = cx - w, R = cx + w, T = cy - h, B = cy + h;

    ctx.beginPath();
    ctx.moveTo(L + r, T);
    // top edge — bulge toward T - tb (above when tb>0, below when tb<0)
    ctx.quadraticCurveTo(cx, T - p.tb, R - r, T);
    // top-right corner
    ctx.quadraticCurveTo(R, T, R, T + r);
    // right edge
    ctx.lineTo(R, B - r);
    // bottom-right corner
    ctx.quadraticCurveTo(R, B, R - r, B);
    // bottom edge — bulge downward by bb
    ctx.quadraticCurveTo(cx, B + p.bb, L + r, B);
    // bottom-left corner
    ctx.quadraticCurveTo(L, B, L, B - r);
    // left edge
    ctx.lineTo(L, T + r);
    // top-left corner
    ctx.quadraticCurveTo(L, T, L + r, T);
    ctx.closePath();
  }

  // ── Mouth path ──
  function mouthPath(mc, mw) {
    ctx.beginPath();
    ctx.moveTo(MX - mw, MY);
    ctx.quadraticCurveTo(MX, MY + mc, MX + mw, MY);
  }

  // ── Heart path ──
  function heartPath(cx, cy, s) {
    ctx.beginPath();
    ctx.moveTo(cx, cy + s * 0.90);
    ctx.bezierCurveTo(cx - s*0.12, cy + s*0.55, cx - s*1.20, cy + s*0.10, cx - s*0.90, cy - s*0.45);
    ctx.bezierCurveTo(cx - s*0.60, cy - s*1.05, cx,           cy - s*0.65, cx,           cy - s*0.10);
    ctx.bezierCurveTo(cx,           cy - s*0.65, cx + s*0.60, cy - s*1.05, cx + s*0.90, cy - s*0.45);
    ctx.bezierCurveTo(cx + s*1.20, cy + s*0.10, cx + s*0.12,  cy + s*0.55, cx,           cy + s*0.90);
    ctx.closePath();
  }

  // ── Render ──
  function render() {
    if (!ctx) return;

    ctx.fillStyle = BG;
    ctx.fillRect(0, 0, W, H);

    var p  = curState();
    var ey = EY_BASE + p.ey;

    // Blink: shrink hh toward 0 (eye closes to a flat line)
    var bs  = 1 - blinkProg;
    var bHH = p.hh * bs;
    var ep  = Object.assign({}, p, { hh: bHH, cr: Math.min(p.cr, bHH) });

    // Talk: oscillate mouth control point
    var mc = talking ? p.mc + Math.sin(talkPhase) * 11 : p.mc;

    // Regular eyes
    if (p.ea > 0.01) {
      glowFill(function() { eyePath(LEX, ey, ep); }, p.ea);
      glowFill(function() { eyePath(REX, ey, ep); }, p.ea);
    }

    // Hearts (loved)
    if (p.ha > 0.01) {
      glowFill(function() { heartPath(LEX, ey - 2, 19); }, p.ha);
      glowFill(function() { heartPath(REX, ey - 2, 19); }, p.ha);
    }

    // Mouth
    glowStroke(function() { mouthPath(mc, p.mw); }, 4);
  }

  // ── Update ──
  function update(dt) {
    if (progress < 1) progress = Math.min(1, progress + dt / animDur);

    // Auto-blink every ~3.5–6 s
    if (!blinking) {
      blinkTimer += dt;
      if (blinkTimer > 3500 + Math.random() * 2500) {
        blinking = true; blinkTimer = 0; blinkPhase = 0;
      }
    }
    if (blinking) {
      blinkPhase += dt;
      blinkProg = Math.max(0, Math.sin(Math.PI * blinkPhase / 160));
      if (blinkPhase >= 160) { blinking = false; blinkProg = 0; }
    }

    if (talking) talkPhase += dt * 0.009;
  }

  function loop(ts) {
    var dt = Math.min(ts - lastTime, 50);
    lastTime = ts;
    update(dt);
    render();
    requestAnimationFrame(loop);
  }

  // ── Control wiring ──
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

  // ── Public API ──
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
