/* One shared, data-agnostic boot surface. Pages own the real readiness boundary. */
(() => {
  const id = 'auroraBootLoader';
  const introWindow = 3200;
  let startedAt = 0;
  let completeRequested = false;
  let hideTimer = 0;
  const markup = () => `<section id="${id}" role="status" aria-live="polite" aria-label="AURORA is initializing" hidden>
    <div class="aurora-boot-atmosphere" aria-hidden="true">
      <span class="aurora-boot-nugget nugget-one"></span><span class="aurora-boot-nugget nugget-two"></span><span class="aurora-boot-nugget nugget-three"></span>
      <span class="aurora-boot-dust dust-one"></span><span class="aurora-boot-dust dust-two"></span><span class="aurora-boot-dust dust-three"></span><span class="aurora-boot-dust dust-four"></span><span class="aurora-boot-dust dust-five"></span>
    </div>
    <div class="aurora-boot-grid" aria-hidden="true"></div><div class="aurora-boot-glow" aria-hidden="true"></div>
    <div class="aurora-boot-panel">
      <div class="aurora-boot-heading"><span class="aurora-boot-mark" aria-hidden="true"><img src="aurora-mark.png" alt=""></span><span class="aurora-boot-wordmark">AURORA</span></div>
      <div class="aurora-terminal" aria-hidden="true">
        <div class="aurora-terminal-label">MARKET INTELLIGENCE <span>INITIALIZING</span></div>
        <div class="aurora-candles">${[25,39,31,54,37,48,29,57,41,63,34,50,43,70,46,59,38,66].map((h, i) => `<i style="--h:${h}px;--i:${i}"></i>`).join('')}</div>
        <svg class="aurora-trace" viewBox="0 0 600 130" preserveAspectRatio="none"><path d="M0,93 C38,88 48,69 81,78 S134,106 171,81 S222,44 261,62 S315,94 352,73 S399,40 439,50 S489,84 525,61 S562,40 600,26"/></svg>
        <span class="aurora-coin" aria-hidden="true"><i>A</i></span>
      </div>
      <div class="aurora-boot-status"><i aria-hidden="true"></i><span id="auroraBootStatus">Initializing workspace</span></div>
      <div class="aurora-boot-progress" role="progressbar" aria-label="Initialization in progress"><span></span></div>
    </div>
  </section>`;
  function node() { let el = document.getElementById(id); if (!el) { document.body.insertAdjacentHTML('afterbegin', markup()); el = document.getElementById(id); } return el; }
  window.AuroraLoader = {
    start(label = 'Initializing workspace') {
      const el = node();
      if (el.hidden || el.classList.contains('is-leaving')) { startedAt = performance.now(); completeRequested = false; window.clearTimeout(hideTimer); }
      el.hidden = false; el.classList.remove('is-leaving'); el.classList.add('is-entering'); this.status(label);
    },
    status(label) { const target = document.getElementById('auroraBootStatus'); if (target) target.textContent = label; },
    complete() {
      const el = document.getElementById(id);
      if (!el || el.hidden || el.classList.contains('is-leaving') || completeRequested) return;
      completeRequested = true;
      const leave = () => {
        if (!el.isConnected || el.hidden) return;
        el.classList.remove('is-entering'); el.classList.add('is-leaving');
        const finish = (event) => { if (event && event.target !== el) return; el.hidden = true; el.removeEventListener('transitionend', finish); };
        el.addEventListener('transitionend', finish);
        hideTimer = window.setTimeout(finish, 650);
      };
      const remaining = Math.max(0, introWindow - (performance.now() - startedAt));
      window.setTimeout(leave, remaining);
    },
    fail(label = 'Unable to initialize workspace') { this.status(label); const indicator = document.querySelector(`#${id} .aurora-boot-status i`); if (indicator) indicator.classList.add('has-error'); }
  };
})();
