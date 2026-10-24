/* AURORA 3D layer: builds gold bars, drifting gold dust, mouse parallax, tilt cards, scroll deck. No dependencies. */
(function () {
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var fine = window.matchMedia && matchMedia('(pointer: fine)').matches;
  var mouse = { x: 0, y: 0 }, smooth = { x: 0, y: 0 };

  /* ---- Gold stacks: data-gold-stack="3,2,1" = bars per row, bottom to top ---- */
  function buildStacks() {
    document.querySelectorAll('[data-gold-stack]').forEach(function (el) {
      var rows = el.dataset.goldStack.split(',').map(Number);
      var W = 150, H = 42, G = 7, n = 0, bars = '';
      rows.forEach(function (count, r) {
        var y = -(r - (rows.length - 1) / 2) * (H + G);
        for (var k = 0; k < count; k++) {
          var x = (k - (count - 1) / 2) * (W + G);
          bars += '<div class="bar" style="--x:' + x + 'px;--y:' + y + 'px">' +
            '<div class="f front"><span>AURORA · 995 BASIS</span></div><div class="f back"></div>' +
            '<div class="f left"></div><div class="f right"></div>' +
            '<div class="f top"><span>AURORA</span><i class="shine" style="--sd:' + (n * 0.7) + 's"></i></div><div class="f bottom"></div></div>';
          n++;
        }
      });
      var chips = el.querySelector('template');
      el.insertAdjacentHTML('afterbegin', '<div class="glow"></div><div class="ground"></div>');
      var rig = document.createElement('div'); rig.className = 'rig';
      rig.innerHTML = '<div class="bob"><div class="sway">' + bars + '</div></div>' + (chips ? chips.innerHTML : '');
      el.appendChild(rig);
    });
  }

  /* ---- Gold dust canvas (depth-projected particles) ---- */
  function dust() {
    var c = document.createElement('canvas'); c.id = 'dust'; c.setAttribute('aria-hidden', 'true'); document.body.appendChild(c);
    var ctx = c.getContext('2d'), w, h, dpr = Math.min(window.devicePixelRatio || 1, 2), pts = [];
    if (!ctx) { c.hidden = true; return function () {}; }
    function size() { w = innerWidth; h = innerHeight; c.width = w * dpr; c.height = h * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); }
    size(); addEventListener('resize', size);
    var isLanding = document.body.classList.contains('landing-page');
    var N = w < 700 ? (isLanding ? 48 : 45) : (isLanding ? 118 : 95);
    for (var i = 0; i < N; i++) pts.push({
      x: Math.random() * 2 - 1, y: Math.random() * 2 - 1, z: Math.random(),
      s: .15 + Math.random() * .35, p: Math.random() * 6.28,
      flake: isLanding && Math.random() < .24, angle: Math.random() * 6.28,
      spin: (Math.random() - .5) * .0018, sway: Math.random() * 6.28
    });
    function frame(t) {
      ctx.clearRect(0, 0, w, h);
      for (var i = 0; i < pts.length; i++) {
        var p = pts[i];
        if (!reduce) {
          p.y += p.s * (p.flake ? 0.00042 : -0.0009) * (1 + p.z);
          if (p.flake) { p.x += Math.sin(t / 1400 + p.sway) * 0.00012; p.angle += p.spin * 16; }
          if (p.y < -1.1 || p.y > 1.1) { p.y = p.y < 0 ? 1.1 : -1.1; p.x = Math.random() * 2 - 1; }
        }
        var depth = 0.25 + p.z * 0.75;
        var px = w / 2 + (p.x * w / 2) * 1.05 - smooth.x * 38 * depth;
        var py = h / 2 + (p.y * h / 2) * 1.05 - smooth.y * 24 * depth;
        var r = (p.flake ? 1.1 : 0.6) + depth * (p.flake ? 1.5 : 2.1), tw = .55 + .45 * Math.sin(t / 900 + p.p);
        var g = ctx.createRadialGradient(px, py, 0, px, py, r * 4);
        g.addColorStop(0, 'rgba(255,224,110,' + ((p.flake ? 0.52 : 0.75) * depth * tw) + ')'); g.addColorStop(1, 'rgba(240,185,11,0)');
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(px, py, r * 4, 0, 6.283); ctx.fill();
        if (p.flake) {
          ctx.save(); ctx.translate(px, py); ctx.rotate(p.angle);
          ctx.globalAlpha = .28 + .38 * depth * tw; ctx.fillStyle = '#ffe9a0';
          ctx.beginPath(); ctx.moveTo(0, -r * 1.8); ctx.lineTo(r * .56, 0); ctx.lineTo(0, r * 1.8); ctx.lineTo(-r * .56, 0); ctx.closePath(); ctx.fill();
          ctx.restore();
        }
      }
    }
    return frame;
  }

  /* ---- Tilt cards ---- */
  function tilt(selector, max) {
    document.querySelectorAll(selector).forEach(function (el) {
      el.classList.add('t3');
      if (!fine || reduce) return;
      var m = parseFloat(getComputedStyle(el).getPropertyValue('--max')) || max;
      el.addEventListener('mousemove', function (e) {
        var r = el.getBoundingClientRect(), px = (e.clientX - r.left) / r.width, py = (e.clientY - r.top) / r.height;
        el.classList.add('t3-on');
        el.style.setProperty('--ry', ((px - .5) * 2 * m).toFixed(2) + 'deg');
        el.style.setProperty('--rx', ((.5 - py) * 2 * m).toFixed(2) + 'deg');
        el.style.setProperty('--gx', (px * 100) + '%'); el.style.setProperty('--gy', (py * 100) + '%');
      });
      el.addEventListener('mouseleave', function () {
        el.classList.remove('t3-on'); el.style.setProperty('--rx', '0deg'); el.style.setProperty('--ry', '0deg');
      });
    });
  }

  /* ---- Init ---- */
  function init() {
    buildStacks();
    var dustFrame = dust();
    tilt('.module, .audience .panel, .compare .panel', 9);
    tilt('.auth-card', 4);
    var scenes = document.querySelectorAll('.scene'), deck = document.getElementById('deckRig'), stage = document.getElementById('stage');

    if (fine && !reduce) addEventListener('mousemove', function (e) { mouse.x = e.clientX / innerWidth * 2 - 1; mouse.y = e.clientY / innerHeight * 2 - 1; });

    var frameId = 0;
    function loop(t) {
      smooth.x += (mouse.x - smooth.x) * 0.06; smooth.y += (mouse.y - smooth.y) * 0.06;
      scenes.forEach(function (s) { s.style.setProperty('--mx', smooth.x.toFixed(3)); s.style.setProperty('--my', smooth.y.toFixed(3)); });
      if (deck && stage) {
        var r = stage.getBoundingClientRect(), vh = innerHeight;
        var p = reduce ? 1 : Math.min(1, Math.max(0, (vh - r.top) / (vh * 0.85)));
        var e = 1 - Math.pow(p, 1.6);
        deck.style.setProperty('--drx', (24 * e + smooth.y * -3).toFixed(2) + 'deg');
        deck.style.setProperty('--dry', (-10 * e + smooth.x * 6).toFixed(2) + 'deg');
        deck.style.setProperty('--dty', (30 * e).toFixed(1) + 'px');
      }
      dustFrame(t);
      if (!document.hidden) frameId = requestAnimationFrame(loop);
    }
    if (reduce) {
      dustFrame(0);
    } else {
      frameId = requestAnimationFrame(loop);
      document.addEventListener('visibilitychange', function () {
        if (document.hidden) cancelAnimationFrame(frameId);
        else frameId = requestAnimationFrame(loop);
      });
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
