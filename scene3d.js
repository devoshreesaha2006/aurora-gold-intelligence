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
            '<div class="f front"><span>FINE GOLD 999.9</span></div><div class="f back"></div>' +
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
    function size() { w = innerWidth; h = innerHeight; c.width = w * dpr; c.height = h * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); }
    size(); addEventListener('resize', size);
    var N = w < 700 ? 45 : 95;
    for (var i = 0; i < N; i++) pts.push({ x: Math.random() * 2 - 1, y: Math.random() * 2 - 1, z: Math.random(), s: .15 + Math.random() * .35, p: Math.random() * 6.28 });
    function frame(t) {
      ctx.clearRect(0, 0, w, h);
      for (var i = 0; i < pts.length; i++) {
        var p = pts[i];
        if (!reduce) { p.y -= p.s * 0.0009 * (1 + p.z); if (p.y < -1.1) { p.y = 1.1; p.x = Math.random() * 2 - 1; } }
        var depth = 0.25 + p.z * 0.75;
        var px = w / 2 + (p.x * w / 2) * 1.05 - smooth.x * 38 * depth;
        var py = h / 2 + (p.y * h / 2) * 1.05 - smooth.y * 24 * depth;
        var r = 0.6 + depth * 2.1, tw = .55 + .45 * Math.sin(t / 900 + p.p);
        var g = ctx.createRadialGradient(px, py, 0, px, py, r * 4);
        g.addColorStop(0, 'rgba(255,224,110,' + (0.75 * depth * tw) + ')'); g.addColorStop(1, 'rgba(240,185,11,0)');
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(px, py, r * 4, 0, 6.283); ctx.fill();
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
      requestAnimationFrame(loop);
    }
    requestAnimationFrame(loop);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
