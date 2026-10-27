/* Shared AURORA gold-star backdrop. Decorative only; never intercepts interaction. */
(() => {
  'use strict';
  if (document.getElementById('aurora-starfield')) return;

  const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;

  const canvas = document.createElement('canvas');
  canvas.id = 'aurora-starfield';
  canvas.setAttribute('aria-hidden', 'true');
  Object.assign(canvas.style, {
    position: 'fixed', inset: '0', width: '100%', height: '100%',
    pointerEvents: 'none', zIndex: '0', opacity: '0.56',
    contain: 'strict'
  });
  document.body.prepend(canvas);
  const ctx = canvas.getContext('2d', { alpha: true });
  if (!ctx) { canvas.remove(); return; }

  let width = 0, height = 0, dpr = 1, stars = [], frame = 0;
  const starCount = () => Math.min(width < 700 ? 54 : 112, Math.max(34, Math.floor((width * height) / 11500)));
  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    width = window.innerWidth; height = window.innerHeight;
    canvas.width = Math.floor(width * dpr); canvas.height = Math.floor(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    stars = Array.from({ length: starCount() }, () => ({
      x: Math.random() * width, y: Math.random() * height,
      radius: 0.55 + Math.random() * 1.35,
      speed: reduceMotion ? 0 : 0.16 + Math.random() * 0.52,
      drift: reduceMotion ? 0 : -0.12 + Math.random() * 0.24,
      alpha: 0.4 + Math.random() * 0.48,
      phase: Math.random() * Math.PI * 2,
      sparkle: Math.random() > 0.77
    }));
  }
  function drawStar(s, glow) {
    ctx.save();
    ctx.translate(s.x, s.y);
    ctx.globalAlpha = s.alpha * glow;
    ctx.fillStyle = '#f4d27d';
    ctx.shadowColor = 'rgba(244, 194, 83, .9)';
    ctx.shadowBlur = s.sparkle ? 15 : 7;
    ctx.beginPath();
    ctx.moveTo(0, -s.radius * (s.sparkle ? 3.2 : 1.8));
    ctx.quadraticCurveTo(s.radius * .23, -s.radius * .22, s.radius * (s.sparkle ? 3.2 : 1.8), 0);
    ctx.quadraticCurveTo(s.radius * .22, s.radius * .22, 0, s.radius * (s.sparkle ? 3.2 : 1.8));
    ctx.quadraticCurveTo(-s.radius * .22, s.radius * .22, -s.radius * (s.sparkle ? 3.2 : 1.8), 0);
    ctx.quadraticCurveTo(-s.radius * .22, -s.radius * .22, 0, -s.radius * (s.sparkle ? 3.2 : 1.8));
    ctx.fill();
    ctx.restore();
  }
  function draw() {
    ctx.clearRect(0, 0, width, height);
    for (const s of stars) {
      s.y += s.speed;
      s.x += s.drift;
      s.phase += 0.022;
      if (s.y > height + 3) { s.y = -3; s.x = Math.random() * width; }
      if (s.x < -3) s.x = width + 3;
      if (s.x > width + 3) s.x = -3;
      const twinkle = reduceMotion ? 0.82 : 0.56 + (Math.sin(s.phase) + 1) * 0.22;
      drawStar(s, twinkle);
    }
    if (!reduceMotion) frame = window.requestAnimationFrame(draw);
  }
  window.addEventListener('resize', resize, { passive: true });
  document.addEventListener('visibilitychange', () => {
    if (reduceMotion) return;
    if (document.hidden && frame) { window.cancelAnimationFrame(frame); frame = 0; }
    else if (!document.hidden && !frame) frame = window.requestAnimationFrame(draw);
  });
  resize();
  draw();
})();
