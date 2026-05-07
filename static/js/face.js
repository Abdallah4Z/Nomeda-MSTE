'use strict';

/* ── Nomeda — Pixel Art Robot Face ── */

const Face = (function () {
  var GRID = 16;
  var SCALE = 9;
  var SIZE = GRID * SCALE; // 144

  var C = {
    head: '#34d399',
    headLight: '#6ee7b7',
    headDark: '#047857',
    eyeWhite: '#f0fdf4',
    pupil: '#064e3b',
    blush: 'rgba(52, 211, 153, 0.25)',
    mouth: '#064e3b',
    bg: 'transparent'
  };

  var EXPRESSIONS = {
    idle: {
      browY: 3, browH: 1, browTilt: 0,
      eyeY: 5, eyeH: 3, eyeOpen: 1,
      pupilX: 0, pupilY: 0,
      mouthType: 'flat', blush: false
    },
    listening: {
      browY: 3, browH: 1, browTilt: 0.3,
      eyeY: 5, eyeH: 3, eyeOpen: 0.9,
      pupilX: 0, pupilY: -0.3,
      mouthType: 'smile', blush: false
    },
    thinking: {
      browY: 2, browH: 1, browTilt: -0.7,
      eyeY: 5, eyeH: 3, eyeOpen: 0.8,
      pupilX: 0, pupilY: -0.8,
      mouthType: 'pursed', blush: false
    },
    happy: {
      browY: 3, browH: 1, browTilt: 0.8,
      eyeY: 6, eyeH: 2, eyeOpen: 0.3,
      pupilX: 0, pupilY: 0,
      mouthType: 'bigSmile', blush: true
    },
    sad: {
      browY: 4, browH: 1, browTilt: 0.2,
      eyeY: 6, eyeH: 2, eyeOpen: 0.4,
      pupilX: 0, pupilY: 0.5,
      mouthType: 'frown', blush: false
    },
    concerned: {
      browY: 2, browH: 1, browTilt: -1,
      eyeY: 5, eyeH: 3, eyeOpen: 0.7,
      pupilX: 0.3, pupilY: 0,
      mouthType: 'slightFrown', blush: false
    },
    surprised: {
      browY: 2, browH: 1, browTilt: 1.2,
      eyeY: 5, eyeH: 4, eyeOpen: 1.5,
      pupilX: 0, pupilY: 0,
      mouthType: 'open', blush: false
    }
  };

  var canvas, ctx, off, offCtx;
  var currentExpr = 'idle';
  var targetExpr = 'idle';
  var blend = 1;
  var blinkTimer = 0;
  var isBlinking = false;
  var isTalking = false;
  var talkPhase = 0;
  var exprFrom = null, exprTo = null;

  function lerp(a, b, t) { return a + (b - a) * t; }

  function lerpExpr(nameFrom, nameTo, t) {
    var f = EXPRESSIONS[nameFrom];
    var to = EXPRESSIONS[nameTo];
    if (!f || !to) return EXPRESSIONS[nameTo] || EXPRESSIONS.idle;
    return {
      browY: lerp(f.browY, to.browY, t),
      browH: lerp(f.browH, to.browH, t),
      browTilt: lerp(f.browTilt, to.browTilt, t),
      eyeY: lerp(f.eyeY, to.eyeY, t),
      eyeH: lerp(f.eyeH, to.eyeH, t),
      eyeOpen: lerp(f.eyeOpen, to.eyeOpen, t),
      pupilX: lerp(f.pupilX, to.pupilX, t),
      pupilY: lerp(f.pupilY, to.pupilY, t),
      mouthType: t < 0.5 ? f.mouthType : to.mouthType,
      blush: t >= 0.5 ? to.blush : f.blush
    };
  }

  function exprParams(name) {
    if (!exprFrom || !exprTo) return Object.assign({}, EXPRESSIONS[name] || EXPRESSIONS.idle);
    if (name === currentExpr && blend >= 1) return Object.assign({}, EXPRESSIONS[name]);
    var t = Math.min(1, blend);
    var eased = t * t * (3 - 2 * t);
    return lerpExpr(exprFrom, exprTo, eased);
  }

  // ── Pixel drawing helpers ──
  function px(ctx, x, y, color) {
    ctx.fillStyle = color;
    ctx.fillRect(x, y, 1, 1);
  }

  function rect(ctx, x, y, w, h, color) {
    ctx.fillStyle = color;
    ctx.fillRect(x, y, w, h);
  }

  function hLine(ctx, x, y, w, color) {
    ctx.fillStyle = color;
    ctx.fillRect(x, y, w, 1);
  }

  function vLine(ctx, x, y, h, color) {
    ctx.fillStyle = color;
    ctx.fillRect(x, y, 1, h);
  }

  // ── Drawing ──
  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
  }

  function drawHead(c) {
    // Head background
    c.fillStyle = C.head;
    roundRect(c, 1, 0, 14, 16, 3);
    c.fill();

    // Top highlight
    c.fillStyle = C.headLight;
    roundRect(c, 3, 1, 10, 3, 1.5);
    c.fill();

    // Bottom shadow
    g.fillStyle = C.headDark;
    hLine(g, 4, 14, 8, C.headDark);
    px(g, 5, 15, C.headDark);
    px(g, 10, 15, C.headDark);

    // Ears
    rect(g, 1, 5, 1, 3, C.headDark);
    rect(g, 14, 5, 1, 3, C.headDark);
    px(g, 1, 6, C.head);
    px(g, 14, 6, C.head);
  }

  function drawBrows(c, p) {
    var browLen = 4;
    var lx = 4;
    var rx = 9;
    var by = Math.round(p.browY);
    var tilt = p.browTilt;

    var col = C.headDark;

    // Left brow (pixels shift based on tilt)
    var ly = by;
    if (tilt > 0) {
      // tilted up (happy)
      hLine(c, lx, ly, browLen, col);
      if (tilt > 0.5) { px(c, lx + 1, ly - 1, col); px(c, lx + 2, ly, col); }
    } else if (tilt < 0) {
      // tilted down (angry/concerned)
      px(c, lx, ly, col);
      px(c, lx + 1, ly + 1, col);
      px(c, lx + 2, ly + 1, col);
      px(c, lx + 3, ly, col);
    } else {
      hLine(c, lx, ly, browLen, col);
    }

    // Right brow
    var ry = by;
    if (tilt > 0) {
      hLine(c, rx, ry, browLen, col);
      if (tilt > 0.5) { px(c, rx + 1, ry - 1, col); px(c, rx + 2, ry, col); }
    } else if (tilt < 0) {
      px(c, rx, ry, col);
      px(c, rx + 1, ry + 1, col);
      px(c, rx + 2, ry + 1, col);
      px(c, rx + 3, ry, col);
    } else {
      hLine(c, rx, ry, browLen, col);
    }
  }

  function drawEyes(c, p, blinking) {
    var eyeY = Math.round(p.eyeY);
    var eyeH = blinking ? 1 : Math.max(1, Math.round(p.eyeH * p.eyeOpen));
    var isClosed = eyeH <= 1;

    // Left eye white
    if (!isClosed) {
      rect(c, 4, eyeY, 3, eyeH, C.eyeWhite);
      // Right eye white
      rect(c, 9, eyeY, 3, eyeH, C.eyeWhite);
    }

    // Pupils
    if (!isClosed && eyeH >= 2) {
      var px = 5 + Math.round(p.pupilX);
      var py = eyeY + Math.round(eyeH / 2) - 1 + Math.round(p.pupilY);
      py = Math.max(eyeY, Math.min(eyeY + eyeH - 1, py));
      px(c, px, py, C.pupil);
      px(c, px + 4, py, C.pupil);
    }

    // Closed eye lines
    if (isClosed) {
      var lineY = eyeY;
      if (p.mouthType === 'frown' || p.mouthType === 'slightFrown') {
        // sad closed eyes (slanted down)
        px(c, 4, lineY - 1, C.headDark);
        hLine(c, 5, lineY, 2, C.headDark);
        px(c, 5, lineY + 1, C.headDark);
        
        px(c, 9, lineY - 1, C.headDark);
        hLine(c, 10, lineY, 2, C.headDark);
        px(c, 10, lineY + 1, C.headDark);
      } else {
        // happy closed eyes (arc up)
        hLine(c, 4, lineY, 3, C.headDark);
        hLine(c, 9, lineY, 3, C.headDark);
        if (p.mouthType === 'bigSmile') {
          px(c, 5, lineY - 1, C.headDark);
          px(c, 10, lineY - 1, C.headDark);
        }
      }
    }

    // Under-eye line
    if (!isClosed && eyeH > 1) {
      hLine(c, 4, eyeY + eyeH, 3, C.headDark);
      hLine(c, 9, eyeY + eyeH, 3, C.headDark);
    }
  }

  function drawMouth(c, p, talking, phase) {
    var col = C.mouth;

    if (talking) {
      // Animate mouth opening/closing
      var open = Math.abs(Math.sin(phase)) * 1.5 + 0.5;
      var mh = Math.round(Math.min(3, open));
      rect(c, 6, 12 - mh + 1, 4, mh, col);
      // teeth
      if (mh > 1) { hLine(c, 7, 12 - mh + 2, 2, C.eyeWhite); }
      return;
    }

    switch (p.mouthType) {
      case 'flat':
        hLine(c, 6, 12, 4, col);
        break;

      case 'smile':
        hLine(c, 6, 12, 4, col);
        px(c, 5, 11, col);
        px(c, 10, 11, col);
        break;

      case 'bigSmile':
        rect(c, 5, 11, 6, 2, col);
        hLine(c, 6, 10, 4, col);
        px(c, 7, 9, col);
        px(c, 8, 9, col);
        break;

      case 'frown':
        hLine(c, 6, 12, 4, col);
        px(c, 5, 13, col);
        px(c, 10, 13, col);
        break;

      case 'pursed':
        rect(c, 6, 12, 4, 2, col);
        px(c, 7, 11, col);
        px(c, 8, 11, col);
        break;

      case 'open':
        rect(c, 6, 11, 4, 3, col);
        hLine(c, 7, 12, 2, C.headDark);
        break;

      case 'slightFrown':
        hLine(c, 6, 12, 4, col);
        break;
    }
  }

  function drawBlush(c, p) {
    if (!p.blush) return;
    px(c, 3, 9, C.blush);
    px(c, 4, 9, C.blush);
    px(c, 3, 10, C.blush);
    px(c, 12, 9, C.blush);
    px(c, 11, 9, C.blush);
    px(c, 12, 10, C.blush);
  }

  function render() {
    if (!offCtx || !ctx) return;

    var oc = offCtx;
    oc.clearRect(0, 0, GRID, GRID);

    var faceExpr = targetExpr;
    if (blend < 1 && exprFrom && exprTo) {
      faceExpr = '__blend__';
    }

    var p = exprParams(targetExpr);

    drawHead(oc);
    drawBlush(oc, p);
    drawBrows(oc, p);
    drawEyes(oc, p, isBlinking);
    drawMouth(oc, p, isTalking, talkPhase);

    // Draw to visible canvas
    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, SIZE, SIZE);
    ctx.drawImage(off, 0, 0, SIZE, SIZE);

    // Pixel grid overlay (subtle)
    ctx.strokeStyle = 'rgba(0,0,0,0.05)';
    ctx.lineWidth = 1;
    for (var i = 0; i <= GRID; i++) {
      ctx.beginPath();
      ctx.moveTo(i * SCALE, 0);
      ctx.lineTo(i * SCALE, SIZE);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(0, i * SCALE);
      ctx.lineTo(SIZE, i * SCALE);
      ctx.stroke();
    }
  }

  function update() {
    // Blink timer
    blinkTimer++;
    if (!isBlinking && blinkTimer > 120 + Math.random() * 100) {
      isBlinking = true;
      blinkTimer = 0;
    }
    if (isBlinking && blinkTimer > 6) {
      isBlinking = false;
      blinkTimer = 0;
    }

    // Talking animation
    if (isTalking) {
      talkPhase += 0.2;
    }

    // Expression transition
    if (blend < 1) {
      blend += 0.06;
      if (blend > 1) { blend = 1; currentExpr = targetExpr; }
    }

  }

  function loop() {
    update();
    render();
    requestAnimationFrame(loop);
  }

  // ── Public API ──
  var api = {};

  api.init = function (canvasEl) {
    canvas = canvasEl;
    ctx = canvas.getContext('2d');
    off = document.createElement('canvas');
    off.width = GRID;
    off.height = GRID;
    offCtx = off.getContext('2d');

    targetExpr = 'idle';
    currentExpr = 'idle';
    exprFrom = 'idle';
    exprTo = 'idle';

    loop();
  };

  api.setExpression = function (name) {
    name = name || 'idle';
    if (!EXPRESSIONS[name]) name = 'idle';
    if (name === targetExpr) return;
    exprFrom = currentExpr;
    exprTo = name;
    targetExpr = name;
    blend = 0;
  };

  api.setEmotion = function (emotion, distress) {
    var d = Number(distress) || 0;
    var e = (emotion || '').toLowerCase();
    if (e === 'happy' || e === 'calm') {
      api.setExpression('happy');
    } else if (e === 'sad' || e === 'anxious') {
      api.setExpression('sad');
    } else if (e === 'angry') {
      api.setExpression('concerned');
    } else if (e === 'surprise') {
      api.setExpression('surprised');
    } else {
      if (d > 60) api.setExpression('concerned');
      else api.setExpression('listening');
    }
  };

  api.startTalking = function () {
    isTalking = true;
    talkPhase = 0;
    api.setExpression('idle');
  };

  api.stopTalking = function () {
    isTalking = false;
    talkPhase = 0;
  };

  return api;
})();
