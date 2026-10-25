(() => {
  'use strict';

  const API_BASE = (window.AURORA_API_BASE || ((location.protocol === 'http:' || location.protocol === 'https:') && !['localhost', '127.0.0.1'].includes(location.hostname) ? location.origin : 'http://127.0.0.1:8000')).replace(/\/$/, '');
  const form = document.getElementById('backtestForm');
  const runButton = document.getElementById('runButton');
  const formError = document.getElementById('formError');
  const alertBox = document.getElementById('resultAlert');
  let equityChart = null;
  let drawdownChart = null;
  let spreadChart = null;
  let allTrades = [];

  const defaults = {
    pair: 'GOLDM-GOLDPETAL', lookback: '30', units: '1', entry: '2.0', exit: '0.5',
    capital: '100000', cost: '10.31', slippage: '15', volume: '0', expiry: '3', start: '', end: '',
  };
  const presets = {
    baseline: { lookback: '30', entry: '2.0', exit: '0.5', volume: '0', expiry: '3' },
    selective: { lookback: '45', entry: '2.5', exit: '0.5', volume: '500', expiry: '5' },
    frequent: { lookback: '15', entry: '1.5', exit: '0.3', volume: '0', expiry: '2' },
  };

  const $ = (id) => document.getElementById(id);
  const value = (id) => $(id).value;
  const apiDate = (id) => value(id) || null;
  const inr = (number, digits = 2) => Number.isFinite(Number(number))
    ? `₹${Number(number).toLocaleString('en-IN', { minimumFractionDigits: digits, maximumFractionDigits: digits })}` : '—';
  const signed = (number, suffix = '') => Number.isFinite(Number(number))
    ? `${Number(number) > 0 ? '+' : ''}${Number(number).toLocaleString('en-IN', { maximumFractionDigits: 2 })}${suffix}` : '—';

  function setStatus(message, icon = 'fa-regular fa-circle-check') {
    $('submitStatus').innerHTML = `<i class="${icon}" aria-hidden="true"></i><span></span>`;
    $('submitStatus').querySelector('span').textContent = message;
  }

  async function loadMarketStatus() {
    const label = $('historyStatus');
    const coverage = $('historyCoverage');
    try {
      const response = await fetch(`${API_BASE}/api/market/status`);
      if (!response.ok) throw new Error('Market status endpoint unavailable');
      const { data } = await response.json();
      const verifiedLive = data.is_live_connected === true && String(data.feed_status).toUpperCase() === 'LIVE';
      label.textContent = verifiedLive ? 'Verified MCX feed' : data.data_mode === 'staged_csv'
        ? 'Imported history · unverified'
        : data.data_mode === 'test_data' ? 'Test data · excluded from analysis'
          : data.data_mode === 'demo_synthetic' ? 'Synthetic demo · excluded from analysis'
            : 'Provider unavailable';
      const observationCount = Number(data.total_observations);
      const countLabel = Number.isFinite(observationCount) ? observationCount.toLocaleString('en-IN') : '—';
      coverage.textContent = `${countLabel} stored observations across all sources · latest ${data.latest_trade_date || 'no date'}`;
      const chip = document.querySelector('.market-status-chip');
      if (chip) {
        const statusText = chip.querySelector('span:last-child');
        if (statusText) statusText.textContent = verifiedLive ? 'API ONLINE · VERIFIED LIVE FEED' : `API ONLINE · ${String(data.feed_status || data.data_mode || 'FEED UNAVAILABLE').replaceAll('_', ' ').toUpperCase()}`;
        chip.title = `${data.provider_name}; live connection: ${data.is_live_connected ? 'connected' : 'not connected'}`;
      }
      const freshness = document.querySelector('.data-freshness-chip span');
      if (freshness) freshness.textContent = data.data_freshness_label || 'No imported history';
    } catch (error) {
      label.textContent = 'API unavailable';
      coverage.textContent = 'Start the AURORA API to inspect history';
      setStatus(`Cannot reach the AURORA API at ${API_BASE}. Check that the backend is running and the configured URL is correct.`, 'fa-solid fa-triangle-exclamation');
    }
  }

  function requestPayload() {
    return {
      pair: value('pairInput'), start_date: apiDate('startInput'), end_date: apiDate('endInput'),
      capital: Number(value('capitalInput')), units: Number(value('unitsInput')),
      lookback: Number(value('lookbackInput')), entry_z: Number(value('entryInput')),
      exit_z: Number(value('exitInput')), transaction_cost_per_10g: Number(value('costInput')),
      slippage_per_10g: Number(value('slippageInput')), min_volume: Number(value('volumeInput')),
      expiry_buffer_days: Number(value('expiryInput')),
    };
  }

  function validatePayload(payload) {
    if (payload.exit_z >= payload.entry_z) return 'Exit threshold must be lower than entry threshold.';
    if (payload.start_date && payload.end_date && payload.start_date > payload.end_date) return 'Start date must be on or before end date.';
    for (const [key, number] of Object.entries(payload)) {
      if (typeof number === 'number' && !Number.isFinite(number)) return `Enter a valid value for ${key.replaceAll('_', ' ')}.`;
    }
    return '';
  }

  function clearCharts() {
    if (equityChart) equityChart.destroy();
    if (drawdownChart) drawdownChart.destroy();
    if (spreadChart) spreadChart.destroy();
    equityChart = drawdownChart = spreadChart = null;
    document.querySelectorAll('.bt-chart-wrap').forEach((wrap) => wrap.classList.remove('has-chart'));
    $('equityEmpty').hidden = false;
    $('drawdownEmpty').hidden = false;
    $('spreadEmpty').hidden = false;
    document.querySelectorAll('.bt-chart-fallback').forEach((svg) => svg.remove());
  }

  function resetDisplay() {
    clearCharts();
    allTrades = [];
    $('exportTradesButton').disabled = true;
    renderTrades([]);
    ['metricReturn', 'metricPnl', 'metricDrawdown', 'metricSharpe', 'metricWinRate', 'metricWinSub', 'metricTrades', 'metricProfitFactor'].forEach((id) => {
      $(id).textContent = id === 'metricPnl' ? 'Waiting for results' : id === 'metricWinSub' ? 'Closed trades' : '—';
      $(id).classList.remove('positive', 'negative');
    });
    $('resultHeading').textContent = 'Waiting for a historical run';
    $('resultDescription').textContent = 'Choose a pair and configuration, then run the strategy against eligible uploaded history.';
    $('runState').innerHTML = '<i class="fa-regular fa-circle"></i> NO RUN';
    $('sourceLabel').textContent = 'Source: awaiting API';
    $('tradeCountTag').textContent = '0';
    alertBox.hidden = true;
  }

  function alert(message, kind = 'info') {
    alertBox.className = `bt-alert ${kind}`;
    alertBox.textContent = message;
    alertBox.hidden = false;
    alertBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  async function runBacktest(event) {
    event.preventDefault();
    formError.hidden = true;
    alertBox.hidden = true;
    const payload = requestPayload();
    const validationMessage = validatePayload(payload);
    if (validationMessage) {
      formError.textContent = validationMessage;
      formError.hidden = false;
      return;
    }
    resetDisplay();
    runButton.disabled = true;
    runButton.setAttribute('aria-busy', 'true');
    runButton.innerHTML = '<i class="fa-solid fa-spinner fa-spin" aria-hidden="true"></i><span>Running on historical data…</span>';
    $('resultHeading').textContent = 'Submitting historical simulation';
    $('resultDescription').textContent = 'Waiting for the backend to validate coverage and calculate the selected strategy.';
    $('runState').innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> RUNNING';
    setStatus('The backend is processing the selected market history.', 'fa-solid fa-spinner fa-spin');
    try {
      const response = await fetch(`${API_BASE}/api/backtests/run`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
      });
      const body = await response.json();
      if (!response.ok) {
        const details = body.details?.map((item) => item.message).filter(Boolean).join(' ');
        throw new Error(body.error || details || 'The backtest request failed.');
      }
      renderResult(body.data);
    } catch (error) {
      $('resultHeading').textContent = 'Backtest could not be completed';
      $('resultDescription').textContent = error.message;
      $('runState').innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> ERROR';
      setStatus('The request failed. Check the API status and configuration.', 'fa-solid fa-triangle-exclamation');
      alert(error.message, 'error');
    } finally {
      runButton.disabled = false;
      runButton.removeAttribute('aria-busy');
      runButton.innerHTML = '<i class="fa-solid fa-play" aria-hidden="true"></i><span>Run backtest</span>';
    }
  }

  function renderResult(result) {
    $('resultHeading').textContent = result.status === 'completed' ? `${result.pair.replace('-', ' / ')} · historical result` : 'History is not ready for this run';
    $('resultDescription').textContent = result.message;
    $('sourceLabel').textContent = result.data_source ? `Source: ${result.data_source}` : 'Source: unavailable for this run';
    $('runState').innerHTML = result.status === 'completed'
      ? '<i class="fa-solid fa-circle-check"></i> COMPLETED'
      : '<i class="fa-regular fa-circle-pause"></i> NO RESULT';
    if (result.first_date && result.last_date) {
      $('historyCoverage').textContent = `${result.observations} synchronized days · ${result.first_date} — ${result.last_date}`;
    }
    if (result.status !== 'completed') {
      setStatus('No result; see the explanation in the summary below.', 'fa-solid fa-circle-info');
      alert(result.message, 'info');
      return;
    }

    setStatus(`Completed on ${result.observations} synchronized observations.`, 'fa-solid fa-circle-check');
    renderMetrics(result.metrics);
    renderCharts(result.equity_curve || [], result.spread_series || []);
    allTrades = result.trades || [];
    $('exportTradesButton').disabled = allTrades.length === 0;
    renderTrades(allTrades);
    $('assumptionList').replaceChildren(...(result.assumptions || []).map((item) => {
      const li = document.createElement('li'); li.textContent = item; return li;
    }));
    $('assumptionLead').textContent = 'Historical simulation only; settlement fills are proxies, costs are user-configured, and results are not a forecast or guarantee.';
    alert(`Historical backtest complete for ${result.first_date} through ${result.last_date}. Review the settlement and cost assumptions below the charts.`, 'success');
  }

  function setMetric(id, text, sentiment = '') {
    const el = $(id); el.textContent = text;
    el.classList.remove('positive', 'negative');
    if (sentiment) el.classList.add(sentiment);
  }

  function renderMetrics(metrics) {
    const returnPct = metrics.total_return_pct;
    setMetric('metricReturn', Number.isFinite(returnPct) ? signed(returnPct, '%') : '—', returnPct > 0 ? 'positive' : returnPct < 0 ? 'negative' : '');
    $('metricPnl').textContent = metrics.total_pnl === null ? 'P&L unavailable' : `${signed(metrics.total_pnl, ' ₹')} net · ${inr(metrics.gross_pnl)} gross`;
    const drawdown = metrics.max_drawdown_pct;
    setMetric('metricDrawdown', Number.isFinite(drawdown) ? `${drawdown.toFixed(2)}%` : '—', drawdown < 0 ? 'negative' : '');
    setMetric('metricSharpe', Number.isFinite(metrics.sharpe_ratio) ? metrics.sharpe_ratio.toFixed(2) : '—');
    setMetric('metricWinRate', Number.isFinite(metrics.win_rate_pct) ? `${metrics.win_rate_pct.toFixed(1)}%` : '—');
    $('metricWinSub').textContent = Number.isFinite(metrics.win_rate_pct) ? `${metrics.total_trades} completed trades` : 'No completed trades';
    setMetric('metricTrades', String(metrics.total_trades));
    setMetric('metricProfitFactor', Number.isFinite(metrics.profit_factor) ? metrics.profit_factor.toFixed(2) : '—');
    if (metrics.total_return_pct === null) $('metricPnl').textContent = 'Insufficient observations';
  }

  function chartOptions(formatter, beginAtZero = false) {
    return {
      responsive: true, maintainAspectRatio: false, animation: { duration: 450 },
      interaction: { intersect: false, mode: 'index' },
      plugins: {
        legend: { display: false },
        tooltip: { backgroundColor: '#171610', borderColor: 'rgba(214,181,106,.28)', borderWidth: 1, titleColor: '#e7d39d', bodyColor: '#e5dfd0', padding: 11, callbacks: { label: (ctx) => ` ${formatter(ctx.parsed.y)}` } },
      },
      scales: {
        x: { grid: { display: false }, border: { display: false }, ticks: { color: '#77746c', maxTicksLimit: 7, font: { family: 'DM Mono', size: 9 } } },
        y: { beginAtZero, grid: { color: 'rgba(255,255,255,.055)' }, border: { display: false }, ticks: { color: '#77746c', maxTicksLimit: 5, font: { family: 'DM Mono', size: 9 }, callback: formatter } },
      },
    };
  }

  function renderCharts(curve, spreadSeries) {
    clearCharts();
    if (!curve.length) return;
    const labels = curve.map((point) => point.trade_date);
    const equity = curve.map((point) => point.equity);
    const drawdown = curve.map((point) => point.drawdown_pct);
    $('equityEmpty').hidden = true; $('drawdownEmpty').hidden = true;
    $('spreadEmpty').hidden = !spreadSeries.length;
    $('spreadEmpty').style.display = spreadSeries.length ? 'none' : 'flex';
    document.querySelectorAll('.bt-chart-wrap').forEach((wrap) => wrap.classList.add('has-chart'));
    if (typeof window.Chart === 'function') {
      equityChart = new Chart($('equityChart'), { type: 'line', data: { labels, datasets: [{ label: 'Portfolio equity', data: equity, borderColor: '#d7b86d', backgroundColor: 'rgba(197,158,70,.1)', fill: true, borderWidth: 2, pointRadius: 0, pointHoverRadius: 4, tension: .22 }] }, options: chartOptions((n) => inr(n, 0)) });
      drawdownChart = new Chart($('drawdownChart'), { type: 'line', data: { labels, datasets: [{ label: 'Drawdown', data: drawdown, borderColor: '#c38e72', backgroundColor: 'rgba(161,94,72,.12)', fill: true, borderWidth: 1.7, pointRadius: 0, pointHoverRadius: 4, tension: .18 }] }, options: chartOptions((n) => `${Number(n).toFixed(2)}%`, true) });
      if (spreadSeries.length) {
        const spreadLabels = spreadSeries.map((point) => point.trade_date);
        const markerValues = (matcher) => spreadSeries.map((point) => point.execution && matcher(point.execution) ? point.spread : null);
        spreadChart = new Chart($('spreadChart'), { type: 'line', data: { labels: spreadLabels, datasets: [
          { label: 'Normalized spread', data: spreadSeries.map((point) => point.spread), borderColor: '#d7b86d', backgroundColor: 'rgba(197,158,70,.08)', fill: true, borderWidth: 1.8, pointRadius: 0, pointHoverRadius: 4, tension: .16 },
          { label: 'Long entry', data: markerValues((text) => text === 'Entry · long'), showLine: false, pointStyle: 'triangle', pointRadius: 6, pointHoverRadius: 8, pointBackgroundColor: '#9ec7a5', pointBorderColor: '#090908' },
          { label: 'Short entry', data: markerValues((text) => text === 'Entry · short'), showLine: false, pointStyle: 'triangle', pointRotation: 180, pointRadius: 6, pointHoverRadius: 8, pointBackgroundColor: '#d99a8d', pointBorderColor: '#090908' },
          { label: 'Exit', data: markerValues((text) => text === 'Exit'), showLine: false, pointStyle: 'rectRot', pointRadius: 5, pointHoverRadius: 7, pointBackgroundColor: '#f0d98f', pointBorderColor: '#090908' },
        ] }, options: { ...chartOptions((n) => inr(n)), plugins: { ...chartOptions((n) => inr(n)).plugins, legend: { display: true, position: 'top', align: 'end', labels: { color: '#9a958a', boxWidth: 10, boxHeight: 7, usePointStyle: true, font: { family: 'Inter', size: 9 } } } } } });
      }
      return;
    }
    renderFallback($('equityChart'), labels, equity, '#d7b86d', (n) => inr(n, 0));
    renderFallback($('drawdownChart'), labels, drawdown, '#c38e72', (n) => `${Number(n).toFixed(2)}%`);
    if (spreadSeries.length) renderFallback($('spreadChart'), spreadSeries.map((point) => point.trade_date), spreadSeries.map((point) => point.spread), '#d7b86d', (n) => inr(n));
  }

  function renderFallback(canvas, labels, values, color, formatter) {
    const wrap = canvas.parentElement;
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 800 250'); svg.setAttribute('preserveAspectRatio', 'none'); svg.classList.add('bt-chart-fallback');
    svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', `Chart from ${labels[0]} to ${labels[labels.length - 1]}`);
    const min = Math.min(...values); const max = Math.max(...values); const range = max - min || 1;
    const coords = values.map((v, i) => [24 + i * (752 / Math.max(1, values.length - 1)), 218 - ((v - min) / range) * 190]);
    for (let i = 0; i < 4; i++) { const y = 25 + i * 62; const grid = document.createElementNS(svg.namespaceURI, 'line'); grid.setAttribute('x1', '24'); grid.setAttribute('x2', '790'); grid.setAttribute('y1', String(y)); grid.setAttribute('y2', String(y)); grid.setAttribute('stroke', 'rgba(255,255,255,.08)'); svg.appendChild(grid); }
    const path = document.createElementNS(svg.namespaceURI, 'path'); path.setAttribute('d', coords.map(([x, y], i) => `${i ? 'L' : 'M'}${x},${y}`).join(' ')); path.setAttribute('fill', 'none'); path.setAttribute('stroke', color); path.setAttribute('stroke-width', '2.4'); svg.appendChild(path);
    const first = document.createElementNS(svg.namespaceURI, 'text'); first.setAttribute('x', '24'); first.setAttribute('y', '245'); first.textContent = labels[0];
    const last = document.createElementNS(svg.namespaceURI, 'text'); last.setAttribute('x', '790'); last.setAttribute('y', '245'); last.setAttribute('text-anchor', 'end'); last.textContent = labels.at(-1);
    [first, last].forEach((text) => { text.setAttribute('fill', '#837f75'); text.setAttribute('font-size', '10'); text.setAttribute('font-family', 'monospace'); svg.appendChild(text); });
    const title = document.createElementNS(svg.namespaceURI, 'title'); title.textContent = `${formatter(min)} to ${formatter(max)}`; svg.appendChild(title);
    canvas.hidden = true; wrap.appendChild(svg);
  }

  function renderTrades(trades) {
    const term = $('tradeSearch').value.trim().toLowerCase();
    const filtered = trades.filter((trade) => `${trade.pair} ${trade.direction} ${trade.exit_reason}`.toLowerCase().includes(term));
    $('tradeCountTag').textContent = String(trades.length);
    const body = $('tradeRows'); body.replaceChildren();
    if (!filtered.length) {
      const row = body.insertRow(); row.className = 'bt-table-empty';
      const cell = row.insertCell(); cell.colSpan = 10; cell.textContent = trades.length ? 'No trades match this search.' : 'No completed trades were recorded for this run.';
      return;
    }
    filtered.forEach((trade) => {
      const row = body.insertRow();
      const cells = [trade.entry_date, trade.exit_date, trade.pair.replace('-', ' / '), `${trade.direction} · ${trade.units}`, inr(trade.entry_spread), inr(trade.exit_spread), inr(trade.gross_pnl), inr(trade.costs), inr(trade.net_pnl), trade.exit_reason];
      cells.forEach((text, index) => { const cell = row.insertCell(); cell.textContent = text; if ([6, 8].includes(index)) cell.className = Number(index === 6 ? trade.gross_pnl : trade.net_pnl) > 0 ? 'positive' : 'negative'; });
    });
  }

  function applyPreset(name) {
    const preset = presets[name]; if (!preset) return;
    Object.entries(preset).forEach(([key, val]) => {
      const map = { lookback: 'lookbackInput', entry: 'entryInput', exit: 'exitInput', volume: 'volumeInput', expiry: 'expiryInput' };
      $(map[key]).value = val;
    });
    document.querySelectorAll('.bt-preset').forEach((button) => button.classList.toggle('is-active', button.dataset.preset === name));
  }

  form.addEventListener('submit', runBacktest);
  $('resetButton').addEventListener('click', () => {
    Object.entries(defaults).forEach(([key, val]) => {
      const map = { pair: 'pairInput', lookback: 'lookbackInput', units: 'unitsInput', entry: 'entryInput', exit: 'exitInput', capital: 'capitalInput', cost: 'costInput', slippage: 'slippageInput', volume: 'volumeInput', expiry: 'expiryInput', start: 'startInput', end: 'endInput' };
      $(map[key]).value = val;
    });
    document.querySelectorAll('.bt-preset').forEach((button) => button.classList.toggle('is-active', button.dataset.preset === 'baseline'));
    formError.hidden = true; resetDisplay(); setStatus('Configuration restored to the documented baseline.');
  });
  document.querySelectorAll('.bt-preset').forEach((button) => button.addEventListener('click', () => applyPreset(button.dataset.preset)));
  function exportTradesCsv() {
    if (!allTrades.length) return;
    const columns = [
      ['entry_date', 'Entry date'], ['exit_date', 'Exit date'], ['pair', 'Pair'],
      ['direction', 'Position'], ['units', 'Units'], ['entry_spread', 'Entry spread INR/10g'],
      ['exit_spread', 'Exit spread INR/10g'], ['gross_pnl', 'Gross P&L INR'],
      ['costs', 'Costs INR'], ['net_pnl', 'Net P&L INR'], ['exit_reason', 'Exit reason'],
    ];
    const escapeCell = (value) => {
      const text = value == null ? '' : String(value);
      return '"' + text.replaceAll('"', '""') + '"';
    };
    const lines = [columns.map(([, label]) => escapeCell(label)).join(',')];
    allTrades.forEach((trade) => lines.push(columns.map(([key]) => escapeCell(trade[key])).join(',')));
    const blob = new Blob(['\uFEFF' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `aurora-backtest-trades-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link); link.click(); link.remove();
    URL.revokeObjectURL(url);
  }
  $('exportTradesButton').addEventListener('click', exportTradesCsv);
  $('tradeSearch').addEventListener('input', () => renderTrades(allTrades));
  $('uploadButton').addEventListener('click', () => {
    const upload = document.getElementById('btnOpenIngestModal');
    if (upload) upload.click();
    else { setStatus('The CSV import control is not available. Open Market Data from the dashboard.', 'fa-solid fa-triangle-exclamation'); window.location.href = 'dashboard.html#data'; }
  });
  $('sidebarToggle').addEventListener('click', () => $('sidebar').classList.toggle('open'));

  loadMarketStatus();
})();
