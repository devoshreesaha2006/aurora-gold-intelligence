/* Shared procedural gold-crystal and sparkle atmosphere. Decorative canvas; never receives pointer input. */
(() => {
  const canvasId = 'aurora-gold-nuggets';
  if (document.getElementById(canvasId)) return;
  if (!document.getElementById('aurora-sparkle-style')) {
    const style = document.createElement('style');
    style.id = 'aurora-sparkle-style';
    style.textContent = `#${canvasId}{position:fixed;inset:0;width:100vw;height:100vh;z-index:0;pointer-events:none;opacity:.22}.aurora-sparkles-over-media{z-index:0!important;opacity:.22!important}@media (max-width:700px){#${canvasId}{opacity:.16}}@media (prefers-reduced-motion:reduce){#${canvasId}{opacity:.12}}`;
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
  const sparkles = [], dust = [], crystals = [];
  let width = 1, height = 1, dpr = 1, pointer = { x: 0, y: 0 }, frameId = 0;
  const random = (min, max) => min + Math.random() * (max - min);

  function makeSparkle() {
    return { x: random(0, width), y: random(0, height), size: random(7, 12), phase: random(0, Math.PI * 2), speed: random(.12, .3), drift: random(8, 28), alpha: random(.78, 1), rotation: random(0, Math.PI * 2), flare: Math.random() > .58 };
  }
  function makeCrystal() {
    const depth = random(.62, 1.35);
    return {
      x: random(-20, width + 20), y: random(-20, height + 20),
      size: random(25, 62) * depth, depth,
      phase: random(0, Math.PI * 2), speed: random(.035, .095),
      drift: random(10, 34), rotation: random(0, Math.PI * 2),
      alpha: random(.18, .34)
    };
  }
  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 1.5); width = window.innerWidth; height = window.innerHeight;
    canvas.width = Math.round(width * dpr); canvas.height = Math.round(height * dpr);
    canvas.style.width = `${width}px`; canvas.style.height = `${height}px`; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    sparkles.length = 0; dust.length = 0; crystals.length = 0;
    const count = smallScreen ? 15 : Math.min(44, Math.max(32, Math.round(width / 58)));
    for (let index = 0; index < count; index += 1) sparkles.push(makeSparkle());
    for (let index = 0; index < (smallScreen ? 3 : Math.min(8, Math.max(5, Math.round(width / 320)))); index += 1) crystals.push(makeCrystal());
    for (let index = 0; index < (smallScreen ? 12 : 34); index += 1) dust.push({ x: random(0, width), y: random(0, height), size: random(.5, 1.25), alpha: random(.07, .2), phase: random(0, Math.PI * 2), speed: random(.06, .18) });
  }
  function drawCrystal(crystal, time) {
    const motion = reducedMotion ? 0 : time;
    const driftX = Math.sin(motion * crystal.speed + crystal.phase) * crystal.drift + pointer.x * 3 * crystal.depth;
    const driftY = Math.cos(motion * crystal.speed * .72 + crystal.phase) * crystal.drift * .7 + pointer.y * 3 * crystal.depth;
    const size = crystal.size * (1 + Math.sin(motion * crystal.speed + crystal.phase) * .025);
    const points = [
      [0, -0.58], [0.34, -0.42], [0.48, -0.06], [0.25, 0.48],
      [-0.13, 0.58], [-0.43, 0.18], [-0.38, -0.22], [-0.16, -0.5]
    ];
    ctx.save();
    ctx.translate(crystal.x + driftX, crystal.y + driftY);
    ctx.rotate(crystal.rotation + motion * crystal.speed * .28);
    ctx.scale(size, size);
    ctx.globalAlpha = crystal.alpha;
    ctx.shadowColor = 'rgba(255,197,70,.9)';
    ctx.shadowBlur = 10 * crystal.depth;

    // Faceted silhouette with individually lit planes gives the shards a 3D cut-gold look.
    ctx.beginPath();
    points.forEach(([x, y], index) => index ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
    ctx.closePath();
    const body = ctx.createLinearGradient(-.45, -.5, .42, .48);
    body.addColorStop(0, 'rgba(255,235,165,.82)');
    body.addColorStop(.34, 'rgba(219,169,56,.7)');
    body.addColorStop(.72, 'rgba(116,74,13,.68)');
    body.addColorStop(1, 'rgba(255,218,112,.76)');
    ctx.fillStyle = body;
    ctx.fill();
    ctx.shadowBlur = 0;

    const center = [-.025, .025];
    const facetColors = [
      'rgba(255,242,192,.58)', 'rgba(251,203,90,.42)', 'rgba(125,82,17,.48)',
      'rgba(255,223,132,.54)', 'rgba(173,119,27,.45)', 'rgba(255,239,176,.5)',
      'rgba(111,73,16,.4)', 'rgba(232,183,72,.44)'
    ];
    points.forEach(([x, y], index) => {
      const next = points[(index + 1) % points.length];
      ctx.beginPath(); ctx.moveTo(center[0], center[1]); ctx.lineTo(x, y); ctx.lineTo(next[0], next[1]); ctx.closePath();
      ctx.fillStyle = facetColors[index]; ctx.fill();
    });
    ctx.strokeStyle = 'rgba(255,230,151,.7)';
    ctx.lineWidth = .018;
    ctx.beginPath(); points.forEach(([x, y], index) => index ? ctx.lineTo(x, y) : ctx.moveTo(x, y)); ctx.closePath(); ctx.stroke();
    ctx.restore();
  }
  function drawSparkle(sparkle, time) {
    const motion = reducedMotion ? 0 : time;
    const twinkle = .32 + .68 * (.5 + .5 * Math.sin(motion * sparkle.speed + sparkle.phase));
    const x = sparkle.x + Math.sin(motion * sparkle.speed * .42 + sparkle.phase) * sparkle.drift + pointer.x * 2;
    const y = sparkle.y - Math.cos(motion * sparkle.speed * .35 + sparkle.phase) * sparkle.drift * .7 + pointer.y * 2;
    const size = sparkle.size * (.76 + twinkle * .32);
    ctx.save(); ctx.translate(x, y); ctx.rotate(sparkle.rotation + motion * .025); ctx.globalAlpha = sparkle.alpha * twinkle;
    const glowRadius = size * (sparkle.flare ? 11 : 8);
    const halo = ctx.createRadialGradient(0, 0, 0, 0, 0, glowRadius);
    halo.addColorStop(0, sparkle.flare ? 'rgba(255,224,143,.54)' : 'rgba(255,224,143,.38)');
    halo.addColorStop(.22, 'rgba(255,207,103,.25)');
    halo.addColorStop(1, 'rgba(255,207,103,0)');
    ctx.fillStyle = halo; ctx.beginPath(); ctx.arc(0, 0, glowRadius, 0, Math.PI * 2); ctx.fill();
    ctx.shadowColor = 'rgba(255,207,103,1)'; ctx.shadowBlur = size * (sparkle.flare ? 8 : 5.8);
    const ray = ctx.createLinearGradient(0, -size * 1.5, 0, size * 1.5);
    ray.addColorStop(0, 'rgba(255,245,205,0)'); ray.addColorStop(.5, 'rgba(255,231,166,.96)'); ray.addColorStop(1, 'rgba(232,184,77,0)');
    ctx.fillStyle = ray; ctx.beginPath(); ctx.moveTo(0, -size * 1.5); ctx.quadraticCurveTo(size * .12, -size * .12, size * 1.15, 0); ctx.quadraticCurveTo(size * .12, size * .12, 0, size * 1.5); ctx.quadraticCurveTo(-size * .12, size * .12, -size * 1.15, 0); ctx.quadraticCurveTo(-size * .12, -size * .12, 0, -size * 1.5); ctx.fill();
    ctx.fillStyle = 'rgba(255,248,220,.92)'; ctx.beginPath(); ctx.arc(0, 0, Math.max(.65, size * .13), 0, Math.PI * 2); ctx.fill(); ctx.restore();
  }
  function drawDust(time) { dust.forEach((particle) => { const x = particle.x + Math.sin(time * particle.speed + particle.phase) * 8, y = particle.y - Math.cos(time * particle.speed * .6 + particle.phase) * 6; ctx.beginPath(); ctx.arc(x, y, particle.size, 0, Math.PI * 2); ctx.fillStyle = `rgba(232,191,85,${particle.alpha * (reducedMotion ? .6 : .9)})`; ctx.fill(); }); }
  function paint(timestamp) { const time = timestamp * .001; ctx.clearRect(0, 0, width, height); drawDust(time); crystals.forEach((crystal) => drawCrystal(crystal, time)); sparkles.forEach((sparkle) => drawSparkle(sparkle, time)); if (!reducedMotion && !document.hidden) frameId = requestAnimationFrame(paint); }
  function restart() { cancelAnimationFrame(frameId); paint(0); }
  window.addEventListener('resize', () => { resize(); restart(); }, { passive: true });
  if (!reducedMotion && !smallScreen) window.addEventListener('pointermove', (event) => { pointer = { x: (event.clientX / Math.max(width, 1) - .5) * 2, y: (event.clientY / Math.max(height, 1) - .5) * 2 }; }, { passive: true });
  document.addEventListener('visibilitychange', () => { if (!document.hidden && !reducedMotion) restart(); });
  resize(); paint(0);
})();
