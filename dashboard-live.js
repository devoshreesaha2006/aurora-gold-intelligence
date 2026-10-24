/* Live dashboard binding. All displayed market values come from the existing API. */
(() => {
  const API = 'http://127.0.0.1:8000/api';
  const pairKeys = ['GOLDM-GOLDTEN', 'GOLDM-GOLDGUINEA', 'GOLDM-GOLDPETAL', 'GOLDTEN-GOLDGUINEA', 'GOLDTEN-GOLDPETAL', 'GOLDGUINEA-GOLDPETAL'];
  const colors = ['#dfc477', '#c99c4e', '#b47d3d', '#9d8b59', '#d7ae5d', '#857a61'];
  const model = { status: null, contracts: [], prices: [], radar: [], radarDate: null, events: [], loaded: {}, timeframe: '30D', pure: true, costFilter: true };
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => Array.from(root.querySelectorAll(s));
  const money = n => Number.isFinite(Number(n)) ? `${Number(n) < 0 ? '-₹' : '₹'}${Math.abs(Number(n)).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—';
  const text = (el, value) => { if (el) el.textContent = value; };
  const empty = (message, icon = 'fa-database') => `<div class="dashboard-empty-state"><i class="fa-solid ${icon}"></i>${message}</div>`;
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const formatSummary = value => String(value ?? '').replace(/₹-(?=\d)/g, '-₹');
  const hasSpread = pair => pair?.spread !== null && pair?.spread !== undefined && Number.isFinite(Number(pair.spread));

  // Clear the legacy demo values before the page paints. Existing controls and routes stay in place.
  function clearDemoContent() {
    const cards = $$('.kpi-card');
    cards.forEach((card, index) => {
      const value = $('.kpi-value', card);
      if (value) { value.innerHTML = '— <span class="kpi-value-unit">Loading</span>'; value.classList.add('is-loading'); }
      const meta = $('.kpi-meta-row', card);
      if (meta) meta.innerHTML = '<span class="kpi-subtitle">Waiting for backend data</span><span class="kpi-tag">Loading</span>';
      const tip = $('.kpi-tooltip', card);
      if (tip) tip.textContent = 'Values appear when API data is available.';
      const title = $('.kpi-title', card);
      if (title && index === 1) title.textContent = 'Investigations';
      if (title && index === 2) title.textContent = 'Mean pair spread';
      if (title && index === 3) title.textContent = 'Highest opportunity';
    });
    const tbody = $('.health-table tbody');
    if (tbody) tbody.innerHTML = '';
    const feed = $('#alertsFeed');
    if (feed) feed.innerHTML = empty('Loading event investigations…', 'fa-spinner fa-spin');
    const intel = $('.intel-feed-timeline');
    if (intel) intel.innerHTML = empty('Loading market events…', 'fa-spinner fa-spin');
    const donutCenter = $('.radar-donut-center');
    if (donutCenter) donutCenter.innerHTML = '<div class="donut-center-num">—</div><div class="donut-center-lbl">Investigations</div>';
    const breakdown = $('.radar-breakdown-list');
    if (breakdown) breakdown.innerHTML = '';
    const spreadSummary = $('.spread-summary-bar');
    if (spreadSummary) spreadSummary.innerHTML = '<span>Spread summary</span><strong>Waiting for API data</strong>';
    const statusChip = $('.market-status-chip');
    if (statusChip) statusChip.innerHTML = '<span class="live-pulse-dot"></span><span>Checking data source…</span>';
    const freshness = $('.data-freshness-chip');
    if (freshness) freshness.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i><span>Checking observations…</span>';
    const notificationList = $('#notifDropdown');
    if (notificationList) {
      const header = $('.notif-header', notificationList);
      notificationList.innerHTML = '';
      if (header) notificationList.appendChild(header);
      notificationList.insertAdjacentHTML('beforeend', empty('No event data loaded yet.', 'fa-bell-slash'));
    }
    const calendar = $('.calendar-grid-box');
    if (calendar) calendar.innerHTML = '';
    const legend = $('.cal-legend-strip'); if (legend) legend.innerHTML = empty('Expiry dates appear when observations include a contract expiry.');
    text($('.calendar-month-name'), 'Loading expiry dates…');
    const cycle = $('#expiry-calendar-section .panel-actions .nav-badge'); if (cycle) cycle.textContent = 'Awaiting observations';
  }

  function getPayload(json) { return json?.data ?? null; }
  async function fetchApi(path) {
    const response = await fetch(`${API}${path}`, { mode: 'cors', headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    const json = await response.json();
    if (json?.success === false) throw new Error(json.message || 'API returned an error');
    return getPayload(json);
  }

  function setEmptyCardValues(message = 'Backend data unavailable') {
    $$('.kpi-card').forEach(card => {
      const value = $('.kpi-value', card);
      if (value) { value.innerHTML = '— <span class="kpi-value-unit">Unavailable</span>'; value.classList.remove('is-loading'); }
      const meta = $('.kpi-meta-row', card);
      if (meta) meta.innerHTML = `<span class="kpi-subtitle">${esc(message)}</span>`;
    });
  }

  function updateStatus() {
    const status = model.status;
    const statusChip = $('.market-status-chip');
    const freshness = $('.data-freshness-chip');
    if (!status) {
      if (statusChip) statusChip.innerHTML = '<span class="live-pulse-dot" style="background:#b66e5b"></span><span>API unavailable</span>';
      if (freshness) freshness.innerHTML = '<i class="fa-solid fa-circle-exclamation"></i><span>Could not load market status</span>';
      return;
    }
    const mode = status.data_mode || 'unknown';
    const feed = String(status.feed_status || '').toUpperCase();
    const label = feed === 'LIVE' && status.is_live_connected === true ? 'Verified MCX live feed'
      : feed === 'DELAYED' ? 'Authorized delayed MCX feed'
      : feed === 'STALE' ? 'Provider feed stale'
      : mode === 'staged_csv' ? 'Imported CSV · unverified'
      : mode === 'demo_synthetic' ? 'Synthetic demo data'
      : mode === 'test_data' ? 'Test data · excluded from analysis'
      : 'Market feed unavailable';
    const dot = feed === 'LIVE' && status.is_live_connected === true ? '#6da982' : feed === 'STALE' ? '#b66e5b' : '#d1ad5e';
      const sessionLabel = status.market_session_status === 'unknown' || status.market_open == null
        ? 'Session unavailable'
        : status.market_open ? 'Session open' : 'Session closed';
    if (statusChip) statusChip.innerHTML = `<span class="live-pulse-dot" style="background:${dot}"></span><span>${esc(label)} · ${sessionLabel}</span>`;
    const when = status.latest_trade_date || status.last_ingestion_at || 'No observation date';
    const provenance = status.data_freshness_label || `${Number(status.total_observations || 0).toLocaleString('en-IN')} stored observations · ${when}`;
    if (freshness) freshness.innerHTML = `<i class="fa-solid fa-database"></i><span>${esc(provenance)}</span>`;
  }

  function latestBySymbol() {
    const map = new Map();
    model.prices.forEach(item => {
      const current = map.get(item.symbol);
      if (!current || String(item.trade_date) > String(current.trade_date)) map.set(item.symbol, item);
    });
    return map;
  }

  function updateKpis() {
    const cards = $$('.kpi-card');
    const activeContracts = model.contracts.filter(c => c.is_active !== false);
    const validPairs = model.radar.filter(hasSpread);
    const investigations = validPairs.filter(p => p.classification === 'Investigate');
    const meanAbsSpread = validPairs.length ? validPairs.reduce((sum, p) => sum + Math.abs(Number(p.spread)), 0) / validPairs.length : null;
    const scoredPairs = validPairs.filter(p => p.opportunity_score != null && Number.isFinite(Number(p.opportunity_score)));
    const best = scoredPairs.reduce((a, b) => !a || Number(b.opportunity_score) > Number(a.opportunity_score) ? b : a, null);
    const values = [
      { value: String(activeContracts.length), unit: 'Active', subtitle: `${activeContracts.length} contract specifications`, tag: model.status ? 'API connected' : 'Status unavailable' },
      { value: String(investigations.length), unit: 'Investigate', subtitle: `Latest radar snapshot · ${model.radarDate || 'date unavailable'}`, tag: `${validPairs.length} pairs with data` },
      { value: meanAbsSpread == null ? '—' : money(meanAbsSpread), unit: '/ 10g', subtitle: `Mean absolute spread · ${validPairs.length} pairs`, tag: 'Relative value' },
      { value: best ? `${Number(best.opportunity_score).toFixed(0)}%` : '—', unit: 'Score', subtitle: best ? `${best.pair} · ${best.classification}` : 'No scored pair data', tag: best ? `Trap risk ${Number(best.trap_risk_score).toFixed(0)}%` : 'Awaiting observations' }
    ];
    cards.forEach((card, i) => {
      const v = values[i];
      if (!v) return;
      const sourceLoaded = i === 0 ? model.loaded.contracts : i === 1 || i === 2 || i === 3 ? model.loaded.radar : false;
      const value = $('.kpi-value', card);
      if (value) { value.innerHTML = sourceLoaded ? `${esc(v.value)} <span class="kpi-value-unit">${esc(v.unit)}</span>` : '— <span class="kpi-value-unit">Unavailable</span>'; value.classList.remove('is-loading'); }
      const meta = $('.kpi-meta-row', card);
      if (meta) meta.innerHTML = `<span class="kpi-subtitle">${esc(sourceLoaded ? v.subtitle : 'Analytics endpoint unavailable')}</span><span class="kpi-tag">${esc(sourceLoaded ? v.tag : 'Unavailable')}</span>`;
      const tip = $('.kpi-tooltip', card);
      if (tip) tip.textContent = i === 0 ? activeContracts.map(c => c.symbol).join(', ') || 'No active contracts returned.' : i === 1 ? investigations.map(p => p.pair).join(', ') || 'No pairs currently classified as Investigate.' : i === 2 ? 'Mean of absolute normalized spread values returned by the radar endpoint.' : best ? `${best.pair}: opportunity ${Number(best.opportunity_score).toFixed(1)}, trap risk ${Number(best.trap_risk_score).toFixed(1)}.` : 'Score appears when observations are available.';
    });
  }

  function updateContracts() {
    const tbody = $('.health-table tbody');
    if (!tbody) return;
    const latest = latestBySymbol();
    const available = model.contracts;
    const priceHeader = $('.health-table thead th:nth-child(2)');
    if (priceHeader) priceHeader.textContent = model.pure ? 'Normalized price / 10g' : 'Raw quoted price';
    const syncBadge = $('.health-table')?.closest('.panel')?.querySelector('.panel-actions .nav-badge');
    if (syncBadge) syncBadge.textContent = model.prices.length ? `Latest · ${model.prices.reduce((a, b) => String(a.trade_date) > String(b.trade_date) ? a : b).trade_date}` : 'No observations';
    if (!available.length) { tbody.innerHTML = `<tr><td colspan="4">${empty(model.loaded.contracts ? 'No contract data is available.' : 'Contract service unavailable.')}</td></tr>`; return; }
    tbody.innerHTML = available.map(contract => {
      const item = latest.get(contract.symbol);
      const status = contract.is_active === false ? 'Inactive' : item ? 'Observed' : 'No observations';
      const norm = item ? (model.pure ? item.normalized_price_10g_basis : item.close_price) : null;
      const quote = item ? item.close_price : null;
      const unit = contract.trading_unit || '—';
      const quoteUnit = contract.quote_unit || '—';
      return `<tr onclick="showContractDetailModal('${esc(contract.symbol)}')"><td><div class="contract-tag-cell"><i class="fa-solid fa-coins" style="color:#d6b363"></i><div><div class="contract-sym">${esc(contract.symbol)}</div><span class="contract-lot">${esc(unit)} · quote ${esc(quoteUnit)}</span></div></div></td><td><div class="price-norm-val">${norm == null ? '—' : money(norm)}</div><div class="price-norm-sub">${quote == null ? 'No observation' : `Quoted ${money(quote)} · ${esc(item.trade_date)}`}</div></td><td><div>${item ? Number(item.volume || 0).toLocaleString('en-IN') : '—'}</div><div class="price-norm-sub">${item ? `OI ${Number(item.open_interest || 0).toLocaleString('en-IN')}` : 'No observation'}</div></td><td><span class="status-badge ${item ? 'active' : 'watch'}">${esc(status)}</span></td></tr>`;
    }).join('');
  }

  function showChartEmpty(message) {
    const holder = $('.chart-box-relative');
    if (!holder) return;
    let state = $('.chart-empty-overlay', holder);
    if (!state) { state = document.createElement('div'); state.className = 'chart-empty-overlay'; holder.appendChild(state); }
    state.innerHTML = empty(message);
    state.hidden = false;
  }

  function canvasContext(id, height = 310) {
    const canvas = document.getElementById(id);
    if (!canvas) return null;
    $('.native-chart-svg', canvas.parentElement)?.remove();
    canvas.style.visibility = 'visible';
    const width = Math.max(280, canvas.parentElement?.clientWidth || canvas.clientWidth || 640);
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.style.width = '100%'; canvas.style.height = `${height}px`;
    canvas.width = Math.round(width * dpr); canvas.height = Math.round(height * dpr);
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);
    return { canvas, ctx, width, height };
  }

  function mountNativeSvg(canvas, width, height, contents, label) {
    const parent = canvas.parentElement;
    let svg = $('.native-chart-svg', parent);
    if (!svg) { svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); svg.classList.add('native-chart-svg'); parent.appendChild(svg); }
    svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
    svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', label);
    svg.innerHTML = contents;
    canvas.style.visibility = 'hidden';
  }

  function drawNativeLine(labels, series) {
    const surface = canvasContext('priceComparisonChart', 310);
    if (!surface) return;
    const { canvas, width, height } = surface;
    const plot = { left: 70, right: width - 20, top: 24, bottom: height - 40 };
    const values = series.flatMap(s => s.values.filter(Number.isFinite));
    if (!values.length) { showChartEmpty(model.loaded.prices ? 'No price observations match this period.' : 'Market price service unavailable.'); return; }
    const floor = Math.floor(Math.min(...values) / 500) * 500;
    const ceiling = Math.ceil(Math.max(...values) / 500) * 500 || floor + 500;
    const range = Math.max(1, ceiling - floor);
    const xAt = i => labels.length <= 1 ? (plot.left + plot.right) / 2 : plot.left + (plot.right - plot.left) * i / (labels.length - 1);
    const yAt = value => plot.bottom - (value - floor) / range * (plot.bottom - plot.top);
    let svg = '';
    for (let tick = 0; tick <= 4; tick++) {
      const y = plot.top + (plot.bottom - plot.top) * tick / 4;
      const value = ceiling - range * tick / 4;
      svg += `<line x1="${plot.left}" y1="${y}" x2="${plot.right}" y2="${y}" stroke="rgba(221,190,116,.15)"/><text x="${plot.left - 10}" y="${y + 4}" text-anchor="end" fill="#b7ad98" font-size="12">${esc(`₹${Math.round(value).toLocaleString('en-IN')}`)}</text>`;
    }
    series.forEach(item => {
      let path = '', open = false;
      item.values.forEach((value, i) => {
        if (!Number.isFinite(value)) { open = false; return; }
        path += `${open ? ' L' : ' M'} ${xAt(i)} ${yAt(value)}`; open = true;
      });
      svg += `<path d="${path}" fill="none" stroke="${item.color}" stroke-width="2.7" stroke-linecap="round" stroke-linejoin="round"/>`;
      item.values.forEach((value, i) => {
        if (!Number.isFinite(value)) return;
        svg += `<circle cx="${xAt(i)}" cy="${yAt(value)}" r="3.2" fill="${item.color}" stroke="#100e09" stroke-width="1.4"><title>${esc(`${item.name} · ${labels[i]} · ${money(value)}${model.pure ? ' / 10g' : ' quoted'}`)}</title></circle>`;
      });
    });
    const labelStep = Math.max(1, Math.ceil(labels.length / 6));
    labels.forEach((label, i) => { if (i % labelStep === 0 || i === labels.length - 1) svg += `<text x="${xAt(i)}" y="${height - 12}" text-anchor="middle" fill="#a79d88" font-size="11">${esc(label)}</text>`; });
    mountNativeSvg(canvas, width, height, svg, 'Normalized MCX contract prices from market observations');
    const overlay = $('.chart-empty-overlay'); if (overlay) overlay.hidden = true;
  }

  function drawNativeDonut(counts) {
    const surface = canvasContext('opportunityDonutChart', 220);
    if (!surface) return;
    const { canvas, width, height } = surface;
    const total = counts.reduce((sum, n) => sum + n, 0);
    const cx = width / 2, cy = height / 2;
    const ring = Math.min(width, height) * .36;
    let angle = -Math.PI / 2, svg = `<circle cx="${cx}" cy="${cy}" r="${ring}" fill="none" stroke="rgba(220,190,120,.15)" stroke-width="20"/>`;
    const donutColors = ['#dfc477', '#c8954d', '#514b3d'];
    if (total) counts.forEach((count, index) => {
      const sweep = count / total * Math.PI * 2;
      if (sweep > .01) {
        const start = [cx + ring * Math.cos(angle), cy + ring * Math.sin(angle)];
        const endAngle = angle + sweep;
        const end = [cx + ring * Math.cos(endAngle), cy + ring * Math.sin(endAngle)];
        svg += `<path d="M ${start[0]} ${start[1]} A ${ring} ${ring} 0 ${sweep > Math.PI ? 1 : 0} 1 ${end[0]} ${end[1]}" fill="none" stroke="${donutColors[index]}" stroke-width="20"><title>${['Investigate','Watch','Cost / expiry / no signal'][index]}: ${count}</title></path>`;
      }
      angle += sweep;
    });
    mountNativeSvg(canvas, width, height, svg, 'Opportunity and trap classification distribution');
  }

  function drawNativeSpread(pairs) {
    const surface = canvasContext('spreadBarChart', 250);
    if (!surface) return;
    const { canvas, width, height } = surface;
    const selected = pairKeys.map(key => {
      const p = pairs.find(item => item.pair === key || item.pair === key.split('-').reverse().join('-'));
      if (!hasSpread(p) || (model.costFilter && ['Cost-Blocked', 'Expiry-Risk'].includes(p.classification))) return null;
      return { name: key.replace('GOLD', '').replace('-', '–'), value: Number(p.spread) * (p.pair === key ? 1 : -1), classification: p.classification };
    });
    const vals = selected.filter(Boolean).map(item => item.value);
    if (!vals.length) { const message = model.loaded.radar ? 'Spread observations unavailable' : 'Relative-value service unavailable'; mountNativeSvg(surface.canvas, width, height, `<text x="${width / 2}" y="${height / 2}" text-anchor="middle" fill="#b1a996" font-size="13">${esc(message)}</text>`, 'Spread analysis unavailable'); return; }
    const max = Math.max(...vals.map(Math.abs), 1), baseline = 26 + (height - 56) * max / (max * 2);
    const plotTop = 20, plotBottom = height - 40, slot = (width - 72) / 6, barWidth = Math.min(34, slot * .52);
    let svg = `<line x1="44" y1="${baseline}" x2="${width - 12}" y2="${baseline}" stroke="rgba(221,190,116,.2)"/>`;
    selected.forEach((item, i) => {
      const x = 48 + slot * i + slot / 2;
      if (item) {
        const y = baseline - item.value / (max * 2) * (plotBottom - plotTop);
        const color = item.classification === 'Investigate' ? '#ead08a' : item.classification === 'Watch' ? '#b68d49' : '#625b4d';
        svg += `<rect x="${x - barWidth / 2}" y="${Math.min(y, baseline)}" width="${barWidth}" height="${Math.max(2, Math.abs(baseline - y))}" rx="5" fill="${color}"><title>${esc(`${item.name}: ${money(item.value)} / 10g · ${item.classification}`)}</title></rect><text x="${x}" y="${item.value >= 0 ? Math.max(12, y - 6) : baseline + 14}" text-anchor="middle" fill="#d6c9aa" font-size="10">${esc(money(item.value).replace('₹',''))}</text>`;
      }
      svg += `<text x="${x}" y="${height - 12}" text-anchor="middle" fill="#a79d88" font-size="10">${esc(item?.name || '—')}</text>`;
    });
    mountNativeSvg(canvas, width, height, svg, 'Pairwise normalized spreads by contract');
  }

  function updatePriceChart() {
    const chart = window.priceChart;
    const symbols = ['GOLDM', 'GOLDTEN', 'GOLDGUINEA', 'GOLDPETAL'];
    const rows = model.prices.filter(item => symbols.includes(item.symbol));
    if (!rows.length) { if (chart) { chart.data.labels = []; chart.data.datasets.forEach(ds => { ds.data = []; }); chart.update(); } else canvasContext('priceComparisonChart', 310); showChartEmpty(model.loaded.prices ? 'Upload an MCX CSV or wait for market observations to compare contracts.' : 'Market price service unavailable.'); return; }
    const maxDate = rows.reduce((latest, row) => String(row.trade_date) > String(latest) ? row.trade_date : latest, rows[0].trade_date);
    const days = model.timeframe === '1D' ? 1 : model.timeframe === '7D' ? 7 : model.timeframe === '30D' ? 30 : model.timeframe === '90D' ? 90 : 365;
    const cutoff = new Date(`${maxDate}T00:00:00`); cutoff.setDate(cutoff.getDate() - days);
    const filtered = rows.filter(row => new Date(`${row.trade_date}T00:00:00`) >= cutoff).sort((a, b) => String(a.trade_date).localeCompare(String(b.trade_date)) || a.symbol.localeCompare(b.symbol));
    const labels = [...new Set(filtered.map(row => row.trade_date))];
    const series = ['GOLDM', 'GOLDTEN', 'GOLDGUINEA', 'GOLDPETAL'].map((symbol, index) => {
      const byDate = new Map(filtered.filter(r => r.symbol === symbol).map(r => [r.trade_date, Number(model.pure ? r.normalized_price_10g_basis : r.close_price)]));
      return { name: symbol, color: colors[index], values: labels.map(d => byDate.has(d) ? byDate.get(d) : null) };
    });
    if (!chart) drawNativeLine(labels.map(d => new Date(`${d}T00:00:00`).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })), series);
    else {
      chart.data.labels = labels.map(d => new Date(`${d}T00:00:00`).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }));
      chart.data.datasets.forEach(ds => { const item = series.find(s => s.name === ds.label.split(' ')[0]); ds.data = item?.values || []; });
      chart.options.plugins.tooltip.callbacks.label = context => ` ${context.dataset.label}: ${money(context.parsed.y)}${model.pure ? ' / 10g' : ' quoted'}`;
      chart.update();
    }
    const overlay = $('.chart-empty-overlay'); if (overlay) overlay.hidden = true;
  }

  function updateRadarCharts() {
    const pairs = model.radar;
    const radarUnavailable = !model.loaded.radar;
    if (radarUnavailable && !window.Chart) { canvasContext('opportunityDonutChart', 220); canvasContext('spreadBarChart', 250); }
    const byPair = new Map(pairs.map(p => [p.pair, p]));
    const doughnut = window.Chart?.getChart('opportunityDonutChart');
    const analyzedPairs = pairs.filter(hasSpread);
    const radarCounts = [analyzedPairs.filter(p => p.classification === 'Investigate').length, analyzedPairs.filter(p => p.classification === 'Watch').length, analyzedPairs.filter(p => ['Cost-Blocked', 'Expiry-Risk', 'No Signal'].includes(p.classification)).length];
    if (doughnut) { doughnut.data.datasets[0].data = radarCounts; doughnut.update(); }
    else if (!radarUnavailable) drawNativeDonut(radarCounts);
    const center = $('.radar-donut-center');
    if (center) center.innerHTML = radarUnavailable ? '<div class="donut-center-num">—</div><div class="donut-center-lbl">Unavailable</div>' : `<div class="donut-center-num">${radarCounts[0]}</div><div class="donut-center-lbl">Investigate</div>`;
    const breakdown = $('.radar-breakdown-list');
    if (breakdown) breakdown.innerHTML = radarUnavailable ? empty('Opportunity and trap service unavailable.') : [
      ['Investigate', radarCounts[0], '#d6b363'], ['Watch', radarCounts[1], '#c8954d'], ['Cost / expiry / no signal', radarCounts[2], '#746c5c']
    ].map(([label, count, color]) => `<div class="radar-stat-item"><div class="radar-item-left"><span class="radar-dot" style="background:${color}"></span><span>${label}</span></div><span class="radar-val-pill">${count} pair${count === 1 ? '' : 's'}</span></div>`).join('');
    const chart = window.spreadChart;
    if (chart) {
      const labels = pairKeys;
      const selected = labels.map(key => byPair.get(key) || byPair.get(key.split('-').reverse().join('-')) || null);
      chart.data.labels = labels.map(key => key.replace('GOLD', '').replace('-', '–'));
      chart.data.datasets[0].data = selected.map((p, i) => hasSpread(p) ? Number(p.spread) * (p.pair === labels[i] ? 1 : -1) : null);
      chart.data.datasets[0].backgroundColor = selected.map((p, i) => p?.classification === 'Investigate' ? '#d6b363' : p?.classification === 'Watch' ? '#aa8243' : '#5e584b');
      chart.update();
    } else if (!radarUnavailable) drawNativeSpread(pairs);
    const summary = $('.spread-summary-bar');
    const withValues = pairs.filter(hasSpread).sort((a, b) => Math.abs(Number(b.spread)) - Math.abs(Number(a.spread)));
    if (summary) {
      const p = withValues[0];
      summary.innerHTML = p ? `<div><span>Largest absolute spread:</span><strong>${esc(p.pair)}</strong></div><span class="spread-threshold-tag">${money(p.spread)} / 10g · ${esc(p.classification)}</span>` : `<span>${radarUnavailable ? 'Relative-value service unavailable.' : 'No spread observations are available.'}</span>`;
    }
    const validPairCount = pairs.filter(hasSpread).length;
    const countBadge = $('#radarPairCount'); if (countBadge) countBadge.textContent = radarUnavailable ? 'Unavailable' : `${validPairCount} Pair${validPairCount === 1 ? '' : 's'} with data`;
    const riskContext = $('#trapRiskContext');
    if (riskContext) {
      const scored = pairs.filter(p => hasSpread(p) && p.trap_risk_score != null && Number.isFinite(Number(p.trap_risk_score)));
      const avgRisk = scored.length ? scored.reduce((sum, p) => sum + Number(p.trap_risk_score), 0) / scored.length : null;
      const highRisk = [...scored].sort((a, b) => Number(b.trap_risk_score) - Number(a.trap_risk_score))[0];
      riskContext.innerHTML = avgRisk == null ? (radarUnavailable ? 'Opportunity and trap service unavailable.' : 'Execution risk scores are unavailable until the backend has observations.') : `Mean trap risk <strong>${avgRisk.toFixed(1)} / 100</strong>${highRisk ? ` · Highest: <strong>${esc(highRisk.pair)} ${Number(highRisk.trap_risk_score).toFixed(1)}</strong>` : ''}`;
    }
    const stateBadge = $('#spreadStateBadge');
    if (stateBadge) {
      const investigate = analyzedPairs.filter(p => p.classification === 'Investigate').length;
      const blocked = analyzedPairs.filter(p => ['Cost-Blocked', 'Expiry-Risk'].includes(p.classification)).length;
      stateBadge.textContent = radarUnavailable ? 'Unavailable' : validPairCount ? `${investigate} investigate · ${blocked} filtered` : 'No observations';
    }
  }

  function updateCalendar() {
    const grid = $('.calendar-grid-box');
    if (!grid) return;
    const now = new Date();
    const year = now.getFullYear(), month = now.getMonth();
    text($('.calendar-month-name'), now.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' }).toUpperCase());
    const cycle = $('#expiry-calendar-section .panel-actions .nav-badge');
    if (cycle) cycle.textContent = model.prices.length ? 'Observation expiries' : 'Awaiting observations';
    const weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const expiries = new Map();
    latestBySymbol().forEach((item, symbol) => {
      if (!item.expiry_date) return;
      const list = expiries.get(item.expiry_date) || [];
      list.push(symbol); expiries.set(item.expiry_date, list);
    });
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    let html = weekdays.map(day => `<div class="cal-day-name">${day}</div>`).join('');
    for (let i = 0; i < new Date(year, month, 1).getDay(); i++) html += '<div class="cal-day-cell empty" aria-hidden="true"></div>';
    for (let day = 1; day <= daysInMonth; day++) {
      const iso = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
      const symbols = expiries.get(iso) || [];
      const className = symbols.length ? ` expiry-${symbols[0].toLowerCase()}` : '';
      const today = day === now.getDate() ? ' today' : '';
      html += `<button type="button" class="cal-day-cell${className}${today}" data-cal-date="${iso}" aria-label="${iso}${symbols.length ? `, expiry ${symbols.join(', ')}` : ''}">${day}${symbols.length ? '<span class="cal-dot-mark"></span>' : ''}</button>`;
    }
    grid.innerHTML = html;
    const legend = $('.cal-legend-strip');
    if (legend) {
      const entries = [...expiries.entries()].filter(([date]) => date.slice(0, 7) === `${year}-${String(month + 1).padStart(2, '0')}`).sort(([a], [b]) => a.localeCompare(b));
      legend.innerHTML = entries.length ? entries.map(([date, symbols]) => `<div class="cal-legend-item"><span class="legend-dot" style="background:#d6b363"></span><span><strong class="cal-item-sym">${date.slice(8)} ${now.toLocaleDateString('en-IN', { month: 'short' })}:</strong> ${symbols.map(esc).join(', ')}</span></div>`).join('') : empty(model.prices.length ? 'No upcoming expiries in this month are present in the loaded observations.' : 'Expiry dates appear when market observations are available.');
    }
    grid.querySelectorAll('[data-cal-date]').forEach(cell => cell.addEventListener('click', () => window.selectCalDate(cell.dataset.calDate)));
  }

  function eventMarkup(evt, index) {
    const evidence = evt.evidence || {};
    const date = evt.trade_date || '';
    const tone = evt.severity === 'critical' || evt.severity === 'high' ? 'sev-red' : 'sev-amber';
    const detail = `${evt.pair} · ${evt.classification}. Spread ${evidence.spread == null ? 'unavailable' : money(evidence.spread) + ' / 10g'}; z-score ${evidence.z_score == null ? 'unavailable' : Number(evidence.z_score).toFixed(2) + 'σ'}; percentile ${evidence.percentile_rank == null ? 'unavailable' : Number(evidence.percentile_rank).toFixed(1) + '%'}. ${evidence.rule_triggered || evt.summary || ''}`;
    return `<article class="alert-card-item" data-event-index="${index}" tabindex="0" role="button" aria-label="${esc(detail)}"><div class="alert-top-row"><div class="alert-indicator"><span class="alert-dot ${tone}"></span><span>${esc(evt.severity || evt.classification)}</span></div><span class="alert-time">${esc(date)}</span></div><div class="alert-text"><strong>${esc(evt.pair)}</strong> · ${esc(formatSummary(evt.summary || evt.classification))}</div></article>`;
  }

  function updateEvents() {
    const feed = $('#alertsFeed');
    if (feed) {
      feed.innerHTML = model.events.length ? model.events.slice(0, 12).map(eventMarkup).join('') : empty(model.loaded.events ? 'No investigation events were returned for the available observations.' : 'Market event service unavailable.', model.loaded.events ? 'fa-circle-check' : 'fa-circle-exclamation');
      $$('.alert-card-item[data-event-index]', feed).forEach(el => {
        const open = () => showEvent(model.events[Number(el.dataset.eventIndex)]);
        el.addEventListener('click', open); el.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); } });
      });
    }
    const intel = $('.intel-feed-timeline');
    if (intel) intel.innerHTML = model.events.length ? model.events.slice(0, 8).map((evt, index) => `<article class="intel-item" data-event-index="${index}" tabindex="0" role="button"><div class="intel-header-row"><div class="intel-title"><i class="fa-solid fa-chart-line"></i> ${esc(evt.pair)} · ${esc(evt.classification)}</div><span class="intel-time">${esc(evt.trade_date || '')}</span></div><div class="intel-desc">${esc(formatSummary(evt.summary || 'Relative-value event returned by the analytics API.'))}</div><div class="intel-tags"><span class="intel-chip">OPPORTUNITY ${Number(evt.opportunity_score || 0).toFixed(0)}</span><span class="intel-chip">TRAP ${Number(evt.trap_risk_score || 0).toFixed(0)}</span></div></article>`).join('') : empty(model.loaded.events ? 'No market events are available yet.' : 'Market event service unavailable.', model.loaded.events ? 'fa-circle-check' : 'fa-circle-exclamation');
    if (intel) $$('.intel-item[data-event-index]', intel).forEach(el => el.addEventListener('click', () => showEvent(model.events[Number(el.dataset.eventIndex)])));
    const badge = $('.notif-badge-pill'); if (badge) badge.textContent = String(model.events.length);
    const radarBadge = $('.sidebar .nav-item[title="Opportunity Radar"] .nav-badge'); if (radarBadge) radarBadge.textContent = `${model.radar.filter(p => p.classification === 'Investigate').length} Review`;
    const contractBadge = $('.sidebar .nav-item[title="Contract Explorer"] .nav-badge'); if (contractBadge) contractBadge.textContent = `${model.contracts.filter(c => c.is_active !== false).length} Contracts`;
    const dropdown = $('#notifDropdown');
    if (dropdown) {
      const header = $('.notif-header', dropdown); dropdown.innerHTML = ''; if (header) dropdown.appendChild(header);
      dropdown.insertAdjacentHTML('beforeend', model.events.length ? model.events.slice(0, 5).map(evt => `<div class="notif-list-item"><i class="fa-solid fa-chart-line" style="color:#d6b363"></i><div><strong>${esc(evt.pair)} · ${esc(evt.classification)}</strong><p>${esc(evt.summary || '')}</p><span>${esc(evt.trade_date || '')}</span></div></div>`).join('') : empty('No backend events are available.', 'fa-bell-slash'));
    }
  }

  function showEvent(evt) {
    if (!evt) return;
    text($('#alertModalTitle'), 'Relative-Value Event Details');
    text($('#alertModalSubtitle'), `${evt.classification || 'Backend event'} · evidence returned by the analytics service`);
    const body = $('#modalAlertBody');
    if (body) body.innerHTML = `<div class="dashboard-event-detail"><h3>${esc(evt.pair)} · ${esc(evt.classification)}</h3><p>${esc(formatSummary(evt.summary || ''))}</p><dl>${Object.entries({ 'Trade date': evt.trade_date, 'Spread (₹/10g)': evt.evidence?.spread == null ? null : Number(evt.evidence.spread).toFixed(2), 'Rolling z-score': evt.evidence?.z_score == null ? null : `${Number(evt.evidence.z_score).toFixed(2)}σ`, 'Percentile': evt.evidence?.percentile_rank == null ? null : `${Number(evt.evidence.percentile_rank).toFixed(1)}%`, 'Opportunity score': evt.opportunity_score, 'Trap risk score': evt.trap_risk_score, 'Cost hurdle (₹/10g)': evt.evidence?.cost_hurdle, 'Days to expiry': `${evt.evidence?.dte_a ?? '—'} / ${evt.evidence?.dte_b ?? '—'}`, 'Liquidity': `Volume ${evt.evidence?.volume_a ?? '—'} / ${evt.evidence?.volume_b ?? '—'} · OI ${evt.evidence?.open_interest_a ?? '—'} / ${evt.evidence?.open_interest_b ?? '—'}`, 'Decision rule': evt.evidence?.rule_triggered }).filter(([,v]) => v != null).map(([k,v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl>${evt.evidence?.caveats?.length ? `<p class="event-caveats">${evt.evidence.caveats.map(esc).join(' ')}</p>` : ''}</div>`;
    $('#alertModal')?.classList.add('active');
  }

  let hasCompletedInitialLoad = false;
  let dashboardRequestId = 0;
  async function loadDashboard() {
    const requestId = ++dashboardRequestId;
    const isInitialLoad = !hasCompletedInitialLoad;
    document.body.classList.add('dashboard-fetching');
    if (isInitialLoad && window.AuroraLoader) {
      window.AuroraLoader.start('Connecting to AURORA market services');
    }
    let hasAnyData = false;
    try {
    const results = await Promise.allSettled([
      fetchApi('/market/status'), fetchApi('/contracts?active_only=false'), fetchApi('/market/prices?limit=1000'), fetchApi('/analytics/radar?window=30'), fetchApi('/analytics/events?limit=12')
    ]);
    if (requestId !== dashboardRequestId) return;
    const [status, contracts, prices, radar, events] = results;
    model.loaded = Object.fromEntries(['status', 'contracts', 'prices', 'radar', 'events'].map((key, index) => [key, results[index].status === 'fulfilled']));
    model.status = status.status === 'fulfilled' ? status.value : null;
    model.contracts = contracts.status === 'fulfilled' && Array.isArray(contracts.value) ? contracts.value : [];
    model.prices = prices.status === 'fulfilled' ? (prices.value?.items || []) : [];
    model.radar = radar.status === 'fulfilled' ? (radar.value?.pairs || []) : [];
    model.radarDate = radar.status === 'fulfilled' ? radar.value?.evaluation_date || null : null;
    model.events = events.status === 'fulfilled' ? (events.value?.items || []) : [];
    // A test-only status is a provenance boundary: ignore any stale or
    // mismatched market payload returned alongside it.
    if (['test_data', 'demo_synthetic'].includes(model.status?.data_mode)) {
      model.prices = [];
      model.radar = [];
      model.radarDate = null;
      model.events = [];
    }
    updateStatus(); updateKpis(); updateContracts(); updatePriceChart(); updateRadarCharts(); updateEvents(); updateCalendar();
    const failures = results.filter(r => r.status === 'rejected');
    if (failures.length) console.warn('AURORA dashboard: one or more data endpoints could not be loaded.', failures.map(r => r.reason));
    hasAnyData = Boolean(model.status || model.contracts.length || model.prices.length || model.radar.length || model.events.length);
    if (!hasAnyData) setEmptyCardValues('Start the backend or upload an MCX CSV');
    } finally {
    document.body.classList.remove('dashboard-fetching');
    if (isInitialLoad && window.AuroraLoader) {
      window.AuroraLoader.status(hasAnyData ? 'Market workspace initialized' : 'Market services unavailable · retry from the dashboard');
      window.AuroraLoader.complete();
    }
    hasCompletedInitialLoad = true;
    }
  }

  // Replace demo-backed actions with actions that operate on actual loaded records.
  window.updateChartTimeframe = function (timeframe) {
    model.timeframe = timeframe;
    $$('#chartTimePills .time-pill-btn').forEach(btn => btn.classList.toggle('active', btn.textContent.trim() === timeframe));
    updatePriceChart();
  };
  window.toggleBasis = function () {
    model.pure = !model.pure;
    const button = $('#btnNormPure');
    if (button) { button.innerHTML = model.pure ? '<i class="fa-solid fa-coins"></i> 995 Fine Gold (₹/10g)' : '<i class="fa-solid fa-coins"></i> Raw Quoted Price'; button.classList.toggle('active', model.pure); }
    const subtitle = $('.row-2-grid .panel .panel-subtitle');
    if (subtitle) subtitle.textContent = model.pure ? 'MCX Gold Futures normalized to ₹/10g (995 fine-gold basis)' : 'MCX Gold Futures at raw quoted close prices';
    updatePriceChart(); updateContracts();
  };
  window.toggleSlippage = function () {
    model.costFilter = !model.costFilter;
    const button = $('#btnSlippageFilter');
    if (button) { button.innerHTML = `<i class="fa-solid fa-filter"></i> Cost Filter: ${model.costFilter ? 'Active' : 'Disabled'}`; button.classList.toggle('active', model.costFilter); }
    const chart = window.spreadChart;
    if (chart) { const p = model.radar; chart.data.datasets[0].data = pairKeys.map(key => { const row = p.find(item => item.pair === key || item.pair === key.split('-').reverse().join('-')); if (!row || !Number.isFinite(Number(row.spread))) return null; if (model.costFilter && ['Cost-Blocked', 'Expiry-Risk'].includes(row.classification)) return null; return Number(row.spread) * (row.pair === key ? 1 : -1); }); chart.update(); }
  };
  window.showContractDetailModal = function (symbol) {
    const modal = $('#contractModal'), title = $('#modalContractTitle'), body = $('#modalContractBody');
    const list = symbol === 'ALL' ? model.contracts : model.contracts.filter(c => c.symbol === symbol);
    if (title) title.textContent = symbol === 'ALL' ? 'Contract specifications' : `${symbol} specification`;
    if (body) body.innerHTML = list.length ? list.map(c => { const row = latestBySymbol().get(c.symbol); return `<article class="dashboard-contract-detail"><h3>${esc(c.symbol)} · ${esc(c.name)}</h3><p>${esc(c.trading_unit)} · quotation ${esc(c.quote_unit)} · ${esc(c.purity)} fineness</p><p>${row ? `Latest ${esc(row.trade_date)} close ${money(row.close_price)} · normalized ${money(row.normalized_price_10g_basis)} / 10g · volume ${Number(row.volume || 0).toLocaleString('en-IN')} · OI ${Number(row.open_interest || 0).toLocaleString('en-IN')}` : 'No market observation is available for this contract.'}</p></article>`; }).join('') : empty('Contract specifications could not be loaded from the backend.');
    modal?.classList.add('active');
  };
  window.filterByAnomalies = function () { const list = model.radar.filter(p => p.classification === 'Investigate'); if (list.length) showEvent(model.events.find(e => e.pair === list[0].pair) || { pair: list[0].pair, classification: list[0].classification, opportunity_score: list[0].opportunity_score, trap_risk_score: list[0].trap_risk_score, evidence: { spread: list[0].spread, z_score: list[0].z_score, percentile_rank: list[0].percentile_rank, cost_hurdle: list[0].estimated_cost_hurdle, rule_triggered: list[0].reason } }); else window.openAlertModal('No pair is currently classified as Investigate by the analytics API.'); };
  window.openAlertModal = function (message) {
    text($('#alertModalTitle'), 'Dashboard details');
    text($('#alertModalSubtitle'), 'Information from loaded project data');
    const body = $('#modalAlertBody');
    if (body) { const note = document.createElement('div'); note.className = 'dashboard-empty-state'; note.textContent = String(message || 'No additional detail is available.'); body.replaceChildren(note); }
    $('#alertModal')?.classList.add('active');
  };
  window.showSpreadDetailsModal = function () {
    text($('#alertModalTitle'), 'Pairwise normalized spreads');
    text($('#alertModalSubtitle'), 'Backend results · ₹/10g fine-gold basis');
    const body = $('#modalAlertBody');
    if (body) body.innerHTML = `<div class="dashboard-event-detail"><h3>Pairwise normalized spreads</h3>${model.radar.length ? `<dl>${model.radar.map(p => `<div><dt>${esc(p.pair)} · ${esc(p.classification)}</dt><dd>${money(p.spread)} / 10g · z ${p.z_score == null ? '—' : `${Number(p.z_score).toFixed(2)}σ`} · percentile ${p.percentile_rank == null ? '—' : `${Number(p.percentile_rank).toFixed(1)}%`}</dd></div>`).join('')}</dl>` : '<p>No pairwise spread observations are available.</p>'}</div>`;
    $('#alertModal')?.classList.add('active');
  };
  window.showBacktestSummary = function () {
    const best = [...model.radar].filter(hasSpread).sort((a, b) => Number(b.opportunity_score) - Number(a.opportunity_score))[0];
    if (best) showEvent(model.events.find(evt => evt.pair === best.pair) || { pair: best.pair, classification: best.classification, opportunity_score: best.opportunity_score, trap_risk_score: best.trap_risk_score, summary: best.reason, evidence: { spread: best.spread, z_score: best.z_score, percentile_rank: best.percentile_rank, cost_hurdle: best.estimated_cost_hurdle, rule_triggered: best.reason } });
    else window.openAlertModal('No opportunity score is available from the analytics API.');
  };
  window.openProfileModal = function () { window.openAlertModal('Account identity and session controls are managed by the authenticated AURORA account.'); };
  window.selectCalDate = function (date) {
    const expiries = [...latestBySymbol().entries()].filter(([, item]) => item.expiry_date === date);
    const detail = expiries.length ? expiries.map(([symbol, item]) => `${symbol} expiry (observation date ${item.trade_date})`).join('; ') : 'No contract expiry was returned for this date in the available market observations.';
    window.openAlertModal(`${date}: ${detail}`);
  };
  window.refreshAlerts = function () { loadDashboard(); };
  window.exportBhavcopyReport = function () {
    const rows = [['pair','trade_date','spread_inr_per_10g','z_score','percentile','classification','opportunity_score','trap_risk_score'], ...model.radar.map(p => [p.pair, p.trade_date, p.spread, p.z_score, p.percentile_rank, p.classification, p.opportunity_score, p.trap_risk_score])];
    if (rows.length === 1) { window.openAlertModal('No backend analytics are available to export yet.'); return; }
    const csv = rows.map(row => row.map(value => `"${String(value ?? '').replaceAll('"','""')}"`).join(',')).join('\r\n');
    const link = document.createElement('a'); link.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' })); link.download = 'aurora-relative-value-report.csv'; link.click(); URL.revokeObjectURL(link.href);
  };

  clearDemoContent();
  document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
    window.setInterval(loadDashboard, 60000);
  });
})();
