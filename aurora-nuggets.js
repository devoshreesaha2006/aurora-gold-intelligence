/* Shared procedural gold-sparkle atmosphere. Decorative canvas; never receives pointer input. */
(() => {
  const canvasId = 'aurora-gold-nuggets';
  if (document.getElementById(canvasId)) return;
  if (!document.getElementById('aurora-sparkle-style')) {
    const style = document.createElement('style');
    style.id = 'aurora-sparkle-style';
    style.textContent = `#${canvasId}{position:fixed;inset:0;width:100vw;height:100vh;z-index:0;pointer-events:none;opacity:.68}.aurora-sparkles-over-media{z-index:0!important;opacity:.4!important}@media (max-width:700px){#${canvasId}{opacity:.5}}@media (prefers-reduced-motion:reduce){#${canvasId}{opacity:.44}}`;
    document.head.appendChild(style);
  }
  const canvas = document.createElement('canvas');
  canvas.id = canvasId;
  canvas.className = document.querySelector('video') ? 'aurora-sparkles-over-media' : '';
  canvas.setAttribute('aria-hidden', 'true');
  document.body.prepend(canvas);
  const ctx = canvas.getContext('2d', { alpha: true });
  if (!ctx) return;
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const smallScreen = matchMedia('(max-width: 700px)').matches;
  const sparkles = [], dust = [];
  let width = 1, height = 1, dpr = 1, pointer = { x: 0, y: 0 }, frameId = 0;
  const random = (min, max) => min + Math.random() * (max - min);

  function makeSparkle() {
    return { x: random(0, width), y: random(0, height), size: random(6.5, 11), phase: random(0, Math.PI * 2), speed: random(.16, .42), drift: random(5, 20), alpha: random(.66, .98), rotation: random(0, Math.PI * 2), flare: Math.random() > .66 };
  }
  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 1.5); width = window.innerWidth; height = window.innerHeight;
    canvas.width = Math.round(width * dpr); canvas.height = Math.round(height * dpr);
    canvas.style.width = `${width}px`; canvas.style.height = `${height}px`; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    sparkles.length = 0; dust.length = 0;
    const count = smallScreen ? 10 : Math.min(30, Math.max(22, Math.round(width / 88)));
    for (let index = 0; index < count; index += 1) sparkles.push(makeSparkle());
    for (let index = 0; index < (smallScreen ? 10 : 24); index += 1) dust.push({ x: random(0, width), y: random(0, height), size: random(.45, 1.1), alpha: random(.05, .16), phase: random(0, Math.PI * 2), speed: random(.08, .22) });
  }
  function drawSparkle(sparkle, time) {
    const motion = reducedMotion ? 0 : time;
    const twinkle = .32 + .68 * (.5 + .5 * Math.sin(motion * sparkle.speed + sparkle.phase));
    const x = sparkle.x + Math.sin(motion * sparkle.speed * .42 + sparkle.phase) * sparkle.drift + pointer.x * 2;
    const y = sparkle.y - Math.cos(motion * sparkle.speed * .35 + sparkle.phase) * sparkle.drift * .7 + pointer.y * 2;
    const size = sparkle.size * (.76 + twinkle * .32);
    ctx.save(); ctx.translate(x, y); ctx.rotate(sparkle.rotation + motion * .025); ctx.globalAlpha = sparkle.alpha * twinkle;
    const glowRadius = size * (sparkle.flare ? 9 : 6.5);
    const halo = ctx.createRadialGradient(0, 0, 0, 0, 0, glowRadius);
    halo.addColorStop(0, sparkle.flare ? 'rgba(255,224,143,.42)' : 'rgba(255,224,143,.28)');
    halo.addColorStop(.22, 'rgba(255,207,103,.2)');
    halo.addColorStop(1, 'rgba(255,207,103,0)');
    ctx.fillStyle = halo; ctx.beginPath(); ctx.arc(0, 0, glowRadius, 0, Math.PI * 2); ctx.fill();
    ctx.shadowColor = 'rgba(255,207,103,1)'; ctx.shadowBlur = size * (sparkle.flare ? 7 : 4.8);
    const ray = ctx.createLinearGradient(0, -size * 1.5, 0, size * 1.5);
    ray.addColorStop(0, 'rgba(255,245,205,0)'); ray.addColorStop(.5, 'rgba(255,231,166,.96)'); ray.addColorStop(1, 'rgba(232,184,77,0)');
    ctx.fillStyle = ray; ctx.beginPath(); ctx.moveTo(0, -size * 1.5); ctx.quadraticCurveTo(size * .12, -size * .12, size * 1.15, 0); ctx.quadraticCurveTo(size * .12, size * .12, 0, size * 1.5); ctx.quadraticCurveTo(-size * .12, size * .12, -size * 1.15, 0); ctx.quadraticCurveTo(-size * .12, -size * .12, 0, -size * 1.5); ctx.fill();
    ctx.fillStyle = 'rgba(255,248,220,.92)'; ctx.beginPath(); ctx.arc(0, 0, Math.max(.65, size * .13), 0, Math.PI * 2); ctx.fill(); ctx.restore();
  }
  function drawDust(time) { dust.forEach((particle) => { const x = particle.x + Math.sin(time * particle.speed + particle.phase) * 8, y = particle.y - Math.cos(time * particle.speed * .6 + particle.phase) * 6; ctx.beginPath(); ctx.arc(x, y, particle.size, 0, Math.PI * 2); ctx.fillStyle = `rgba(232,191,85,${particle.alpha * (reducedMotion ? .6 : .9)})`; ctx.fill(); }); }
  function paint(timestamp) { const time = timestamp * .001; ctx.clearRect(0, 0, width, height); drawDust(time); sparkles.forEach((sparkle) => drawSparkle(sparkle, time)); if (!reducedMotion && !document.hidden) frameId = requestAnimationFrame(paint); }
  function restart() { cancelAnimationFrame(frameId); paint(0); }
  window.addEventListener('resize', () => { resize(); restart(); }, { passive: true });
  if (!reducedMotion && !smallScreen) window.addEventListener('pointermove', (event) => { pointer = { x: (event.clientX / Math.max(width, 1) - .5) * 2, y: (event.clientY / Math.max(height, 1) - .5) * 2 }; }, { passive: true });
  document.addEventListener('visibilitychange', () => { if (!document.hidden && !reducedMotion) restart(); });
  resize(); paint(0);
})();
