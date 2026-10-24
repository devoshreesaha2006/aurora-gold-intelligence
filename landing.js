/* Small, dependency-free interactions for the AURORA landing page. */
(function () {
  'use strict';

  var menu = document.getElementById('navToggle');
  var nav = document.getElementById('nav');

  function closeMenu() {
    if (!menu || !nav) return;
    menu.setAttribute('aria-expanded', 'false');
    menu.setAttribute('aria-label', 'Open navigation');
    nav.classList.remove('open');
  }

  if (menu && nav) {
    menu.addEventListener('click', function () {
      var open = menu.getAttribute('aria-expanded') !== 'true';
      menu.setAttribute('aria-expanded', String(open));
      menu.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
      nav.classList.toggle('open', open);
    });
    nav.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', closeMenu);
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') closeMenu();
    });
    document.addEventListener('click', function (event) {
      if (!nav.contains(event.target) && !menu.contains(event.target)) closeMenu();
    });
  }

  var revealItems = document.querySelectorAll('[data-reveal]');
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var hero = document.querySelector('.gold-hero');
  var coins = document.querySelectorAll('.coin');

  if (hero && coins.length && !reduceMotion) {
    var finePointer = window.matchMedia && window.matchMedia('(pointer: fine)').matches;
    var motionFrame = 0;
    var pointer = { x: 0, y: 0 };
    function updateCoinMotion() {
      motionFrame = 0;
      var bounds = hero.getBoundingClientRect();
      var progress = Math.max(0, Math.min(1, (window.innerHeight - bounds.top) / (window.innerHeight + bounds.height)));
      coins.forEach(function (coin, index) {
        var side = index === 0 ? -1 : 1;
        coin.style.setProperty('--coin-scroll-x', (side * progress * 36).toFixed(1) + 'px');
        coin.style.setProperty('--coin-scroll-y', ((progress - .2) * (index === 0 ? -42 : 34)).toFixed(1) + 'px');
        coin.style.setProperty('--coin-mouse-x', (pointer.x * (index === 0 ? 16 : 25)).toFixed(1) + 'px');
        coin.style.setProperty('--coin-mouse-y', (pointer.y * (index === 0 ? 11 : 17)).toFixed(1) + 'px');
      });
    }
    function scheduleCoinMotion() {
      if (!motionFrame) motionFrame = window.requestAnimationFrame(updateCoinMotion);
    }
    window.addEventListener('scroll', scheduleCoinMotion, { passive: true });
    window.addEventListener('resize', scheduleCoinMotion, { passive: true });
    if (finePointer) {
      hero.addEventListener('pointermove', function (event) {
        var rect = hero.getBoundingClientRect();
        pointer.x = ((event.clientX - rect.left) / rect.width - .5) * 2;
        pointer.y = ((event.clientY - rect.top) / rect.height - .5) * 2;
        scheduleCoinMotion();
      }, { passive: true });
      hero.addEventListener('pointerleave', function () { pointer.x = 0; pointer.y = 0; scheduleCoinMotion(); }, { passive: true });
    }
    updateCoinMotion();
  }

  if (reduceMotion || !('IntersectionObserver' in window)) {
    revealItems.forEach(function (item) { item.classList.add('is-visible'); });
    return;
  }

  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-visible');
      observer.unobserve(entry.target);
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -35px 0px' });

  revealItems.forEach(function (item) { observer.observe(item); });
})();
