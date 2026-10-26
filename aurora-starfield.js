/* AURORA ambient star shower: lightweight, decorative, and shared across research pages. */
(() => {
  'use strict';
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  if (document.getElementById('aurora-starfield')) return;

  const canvas = document.createElement('canvas');
  canvas.id = 'aurora-starfield';
  canvas.setAttribute('aria-hidden', 'true');
  Object.assign(canvas.style, {
    position: 'fixed', inset: '0', width: '100%', height: '100%',
    pointerEvents: 'none', zIndex: '-1', opacity: '0.36'
  });
  document.body.prepend(canvas);
  const ctx = canvas.getContext('2d', { alpha: true });
  if (!ctx) { canvas.remove(); return; }

  let width = 0, height = 0, dpr = 1, stars = [], frame = 0;
  const reducedDensity = () => Math.min(90, Math.max(28, Math.floor((width * height) / 18000)));
  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    width = window.innerWidth; height = window.innerHeight;
    canvas.width = Math.floor(width * dpr); canvas.height = Math.floor(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    stars = Array.from({ length: reducedDensity() }, () => ({
      x: Math.random() * width, y: Math.random() * height,
      radius: 0.35 + Math.random() * 1.05,
      speed: 0.12 + Math.random() * 0.42,
      drift: -0.13 + Math.random() * 0.26,
      alpha: 0.18 + Math.random() * 0.56,
      phase: Math.random() * Math.PI * 2,
      gold: Math.random() > 0.68
    }));
  }
  function draw() {
    ctx.clearRect(0, 0, width, height);
    for (const s of stars) {
      s.y += s.speed;
      s.x += s.drift;
      s.phase += 0.018;
      if (s.y > height + 3) { s.y = -3; s.x = Math.random() * width; }
      if (s.x < -3) s.x = width + 3;
      if (s.x > width + 3) s.x = -3;
      const twinkle = 0.65 + (Math.sin(s.phase) + 1) * 0.175;
      ctx.globalAlpha = s.alpha * twinkle;
      ctx.fillStyle = s.gold ? '#f4ca65' : '#dbe8ff';
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.radius, 0, Math.PI * 2);
      ctx.fill();
      if (s.radius > 1.05) {
        ctx.globalAlpha = s.alpha * twinkle * 0.3;
        ctx.fillRect(s.x - 2.1, s.y - 0.25, 4.2, 0.5);
        ctx.fillRect(s.x - 0.25, s.y - 2.1, 0.5, 4.2);
      }
    }
    ctx.globalAlpha = 1;
    frame = window.requestAnimationFrame(draw);
  }
  window.addEventListener('resize', resize, { passive: true });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) { window.cancelAnimationFrame(frame); }
    else if (!frame) frame = window.requestAnimationFrame(draw);
  });
  resize();
  draw();
})();