/* Contract Explorer bindings. Values and charts come only from eligible API rows. */
(() => {
  const API = 'http://127.0.0.1:8000/api';
  const SYMBOLS = ['GOLDM', 'GOLDTEN', 'GOLDGUINEA', 'GOLDPETAL'];
  const COLORS = ['#c99a34', '#b68c40', '#d08a45', '#789b7a'];
  const model = { contracts: new Map(), rows: new Map(), status: null, range: 90 };
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const money = value => Number.isFinite(Number(value)) ? `₹${Number(value).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—';
  const dateLabel = value => value ? new Date(`${value}T12:00:00`).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '—';
  const dayDiff = (from, to) => Math.round((Date.parse(`${to}T12:00:00Z`) - Date.parse(`${from}T12:00:00Z`)) / 86400000);
  const setText = (node, value) => { if (node) node.textContent = value; };
  const toast = message => { if (typeof window.showToast === 'function') window.showToast(message); };
  const unwrap = payload => payload?.data ?? null;

  function setDataNotice(message, state = 'info', retry = false) {
    let notice = document.getElementById('contractDataNotice');
    if (!notice) {
      notice = document.createElement('div');
      notice.id = 'contractDataNotice';
      notice.className = 'contract-data-notice';
      notice.setAttribute('role', 'status');
      notice.setAttribute('aria-live', 'polite');
      $('.quick-stats-ribbon')?.before(notice);
    }
    notice.dataset.state = state;
    notice.replaceChildren(document.createTextNode(message));
    if (retry) {
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'contract-data-retry'; button.textContent = 'Retry';
      button.addEventListener('click', () => refresh()); notice.append(' ', button);
    }
  }

  function resetVisibleMarketData() {
    $$('.header-ticker .ticker-chip').forEach(chip => {
      setText($('.val', chip), '—'); setText($('.chg', chip), '—');
      chip.title = 'Waiting for eligible historical observations';
    });
    $$('.stat-chip-value').forEach((node, i) => setText(node, i === 0 ? 'Loading…' : '—'));
    const badge = $('.market-badge');
    if (badge) { badge.replaceChildren(document.createElement('span')); badge.firstChild.className = 'pulse-dot'; badge.append(' Checking market status…'); }
    $$('.contract-card').forEach(card => {
      setText($('.price-value-raw', card), '—'); setText($('.price-value-norm', card), '—');
      setText($('.price-label', card), 'Latest Observed Close');
      const change = $('.price-chg-pill', card); if (change) { change.className = 'price-chg-pill'; setText(change, 'Historical change unavailable'); }
      const normalizedNote = $('.normalized-col > span:last-child', card); setText(normalizedNote, 'Awaiting eligible observation');
      $$('.spec-v', card).forEach(node => setText(node, '—'));
      setText($('.health-pill', card), 'Not assessed by price API');
      setText($('.health-label', card), 'Liquidity assessment');
      const dte = $('.liquidity-health-block > span:last-child', card); setText(dte, 'Days to expiry at observation: —');
      setText($('.card-note-pill span', card), 'Historical observation status unavailable. No live quote is shown.');
      card.dataset.status = 'unavailable'; card.dataset.days = '';
    });
    const table = $('.aurora-table tbody');
    if (table) $$('.data-col', table).forEach(cell => setText(cell, '—'));
    $$('.quick-stats-ribbon .stat-chip-value').forEach((node, i) => {
      if (i === 0) setText(node, 'Loading…');
      else if (i > 1) setText(node, '—');
    });
    ['sparkline-goldm','sparkline-goldten','sparkline-goldguinea','sparkline-goldpetal','historicalPriceChart'].forEach(id => {
      const canvas = document.getElementById(id);
      if (canvas) { window.Chart?.getChart(canvas)?.destroy(); const ctx = canvas.getContext('2d'); if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height); }
    });
    const subtitle = $('.chart-subtitle');
    setText(subtitle, 'Eligible user-imported historical observations · no live feed is configured');
  }

  async function request(path) {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 30000);
    let response;
    try {
      response = await fetch(`${API}${path}`, { mode: 'cors', headers: { Accept: 'application/json' }, signal: controller.signal });
    } catch (error) {
      if (error.name === 'AbortError') throw new Error(`timed out after 30 seconds (${path})`);
      throw new Error(`could not reach API (${path}): ${error.message}`);
    } finally {
      window.clearTimeout(timeout);
    }
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    const json = await response.json();
    if (json?.success === false) throw new Error(json.message || 'API request failed');
    return unwrap(json);
  }

  function rowOrder(a, b) {
    return String(b.trade_date).localeCompare(String(a.trade_date)) || String(a.expiry_date).localeCompare(String(b.expiry_date));
  }
  function latestRows(rows) {
    const sorted = [...rows].sort(rowOrder);
    if (!sorted.length) return null;
    const date = sorted[0].trade_date;
    return sorted.filter(row => row.trade_date === date).sort((a, b) => String(a.expiry_date).localeCompare(String(b.expiry_date)))[0];
  }
  function nearestExpiryPerDate(rows) {
    const sessions = new Map();
    rows.forEach(row => {
      if (!Number.isFinite(Number(row.normalized_price_10g_basis))) return;
      const current = sessions.get(row.trade_date);
      if (!current || String(row.expiry_date).localeCompare(String(current.expiry_date)) < 0) sessions.set(row.trade_date, row);
    });
    return [...sessions.values()].sort((a, b) => String(a.trade_date).localeCompare(String(b.trade_date)));
  }
  function previousSameExpiry(rows, latest) {
    return rows.filter(row => row.expiry_date === latest.expiry_date && row.trade_date < latest.trade_date)
      .sort((a, b) => String(b.trade_date).localeCompare(String(a.trade_date)))[0] || null;
  }
  function statusText(status) {
    const feed = String(status?.feed_status || '').toUpperCase();
    if (feed === 'LIVE' && status?.is_live_connected === true) return { text: 'VERIFIED LIVE PROVIDER FEED', live: true };
    if (feed === 'DELAYED') return { text: 'AUTHORIZED DELAYED PROVIDER FEED', live: false };
    if (feed === 'STALE') return { text: 'PROVIDER FEED STALE', live: false };
    if (status?.data_mode === 'staged_csv' || /user-imported historical csv/i.test(status?.data_provenance || '')) return { text: 'HISTORICAL CSV · UNVERIFIED', live: false };
    return { text: `MARKET FEED ${feed === 'UNAVAILABLE' || !feed ? 'UNAVAILABLE' : feed}`, live: false };
  }
  function renderStatus() {
    const badge = $('.market-badge'); if (!badge) return;
    const status = statusText(model.status);
    badge.replaceChildren(document.createElement('span'));
    badge.firstChild.className = 'pulse-dot';
    badge.firstChild.style.background = status.live ? '#4ea77a' : '#c69d46';
    badge.append(` ${status.text}`);
    badge.title = model.status?.data_provenance || 'Provider observations unavailable';
  }
  function renderTicker(latest) {
    $$('.header-ticker .ticker-chip').forEach(chip => {
      const symbol = $('.sym', chip)?.textContent.trim();
      const row = latest.get(symbol);
      const values = model.rows.get(symbol) || [];
      const prior = row ? previousSameExpiry(values, row) : null;
      setText($('.val', chip), row ? money(row.close_price) : '—');
      const change = $('.chg', chip);
      if (change) {
        change.className = 'chg';
        if (row && prior && Number(prior.close_price) !== 0) {
          const pct = ((Number(row.close_price) - Number(prior.close_price)) / Number(prior.close_price)) * 100;
          change.classList.add(pct >= 0 ? 'up' : 'down');
          change.textContent = `${pct >= 0 ? '+' : ''}${pct.toFixed(2)}% hist.`;
        } else setText(change, '—');
      }
      chip.title = row ? `Historical close · ${row.trade_date} · expiry ${row.expiry_date} · not a live quote` : 'No eligible historical observation available';
    });
  }
  function renderSummary(latest) {
    const stats = $$('.quick-stats-ribbon .stat-chip-value');
    if (stats[0]) setText(stats[0], `${model.contracts.size} Symbols`);
    if (stats[1]) setText(stats[1], '10g @ 995 configured basis');
    const rows = [...latest.values()];
    const shared = rows.length === SYMBOLS.length && rows.every(row => row.trade_date === rows[0].trade_date && row.expiry_date === rows[0].expiry_date);
    if (stats[2]) setText(stats[2], shared ? `${rows.reduce((sum, row) => sum + Number(row.open_interest || 0), 0).toLocaleString('en-IN')} contracts · ${rows[0].trade_date}` : '— · no synchronized all-contract snapshot');
    if (stats[3]) {
      const prices = shared ? rows.map(row => Number(row.normalized_price_10g_basis)) : [];
      setText(stats[3], shared ? `${money(Math.max(...prices) - Math.min(...prices))} range · same date/expiry` : '— · awaiting matched snapshot');
    }
    stats[2]?.setAttribute('title', 'Only summed when all four latest observations share the same trade date and explicit expiry.');
    stats[3]?.setAttribute('title', 'Range of backend-normalized 10g values, only for a common trade date and exact expiry.');
    const goldmHistory = nearestExpiryPerDate(model.rows.get('GOLDM') || []).slice(-90);
    const highLow = $$('.chart-stats-row .chart-mini-v');
    if (highLow[0]) setText(highLow[0], goldmHistory.length ? money(Math.max(...goldmHistory.map(row => Number(row.close_price)))) : '—');
    if (highLow[1]) setText(highLow[1], goldmHistory.length ? money(Math.min(...goldmHistory.map(row => Number(row.close_price)))) : '—');
    highLow[0]?.setAttribute('title', 'Highest observed GOLDM close in the latest 90 available sessions, using rolling nearest-expiry observations.');
    highLow[1]?.setAttribute('title', 'Lowest observed GOLDM close in the latest 90 available sessions, using rolling nearest-expiry observations.');
  }
  function renderContractCard(symbol, latest) {
    const card = $(`.contract-card[data-contract="${symbol}"]`);
    const contract = model.contracts.get(symbol);
    const row = latest.get(symbol);
    if (!card) return;
    const name = contract?.name || symbol;
    const title = $('.contract-fullname', card);
    if (title) setText(title, name);
    const badge = $('.status-badge', card);
    if (badge) {
      badge.className = `status-badge ${contract?.is_active ? 'active-badge' : 'watch-badge'}`;
      setText(badge, contract ? (contract.is_active ? 'Configured active' : 'Configured inactive') : 'Specification unavailable');
      badge.title = 'Status reflects the configured contract record, not exchange session status.';
    }
    setText($('.price-value-raw', card), row ? money(row.close_price) : '—');
    setText($('.price-value-norm', card), row ? money(row.normalized_price_10g_basis) : '—');
    const dateNote = $('.normalized-col > span:last-child', card);
    setText(dateNote, row ? `Historical · ${row.trade_date} · expiry ${row.expiry_date}` : 'No eligible observation');
    if (dateNote) dateNote.title = 'User-imported historical data is not provider-verified and is not a live quote.';
    const change = $('.price-chg-pill', card);
    const prior = row ? previousSameExpiry(model.rows.get(symbol) || [], row) : null;
    if (change) {
      change.className = 'price-chg-pill';
      setText(change, row && prior && Number(prior.close_price) !== 0
        ? `${((Number(row.close_price) - Number(prior.close_price)) / Number(prior.close_price) * 100).toFixed(2)}% historical change · same expiry`
        : 'Historical change unavailable');
    }
    const specs = $$('.specs-grid .spec-item .spec-v', card);
    if (contract) {
      setText(specs[0], contract.trading_unit || '—');
      setText(specs[1], `₹ / ${contract.quote_unit || '—'}`);
      setText(specs[2], `${contract.purity ?? '—'} Fine`);
    }
    setText(specs[3], row && row.volume != null ? `${Number(row.volume).toLocaleString('en-IN')} lots` : '—');
    setText(specs[4], row && row.open_interest != null ? Number(row.open_interest).toLocaleString('en-IN') : '—');
    setText(specs[5], row ? dateLabel(row.expiry_date) : '—');
    const health = $('.health-pill', card); setText(health, 'Not assessed by API');
    const dteLabel = $('.liquidity-health-block > span:last-child', card);
    if (dteLabel) setText(dteLabel, row ? `Calendar days to expiry at observation: ${dayDiff(row.trade_date, row.expiry_date)}` : 'Expiry date unavailable');
    const note = $('.card-note-pill span', card);
    if (note) setText(note, row ? `Historical user-imported observation · ${row.trade_date} · not provider-verified.` : 'No eligible historical market observations are available for this contract.');
    card.dataset.status = contract?.is_active ? 'active' : 'inactive';
    const now = new Date();
    const localDate = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    card.dataset.days = row ? String(dayDiff(localDate, row.expiry_date)) : '';
  }
  function renderSpecsTable(latest) {
    const rows = $$('.aurora-table tbody tr');
    const columns = SYMBOLS.map(symbol => ({ symbol, contract: model.contracts.get(symbol), current: latest.get(symbol), all: model.rows.get(symbol) || [] }));
    rows.forEach((tr, rowIndex) => {
      const cells = $$('.data-col', tr);
      cells.forEach((cell, i) => {
        const item = columns[i]; if (!item) return;
        const { contract, current, all } = item;
        const prior = current ? previousSameExpiry(all, current) : null;
        const value = rowIndex === 0 ? contract?.trading_unit
          : rowIndex === 1 ? (contract?.quote_unit ? `₹ per ${contract.quote_unit}` : null)
          : rowIndex === 2 ? (contract?.purity != null ? `${contract.purity} Fineness` : null)
          : rowIndex === 3 ? (current ? money(current.close_price) : null)
          : rowIndex === 4 ? (current ? money(current.normalized_price_10g_basis) : null)
          : rowIndex === 5 ? (current && prior && Number(prior.close_price) !== 0 ? `${(((Number(current.close_price) - Number(prior.close_price)) / Number(prior.close_price)) * 100).toFixed(2)}% · same expiry` : 'Unavailable')
          : rowIndex === 6 ? (current?.volume != null ? `${Number(current.volume).toLocaleString('en-IN')} lots` : null)
          : rowIndex === 7 ? (current?.open_interest != null ? `${Number(current.open_interest).toLocaleString('en-IN')} contracts` : null)
          : rowIndex === 8 ? 'Not assessed by market-price API'
          : rowIndex === 9 ? (current ? dateLabel(current.expiry_date) : null)
          : rowIndex === 10 ? (current ? `${dayDiff(current.trade_date, current.expiry_date)} days at observation` : null)
          : rowIndex === 11 ? (contract ? (contract.is_active ? 'Configured active' : 'Configured inactive') : null)
          : rowIndex === 12 ? 'Not returned by contract API'
          : rowIndex === 13 ? (() => {
            if (item.symbol === 'GOLDM') return 'Benchmark';
            if (!current) return 'Unavailable';
            const benchmark = (model.rows.get('GOLDM') || []).find(row => row.trade_date === current.trade_date && row.expiry_date === current.expiry_date);
            return benchmark ? `${money(Number(current.normalized_price_10g_basis) - Number(benchmark.normalized_price_10g_basis))} / 10g · exact expiry` : 'Unavailable · no same-date, same-expiry GOLDM observation';
          })() : null;
        cell.replaceChildren(document.createTextNode(value ?? '—'));
      });
    });
  }
  function chartTheme() {
    return document.body.dataset.auroraTheme === 'light'
      ? { tick: '#586052', grid: 'rgba(77,83,68,.12)', tooltip: 'rgba(255,254,249,.97)' }
      : { tick: '#89909b', grid: 'rgba(255,255,255,.07)', tooltip: 'rgba(10,12,15,.95)' };
  }
  function makeChart(canvas, labels, datasets, compact = false) {
    if (!canvas || !window.Chart) return;
    window.Chart.getChart(canvas)?.destroy();
    const ctx = canvas.getContext('2d');
    const theme = chartTheme();
    new Chart(ctx, {
      type: 'line', data: { labels, datasets },
      options: {
        responsive: true, maintainAspectRatio: false, animation: { duration: 420 },
        interaction: { mode: 'index', intersect: false },
        plugins: { legend: { display: !compact, labels: { color: theme.tick, usePointStyle: true } },
          tooltip: { backgroundColor: theme.tooltip, titleColor: '#9a772c', bodyColor: theme.tick, borderColor: 'rgba(190,151,58,.35)', borderWidth: 1 } },
        scales: compact ? { x: { display: false }, y: { display: false } } : {
          x: { grid: { color: theme.grid }, ticks: { color: theme.tick, maxTicksLimit: 12 } },
          y: { type: 'linear', position: 'left', grid: { color: theme.grid }, ticks: { color: theme.tick, callback: value => `₹${Number(value).toLocaleString('en-IN')}` } },
          volume: { type: 'linear', position: 'right', grid: { display: false }, ticks: { color: theme.tick, callback: value => `${Number(value).toLocaleString('en-IN')} lots` } }
        }
      }
    });
  }
  function renderCharts() {
    const series = new Map(SYMBOLS.map(symbol => [symbol, nearestExpiryPerDate(model.rows.get(symbol) || [])]));
    const allDates = [...new Set([...series.values()].flatMap(rows => rows.map(row => row.trade_date)))].sort();
    const dates = allDates.slice(-model.range);
    const colors = new Map(SYMBOLS.map((symbol, index) => [symbol, COLORS[index]]));
    SYMBOLS.forEach(symbol => {
      const byDate = new Map(series.get(symbol).map(row => [row.trade_date, row]));
      const aligned = dates.map(date => byDate.get(date));
      const canvas = document.getElementById(`sparkline-${symbol.toLowerCase()}`);
      const values = aligned.filter(Boolean);
      if (canvas && values.length >= 2) makeChart(canvas, values.map(row => row.trade_date), [{ data: values.map(row => row.normalized_price_10g_basis), borderColor: colors.get(symbol), borderWidth: 2, pointRadius: 0, tension: .24, fill: false }], true);
      else if (canvas) { const wrapper = canvas.closest('.sparkline-wrapper'); if (wrapper) { let empty = $('.history-empty', wrapper); if (!empty) { empty = document.createElement('div'); empty.className = 'history-empty'; wrapper.appendChild(empty); } setText(empty, 'No historical series available'); } }
    });
    const range = document.querySelector('.range-btn.active')?.textContent.trim() || '90D';
    const requested = range === '7D' ? 7 : range === '30D' ? 30 : range === '90D' ? 90 : range === '6M' ? 126 : 252;
    model.range = requested;
    const visibleDates = allDates.slice(-requested);
    const mapData = symbol => new Map(series.get(symbol).map(row => [row.trade_date, row]));
    const datasets = SYMBOLS.map((symbol, index) => {
      const map = mapData(symbol);
      return { label: `${symbol} · nearest-expiry history`, data: visibleDates.map(date => map.get(date)?.normalized_price_10g_basis ?? null), borderColor: COLORS[index], backgroundColor: `${COLORS[index]}22`, borderWidth: 2, tension: .24, pointRadius: 0, spanGaps: false };
    });
    const volumeByDate = new Map();
    SYMBOLS.forEach(symbol => series.get(symbol).forEach(row => volumeByDate.set(row.trade_date, (volumeByDate.get(row.trade_date) || 0) + Number(row.volume || 0))));
    datasets.push({ label: 'Observed volume (lots; sum across available symbols)', data: visibleDates.map(date => volumeByDate.get(date) ?? null), type: 'bar', yAxisID: 'volume', backgroundColor: 'rgba(130,135,137,.22)', borderWidth: 0 });
    const title = $('.chart-subtitle');
    if (title) setText(title, `Rolling nearest-expiry historical observations · last ${visibleDates.length} sessions · imported CSV is not provider-verified`);
    const canvas = document.getElementById('historicalPriceChart');
    if (visibleDates.length) makeChart(canvas, visibleDates, datasets);
    else {
      if (canvas) window.Chart?.getChart(canvas)?.destroy();
      const wrap = canvas?.parentElement;
      if (wrap) { let empty = $('.history-empty', wrap); if (!empty) { empty = document.createElement('div'); empty.className = 'history-empty'; wrap.appendChild(empty); } setText(empty, 'No eligible historical price series. Import eligible historical CSV observations; live data is unavailable.'); }
    }
  }
  function render(latest) {
    renderStatus(); renderTicker(latest); renderSummary(latest);
    SYMBOLS.forEach(symbol => renderContractCard(symbol, latest));
    renderSpecsTable(latest);
    const activeCount = [...model.contracts.values()].filter(item => item.is_active).length;
    const cards = $$('.contract-card');
    const filters = $$('.filter-pill');
    filters.forEach(button => {
      const type = button.dataset.filter;
      const count = type === 'all' ? cards.length : type === 'active' ? activeCount : cards.filter(card => Number(card.dataset.days) >= 0 && Number(card.dataset.days) <= 20).length;
      setText($('.count', button), String(count));
    });
    if (typeof window.filterContracts === 'function') {
      const active = $('.filter-pill.active')?.dataset.filter || 'all';
      window.filterContracts(active);
    }
    renderCharts();
  }
  function setSandboxSelection(symbol) {
    $$('.calc-tab-btn').forEach(button => {
      const active = button.dataset.symbol === symbol;
      button.classList.toggle('active', active);
      button.setAttribute('aria-pressed', String(active));
    });
  }
  function refresh() {
    setDataNotice('Connecting to the AURORA API… Values appear only after eligible historical observations load; no live feed is configured.', 'loading');
    const button = $('.contract-top-header .header-btn[onclick*="refreshContractData"]');
    if (button) { button.disabled = true; button.title = 'Refresh historical market observations from the backend'; }
    const requestLabels = ['market status', 'contract specifications', ...SYMBOLS.map(symbol => `${symbol} historical prices`)];
    return Promise.allSettled([
      request('/market/status'), request('/contracts?active_only=false'),
      ...SYMBOLS.map(symbol => request(`/market/prices?symbol=${symbol}&limit=500`))
    ]).then(results => {
      const value = (index, fallback = null) => results[index]?.status === 'fulfilled' ? results[index].value : fallback;
      model.status = value(0);
      const contracts = value(1, []);
      (Array.isArray(contracts) ? contracts : []).forEach(contract => model.contracts.set(contract.symbol, contract));
      SYMBOLS.forEach((symbol, index) => {
        const payload = value(index + 2, { items: [] });
        model.rows.set(symbol, Array.isArray(payload?.items) ? payload.items.filter(row => row.is_synthetic !== true && row.data_source && !/^(test|synthetic|demo|sample)/i.test(row.data_source)) : []);
      });
      const latest = new Map(SYMBOLS.map(symbol => [symbol, latestRows(model.rows.get(symbol) || [])]).filter(([, row]) => row));
      render(latest);
      const selectedSandboxButton = $('.calc-tab-btn.active');
      const selectedSandboxSymbol = selectedSandboxButton?.dataset.symbol || 'GOLDGUINEA';
      window.loadSandboxContract(selectedSandboxSymbol);
      const failures = results.flatMap((result, index) => result.status === 'rejected'
        ? [`${requestLabels[index]}: ${result.reason?.message || 'request failed'}`]
        : []);
      const eligibleCount = SYMBOLS.reduce((total, symbol) => total + (model.rows.get(symbol)?.length || 0), 0);
      const subtitle = $('.chart-subtitle');
      if (failures.length) {
        const timeoutOnly = results.some(result => result.status === 'rejected' && /timed out after/i.test(result.reason?.message || ''));
        const lead = timeoutOnly
          ? 'Some API requests did not respond before the 12-second timeout.'
          : 'Some API requests could not be completed.';
        const detail = failures.join(' · ');
        setDataNotice(`${lead} Successful historical results remain visible; failed requests are identified below. ${detail}`, 'error', true);
        setText(subtitle, `Partial historical data only. Failed requests: ${detail}. Visible prices are imported observations, not live quotes.`);
      } else if (!eligibleCount) {
        setDataNotice('The API responded, but there are no eligible historical observations to display. Test and synthetic rows are excluded; imported historical CSV is not live market data.', 'empty');
        setText(subtitle, 'Backend responded, but returned no eligible historical price observations. Test and synthetic rows are excluded; import eligible historical CSV data to populate these charts.');
      } else {
        setDataNotice(`${eligibleCount.toLocaleString('en-IN')} eligible historical observations loaded. Imported CSV is unverified and is not a live quote.`, 'success');
        setText(subtitle, `Rolling nearest-expiry historical observations · last ${model.range} sessions · imported CSV is not provider-verified`);
      }
      if (failures.length) toast(`Some Contract Explorer data is unavailable: ${failures.join('; ')}`);
      else toast(model.status?.data_mode === 'staged_csv' ? 'Historical CSV observations refreshed; no verified live feed.' : model.status?.is_live_connected ? 'Provider status refreshed.' : 'Market data status refreshed; live provider unavailable.');
    }).finally(() => { if (button) button.disabled = false; });
  }

  window.refreshContractData = () => refresh();
  window.updateChartRange = range => {
    $$('.range-btn').forEach(button => button.classList.toggle('active', button.textContent.trim() === range));
    renderCharts();
  };
  window.exportTableData = () => {
    const header = ['symbol','trade_date','expiry_date','close_price','normalized_price_10g_basis','volume_lots','open_interest','data_source','is_provider_verified'];
    const lines = [header.join(',')];
    SYMBOLS.forEach(symbol => (model.rows.get(symbol) || []).forEach(row => lines.push([
      symbol, row.trade_date, row.expiry_date, row.close_price, row.normalized_price_10g_basis,
      row.volume ?? '', row.open_interest ?? '', row.data_source, row.is_provider_verified === true
    ].map(value => `"${String(value ?? '').replaceAll('"', '""')}"`).join(','))));
    if (lines.length === 1) { toast('No eligible market observations are available to export.'); return; }
    const url = URL.createObjectURL(new Blob([lines.join('\r\n')], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a'); link.href = url; link.download = 'AURORA_Contract_Observations.csv'; link.click(); URL.revokeObjectURL(url);
  };
  window.loadSandboxContract = symbol => {
    setSandboxSelection(symbol);
    const contract = model.contracts.get(symbol);
    const row = latestRows(model.rows.get(symbol) || []);
    if (!contract || !row) {
      ['sb-raw','sb-size','sb-purity','sb-result'].forEach(id => setText(document.getElementById(id), '—'));
      ['sb-raw-sub','sb-size-sub','sb-purity-sub','sb-result-sub'].forEach(id => setText(document.getElementById(id), 'No eligible observation returned by the API.'));
      toast('No eligible historical observation is available for this contract.'); return;
    }
    setText(document.getElementById('sb-raw'), money(row.close_price));
    setText(document.getElementById('sb-raw-sub'), `Historical close · ${row.trade_date} · expiry ${row.expiry_date}`);
    setText(document.getElementById('sb-size'), contract.trading_unit || '—');
    setText(document.getElementById('sb-size-sub'), `Configured quote unit: ${contract.quote_unit || '—'}`);
    setText(document.getElementById('sb-purity'), `${contract.purity ?? '—'} fineness`);
    setText(document.getElementById('sb-purity-sub'), 'Configured contract specification; historical standard changes are not effective-dated here.');
    setText(document.getElementById('sb-result'), money(row.normalized_price_10g_basis));
    setText(document.getElementById('sb-result-sub'), 'Backend normalized value · 10g fine-gold basis');
  };

  resetVisibleMarketData();
  setDataNotice('Connecting to the AURORA API… Values appear only after eligible historical observations load; no live feed is configured.', 'loading');
  ['sb-raw','sb-size','sb-purity','sb-result'].forEach(id => setText(document.getElementById(id), '—'));
  ['sb-raw-sub','sb-size-sub','sb-purity-sub','sb-result-sub'].forEach(id => setText(document.getElementById(id), 'Waiting for eligible historical observations…'));
  document.addEventListener('DOMContentLoaded', refresh, { once: true });
})();
