/**
 * AURORA Commodity Intelligence — Data Pipeline & Ingestion Client (Phase 1)
 * Preserves all existing styles, animations, and pages.
 * Connects frontend to FastAPI backend:
 * - Real backend health & market status surveillance
 * - Interactive CSV Bhavcopy ingestion modal with validation diagnostics
 * - Real-time contract & normalized price inspection
 */

(function () {
  const API_BASE = (window.AURORA_API_ORIGIN || 'https://aurora-gold-intelligence.onrender.com').replace(/\/$/, '');
  let backendOnline = false;
  let radarPairMap = {};
  let radarRequestId = 0;
  let distributionRequestId = 0;
  let priceSnapshotRequestId = 0;
  let detectiveRequestId = 0;
  let selectedDetectiveEvent = null;
  let detectiveFeedLabel = null;
  let selectedRadarPairKey = null;
  const sparklineRequestIds = new Map();
  const RADAR_CANONICAL_PAIRS = [
    ['GOLDM', 'GOLDTEN'], ['GOLDM', 'GOLDGUINEA'], ['GOLDM', 'GOLDPETAL'],
    ['GOLDTEN', 'GOLDGUINEA'], ['GOLDTEN', 'GOLDPETAL'], ['GOLDGUINEA', 'GOLDPETAL']
  ].map(([leg_a, leg_b]) => ({ pair: `${leg_a}-${leg_b}`, leg_a, leg_b }));

  // Initialize once DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPipeline);
  } else {
    initPipeline();
  }

  function initPipeline() {
    injectStyles();
    injectHeaderControls();
    injectIngestModal();
    checkBackendStatus();
    // Poll backend status periodically (every 12 seconds)
    setInterval(checkBackendStatus, 12000);
    // Initialize Phase 2 Relative-Value Analytics Live Integration
    initPhase2AnalyticsSync();
  }

  /* --------------------------------------------------------------------------
     1. Status Surveillance (Replaces fake status with live backend truth)
     -------------------------------------------------------------------------- */
  async function checkBackendStatus() {
    const statusChip = document.querySelector('.market-status-chip');
    const freshnessChip = document.querySelector('.data-freshness-chip');

    try {
      const res = await fetch(`${API_BASE}/api/market/status`, { mode: 'cors' });
      if (!res.ok) throw new Error('Status endpoint non-200');
      const data = await res.json();
      backendOnline = true;
      const payload = data.data || {};

      if (statusChip) {
        const isLive = payload.feed_status === 'LIVE' && payload.is_live_connected === true;
        statusChip.style.background = isLive ? 'rgba(16, 185, 129, 0.15)' : 'rgba(209, 173, 94, 0.12)';
        statusChip.style.borderColor = isLive ? 'rgba(16, 185, 129, 0.4)' : 'rgba(209, 173, 94, 0.35)';
        statusChip.style.color = isLive ? '#34d399' : '#d1ad5e';
        statusChip.title = `Backend connected · ${payload.provider_name || 'AURORA local data'} · feed ${payload.feed_status || 'UNAVAILABLE'}`;
        statusChip.innerHTML = `
          <div class="live-pulse-dot" style="background:${isLive ? '#10b981' : '#d1ad5e'};box-shadow:0 0 8px ${isLive ? '#10b981' : '#d1ad5e'};"></div>
          <span>API CONNECTED &bull; ${formatDataMode(payload.data_mode, payload)}</span>
        `;
      }

      if (freshnessChip) {
        freshnessChip.title = `Server UTC: ${payload.server_time || ''}`;
        freshnessChip.innerHTML = `
          <i class="fa-solid fa-database" style="color:var(--gold-primary);"></i>
          <span>${payload.data_freshness_label || 'Data Staged'} (${payload.total_observations || 0} obs)</span>
        `;
      }
    } catch (err) {
      backendOnline = false;
      if (statusChip) {
        statusChip.style.background = 'rgba(239, 68, 68, 0.12)';
        statusChip.style.borderColor = 'rgba(239, 68, 68, 0.4)';
        statusChip.style.color = '#f87171';
        statusChip.title = 'Backend offline: Ensure FastAPI server is running on http://127.0.0.1:8000';
        statusChip.innerHTML = `
          <div class="live-pulse-dot" style="background:#ef4444;box-shadow:0 0 8px #ef4444;"></div>
          <span>Backend Offline &bull; Local Mode</span>
        `;
      }
      if (freshnessChip) {
        freshnessChip.innerHTML = `
          <i class="fa-solid fa-triangle-exclamation" style="color:#f59e0b;"></i>
          <span>Awaiting Server (Port 8000)</span>
        `;
      }
    }
  }

  function formatDataMode(mode, payload = {}) {
    if (payload.feed_status === 'LIVE' && payload.is_live_connected === true) return 'Verified MCX Live Feed';
    if (payload.feed_status === 'DELAYED') return 'Authorized MCX Delayed Feed';
    if (payload.feed_status === 'STALE') return 'Provider Feed Stale';
    if (mode === 'staged_csv') return 'User CSV (Unverified)';
    if (mode === 'live_feed_disconnected') return 'Live Feed Disconnected';
    if (mode === 'live_feed_stale') return 'Provider Feed Stale';
    if (mode === 'delayed_feed_authorized') return 'Authorized MCX Delayed Feed';
    if (mode === 'test_data') return 'Test Data · Excluded from Analysis';
    if (mode === 'demo_synthetic') return 'Synthetic Demo Data';
    return 'Feed Unavailable';
  }

  /* --------------------------------------------------------------------------
     2. Header Controls Injection
     -------------------------------------------------------------------------- */
  function injectHeaderControls() {
    const headerRight = document.querySelector('.header-right');
    if (!headerRight || document.getElementById('btnOpenIngestModal')) return;

    const btn = document.createElement('button');
    btn.id = 'btnOpenIngestModal';
    btn.type = 'button';
    btn.className = 'aurora-pipeline-btn';
    btn.innerHTML = `<i class="fa-solid fa-cloud-arrow-up"></i><span>Ingest Bhavcopy CSV</span>`;
    btn.title = 'Upload, validate, and inspect MCX Bhavcopy market data';
    btn.addEventListener('click', openIngestModal);

    // Insert as first element in header-right
    headerRight.insertBefore(btn, headerRight.firstChild);
  }

  /* --------------------------------------------------------------------------
     3. Modal Creation & Tab Navigation
     -------------------------------------------------------------------------- */
  function injectIngestModal() {
    if (document.getElementById('auroraIngestModal')) return;

    const modal = document.createElement('div');
    modal.id = 'auroraIngestModal';
    modal.className = 'aurora-modal-overlay';
    modal.innerHTML = `
      <div class="aurora-modal-container">
        <!-- Modal Header -->
        <div class="aurora-modal-head">
          <div class="modal-title-group">
            <div class="modal-icon-badge"><i class="fa-solid fa-file-csv"></i></div>
            <div>
              <h3>MCX Market Data Pipeline</h3>
              <p>Phase 1 &bull; CSV Ingestion, Multi-Layer Validation, Normalization & Audit</p>
            </div>
          </div>
          <button type="button" class="aurora-modal-close" id="btnCloseIngestModal">&times;</button>
        </div>

        <!-- Navigation Tabs -->
        <div class="aurora-modal-tabs">
          <button type="button" class="tab-btn active" data-tab="tabUpload">
            <i class="fa-solid fa-upload"></i> Upload CSV
          </button>
          <button type="button" class="tab-btn" data-tab="tabInspectPrices">
            <i class="fa-solid fa-table-list"></i> Normalized Prices
          </button>
          <button type="button" class="tab-btn" data-tab="tabContracts">
            <i class="fa-solid fa-shapes"></i> Contract Specs
          </button>
          <button type="button" class="tab-btn" data-tab="tabBatches">
            <i class="fa-solid fa-clock-rotate-left"></i> Import History
          </button>
        </div>

        <!-- Modal Body -->
        <div class="aurora-modal-body">
          <!-- TAB 1: UPLOAD -->
          <div class="tab-content active" id="tabUpload">
            <div class="upload-dropzone" id="uploadDropzone">
              <i class="fa-solid fa-cloud-arrow-up drop-icon"></i>
              <h4>Drag & drop Bhavcopy CSV here</h4>
              <p>Supports MCX EOD CSV format (GOLDM, GOLDTEN, GOLDGUINEA, GOLDPETAL)</p>
              <input type="file" id="csvFileInput" accept=".csv" style="display:none;" />
              <button type="button" class="browse-btn" id="btnBrowseFile">
                <i class="fa-solid fa-folder-open"></i> Browse File
              </button>
              <div id="selectedFileName" class="selected-file-label"></div>
            </div>

            <!-- Preloaded Test Data Triggers (1-Click Evaluation for Hackathon Judges) -->
            <div class="sample-actions-row">
              <span class="sample-label">Quick Test Datasets:</span>
              <button type="button" class="sample-btn" id="btnLoadValidSample">
                <i class="fa-solid fa-circle-check" style="color:#10b981;"></i> Load Valid Sample Data
              </button>
              <button type="button" class="sample-btn" id="btnLoadInvalidSample">
                <i class="fa-solid fa-circle-exclamation" style="color:#f59e0b;"></i> Test Malformed CSV (Rejection Demo)
              </button>
            </div>

            <!-- Upload Parameters -->
            <div class="upload-options-grid">
              <div>
                <label>Data Provenance Label</label>
                <input type="text" id="inputDataSource" value="mcx_bhavcopy_public" placeholder="e.g. mcx_bhavcopy_public" />
              </div>
              <div>
                <label>Data Class</label>
                <select id="selectDataClass">
                  <option value="false">Official Bhavcopy / Staged Data</option>
                  <option value="true">Synthetic Demo Data (Testing)</option>
                </select>
              </div>
            </div>

            <!-- Submit Button & Feedback -->
            <div class="submit-action-row">
              <button type="button" class="submit-upload-btn" id="btnSubmitUpload">
                <i class="fa-solid fa-play"></i> Ingest & Normalize Data
              </button>
            </div>

            <div id="uploadFeedbackBox" class="feedback-box" style="display:none;"></div>
            <div id="errorDetailsSection" class="error-details-section" style="display:none;"></div>
          </div>

          <!-- TAB 2: NORMALIZED OBSERVATIONS -->
          <div class="tab-content" id="tabInspectPrices">
            <div class="tab-filter-bar">
              <div class="filter-group">
                <label>Contract</label>
                <select id="filterPriceSymbol">
                  <option value="">All Contracts</option>
                  <option value="GOLDM">GOLDM</option>
                  <option value="GOLDTEN">GOLDTEN</option>
                  <option value="GOLDGUINEA">GOLDGUINEA</option>
                  <option value="GOLDPETAL">GOLDPETAL</option>
                </select>
              </div>
              <button type="button" class="refresh-btn" id="btnRefreshPrices">
                <i class="fa-solid fa-rotate"></i> Refresh
              </button>
            </div>
            <div class="data-table-scroll" id="pricesTableContainer">
              <div class="table-loading"><i class="fa-solid fa-circle-notch fa-spin"></i> Loading observations...</div>
            </div>
          </div>

          <!-- TAB 3: CONTRACT SPECIFICATIONS -->
          <div class="tab-content" id="tabContracts">
            <div class="data-table-scroll" id="contractsTableContainer">
              <div class="table-loading"><i class="fa-solid fa-circle-notch fa-spin"></i> Loading contract metadata...</div>
            </div>
          </div>

          <!-- TAB 4: IMPORT BATCHES -->
          <div class="tab-content" id="tabBatches">
            <div class="data-table-scroll" id="batchesTableContainer">
              <div class="table-loading"><i class="fa-solid fa-circle-notch fa-spin"></i> Loading audit history...</div>
            </div>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    // Bind Modal Events
    document.getElementById('btnCloseIngestModal').addEventListener('click', closeIngestModal);
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeIngestModal();
    });

    // Tab Switching
    modal.querySelectorAll('.tab-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        modal.querySelectorAll('.tab-btn').forEach((b) => b.classList.remove('active'));
        modal.querySelectorAll('.tab-content').forEach((c) => c.classList.remove('active'));
        btn.classList.add('active');
        const targetId = btn.getAttribute('data-tab');
        const targetContent = document.getElementById(targetId);
        if (targetContent) targetContent.classList.add('active');

        // Load data on tab open
        if (targetId === 'tabInspectPrices') fetchAndRenderPrices();
        if (targetId === 'tabContracts') fetchAndRenderContracts();
        if (targetId === 'tabBatches') fetchAndRenderBatches();
      });
    });

    // File Browse & Drag-Drop
    const fileInput = document.getElementById('csvFileInput');
    const dropzone = document.getElementById('uploadDropzone');
    const browseBtn = document.getElementById('btnBrowseFile');
    const selectedLabel = document.getElementById('selectedFileName');

    browseBtn.addEventListener('click', () => fileInput.click());
    dropzone.addEventListener('click', (e) => {
      if (e.target !== browseBtn) fileInput.click();
    });

    fileInput.addEventListener('change', () => {
      if (fileInput.files.length > 0) {
        selectedLabel.textContent = `Selected: ${fileInput.files[0].name} (${(fileInput.files[0].size / 1024).toFixed(1)} KB)`;
      }
    });

    dropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
      if (e.dataTransfer.files.length > 0) {
        fileInput.files = e.dataTransfer.files;
        selectedLabel.textContent = `Selected: ${fileInput.files[0].name} (${(fileInput.files[0].size / 1024).toFixed(1)} KB)`;
      }
    });

    // Quick Test Buttons
    document.getElementById('btnLoadValidSample').addEventListener('click', () => handleSampleUpload('valid'));
    document.getElementById('btnLoadInvalidSample').addEventListener('click', () => handleSampleUpload('invalid'));

    // Manual Submit Upload
    document.getElementById('btnSubmitUpload').addEventListener('click', handleManualUpload);

    // Refresh Prices
    document.getElementById('btnRefreshPrices').addEventListener('click', fetchAndRenderPrices);
    document.getElementById('filterPriceSymbol').addEventListener('change', fetchAndRenderPrices);
  }

  function openIngestModal() {
    const modal = document.getElementById('auroraIngestModal');
    if (modal) {
      modal.classList.add('active');
      checkBackendStatus();
    }
  }

  function closeIngestModal() {
    const modal = document.getElementById('auroraIngestModal');
    if (modal) modal.classList.remove('active');
  }

  /* --------------------------------------------------------------------------
     4. Upload Handlers
     -------------------------------------------------------------------------- */
  async function handleManualUpload() {
    const fileInput = document.getElementById('csvFileInput');
    if (!fileInput.files || fileInput.files.length === 0) {
      showFeedback('warning', 'Please select or drag a CSV file first, or use the 1-click sample buttons below.');
      return;
    }
    const file = fileInput.files[0];
    const sourceLabel = document.getElementById('inputDataSource').value.trim() || 'csv_upload';
    const isSynthetic = document.getElementById('selectDataClass').value === 'true';

    await executeUpload(file, sourceLabel, isSynthetic);
  }

  async function handleSampleUpload(type) {
    let filename, csvContent, isSynthetic;
    if (type === 'valid') {
      filename = 'sample_mcx_gold_bhavcopy_valid.csv';
      isSynthetic = true;
      csvContent = `symbol,trade_date,expiry_date,open,high,low,close,volume,open_interest
GOLDM,2026-10-12,2026-10-30,62350,62600,62280,62450,12450,34567
GOLDTEN,2026-10-12,2026-11-27,62250,62480,62190,62380,3200,8900
GOLDGUINEA,2026-10-12,2026-10-28,50050,50220,49980,50120,1890,5670
GOLDPETAL,2026-10-12,2026-10-28,6290,6325,6280,6310,890,2340
GOLDM,2026-10-15,2026-10-30,62790,63100,62710,62980,15400,37800
GOLDTEN,2026-10-15,2026-11-27,62700,62990,62630,62890,3850,9720
GOLDGUINEA,2026-10-15,2026-10-28,50400,50650,50330,50540,2250,6080
GOLDPETAL,2026-10-15,2026-10-28,6355,6390,6345,6378,1150,2690`;
    } else {
      filename = 'sample_mcx_gold_bhavcopy_invalid.csv';
      isSynthetic = true;
      csvContent = `symbol,trade_date,expiry_date,open,high,low,close,volume,open_interest
GOLDM,2026-10-15,2026-10-30,62790,63100,62710,62980,15400,37800
SILVERM,2026-10-15,2026-11-20,74000,74500,73800,74200,5000,12000
GOLDTEN,2026-10-15,2026-11-27,62700,62990,62630,-62890,3850,9720
GOLDGUINEA,2026-10-15,2026-10-28,50400,50200,50800,50540,2250,6080
GOLDPETAL,2026-10-15,2026-10-28,6355,6390,6345,,1150,2690
GOLDM,invalid-date,2026-10-30,62790,63100,62710,62980,15400,37800
GOLDTEN,2026-10-15,2026-10-01,62700,62990,62630,62890,3850,9720`;
    }

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const file = new File([blob], filename, { type: 'text/csv' });
    await executeUpload(file, `sample_${type}_demo`, isSynthetic, true);
  }

  async function executeUpload(file, sourceLabel, isSynthetic, allowDuplicates = true) {
    const feedbackBox = document.getElementById('uploadFeedbackBox');
    const errorSection = document.getElementById('errorDetailsSection');
    const submitBtn = document.getElementById('btnSubmitUpload');

    feedbackBox.style.display = 'block';
    feedbackBox.className = 'feedback-box loading pipeline-progress';
    feedbackBox.innerHTML = `<div class="pipeline-progress-head"><i class="fa-solid fa-circle-notch fa-spin"></i><span>Uploading <b>${file.name}</b> for validation and fine-gold normalization…</span></div><div class="pipeline-progress-track" aria-label="Processing upload"><span></span></div><small>Progress becomes available when the server reports it.</small>`;
    errorSection.style.display = 'none';
    submitBtn.disabled = true;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('data_source', sourceLabel);
    formData.append('is_synthetic', isSynthetic ? 'true' : 'false');
    formData.append('allow_duplicates', allowDuplicates ? 'true' : 'false');

    try {
      const response = await fetch(`${API_BASE}/api/data/upload`, {
        method: 'POST',
        body: formData,
        mode: 'cors'
      });

      feedbackBox.querySelector('.pipeline-progress-head span').textContent = 'Validation and normalization response received…';
      const resData = await response.json();
      submitBtn.disabled = false;

      if (!response.ok || !resData.success) {
        showFeedback('error', resData.error || resData.message || 'Upload failed');
        return;
      }

      const res = resData.data;
      let badgeClass = res.status === 'completed' ? 'success' : res.status === 'partial_success' ? 'warning' : 'error';

      feedbackBox.className = `feedback-box ${badgeClass}`;
      feedbackBox.innerHTML = `
        <div class="feedback-head">
          <i class="fa-solid ${res.status === 'completed' ? 'fa-circle-check' : 'fa-circle-exclamation'}"></i>
          <strong>Batch #${res.batch_id} Processed: ${res.status.toUpperCase()}</strong>
        </div>
        <p>${res.message}</p>
        <div class="stat-pills-row">
          <span class="pill-stat green">Accepted: <b>${res.accepted_rows}</b></span>
          <span class="pill-stat red">Rejected: <b>${res.rejected_rows}</b></span>
          <span class="pill-stat amber">Duplicates Skipped: <b>${res.duplicate_rows}</b></span>
          <span class="pill-stat">Total: <b>${res.total_rows}</b></span>
        </div>
        <small style="display:block;margin-top:8px;color:var(--text-muted);font-family:monospace;">
          SHA-256 Checksum: ${res.file_hash ? res.file_hash.slice(0, 16) + '...' : 'N/A'} &bull; Source: ${res.data_source}
        </small>
      `;

      // Render Rejection Diagnostics Table if errors occurred
      if (res.errors && res.errors.length > 0) {
        errorSection.style.display = 'block';
        errorSection.innerHTML = `
          <h4><i class="fa-solid fa-bug" style="color:#f87171;"></i> Validation Rejections Breakdown (${res.errors.length} rows)</h4>
          <div class="data-table-scroll" style="max-height:220px;">
            <table class="aurora-pipeline-table">
              <thead>
                <tr>
                  <th>Row #</th>
                  <th>Field</th>
                  <th>Rejection Diagnostic Reason</th>
                </tr>
              </thead>
              <tbody>
                ${res.errors.map(err => `
                  <tr>
                    <td><b style="color:var(--gold-primary);">#${err.row_number}</b></td>
                    <td><code>${err.field || 'general'}</code></td>
                    <td style="color:#fca5a5;">${err.reason}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        `;
      }

      // Update backend status indicators
      checkBackendStatus();
    } catch (e) {
      submitBtn.disabled = false;
      showFeedback('error', `Network / API Error: ${e.message}. Ensure backend is running at ${API_BASE}`);
    }
  }

  function showFeedback(type, message) {
    const box = document.getElementById('uploadFeedbackBox');
    if (!box) return;
    box.style.display = 'block';
    box.className = `feedback-box ${type}`;
    box.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> <span>${message}</span>`;
  }

  /* --------------------------------------------------------------------------
     5. Data Inspection Fetchers
     -------------------------------------------------------------------------- */
  async function fetchAndRenderPrices() {
    const container = document.getElementById('pricesTableContainer');
    if (!container) return;
    container.innerHTML = `<div class="table-loading"><i class="fa-solid fa-circle-notch fa-spin"></i> Querying observations...</div>`;

    const symbolFilter = document.getElementById('filterPriceSymbol').value;
    const url = symbolFilter
      ? `${API_BASE}/api/market/prices?symbol=${encodeURIComponent(symbolFilter)}&limit=50`
      : `${API_BASE}/api/market/prices?limit=50`;

    try {
      const res = await fetch(url, { mode: 'cors' });
      const json = await res.json();
      const items = json.data?.items || [];

      if (items.length === 0) {
        container.innerHTML = `<div class="table-empty"><i class="fa-solid fa-inbox"></i> No observations found in database. Ingest a CSV to populate.</div>`;
        return;
      }

      container.innerHTML = `
        <table class="aurora-pipeline-table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Trade Date</th>
              <th>Expiry</th>
              <th>Quoted Close (INR)</th>
              <th>Volume</th>
              <th>Open Int</th>
              <th>Norm Price (₹/g Fine)</th>
              <th>10g 995 Basis</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            ${items.map(row => `
              <tr>
                <td><b class="gold-badge">${row.symbol}</b></td>
                <td>${row.trade_date}</td>
                <td>${row.expiry_date}</td>
                <td><b>₹${Number(row.close_price).toLocaleString('en-IN')}</b></td>
                <td>${Number(row.volume).toLocaleString('en-IN')}</td>
                <td>${Number(row.open_interest).toLocaleString('en-IN')}</td>
                <td style="color:#34d399;font-weight:600;">₹${Number(row.normalized_price_per_gram).toFixed(2)}/g</td>
                <td style="color:var(--gold-primary);font-weight:700;">₹${Number(row.normalized_price_10g_basis).toLocaleString('en-IN')}</td>
                <td><small class="source-tag ${row.is_synthetic ? 'synth' : 'real'}">${row.data_source}</small></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
    } catch (e) {
      container.innerHTML = `<div class="table-empty" style="color:#f87171;"><i class="fa-solid fa-circle-exclamation"></i> Error loading observations: ${e.message}</div>`;
    }
  }

  async function fetchAndRenderContracts() {
    const container = document.getElementById('contractsTableContainer');
    if (!container) return;
    container.innerHTML = `<div class="table-loading"><i class="fa-solid fa-circle-notch fa-spin"></i> Querying contracts...</div>`;

    try {
      const res = await fetch(`${API_BASE}/api/contracts`, { mode: 'cors' });
      const json = await res.json();
      const contracts = json.data || [];

      if (contracts.length === 0) {
        container.innerHTML = `<div class="table-empty">No contract specifications found.</div>`;
        return;
      }

      container.innerHTML = `
        <table class="aurora-pipeline-table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Contract Name</th>
              <th>Trading Unit</th>
              <th>Quotation Unit</th>
              <th>Purity</th>
              <th>Expiry Window</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            ${contracts.map(c => `
              <tr>
                <td><b class="gold-badge">${c.symbol}</b></td>
                <td>${c.name}</td>
                <td>${c.trading_unit}</td>
                <td>${c.quote_unit}</td>
                <td><b>${c.purity}</b> (${(c.purity_factor * 100).toFixed(1)}%)</td>
                <td>${c.expiry_window || 'N/A'}</td>
                <td><span class="status-pill active">Active</span></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
    } catch (e) {
      container.innerHTML = `<div class="table-empty" style="color:#f87171;">Error loading contracts: ${e.message}</div>`;
    }
  }

  async function fetchAndRenderBatches() {
    const container = document.getElementById('batchesTableContainer');
    if (!container) return;
    container.innerHTML = `<div class="table-loading"><i class="fa-solid fa-circle-notch fa-spin"></i> Querying batch logs...</div>`;

    try {
      const res = await fetch(`${API_BASE}/api/data/imports`, { mode: 'cors' });
      const json = await res.json();
      const batches = json.data || [];

      if (batches.length === 0) {
        container.innerHTML = `<div class="table-empty"><i class="fa-solid fa-clock-rotate-left"></i> No historical batches recorded yet.</div>`;
        return;
      }
      const formatCount = value => {
        const count = Number(value);
        return value == null || !Number.isFinite(count) ? '—' : count.toLocaleString('en-IN');
      };

      container.innerHTML = `
        <table class="aurora-pipeline-table">
          <thead>
            <tr>
              <th>Batch #</th>
              <th>Filename</th>
              <th>Total Rows</th>
              <th>Accepted</th>
              <th>Rejected</th>
              <th>Duplicates Skipped</th>
              <th>Status</th>
              <th>Checksum (SHA-256)</th>
              <th>Import Timestamp</th>
            </tr>
          </thead>
          <tbody>
            ${batches.map(b => `
              <tr>
                <td><b>#${b.id}</b></td>
                <td><code>${b.filename}</code></td>
                <td>${formatCount(b.total_rows)}</td>
                <td style="color:#34d399;font-weight:600;">${formatCount(b.accepted_rows)}</td>
                <td style="color:${Number(b.rejected_rows) > 0 ? '#f87171' : 'var(--text-dim)'};">${formatCount(b.rejected_rows)}</td>
                <td>${formatCount(b.duplicate_rows)}</td>
                <td><span class="batch-status batch-status-${String(b.status || 'unavailable').toLowerCase().replace(/[^a-z0-9_-]/g, '')}">${String(b.status || 'Unavailable').replace(/_/g, ' ')}</span></td>
                <td><small style="font-family:monospace;">${b.file_hash.slice(0, 16)}...</small></td>
                <td>${formatImportTimestamp(b.created_at)}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
    } catch (e) {
      container.innerHTML = `<div class="table-empty" style="color:#f87171;">Error loading batches: ${e.message}</div>`;
    }
  }

  function formatImportTimestamp(value) {
    if (!value) return '—';
    // API timestamps are UTC. Treat legacy offset-less values as UTC too,
    // then display consistently in the application's India market timezone.
    const timestamp = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value) ? value : `${value}Z`;
    const parsed = new Date(timestamp);
    if (!Number.isFinite(parsed.getTime())) return '—';
    return `${new Intl.DateTimeFormat('en-IN', {
      timeZone: 'Asia/Kolkata', day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true
    }).format(parsed)} IST`;
  }

  /* --------------------------------------------------------------------------
     6. Stylesheet Injection (Claymorphism + Glassmorphism)
     -------------------------------------------------------------------------- */
  function injectStyles() {
    if (document.getElementById('auroraPipelineStyles')) return;
    const style = document.createElement('style');
    style.id = 'auroraPipelineStyles';
    style.textContent = `
      /* Pipeline Ingestion Button in Top Header */
      .aurora-pipeline-btn {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 16px;
        border-radius: 14px;
        background: linear-gradient(135deg, rgba(240, 185, 11, 0.22) 0%, rgba(212, 160, 23, 0.08) 100%);
        border: 1px solid rgba(240, 185, 11, 0.45);
        color: #ffd700;
        font-family: 'Inter', sans-serif;
        font-size: 12.5px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.25s ease;
        box-shadow: 0 4px 14px rgba(240, 185, 11, 0.15);
      }
      .aurora-pipeline-btn:hover {
        background: linear-gradient(135deg, rgba(240, 185, 11, 0.35) 0%, rgba(212, 160, 23, 0.18) 100%);
        border-color: rgba(240, 185, 11, 0.7);
        color: #ffffff;
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(240, 185, 11, 0.25);
      }

      /* Modal Overlay */
      .aurora-modal-overlay {
        position: fixed;
        inset: 0;
        z-index: 99999;
        background: rgba(4, 7, 20, 0.78);
        backdrop-filter: blur(12px);
        display: none;
        align-items: center;
        justify-content: center;
        padding: 24px;
        opacity: 0;
        transition: opacity 0.3s ease;
      }
      .aurora-modal-overlay.active {
        display: flex;
        opacity: 1;
      }

      /* Modal Box (Claymorphism + Glassmorphism) */
      .aurora-modal-container {
        width: 100%;
        max-width: 860px;
        max-height: 90vh;
        background: linear-gradient(145deg, rgba(16, 24, 56, 0.94) 0%, rgba(10, 15, 38, 0.96) 100%);
        border: 1px solid rgba(240, 185, 11, 0.3);
        border-radius: 24px;
        box-shadow:
          0 24px 60px rgba(0, 0, 0, 0.75),
          inset 1px 1px 2px rgba(255, 255, 255, 0.15),
          inset -2px -2px 4px rgba(0, 0, 0, 0.4);
        display: flex;
        flex-direction: column;
        overflow: hidden;
        animation: auroraModalPop 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      }
      @keyframes auroraModalPop {
        from { transform: scale(0.95) translateY(12px); opacity: 0; }
        to { transform: scale(1) translateY(0); opacity: 1; }
      }

      /* Head */
      .aurora-modal-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 22px 28px;
        border-bottom: 1px solid rgba(240, 185, 11, 0.15);
      }
      .modal-title-group {
        display: flex;
        align-items: center;
        gap: 14px;
      }
      .modal-icon-badge {
        width: 44px;
        height: 44px;
        border-radius: 12px;
        background: rgba(240, 185, 11, 0.15);
        border: 1px solid rgba(240, 185, 11, 0.35);
        color: var(--gold-primary, #f0b90b);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
      }
      .modal-title-group h3 {
        font-family: 'Orbitron', sans-serif;
        font-size: 18px;
        font-weight: 700;
        color: #ffffff;
        margin: 0;
      }
      .modal-title-group p {
        font-size: 12.5px;
        color: #94a3b8;
        margin: 3px 0 0;
      }
      .aurora-modal-close {
        background: none;
        border: none;
        color: #94a3b8;
        font-size: 28px;
        cursor: pointer;
        transition: color 0.2s;
        line-height: 1;
      }
      .aurora-modal-close:hover { color: #ffffff; }

      /* Tabs */
      .aurora-modal-tabs {
        display: flex;
        gap: 8px;
        padding: 12px 28px 0;
        background: rgba(8, 12, 32, 0.5);
        border-bottom: 1px solid rgba(240, 185, 11, 0.12);
      }
      .tab-btn {
        background: none;
        border: none;
        color: #94a3b8;
        padding: 10px 16px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 8px;
        border-bottom: 2px solid transparent;
        transition: all 0.2s;
      }
      .tab-btn:hover { color: #ffffff; }
      .tab-btn.active {
        color: #ffd700;
        border-bottom-color: #f0b90b;
      }

      /* Body & Tabs */
      .aurora-modal-body {
        padding: 24px 28px;
        overflow-y: auto;
        flex: 1;
      }
      .tab-content { display: none; }
      .tab-content.active { display: block; }

      /* Upload Dropzone */
      .upload-dropzone {
        border: 2px dashed rgba(240, 185, 11, 0.35);
        border-radius: 18px;
        background: rgba(10, 15, 40, 0.45);
        padding: 32px 20px;
        text-align: center;
        cursor: pointer;
        transition: all 0.25s ease;
      }
      .upload-dropzone:hover, .upload-dropzone.dragover {
        border-color: #f0b90b;
        background: rgba(240, 185, 11, 0.06);
      }
      .drop-icon {
        font-size: 38px;
        color: #f0b90b;
        margin-bottom: 12px;
      }
      .upload-dropzone h4 {
        color: #ffffff;
        font-size: 16px;
        margin-bottom: 6px;
      }
      .upload-dropzone p {
        color: #94a3b8;
        font-size: 13px;
        margin-bottom: 16px;
      }
      .browse-btn {
        background: rgba(240, 185, 11, 0.15);
        border: 1px solid rgba(240, 185, 11, 0.4);
        color: #ffd700;
        padding: 8px 18px;
        border-radius: 10px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
      }
      .browse-btn:hover {
        background: #f0b90b;
        color: #060919;
      }
      .selected-file-label {
        margin-top: 12px;
        font-size: 13px;
        color: #34d399;
        font-weight: 600;
      }

      /* 1-Click Sample Actions */
      .sample-actions-row {
        display: flex;
        align-items: center;
        gap: 10px;
        flex-wrap: wrap;
        margin: 16px 0;
        padding: 12px 16px;
        border-radius: 14px;
        background: rgba(16, 24, 56, 0.5);
        border: 1px solid rgba(240, 185, 11, 0.12);
      }
      .sample-label {
        font-size: 12px;
        color: #94a3b8;
        font-weight: 600;
      }
      .sample-btn {
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.14);
        color: #e2e8f0;
        padding: 6px 14px;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 500;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        transition: all 0.2s;
      }
      .sample-btn:hover {
        background: rgba(255, 255, 255, 0.12);
        color: #ffffff;
      }

      /* Options Grid */
      .upload-options-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
        margin-bottom: 20px;
      }
      .upload-options-grid label {
        display: block;
        font-size: 12px;
        font-weight: 600;
        color: #cbd5e1;
        margin-bottom: 6px;
      }
      .upload-options-grid input, .upload-options-grid select {
        width: 100%;
        padding: 9px 14px;
        border-radius: 10px;
        background: rgba(6, 9, 25, 0.7);
        border: 1px solid rgba(240, 185, 11, 0.2);
        color: #ffffff;
        font-size: 13px;
        font-family: inherit;
        outline: none;
      }
      .upload-options-grid input:focus, .upload-options-grid select:focus {
        border-color: #f0b90b;
      }

      /* Submit Button */
      .submit-action-row {
        text-align: right;
      }
      .submit-upload-btn {
        background: linear-gradient(135deg, #f0b90b 0%, #d4a017 100%);
        color: #060919;
        border: none;
        padding: 11px 26px;
        border-radius: 12px;
        font-size: 14px;
        font-weight: 700;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        box-shadow: 0 4px 18px rgba(240, 185, 11, 0.35);
        transition: all 0.2s;
      }
      .submit-upload-btn:hover:not(:disabled) {
        transform: translateY(-2px);
        box-shadow: 0 6px 24px rgba(240, 185, 11, 0.5);
      }
      .submit-upload-btn:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }

      /* Feedback Boxes */
      .feedback-box {
        margin-top: 20px;
        padding: 16px 20px;
        border-radius: 14px;
        font-size: 13.5px;
        line-height: 1.5;
      }
      .feedback-box.loading {
        background: rgba(213, 179, 99, 0.08);
        border: 1px solid rgba(220, 190, 116, 0.26);
        color: #ead8a4;
      }
      .pipeline-progress-head { display:flex; align-items:flex-start; gap:9px; }
      .pipeline-progress-head b { color:#fff1bc; font-weight:600; overflow-wrap:anywhere; }
      .pipeline-progress-track { height:3px; overflow:hidden; margin:12px 0 6px; border-radius:9px; background:rgba(255,255,255,.11); }
      .pipeline-progress-track span { display:block; width:40%; height:100%; border-radius:inherit; background:linear-gradient(90deg,transparent,#f1d378,transparent); animation:auroraPipelineIndeterminate 1.3s ease-in-out infinite; }
      .pipeline-progress small { color:rgba(231,218,182,.7); }
      @keyframes auroraPipelineIndeterminate { from { transform:translateX(-160%); } to { transform:translateX(310%); } }
      @media (prefers-reduced-motion: reduce) { .pipeline-progress-track span { animation:none; transform:translateX(75%); } }
      .feedback-box.success {
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.4);
        color: #6ee7b7;
      }
      .feedback-box.warning {
        background: rgba(245, 158, 11, 0.12);
        border: 1px solid rgba(245, 158, 11, 0.4);
        color: #fcd34d;
      }
      .feedback-box.error {
        background: rgba(239, 68, 68, 0.12);
        border: 1px solid rgba(239, 68, 68, 0.4);
        color: #fca5a5;
      }
      .feedback-head {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 15px;
        margin-bottom: 6px;
      }
      .stat-pills-row {
        display: flex;
        gap: 10px;
        margin-top: 10px;
        flex-wrap: wrap;
      }
      .pill-stat {
        padding: 4px 10px;
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.08);
        font-size: 12px;
        color: #cbd5e1;
      }
      .pill-stat.green b { color: #34d399; }
      .pill-stat.red b { color: #f87171; }
      .pill-stat.amber b { color: #fbbf24; }

      /* Error Diagnostics */
      .error-details-section {
        margin-top: 18px;
        padding: 16px;
        border-radius: 14px;
        background: rgba(239, 68, 68, 0.05);
        border: 1px solid rgba(239, 68, 68, 0.25);
      }
      .error-details-section h4 {
        margin: 0 0 10px;
        font-size: 13.5px;
        color: #fca5a5;
      }

      /* Inspection Tables */
      .data-table-scroll {
        max-height: 420px;
        overflow: auto;
        border-radius: 12px;
        border: 1px solid rgba(240, 185, 11, 0.15);
        background: rgba(6, 9, 25, 0.6);
      }
      #batchesTableContainer .aurora-pipeline-table { min-width: 1120px; }
      .aurora-pipeline-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 12.5px;
        text-align: left;
      }
      .aurora-pipeline-table th {
        background: rgba(16, 24, 56, 0.9);
        color: #f0b90b;
        padding: 10px 14px;
        font-weight: 600;
        position: sticky;
        top: 0;
        z-index: 2;
        border-bottom: 1px solid rgba(240, 185, 11, 0.2);
        white-space: nowrap;
      }
      .aurora-pipeline-table td {
        padding: 10px 14px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        color: #e2e8f0;
        white-space: nowrap;
      }
      .aurora-pipeline-table tr:hover {
        background: rgba(240, 185, 11, 0.04);
      }
      .batch-status {
        display: inline-flex;
        align-items: center;
        border: 1px solid rgba(201, 166, 80, 0.28);
        border-radius: 999px;
        padding: 3px 9px;
        color: #e7cc83;
        background: rgba(201, 166, 80, 0.09);
        font-size: 11px;
        font-weight: 650;
        text-transform: capitalize;
      }
      .batch-status-failed { color: #ff9a9a; border-color: rgba(248, 113, 113, 0.3); background: rgba(248, 113, 113, 0.09); }
      .batch-status-partial_success { color: #f2c66d; border-color: rgba(242, 198, 109, 0.3); background: rgba(242, 198, 109, 0.09); }
      .gold-badge {
        color: #ffd700;
        background: rgba(240, 185, 11, 0.12);
        padding: 3px 8px;
        border-radius: 6px;
        border: 1px solid rgba(240, 185, 11, 0.3);
      }
      .source-tag {
        font-size: 11px;
        padding: 2px 6px;
        border-radius: 4px;
      }
      .source-tag.synth {
        background: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
      }
      .source-tag.real {
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
      }
      .status-pill.active {
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 11px;
      }

      .tab-filter-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 14px;
      }
      .filter-group {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 12.5px;
        color: #94a3b8;
      }
      .filter-group select {
        padding: 6px 12px;
        border-radius: 8px;
        background: rgba(6, 9, 25, 0.7);
        border: 1px solid rgba(240, 185, 11, 0.2);
        color: #ffffff;
      }
      .refresh-btn {
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.15);
        color: #cbd5e1;
        padding: 6px 14px;
        border-radius: 8px;
        font-size: 12px;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 6px;
      }
      .refresh-btn:hover { background: rgba(255, 255, 255, 0.12); color: #ffffff; }

      .table-loading, .table-empty {
        padding: 40px 20px;
        text-align: center;
        color: #94a3b8;
        font-size: 13.5px;
      }

      /* Warm AURORA treatment for the existing market-data pipeline modal. */
      #auroraIngestModal .aurora-modal-container {
        color: #eee8dc;
        background: linear-gradient(145deg, rgba(26, 23, 17, 0.97), rgba(10, 10, 9, 0.98));
        border-color: rgba(202, 169, 91, 0.28);
        box-shadow: 0 28px 80px rgba(0, 0, 0, 0.78), inset 0 1px rgba(255, 244, 211, 0.08);
        backdrop-filter: blur(20px);
      }
      #auroraIngestModal .aurora-modal-head,
      #auroraIngestModal .aurora-modal-tabs {
        border-color: rgba(202, 169, 91, 0.16);
      }
      #auroraIngestModal .aurora-modal-tabs {
        background: rgba(8, 8, 7, 0.48);
      }
      #auroraIngestModal .modal-icon-badge {
        color: #e6c77d;
        background: linear-gradient(145deg, rgba(210, 173, 91, 0.18), rgba(80, 58, 21, 0.18));
        border-color: rgba(210, 173, 91, 0.34);
      }
      #auroraIngestModal .modal-title-group h3 { color: #f5f0e6; }
      #auroraIngestModal .modal-title-group p,
      #auroraIngestModal .tab-btn { color: #aaa395; }
      #auroraIngestModal .tab-btn:hover,
      #auroraIngestModal .aurora-modal-close:hover { color: #f6e3b0; }
      #auroraIngestModal .tab-btn.active {
        color: #e8c977;
        border-bottom-color: #c9a650;
      }
      #auroraIngestModal .aurora-modal-body { color: #e8e1d3; }
      #auroraIngestModal .upload-dropzone,
      #auroraIngestModal .sample-actions-row,
      #auroraIngestModal .data-table-scroll {
        background: rgba(15, 14, 12, 0.68);
        border-color: rgba(202, 169, 91, 0.2);
        box-shadow: inset 0 1px rgba(255, 244, 211, 0.035);
      }
      #auroraIngestModal .upload-dropzone:hover,
      #auroraIngestModal .upload-dropzone.dragover {
        background: rgba(202, 169, 91, 0.075);
        border-color: rgba(222, 190, 119, 0.7);
      }
      #auroraIngestModal .upload-dropzone h4 { color: #f5f0e6; }
      #auroraIngestModal .upload-dropzone p,
      #auroraIngestModal .sample-label,
      #auroraIngestModal .table-loading,
      #auroraIngestModal .table-empty { color: #b2aa9a; }
      #auroraIngestModal .drop-icon { color: #d8b765; }
      #auroraIngestModal .sample-btn,
      #auroraIngestModal .refresh-btn {
        color: #e6dfd1;
        background: rgba(255, 255, 255, 0.035);
        border-color: rgba(220, 208, 181, 0.16);
      }
      #auroraIngestModal .sample-btn:hover,
      #auroraIngestModal .refresh-btn:hover {
        color: #f8e8bd;
        background: rgba(202, 169, 91, 0.1);
        border-color: rgba(202, 169, 91, 0.32);
      }
      #auroraIngestModal .upload-options-grid label,
      #auroraIngestModal .filter-group { color: #c4bcad; }
      #auroraIngestModal .upload-options-grid input,
      #auroraIngestModal .upload-options-grid select,
      #auroraIngestModal .filter-group select {
        color: #f0eade;
        background: rgba(9, 9, 8, 0.76);
        border-color: rgba(202, 169, 91, 0.22);
      }
      #auroraIngestModal .upload-options-grid input:focus,
      #auroraIngestModal .upload-options-grid select:focus,
      #auroraIngestModal .filter-group select:focus {
        border-color: #c9a650;
        box-shadow: 0 0 0 3px rgba(201, 166, 80, 0.12);
      }
      #auroraIngestModal .submit-upload-btn {
        color: #17130b;
        background: linear-gradient(110deg, #ead18a, #c9a650 58%, #a98234);
        box-shadow: 0 6px 20px rgba(167, 128, 45, 0.22);
      }
      #auroraIngestModal .submit-upload-btn:hover:not(:disabled) {
        box-shadow: 0 8px 24px rgba(167, 128, 45, 0.32);
      }
      #auroraIngestModal .aurora-pipeline-table th {
        color: #dfc77f;
        background: rgba(31, 27, 19, 0.97);
        border-bottom-color: rgba(202, 169, 91, 0.22);
      }
      #auroraIngestModal .aurora-pipeline-table td {
        color: #e2dccf;
        border-bottom-color: rgba(225, 213, 184, 0.075);
      }
      #auroraIngestModal .aurora-pipeline-table tbody tr:hover {
        background: rgba(202, 169, 91, 0.055);
      }
      #auroraIngestModal .gold-badge {
        color: #e6c66d;
        background: rgba(167, 128, 45, 0.13);
        border-color: rgba(202, 169, 91, 0.28);
      }
      @media (prefers-reduced-transparency: reduce) {
        #auroraIngestModal .aurora-modal-container { backdrop-filter: none; background: #11100d; }
        #auroraIngestModal .aurora-modal-tabs,
        #auroraIngestModal .upload-dropzone,
        #auroraIngestModal .sample-actions-row,
        #auroraIngestModal .data-table-scroll { background: #15130f; }
      }
    `;
    document.head.appendChild(style);
  }

  /* --------------------------------------------------------------------------
     4. Phase 2 Relative-Value Intelligence Engine Frontend Integration
     -------------------------------------------------------------------------- */
  function initPhase2AnalyticsSync() {
    setupRadarForecastValidation();
    if (document.getElementById('radarChartCanvas')) {
      setupOpportunityRadarSync();
    }
    if (document.getElementById('eventSelector')) {
      setupMarketDetectiveSync();
    }
  }

  function setupRadarForecastValidation() {
    const button = document.getElementById('runRadarForecastValidation');
    if (!button || button.dataset.bound === 'true') return;
    button.dataset.bound = 'true';
    const status = document.getElementById('radarForecastValidationStatus');
    const results = document.getElementById('radarForecastValidationResults');
    const rows = document.getElementById('radarForecastValidationRows');
    button.addEventListener('click', async () => {
      const symbol = document.getElementById('radarForecastSymbol')?.value || 'GOLDM';
      const horizon = Math.max(2, Math.min(20, Number(document.getElementById('radarForecastHorizon')?.value) || 5));
      const folds = Math.max(10, Math.min(120, Number(document.getElementById('radarForecastFolds')?.value) || 30));
      status.textContent = 'Running chronological multi-step validation…';
      results.style.display = 'none';
      button.disabled = true;
      try {
        const query = new URLSearchParams({symbol, horizon: String(horizon), max_folds: String(folds)});
        const response = await fetch(`${API_BASE}/api/research/forecast-horizon-validation?${query.toString()}`, {mode: 'cors'});
        if (!response.ok) throw new Error('Research API returned HTTP ' + response.status);
        const data = await response.json();
        if (data.status !== 'evaluated') {
          status.textContent = (data.message || 'Insufficient eligible history.') + ' Eligible observations: ' + (data.observations ?? '—') + '; minimum required: ' + (data.minimum_required ?? '—') + '.';
          return;
        }
        const modelRows = [
          ['Naive · last value', data.models?.naive_last_value],
          ['Rolling mean · 5 observations', data.models?.rolling_mean_5],
          ['Linear trend', data.models?.linear_trend]
        ];
        rows.replaceChildren();
        modelRows.forEach(([label, metrics]) => {
          const tr = document.createElement('tr');
          [label, metrics?.mae, metrics?.rmse, metrics?.mape_pct == null ? '—' : metrics.mape_pct + '%'].forEach(value => {
            const td = document.createElement('td');
            td.textContent = value == null ? '—' : String(value);
            tr.appendChild(td);
          });
          if (label.toLowerCase().replaceAll(' · ', '_').replaceAll(' ', '_') === data.selection?.lowest_mae_model) tr.style.fontWeight = '700';
          rows.appendChild(tr);
        });
        status.textContent = symbol + ' · ' + data.horizon_observations + '-observation horizon · ' + data.test_folds + ' folds · target dates ' + (data.first_target_date || '—') + ' to ' + (data.last_target_date || '—') + '. Lowest MAE baseline: ' + String(data.selection?.lowest_mae_model || 'unavailable').replaceAll('_', ' ') + '. ' + data.caveat;
        results.style.display = 'block';
      } catch (error) {
        status.textContent = 'Forecast validation unavailable: ' + error.message + '. Confirm the local AURORA API is running.';
      } finally {
        button.disabled = false;
      }
    });
  }

  async function setupOpportunityRadarSync() {
    const windowFilter = document.getElementById('dateRangeFilter');
    const selectedPair = await loadLiveRadarData(Number(windowFilter?.value) || 30);
    if (selectedPair) await loadLiveDistributionData(selectedPair);
    else clearDistributionSampleData();
    loadRadarPriceSnapshots();
    loadPairCoverageDiagnostics();

    const coverageBtn = document.getElementById('refreshPairCoverageBtn');
    if (coverageBtn) coverageBtn.addEventListener('click', loadPairCoverageDiagnostics);

    const refreshBtn = document.getElementById('refresh-radar-btn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', async () => {
        try {
          const selectedPair = await loadLiveRadarData(Number(windowFilter?.value) || 30);
          if (selectedPair) loadLiveDistributionData(selectedPair);
          else clearDistributionSampleData();
          loadRadarPriceSnapshots();
          loadPairCoverageDiagnostics();
        } finally {
          refreshBtn.querySelector('i')?.classList.remove('fa-spin');
        }
      });
    }

    if (windowFilter) {
      windowFilter.addEventListener('change', async () => {
        const selectedPair = await loadLiveRadarData(Number(windowFilter.value) || 30);
        if (selectedPair) loadLiveDistributionData(selectedPair);
        else clearDistributionSampleData();
      });
    }
  }

  function coverageEscape(value) {
    return String(value ?? '—').replace(/[&<>"']/g, char => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[char]);
  }

  function coverageDate(value) {
    if (!value) return '—';
    const dateText = String(value).slice(0, 10);
    return /^\d{4}-\d{2}-\d{2}$/.test(dateText) ? dateText : '—';
  }

  async function loadPairCoverageDiagnostics() {
    const meta = document.getElementById('pairCoverageMeta');
    const rows = document.getElementById('pairCoverageRows');
    const footnote = document.getElementById('pairCoverageFootnote');
    if (!meta || !rows) return;
    meta.innerHTML = '<span class="pair-coverage-chip">Refreshing coverage…</span>';
    try {
      const response = await fetch(`${API_BASE}/api/analytics/pair-coverage`, { mode: 'cors' });
      if (!response.ok) throw new Error(`Coverage endpoint returned ${response.status}`);
      const payload = await response.json();
      const data = payload?.success ? payload.data : null;
      if (!data || !Array.isArray(data.pairs)) throw new Error('Unexpected pair-coverage response.');
      const pairs = data.pairs;
      const latestDate = coverageDate(data.dataset_latest_trade_date);
      const currentMatches = pairs.filter(pair => pair.freshness === 'matches-latest-dataset-date').length;
      const historicalMatches = pairs.filter(pair => pair.freshness === 'historical-only').length;
      const unavailable = pairs.filter(pair => pair.status === 'no-shared-expiry-history').length;
      meta.innerHTML = [
        `<span class="pair-coverage-chip">Dataset latest: ${coverageEscape(latestDate)}</span>`,
        `<span class="pair-coverage-chip">Pairs matching latest date: ${currentMatches}/${pairs.length}</span>`,
        `<span class="pair-coverage-chip">Historical-only: ${historicalMatches}</span>`,
        `<span class="pair-coverage-chip">No shared expiry history: ${unavailable}</span>`,
        `<span class="pair-coverage-chip">Mode: ${coverageEscape(data.data_mode || 'stored history')}</span>`
      ].join('');
      rows.innerHTML = pairs.map(pair => {
        const freshness = pair.freshness || 'unavailable';
        const statusClass = freshness === 'matches-latest-dataset-date' ? 'match'
          : freshness === 'historical-only' || freshness === 'future-dated' ? 'historical' : 'unavailable';
        const statusLabel = freshness === 'matches-latest-dataset-date' ? 'LATEST DATA DATE'
          : freshness === 'historical-only' ? 'HISTORICAL ONLY'
          : freshness === 'future-dated' ? 'FUTURE-DATED' : 'NO MATCH';
        const age = pair.days_since_shared_observation == null ? '' : ` · ${coverageEscape(pair.days_since_shared_observation)}d old`;
        const detail = pair.status === 'no-shared-expiry-history'
          ? 'No exact same-date + same-expiry match'
          : `Shared observation${age}`;
        return `<tr>
          <td><strong>${coverageEscape(pair.pair)}</strong><div style="color:#9ca9bd;font-size:.69rem;margin-top:4px;">${coverageEscape(detail)}</div></td>
          <td>${coverageEscape(coverageDate(pair.latest_leg_a_date))}</td>
          <td>${coverageEscape(coverageDate(pair.latest_leg_b_date))}</td>
          <td>${coverageEscape(coverageDate(pair.latest_shared_trade_date))}</td>
          <td>${coverageEscape(coverageDate(pair.latest_shared_expiry))}</td>
          <td>${coverageEscape(pair.synchronized_observation_count ?? 0)}</td>
          <td><span class="coverage-status ${statusClass}">${statusLabel}</span></td>
        </tr>`;
      }).join('');
      if (footnote) footnote.textContent = `Exact trade-date + expiry matching only. Latest eligible dataset date: ${latestDate}. Data mode: ${data.data_mode || 'stored history'}; not provider-verified live market data.`;
    } catch (error) {
      meta.innerHTML = '<span class="pair-coverage-chip">Diagnostics unavailable</span>';
      rows.innerHTML = `<tr><td colspan="7" class="coverage-empty">${coverageEscape(error?.message || 'Unable to load pair coverage.')} Ensure the backend is running and updated with the pair-coverage endpoint.</td></tr>`;
      if (footnote) footnote.textContent = 'Pair coverage could not be loaded. Other dashboard panels remain available.';
    }
  }

  async function loadRadarPriceSnapshots() {
    const requestId = ++priceSnapshotRequestId;
    const items = document.querySelectorAll('.ticker-item[data-market-symbol]');
    try {
      const response = await fetch(`${API_BASE}/api/market/prices?limit=1000`);
      if (requestId !== priceSnapshotRequestId) return;
      if (!response.ok) throw new Error(`Market prices unavailable (${response.status})`);
      const json = await response.json();
      const rows = json?.success && Array.isArray(json?.data?.items) ? json.data.items : [];
      const latest = new Map();
      rows.forEach(row => {
        const current = latest.get(row.symbol);
        if (!current || String(row.trade_date) > String(current.trade_date) ||
            (row.trade_date === current.trade_date && String(row.expiry_date) < String(current.expiry_date))) latest.set(row.symbol, row);
      });
      items.forEach(item => {
        const row = latest.get(item.dataset.marketSymbol);
        const name = item.querySelector('.ticker-name');
        const price = item.querySelector('.ticker-price');
        if (!row) {
          if (name) name.textContent = `${item.dataset.marketSymbol} · latest close:`;
          if (price) price.textContent = '—';
          return;
        }
        const source = row.is_synthetic ? 'synthetic' : row.data_source === 'csv_upload' ? 'user CSV' : row.data_source || 'unverified';
        if (name) name.textContent = `${row.symbol} · ${row.trade_date} · ${source}:`;
        if (price) price.textContent = `₹${Number(row.close_price).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
      });
    } catch (error) {
      if (requestId !== priceSnapshotRequestId) return;
      console.warn('AURORA: Market snapshot unavailable:', error);
      items.forEach(item => {
        const name = item.querySelector('.ticker-name');
        const price = item.querySelector('.ticker-price');
        if (name) name.textContent = `${item.dataset.marketSymbol} · backend unavailable:`;
        if (price) price.textContent = '—';
      });
    }
  }

  async function loadLiveRadarData(windowDays = 30) {
    const requestId = ++radarRequestId;
    clearRadarSampleData('Loading backend signal data…');
    try {
      const [statusRes, res] = await Promise.all([
        fetch(`${API_BASE}/api/market/status`),
        fetch(`${API_BASE}/api/analytics/radar?window=${encodeURIComponent(windowDays)}`)
      ]);
      if (requestId !== radarRequestId) return null;
      if (!statusRes.ok) {
        clearRadarSampleData('Market status unavailable');
        updateRadarFreshnessIndicator(null, 'Market status endpoint returned an error.');
        return null;
      }
      const statusJson = await statusRes.json();
      if (requestId !== radarRequestId) return null;
      if (!statusJson.success || !statusJson.data) {
        clearRadarSampleData('Market status unavailable');
        updateRadarFreshnessIndicator(null, 'Market status data unavailable.');
        return null;
      }
      if (['test_data', 'demo_synthetic'].includes(statusJson.data.data_mode)) {
        clearRadarSampleData(statusJson.data.data_mode === 'test_data'
          ? 'Test-only data excluded from analysis'
          : 'Synthetic demo data excluded from analysis');
        updateRadarFreshnessIndicator(statusJson.data, statusJson.data.data_mode === 'test_data'
          ? 'Test data excluded from market analysis.'
          : 'Synthetic demo data excluded from market analysis.');
        return null;
      }
      if (!res.ok) {
        clearRadarSampleData('Backend data unavailable');
        updateRadarFreshnessIndicator(statusJson.data, 'Backend relative-value analytics unavailable.');
        return null;
      }
      const json = await res.json();
      if (requestId !== radarRequestId) return null;
      updateRadarFreshnessIndicator(statusJson.data);
      const pairs = json.success && json.data && Array.isArray(json.data.pairs) ? json.data.pairs : [];
      const usablePairs = pairs.filter(p => p && p.spread !== null && p.spread !== undefined && Number.isFinite(Number(p.spread)));
      ensureRadarSignalCards(pairs);
      if (!usablePairs.length) {
        clearRadarSampleData('No synchronized backend snapshots');
      } else {
        clearRadarSampleData('');
      }

      const signalCount = document.querySelector('.signals-section .clay-chip');
      const unavailableCount = Math.max(0, pairs.length - usablePairs.length);
      if (signalCount) signalCount.textContent = `${usablePairs.length}/${pairs.length} pairs have synchronized snapshots · ${unavailableCount} unavailable`;
      renderRadarFunnel(pairs);
      const pairMap = {};
      pairs.forEach(p => {
        pairMap[p.pair] = p;
        const inv = p.pair.split('-').reverse().join('-');
        pairMap[inv] = orientRadarPair(p, inv);
      });
      radarPairMap = pairMap;
      window.AURORA_RADAR_PAIRS = radarPairMap;

      // Update Radar Polar Chart
      if (typeof Chart !== 'undefined') {
        const radarChart = Chart.getChart('radarChartCanvas');
        if (radarChart && radarChart.data && radarChart.data.labels) {
          const newData = radarChart.data.labels.map(lbl => {
            const p = pairMap[lbl];
            return p && p.spread != null && p.deviation_intensity != null && Number.isFinite(Number(p.deviation_intensity)) ? Math.round(Number(p.deviation_intensity)) : null;
          });
          radarChart.data.datasets[0].data = newData;
          if (radarChart.data.datasets[1]) radarChart.data.datasets[1].data = radarChart.data.labels.map(lbl => pairMap[lbl]?.historical_norm != null ? Number(pairMap[lbl].historical_norm) : null);
          if (radarChart.data.datasets[2]) radarChart.data.datasets[2].data = radarChart.data.labels.map(lbl => pairMap[lbl]?.friction_boundary != null ? Number(pairMap[lbl].friction_boundary) : null);
          radarChart.update();
        }
      }

      // Update Top Anomaly in Hero Stat Claybox
      const sorted = [...usablePairs].sort((a, b) => {
        const scoreA = a.opportunity_score == null ? -Infinity : Number(a.opportunity_score);
        const scoreB = b.opportunity_score == null ? -Infinity : Number(b.opportunity_score);
        return scoreB - scoreA;
      });
      const top = sorted[0];
      if (top) renderRadarPair(top);
      window.AURORA_SELECT_RADAR_PAIR = selectRadarPairFromUi;
      window.AURORA_LOAD_DISTRIBUTION = loadLiveDistributionData;

      // Update Pairwise Spread Matrix Table
      const matrixTable = document.querySelector('.matrix-table');
      if (matrixTable) {
        const contracts = ['GOLDM', 'GOLDTEN', 'GOLDGUINEA', 'GOLDPETAL'];
        const rows = matrixTable.querySelectorAll('tbody tr');
        rows.forEach((tr, rIdx) => {
          const rowContract = contracts[rIdx];
          const cells = tr.querySelectorAll('td');
          cells.forEach((td, cIdx) => {
            const colContract = contracts[cIdx];
            if (rowContract === colContract) return;

            const pairKey = `${rowContract}-${colContract}`;
            const p = pairMap[pairKey];
            if (p && p.spread !== null && p.spread !== undefined) {
              td.setAttribute('onclick', `selectPairFromMatrix('${pairKey}')`);
              // pairMap is keyed by the requested orientation and reverse entries are
              // already normalized by orientRadarPair(). Do not invert them a second time.
              const cellSpread = Number(p.spread).toFixed(2);
              const cellZ = p.z_score !== null && p.z_score !== undefined
                ? Number(p.z_score).toFixed(2)
                : 'N/A';
              td.innerHTML = `${cellSpread > 0 ? '+' : ''}${cellSpread}<br><span style="font-size:0.6rem;">${cellZ}σ</span>`;
              td.title = `${pairKey} · ${p.trade_date} · expiry ${p.expiry_date} · Spread ₹${cellSpread} · Z ${cellZ}σ · ${p.classification}`;
              td.classList.remove('cell-normal', 'cell-high', 'cell-critical', 'cell-unavailable');
              td.classList.add(p.classification === 'Investigate' ? 'cell-critical' : ['Cost-Blocked', 'Expiry-Risk'].includes(p.classification) ? 'cell-high' : 'cell-normal');
            } else {
              td.removeAttribute('onclick');
              td.title = p?.reason ? `Unavailable: ${p.reason}` : 'No synchronized same-date, same-expiry snapshot is available.';
              td.classList.remove('cell-normal', 'cell-high', 'cell-critical');
              td.classList.add('cell-unavailable');
            }
          });
        });
      }

      updateRadarSignalCards(pairs);
      if (typeof window.applySignalFilters === 'function') window.applySignalFilters();

      // Cards and hero are rendered once by updateRadarSignalCards/renderRadarPair.
      // Do not rewrite a reversed card with the backend's canonical pair values here.

      ensureLiveBadge(usablePairs.length, pairs.length);
      return top ? top.pair : null;
    } catch (e) {
      if (requestId !== radarRequestId) return null;
      console.warn('AURORA: Error syncing live radar data:', e);
      clearRadarSampleData('Backend data unavailable');
      updateRadarFreshnessIndicator(null, 'Network error / backend unavailable.');
      return null;
    }
  }

  function clearRadarSampleData(message) {
    // Invalidate any in-flight histogram request so a late response cannot
    // repopulate the page after the selected Radar snapshot becomes empty.
    distributionRequestId += 1;
    clearDistributionSampleData();
    radarPairMap = {};
    window.AURORA_RADAR_PAIRS = radarPairMap;
    window.AURORA_SELECT_RADAR_PAIR = selectRadarPairFromUi;
    window.AURORA_SYNC_RADAR_FILTER_STATE = syncRadarSelectionFilterState;
    selectedRadarPairKey = null;
    syncRadarSelectionFilterState();
    // Keep the complete canonical pair grid visible even when the first
    // request fails or the API has no eligible observations.
    ensureRadarSignalCards(RADAR_CANONICAL_PAIRS);
    renderRadarFunnel([]);
    if (typeof Chart !== 'undefined') {
      const radarChart = Chart.getChart('radarChartCanvas');
      if (radarChart) {
        radarChart.data.datasets.forEach(dataset => { dataset.data = radarChart.data.labels.map(() => null); });
        radarChart.update();
      }
      document.querySelectorAll('.signal-card canvas').forEach(canvas => {
        const chart = Chart.getChart(canvas);
        if (!chart) return;
        chart.data.labels = [];
        chart.data.datasets.forEach(dataset => { dataset.data = []; });
        chart.update();
      });
    }
    const title = document.querySelector('.headline-pair-title');
    if (title) title.textContent = message || 'No backend signal data';
    const badge = document.getElementById('radarPairStatusBadge');
    if (badge) badge.textContent = message === 'Loading backend signal data…' ? 'Loading' : message?.toLowerCase().includes('unavailable') ? 'Unavailable' : message?.toLowerCase().includes('excluded') ? 'Excluded' : 'No data';
    const liveBadge = document.querySelector('.live-radar-badge');
    if (liveBadge) liveBadge.textContent = message === 'Loading backend signal data…' ? 'Loading backend data' : message?.toLowerCase().includes('unavailable') ? 'Backend data unavailable' : message?.toLowerCase().includes('excluded') ? 'Test-only data excluded' : 'No backend pair data';
    const classification = document.getElementById('radarClassification');
    if (classification) classification.textContent = message || 'No signal';
    const snapshotDate = document.getElementById('radarSnapshotDate');
    if (snapshotDate) snapshotDate.textContent = 'As of —';
    const signalCount = document.querySelector('.signals-section .clay-chip');
    if (signalCount) signalCount.textContent = message || 'No backend signal data';
    const spread = document.getElementById('radarHeroSpread');
    if (spread) spread.textContent = '—';
    document.getElementById('radarDeepDiveButton')?.setAttribute('disabled', 'disabled');
    document.getElementById('radarWatchButton')?.setAttribute('disabled', 'disabled');
    document.querySelectorAll('.headline-metric-cell .value').forEach(el => { el.textContent = '—'; });
    document.querySelectorAll('.matrix-table tbody tr').forEach(row => {
      row.querySelectorAll('td:not(.cell-self)').forEach(cell => {
        cell.textContent = '—';
        cell.removeAttribute('title');
        cell.removeAttribute('onclick');
        cell.classList.remove('cell-normal', 'cell-high', 'cell-critical');
        cell.classList.add('cell-unavailable');
      });
    });
    document.querySelectorAll('.signal-card').forEach(card => {
      const pairKey = card.getAttribute('data-pair');
      if (pairKey) sparklineRequestIds.set(pairKey, (sparklineRequestIds.get(pairKey) || 0) + 1);
      const reason = card.querySelector('.pair-data-reason');
      if (reason) { reason.textContent = ''; reason.hidden = true; }
      const sparklineState = card.querySelector('.sparkline-empty-state');
      if (sparklineState) { sparklineState.textContent = message || 'No eligible synchronized snapshot to display.'; sparklineState.hidden = false; }
      const pill = card.querySelector('.severity-pill');
      if (pill) {
        pill.textContent = 'DATA UNAVAILABLE';
        pill.className = 'severity-pill';
      }
      card.querySelectorAll('.stat-num, .radial-text').forEach(el => { el.textContent = '—'; });
      card.querySelectorAll('.v-status').forEach(el => { el.textContent = 'Unavailable'; });
      card.querySelectorAll('.pair-direction-tag, .confidence-radial-box > div:last-child span:last-child').forEach(el => { el.textContent = 'Unavailable'; });
      const confidence = card.querySelector('.confidence-radial-box');
      if (confidence) confidence.title = 'No backend confidence data available';
      card.classList.remove('critical', 'high', 'medium', 'no-signal');
      card.dataset.hasSnapshot = 'false';
      card.dataset.classification = 'unavailable';
      card.dataset.zScore = '';
      card.dataset.liquidityTrap = 'false';
      card.dataset.costBlocked = 'false';
      card.dataset.expiryRisk = 'false';
      card.querySelectorAll('button').forEach(button => {
        button.disabled = true;
        button.removeAttribute('onclick');
        button.title = message || 'No eligible synchronized snapshot is available.';
      });
      const unavailableAction = card.querySelector('.card-investigate-btn');
      if (unavailableAction) unavailableAction.textContent = 'Unavailable';
    });
    document.querySelectorAll('.dist-tab-btn').forEach(tab => {
      tab.textContent = tab.textContent.replace(/\s+\([^)]*\)$/, '');
    });
    if (typeof window.applySignalFilters === 'function') window.applySignalFilters();
  }

  async function loadLiveDistributionData(pairKey) {
    const requestId = ++distributionRequestId;
    window.AURORA_LOAD_DISTRIBUTION = loadLiveDistributionData;
    window.AURORA_SELECT_RADAR_PAIR = selectRadarPairFromUi;
    document.querySelectorAll('.dist-tab-btn').forEach(tab => tab.classList.remove('active'));
    const distributionTabs = {
      'GOLDM-GOLDPETAL': 'tab-goldm-petal',
      'GOLDTEN-GOLDGUINEA': 'tab-guinea-ten',
      'GOLDM-GOLDTEN': 'tab-goldm-ten',
      'GOLDM-GOLDGUINEA': 'tab-goldm-guinea',
      'GOLDTEN-GOLDPETAL': 'tab-ten-petal',
      'GOLDGUINEA-GOLDPETAL': 'tab-guinea-petal'
    };
    const tabId = distributionTabs[pairKey];
    if (tabId) document.getElementById(tabId)?.classList.add('active');
    clearDistributionSampleData();
    const distributionContext = document.getElementById('distributionContext');
    if (distributionContext) distributionContext.textContent = `Loading ${pairKey} historical distribution from the backend…`;
    try {
      const res = await fetch(`${API_BASE}/api/analytics/distribution?pair=${encodeURIComponent(pairKey)}&window=365&bins=15`);
      if (requestId !== distributionRequestId) return;
      if (!res.ok) {
        if (distributionContext) distributionContext.textContent = `${pairKey} historical distribution is unavailable (${res.status}).`;
        return;
      }
      const json = await res.json();
      if (requestId !== distributionRequestId) return;
      if (!json.success || !json.data || !json.data.sample_size || !json.data.bins || !json.data.frequencies) {
        if (distributionContext) distributionContext.textContent = `${pairKey} has no eligible synchronized historical distribution.`;
        return;
      }

      const d = json.data;
      const meanEl = document.getElementById('stat-mean');
      const sigmaEl = document.getElementById('stat-sigma');
      const medEl = document.getElementById('stat-median');
      const kurtEl = document.getElementById('stat-kurtosis');
      const skewEl = document.getElementById('stat-skewness');

      if (meanEl && d.mean !== null) meanEl.textContent = `₹${d.mean.toFixed(2)}`;
      if (sigmaEl && d.sigma !== null) sigmaEl.textContent = `₹${d.sigma.toFixed(2)}`;
      if (medEl && d.median !== null) medEl.textContent = `₹${d.median.toFixed(2)}`;
      if (kurtEl && d.kurtosis !== null) kurtEl.textContent = d.kurtosis;
      if (skewEl && d.skewness !== null) skewEl.textContent = `${d.skewness >= 0 ? '+' : ''}${d.skewness.toFixed(2)}`;
      const currentZ = document.getElementById('stat-current-z');
      if (currentZ) currentZ.textContent = d.current_z_score || '—';
      if (distributionContext) {
        const latest = d.evaluation_date ? `Latest exact-expiry observation ${d.evaluation_date} · expiry ${d.expiry_date || 'unavailable'}` : 'Latest observation date and expiry unavailable';
        const spread = d.current_spread == null ? 'spread unavailable' : `spread ₹${Number(d.current_spread).toFixed(2)}/10g`;
        const expiryPolicy = d.expiry_policy || 'Each point matches trade date and expiry; expiry may roll between historical points.';
        const radarWindow = Number(document.getElementById('dateRangeFilter')?.value) || 30;
        distributionContext.textContent = `${pairKey} · ${Number(d.sample_size).toLocaleString('en-IN')} synchronized observations (up to ${d.window_days}) · ${latest} · ${spread}. Distribution Z-score uses this distribution window; Radar uses ${radarWindow} synchronized sessions. Rolling-contract history: ${expiryPolicy}`;
      }

      if (typeof Chart !== 'undefined') {
        const distChart = Chart.getChart('distributionChartCanvas');
        if (distChart && d.bins && d.frequencies) {
          distChart.data.labels = d.bins.map(b => `₹${b}`);
          distChart.data.datasets[0].data = d.frequencies;
          if (d.gaussian_pdf && distChart.data.datasets[1]) {
            distChart.data.datasets[1].data = d.gaussian_pdf;
          }
          distChart.update();
        }
      }
    } catch (e) {
      if (requestId !== distributionRequestId) return;
      if (distributionContext) distributionContext.textContent = `${pairKey} historical distribution is unavailable.`;
      console.warn('AURORA: Error syncing live distribution data:', e);
    }
  }

  function clearDistributionSampleData() {
    ['stat-mean', 'stat-sigma', 'stat-median', 'stat-kurtosis', 'stat-skewness', 'stat-current-z'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.textContent = '—';
    });
    const chart = typeof Chart !== 'undefined' ? Chart.getChart('distributionChartCanvas') : null;
    if (chart) {
      chart.data.labels = [];
      chart.data.datasets.forEach(dataset => { dataset.data = []; });
      chart.update();
    }
  }

  function setDetectiveUnavailable(message) {
    detectiveRequestId += 1;
    selectedDetectiveEvent = null;
    window.AURORA_SELECTED_EVENT = null;
    window.AURORA_LIVE_EVENTS = {};
    window.AURORA_EVENT_PROVENANCE = null;
    const feedLabel = document.getElementById('detectiveFeedLabel');
    if (feedLabel) feedLabel.textContent = detectiveFeedLabel || 'Feed status unavailable';
    const selector = document.getElementById('eventSelector');
    const grid = document.querySelector('.investigation-grid');
    const summary = document.querySelector('.ai-explanation-panel');
    if (selector) {
      selector.replaceChildren(new Option(message, '', true, true));
      selector.disabled = true;
    }
    if (grid) {
      grid.hidden = true;
      grid.style.display = 'none';
    }
    if (summary) {
      summary.hidden = true;
      summary.style.display = 'none';
    }
    document.querySelectorAll('[data-detective-action]').forEach(button => {
      button.disabled = true;
      button.setAttribute('aria-disabled', 'true');
    });
    clearDetectiveDossier();
    let notice = document.getElementById('detectiveDataNotice');
    if (!notice && selector) {
      notice = document.createElement('p');
      notice.id = 'detectiveDataNotice';
      notice.setAttribute('role', 'status');
      notice.style.cssText = 'padding:16px 20px;margin:12px 0;color:var(--text-muted,#b7b2a5);border:1px solid rgba(202,169,91,.24);border-radius:12px;background:rgba(20,18,14,.72);';
      const header = document.querySelector('.page-header-card');
      if (header) header.insertAdjacentElement('afterend', notice);
    }
    if (notice) notice.textContent = message;
  }

  function clearDetectiveDossier() {
    document.querySelectorAll('.investigation-grid .detail-val').forEach(el => { el.textContent = '—'; });
    document.querySelectorAll('.investigation-grid .step-badge').forEach(el => { el.textContent = 'Awaiting data'; });
    const stepsBadge = document.getElementById('stepsCountBadge'); if (stepsBadge) stepsBadge.textContent = 'AWAITING BACKEND DATA';
    const score = document.getElementById('verdictScoreVal'); if (score) score.textContent = '—';
    const verdict = document.getElementById('verdictBadgeText'); if (verdict) verdict.textContent = 'NO INVESTIGATION';
    const finding = document.getElementById('verdictKeyFinding'); if (finding) finding.textContent = '';
    const recommendation = document.getElementById('verdictRecommendation'); if (recommendation) recommendation.textContent = '';
    const circle = document.getElementById('scoreProgressCircle'); if (circle) circle.style.strokeDashoffset = '240';
    const narrative = document.getElementById('aiParagraphText');
    if (narrative) narrative.textContent = 'A current backend investigation summary will appear here when eligible observations produce an event.';
    const confidence = document.querySelector('.ai-confidence-pill span');
    if (confidence) confidence.textContent = 'OPPORTUNITY SCORE: UNAVAILABLE';
    const signalConfidence = document.getElementById('detectiveSignalConfidence');
    if (signalConfidence) signalConfidence.textContent = 'UNAVAILABLE';
    const executionState = document.getElementById('detectiveExecutionState');
    if (executionState) executionState.textContent = 'No backend execution assessment';
    const caveats = document.getElementById('verdictCaveats');
    if (caveats) caveats.textContent = 'Backend caveats will appear here when returned for the selected event.';
    const signalConfidenceLabel = document.querySelector('.verdict-header-row #detectiveSignalConfidence')?.previousElementSibling;
    if (signalConfidenceLabel) signalConfidenceLabel.textContent = 'SIGNAL CONFIDENCE';
    const source = document.querySelector('.ai-source-row span');
    if (source) source.textContent = 'Sources will be shown for a selected backend investigation.';
    const raw = document.getElementById('rawPayloadBlock');
    if (raw) raw.textContent = 'No valid backend investigation selected.';
    const rawNotice = document.getElementById('rawPayloadNotice');
    if (rawNotice) rawNotice.textContent = 'Backend investigation payload appears when a valid event is selected.';
    document.querySelectorAll('.chart-footer-metrics .chart-metric-value').forEach(el => { el.textContent = '—'; });
    document.querySelectorAll('.subscore-val').forEach(el => { el.textContent = '—'; });
    document.querySelectorAll('.subscore-val-wrap span:last-child').forEach(el => { el.textContent = 'Unavailable'; });
    document.querySelectorAll('.subscore-mini-fill').forEach(el => { el.style.width = '0%'; });
    document.querySelectorAll('.z-meter-fill').forEach(el => { el.style.width = '0%'; });
    document.querySelectorAll('.warning-callout').forEach(el => { el.hidden = true; el.style.display = 'none'; });
    document.querySelectorAll('.z-meter-labels .highlight').forEach(el => { el.textContent = 'Selected event Z-score: —'; });
    clearDetectiveCharts();
  }

  function clearDetectiveCharts() {
    ['spreadChartCanvas', 'volumeOIChartCanvas'].forEach(id => {
      const chart = typeof Chart !== 'undefined' ? Chart.getChart(id) : null;
      if (!chart) return;
      chart.data.labels = [];
      chart.data.datasets.forEach(dataset => { dataset.data = []; });
      chart.update();
    });
  }

  function isValidDetectiveEvent(evt) {
    const evidence = evt?.evidence;
    const finite = value => value !== null && value !== undefined && Number.isFinite(Number(value));
    const actionable = ['investigate', 'watch', 'cost-blocked', 'expiry-risk'];
    return Boolean(
      evt && typeof evt.event_id === 'string' && evt.event_id.trim() &&
      typeof evt.pair === 'string' && evt.pair === `${evt.leg_a}-${evt.leg_b}` &&
      evt.trade_date && evidence && finite(evidence.spread) && finite(evidence.z_score) &&
      finite(evidence.percentile_rank) && finite(evt.opportunity_score) &&
      typeof evt.classification === 'string' && actionable.includes(evt.classification.toLowerCase())
    );
  }

  function setDetectiveFeedStatus(status) {
    const element = document.getElementById('detectiveFeedLabel');
    if (!status) {
      detectiveFeedLabel = null;
      if (element) element.textContent = 'Feed status unavailable';
      return;
    }
    const state = String(status.feed_status || 'UNAVAILABLE').toUpperCase();
    const provenance = status.data_freshness_label || status.data_provenance || 'Market-data provenance unavailable';
    detectiveFeedLabel = `${state} · ${provenance}`;
    if (element) element.textContent = detectiveFeedLabel;
  }

  async function loadDetectiveChartData(evt, days, requestId) {
    try {
      const url = `${API_BASE}/api/analytics/spreads?pair=${encodeURIComponent(evt.pair)}&window=${encodeURIComponent(days)}&end_date=${encodeURIComponent(evt.trade_date)}`;
      const response = await fetch(url);
      if (requestId !== detectiveRequestId) return;
      if (!response.ok) throw new Error(`Spread history unavailable (${response.status})`);
      const json = await response.json();
      if (requestId !== detectiveRequestId) return;
      const points = json?.success && Array.isArray(json?.data?.data_points) ? json.data.data_points : [];
      if (!points.length) {
        document.querySelectorAll('.chart-footer-metrics .chart-metric-value').forEach(el => { el.textContent = '—'; });
        return;
      }

      const chart = typeof Chart !== 'undefined' ? Chart.getChart('spreadChartCanvas') : null;
      if (chart) {
        chart.data.labels = points.map(point => point.trade_date);
        if (chart.data.datasets[3]) chart.data.datasets[3].label = `${evt.pair} normalized spread`;
        const values = [
          points.map(point => point.upper_2sigma),
          points.map(point => point.rolling_mean),
          points.map(point => point.lower_2sigma),
          points.map(point => point.spread),
        ];
        chart.data.datasets.forEach((dataset, index) => { dataset.data = values[index] || []; });
        chart.update();
      }
      const volumeChart = typeof Chart !== 'undefined' ? Chart.getChart('volumeOIChartCanvas') : null;
      if (volumeChart) {
        volumeChart.data.labels = points.map(point => point.trade_date);
        if (volumeChart.data.datasets[0]) volumeChart.data.datasets[0].label = `${evt.leg_a} Volume`;
        if (volumeChart.data.datasets[1]) volumeChart.data.datasets[1].label = `${evt.leg_b} Volume`;
        const values = [
          points.map(point => point.volume_a),
          points.map(point => point.volume_b),
          points.map(point => point.open_interest_a == null || point.open_interest_b == null ? null : Number(point.open_interest_a) + Number(point.open_interest_b)),
        ];
        volumeChart.data.datasets.forEach((dataset, index) => { dataset.data = values[index] || []; });
        volumeChart.update();
      }

      const footer = document.querySelectorAll('.chart-footer-metrics .chart-metric-value');
      const spreadDescription = document.querySelector('.evidence-column .evidence-panel .panel-title-group p');
      if (spreadDescription) spreadDescription.textContent = `${evt.pair} · ${days}-observation backend spread history with rolling statistical bands`;
      const latest = points[points.length - 1];
      const set = (index, value) => { if (footer[index]) footer[index].textContent = value; };
      set(0, `₹${Number(evt.evidence.spread).toFixed(2)}`);
      set(1, evt.evidence.rolling_mean == null ? '—' : `₹${Number(evt.evidence.rolling_mean).toFixed(2)}`);
      set(2, latest.upper_2sigma == null ? '—' : `₹${Number(latest.upper_2sigma).toFixed(2)}`);
      set(3, `${Number(evt.evidence.z_score) >= 0 ? '+' : ''}${Number(evt.evidence.z_score).toFixed(2)}σ`);
      set(4, evt.evidence.volume_a == null ? 'Unavailable' : Number(evt.evidence.volume_a).toLocaleString('en-IN'));
      set(5, evt.evidence.volume_b == null ? 'Unavailable' : Number(evt.evidence.volume_b).toLocaleString('en-IN'));
      set(6, evt.evidence.volume_a == null || evt.evidence.volume_b == null || Number(evt.evidence.volume_a) <= 0 ? '—' : `${(Number(evt.evidence.volume_b) / Number(evt.evidence.volume_a)).toFixed(3)}`);
      set(7, evt.evidence.open_interest_a == null || evt.evidence.open_interest_b == null ? 'Unavailable' : (Number(evt.evidence.open_interest_a) + Number(evt.evidence.open_interest_b)).toLocaleString('en-IN'));
    } catch (error) {
      if (requestId === detectiveRequestId) {
        clearDetectiveCharts();
        document.querySelectorAll('.chart-footer-metrics .chart-metric-value').forEach(el => { el.textContent = '—'; });
        console.warn('AURORA: Detective chart history unavailable:', error);
      }
    }
  }

  async function setupMarketDetectiveSync() {
    setDetectiveFeedStatus(null);
    setDetectiveUnavailable('Loading backend investigation data…');
    const requestId = detectiveRequestId;
    try {
      const [statusRes, eventsRes] = await Promise.all([
        fetch(`${API_BASE}/api/market/status`),
        fetch(`${API_BASE}/api/analytics/events?limit=30`),
      ]);
      if (requestId !== detectiveRequestId) return;
      let statusJson = null;
      if (statusRes.ok) statusJson = await statusRes.json();
      if (requestId !== detectiveRequestId) return;
      const mode = statusJson?.data?.data_mode;
      if (!statusJson?.success || !statusJson.data) {
        setDetectiveFeedStatus(null);
        setDetectiveUnavailable('Market status is unavailable; investigation data cannot be verified.');
        return;
      }
      setDetectiveFeedStatus(statusJson.data);
      if (['test_data', 'demo_synthetic'].includes(mode)) {
        setDetectiveUnavailable(mode === 'test_data' || mode === 'demo_synthetic'
          ? 'Test/demo data is excluded from investigations.'
          : 'Market status is unavailable; investigation data cannot be verified.');
        return;
      }
      window.AURORA_EVENT_PROVENANCE = statusJson.data.data_provenance || statusJson.data.data_freshness_label || 'Backend market observations';
      if (!eventsRes.ok) {
        setDetectiveUnavailable('Investigation data is unavailable. Check the backend connection or upload historical CSV data.');
        return;
      }
      const json = await eventsRes.json();
      if (requestId !== detectiveRequestId) return;
      const events = json?.success && Array.isArray(json?.data?.items)
        ? json.data.items.filter(isValidDetectiveEvent)
        : [];
      if (!events.length) {
        setDetectiveUnavailable('No backend investigations are available for the current data.');
        return;
      }

      const selector = document.getElementById('eventSelector');
      if (!selector) return;

      selector.disabled = false;
      selector.replaceChildren();
      const grid = document.querySelector('.investigation-grid');
      if (grid) {
        grid.hidden = false;
        grid.style.display = '';
      }
      const summary = document.querySelector('.ai-explanation-panel');
      if (summary) { summary.hidden = false; summary.style.display = ''; }
      document.querySelectorAll('[data-detective-action]').forEach(button => {
        button.disabled = false;
        button.setAttribute('aria-disabled', 'false');
      });
      const notice = document.getElementById('detectiveDataNotice');
      if (notice) notice.remove();
      window.AURORA_LIVE_EVENTS = {};
      const optGroup = document.createElement('optgroup');
      optGroup.label = 'Backend events · observation date shown (historical events may differ from the latest radar snapshot)';

      events.forEach((evt, idx) => {
        window.AURORA_LIVE_EVENTS[evt.event_id] = evt;
        const opt = document.createElement('option');
        opt.value = evt.event_id;
        opt.textContent = `${evt.trade_date} · ${evt.event_id} — ${evt.pair} (${evt.classification} | Z=${evt.evidence.z_score >= 0 ? '+' : ''}${evt.evidence.z_score}σ)`;
        if (idx === 0) opt.selected = true;
        optGroup.appendChild(opt);
      });

      selector.insertBefore(optGroup, selector.firstChild);

      selector.onchange = (e) => window.handleEventSwitch?.(e.target.value);
      window.AURORA_INVALIDATE_DETECTIVE = setDetectiveUnavailable;
      window.AURORA_RENDER_DETECTIVE_EVENT = renderLiveEventDossier;
      window.AURORA_REFRESH_DETECTIVE_CHARTS = days => {
        if (!selectedDetectiveEvent) return;
        const chartRequestId = ++detectiveRequestId;
        clearDetectiveCharts();
        loadDetectiveChartData(selectedDetectiveEvent, days, chartRequestId);
      };
      renderLiveEventDossier(events[0]);
    } catch (e) {
      console.warn('AURORA: Error loading live detective events:', e);
      setDetectiveUnavailable('Investigation data is unavailable. Check the backend connection or upload historical CSV data.');
    }
  }

  async function renderLiveEventDossier(evt) {
    if (!isValidDetectiveEvent(evt) || window.AURORA_LIVE_EVENTS?.[evt.event_id] !== evt) {
      setDetectiveUnavailable('No backend investigations are available for the current data.');
      return;
    }
    const requestId = ++detectiveRequestId;
    selectedDetectiveEvent = evt;
    window.AURORA_SELECTED_EVENT = evt;
    clearDetectiveCharts();
    document.querySelectorAll('.chart-footer-metrics .chart-metric-value').forEach(el => { el.textContent = '—'; });
    const legALabel = document.getElementById('volumeLegALabel');
    const legBLabel = document.getElementById('volumeLegBLabel');
    if (legALabel) legALabel.textContent = evt.leg_a;
    if (legBLabel) legBLabel.textContent = evt.leg_b;
    const liquidityDescription = document.querySelector('#volumeOIChartCanvas')?.closest('.evidence-panel')?.querySelector('.panel-title-group p');
    if (liquidityDescription) liquidityDescription.textContent = `Contracts traded vs. Open Commitment · ${evt.leg_a} / ${evt.leg_b}`;
    const stepStates = ['EVENT DATA', 'NORMALIZED EVENT', 'BACKEND SPREAD', 'BACKEND STATISTICS', 'BACKEND LIQUIDITY', 'BACKEND EXPIRY', 'BACKEND COST', 'NOT RETURNED'];
    document.querySelectorAll('.investigation-grid .step-badge').forEach((el, index) => {
      el.textContent = stepStates[index] || 'BACKEND DATA';
    });

    const scoreVal = document.getElementById('verdictScoreVal');
    const badgeText = document.getElementById('verdictBadgeText');
    const keyFinding = document.getElementById('verdictKeyFinding');
    const recommendation = document.getElementById('verdictRecommendation');
    const circle = document.getElementById('scoreProgressCircle');

    if (scoreVal) scoreVal.textContent = Math.round(evt.opportunity_score);
    const signalConfidenceLabel = document.querySelector('.verdict-header-row #detectiveSignalConfidence')?.previousElementSibling;
    if (signalConfidenceLabel) signalConfidenceLabel.textContent = 'SIGNAL CONFIDENCE';
    if (badgeText) badgeText.textContent = evt.classification.toUpperCase();
    const stepsBadge = document.getElementById('stepsCountBadge'); if (stepsBadge) stepsBadge.textContent = `BACKEND EVENT · ${evt.event_id}`;
    if (circle) {
      const offset = 240 - (240 * (evt.opportunity_score / 100));
      circle.style.strokeDashoffset = String(offset);
    }
    if (keyFinding) keyFinding.textContent = `${evt.pair} · ${Number(evt.evidence.spread).toFixed(2)} per 10g · ${Number(evt.evidence.z_score) >= 0 ? '+' : ''}${Number(evt.evidence.z_score).toFixed(2)}σ · ${Number(evt.evidence.percentile_rank).toFixed(1)}th percentile. ${evt.evidence.rule_triggered || ''}`;
    if (recommendation) {
      recommendation.textContent = `${evt.classification}: ${evt.summary || evt.evidence.rule_triggered || 'Backend classification returned.'}`;
    }

    const s1 = document.getElementById('step1Card');
    if (s1) {
      const vals = s1.querySelectorAll('.detail-val');
      if (vals.length >= 2) {
        vals[0].textContent = window.AURORA_EVENT_PROVENANCE || 'Backend observations';
        vals[1].textContent = evt.trade_date;
      }
    }

    const s2 = document.getElementById('step2Card');
    if (s2) {
      const vals = s2.querySelectorAll('.detail-val.gold');
      if (vals.length >= 2) {
        vals[0].textContent = `${evt.leg_a} · ${evt.evidence.benchmark_basis || 'normalized basis'}`;
        vals[1].textContent = `${evt.leg_b} · ${evt.evidence.benchmark_basis || 'normalized basis'}`;
      }
    }

    const s3 = document.getElementById('step3Card');
    if (s3) {
      const rawVal = s3.querySelector('.detail-val.gold');
      if (rawVal) rawVal.textContent = `₹${evt.evidence.spread.toFixed(2)} / 10g`;
      const allVals = s3.querySelectorAll('.detail-val');
      if (allVals.length >= 2) allVals[1].textContent = 'Not returned by backend';
      const direction = s3.querySelector('.detail-val.warn');
      if (direction) {
        const spread = Number(evt.evidence.spread);
        const roundedSpread = Number(spread.toFixed(2));
        direction.textContent = roundedSpread === 0
          ? 'At normalized parity (Leg A − Leg B)'
          : `${spread > 0 ? evt.leg_a : evt.leg_b} normalized premium (Leg A − Leg B)`;
      }
    }

    const s4 = document.getElementById('step4Card');
    if (s4) {
      const goldVals = s4.querySelectorAll('.detail-val.gold');
      if (goldVals.length >= 2) {
        goldVals[0].textContent = `${evt.evidence.z_score >= 0 ? '+' : ''}${evt.evidence.z_score.toFixed(2)}σ (30d)`;
        goldVals[1].textContent = `${evt.evidence.percentile_rank.toFixed(1)}%`;
      }
      const allVals = s4.querySelectorAll('.detail-val');
      if (allVals.length >= 4) {
        allVals[2].textContent = 'Not returned by backend';
        allVals[3].textContent = 'Not returned by backend';
      }
      const meterFill = s4.querySelector('.z-meter-fill');
      if (meterFill) {
        const pctPos = Math.min(100, Math.max(0, ((evt.evidence.z_score + 3) / 6) * 100));
        meterFill.style.width = `${pctPos}%`;
      }
      const actualLabel = s4.querySelector('.z-meter-labels .highlight');
      if (actualLabel) actualLabel.textContent = `Selected event: ${Number(evt.evidence.z_score) >= 0 ? '+' : ''}${Number(evt.evidence.z_score).toFixed(2)}σ`;
    }

    const s5 = document.getElementById('step5Card');
    if (s5) {
      const vals = s5.querySelectorAll('.detail-val');
      if (vals.length >= 3) {
        vals[0].textContent = evt.evidence.volume_a == null ? 'Unavailable' : `${Number(evt.evidence.volume_a).toLocaleString()} lots`;
        vals[1].textContent = evt.evidence.volume_b == null ? 'Unavailable' : `${Number(evt.evidence.volume_b).toLocaleString()} lots`;
        vals[2].textContent = evt.evidence.open_interest_a == null || evt.evidence.open_interest_b == null ? 'Unavailable' : `${(Number(evt.evidence.open_interest_a) + Number(evt.evidence.open_interest_b)).toLocaleString()} contracts`;
      }
    }

    const s6 = document.getElementById('step6Card');
    if (s6) {
      const vals = s6.querySelectorAll('.detail-val');
      if (vals.length >= 2) {
        vals[0].textContent = `${evt.evidence.dte_a !== null ? evt.evidence.dte_a + ' days' : 'N/A'}`;
        vals[1].textContent = `${evt.evidence.dte_b !== null ? evt.evidence.dte_b + ' days' : 'N/A'}`;
      }
    }

    const s7 = document.getElementById('step7Card');
    if (s7) {
      const warnVal = s7.querySelector('.detail-val.warn');
      if (warnVal) warnVal.textContent = `₹${evt.evidence.cost_hurdle.toFixed(2)} / 10g`;
      const goldVal = s7.querySelector('.detail-val.gold');
      if (goldVal) goldVal.textContent = evt.evidence.net_edge == null ? 'Not returned by backend' : `₹${Number(evt.evidence.net_edge).toFixed(2)} / 10g`;
    }

    const step8 = document.querySelectorAll('#step8Card .detail-val');
    step8.forEach(el => { el.textContent = 'Not returned by backend'; });
    const caveats = Array.isArray(evt.evidence.caveats) ? evt.evidence.caveats.filter(Boolean) : [];
    document.querySelectorAll('.warning-callout').forEach((el, index) => {
      if (!caveats.length || index > 0) { el.hidden = true; el.style.display = 'none'; return; }
      el.hidden = false;
      el.style.display = '';
      const text = el.querySelector('span');
      if (text) text.textContent = caveats.join(' ');
    });

    const aiText = document.getElementById('aiParagraphText');
    if (aiText) {
      const p = document.createElement('p');
      p.textContent = evt.summary || `${evt.event_id} · ${evt.pair} · ${evt.trade_date} · ${evt.classification}`;
      const details = document.createElement('p');
      details.textContent = `Spread ₹${Number(evt.evidence.spread).toFixed(2)} / 10g · Z-score ${Number(evt.evidence.z_score) >= 0 ? '+' : ''}${Number(evt.evidence.z_score).toFixed(2)} · Percentile ${Number(evt.evidence.percentile_rank).toFixed(1)}%. Cost hurdle ${evt.evidence.cost_hurdle == null ? 'not returned' : `₹${Number(evt.evidence.cost_hurdle).toFixed(2)} / 10g`}. Historical analogues are not provided by this endpoint.`;
      aiText.replaceChildren(p, details);
    }
    const confidence = document.querySelector('.ai-confidence-pill span');
    if (confidence) confidence.textContent = `OPPORTUNITY SCORE: ${Math.round(Number(evt.opportunity_score))}/100`;
    const signalConfidence = document.getElementById('detectiveSignalConfidence');
    if (signalConfidence) signalConfidence.textContent = 'Not returned by backend';
    const executionState = document.getElementById('detectiveExecutionState');
    if (executionState) executionState.textContent = `Backend classification: ${evt.classification}`;
    const caveatsNode = document.getElementById('verdictCaveats');
    if (caveatsNode) caveatsNode.textContent = Array.isArray(evt.evidence.caveats) && evt.evidence.caveats.length
      ? evt.evidence.caveats.join(' ')
      : 'No additional caveats were returned for this event.';
    const source = document.querySelector('.ai-source-row span');
    if (source) source.textContent = `Backend event ${evt.event_id} · ${evt.trade_date} · ${window.AURORA_EVENT_PROVENANCE || 'market-data provenance unavailable'}.`;

    const rawPre = document.getElementById('rawPayloadBlock');
    if (rawPre) {
      rawPre.textContent = JSON.stringify(evt, null, 2);
    }
    const rawNotice = document.getElementById('rawPayloadNotice');
    if (rawNotice) rawNotice.textContent = `Backend analytics event ${evt.event_id} · ${evt.trade_date} · ${window.AURORA_EVENT_PROVENANCE || 'market-data provenance unavailable'}.`;

    loadDetectiveChartData(evt, 30, requestId);
  }

  function renderRadarPair(pair) {
    selectedRadarPairKey = pair.pair;
    const title = document.querySelector('.headline-pair-title');
    if (title) title.textContent = `${pair.leg_a} vs ${pair.leg_b}`;
    const classification = document.getElementById('radarClassification');
    const pairClass = pair.classification || 'No Signal';
    if (classification) classification.textContent = pairClass === 'No Signal' ? 'NO SIGNAL · NOT ACTIONABLE' : pairClass;
    const snapshotDate = document.getElementById('radarSnapshotDate');
    if (snapshotDate) snapshotDate.textContent = `As of ${pair.trade_date || '—'} · Expiry ${pair.expiry_date || '—'}`;
    const spread = document.getElementById('radarHeroSpread');
    const roundedSpread = Number(Number(pair.spread).toFixed(2));
    if (spread) spread.textContent = `${roundedSpread > 0 ? '+' : ''}₹${roundedSpread.toFixed(2)}/10g`;
    const values = document.querySelectorAll('.headline-metric-cell .value');
    if (values.length >= 3) {
      values[0].textContent = pair.z_score == null ? '—' : `${Number(pair.z_score) >= 0 ? '+' : ''}${Number(pair.z_score).toFixed(2)}σ`;
      values[1].textContent = pair.percentile_rank == null ? '—' : `${Number(pair.percentile_rank).toFixed(1)}%`;
      values[2].textContent = pair.opportunity_score == null ? '—' : `${Math.round(Number(pair.opportunity_score))}/100`;
    }
    const badge = document.getElementById('radarPairStatusBadge');
    const validPairs = new Set(Object.values(radarPairMap)
      .filter(item => item.spread != null)
      .map(item => [item.leg_a, item.leg_b].sort().join('-')));
    if (badge) badge.textContent = `${validPairs.size}/6 matched`;
    syncRadarSelectionFilterState();
    const deepDive = document.getElementById('radarDeepDiveButton');
    if (deepDive) { deepDive.disabled = false; deepDive.removeAttribute('title'); deepDive.setAttribute('onclick', `openInvestigationModal('${pair.pair}')`); }
    const watch = document.getElementById('radarWatchButton');
    if (watch) { watch.disabled = false; watch.removeAttribute('title'); watch.setAttribute('onclick', `triggerToast('Added ${pair.pair} to high-priority watchlist')`); }
  }

  function selectRadarPairFromUi(pairKey) {
    const pair = radarPairMap[pairKey];
    if (pair && pair.spread != null) {
      renderRadarPair(pair);
      return;
    }
    renderUnavailableRadarPair(pairKey, pair);
  }

  function renderUnavailableRadarPair(pairKey, pair = null) {
    selectedRadarPairKey = pairKey;
    const [legA, legB] = pairKey.split('-');
    const title = document.querySelector('.headline-pair-title');
    if (title) title.textContent = `${legA} vs ${legB}`;
    const classification = document.getElementById('radarClassification');
    if (classification) classification.textContent = 'NO SYNCHRONIZED SNAPSHOT';
    const snapshotDate = document.getElementById('radarSnapshotDate');
    if (snapshotDate) snapshotDate.textContent = 'Current snapshot · unavailable';
    const spread = document.getElementById('radarHeroSpread');
    if (spread) spread.textContent = '—';
    document.querySelectorAll('.headline-metric-cell .value').forEach(node => { node.textContent = '—'; });
    const deepDive = document.getElementById('radarDeepDiveButton');
    if (deepDive) {
      deepDive.disabled = true;
      deepDive.removeAttribute('onclick');
      deepDive.title = pair?.reason || 'Unavailable until a synchronized same-expiry snapshot exists.';
    }
    const watch = document.getElementById('radarWatchButton');
    if (watch) {
      watch.disabled = true;
      watch.removeAttribute('onclick');
      watch.title = pair?.reason || 'Unavailable until a synchronized same-expiry snapshot exists.';
    }
    const badge = document.getElementById('radarPairStatusBadge');
    if (badge) badge.title = pair?.reason || 'No current synchronized same-date, same-expiry snapshot is available.';
    syncRadarSelectionFilterState();
  }

  function syncRadarSelectionFilterState() {
    const notice = document.getElementById('radarSelectionFilterNotice');
    if (!notice) return;
    if (!selectedRadarPairKey) {
      notice.hidden = true;
      notice.textContent = '';
      return;
    }
    const pair = radarPairMap[selectedRadarPairKey];
    const reverseKey = selectedRadarPairKey.split('-').reverse().join('-');
    const card = document.querySelector(`.signal-card[data-pair="${selectedRadarPairKey}"]`) ||
      document.querySelector(`.signal-card[data-pair="${reverseKey}"]`);
    if (!pair || pair.spread == null || !card) {
      const reason = pair?.reason ? ` ${pair.reason}` : ' Matching requires the same trade date and explicit expiry; different expiries are never paired.';
      notice.textContent = `${selectedRadarPairKey}: no current synchronized snapshot.${reason} Historical distribution is separate from the current snapshot.`;
      notice.hidden = false;
      return;
    }
    if (card.style.display === 'none') {
      notice.textContent = 'Selected pair is outside the active Status / Severity filters. The hero and history show this selection; cards show only matching pairs.';
      notice.hidden = false;
      return;
    }
    notice.hidden = true;
    notice.textContent = '';
  }

  function orientRadarPair(pair, requestedPair) {
    if (!pair || pair.pair === requestedPair) return pair;
    if (pair.pair !== requestedPair.split('-').reverse().join('-')) return pair;
    return {
      ...pair,
      pair: requestedPair,
      leg_a: pair.leg_b,
      leg_b: pair.leg_a,
      spread: pair.spread == null ? null : -Number(pair.spread),
      rolling_mean: pair.rolling_mean == null ? null : -Number(pair.rolling_mean),
      z_score: pair.z_score == null ? null : -Number(pair.z_score),
      percentile_rank: pair.percentile_rank == null ? null : 100 - Number(pair.percentile_rank),
    };
  }

  function updateRadarSignalCards(pairs) {
    pairs.forEach(pair => {
      const card = document.querySelector(`.signal-card[data-pair="${pair.pair}"]`) ||
        document.querySelector(`.signal-card[data-pair="${pair.pair.split('-').reverse().join('-')}"]`);
      if (!card) return;
      const displayPair = orientRadarPair(pair, card.getAttribute('data-pair'));
      const unavailableReason = card.querySelector('.pair-data-reason');
      if (displayPair.spread == null) {
        const reason = displayPair.reason || 'No synchronized snapshot is available for this pair.';
        const sparklineKey = displayPair.pair;
        sparklineRequestIds.set(sparklineKey, (sparklineRequestIds.get(sparklineKey) || 0) + 1);
        const sparklineCanvas = card.querySelector('.sparkline-box canvas');
        const sparklineChart = sparklineCanvas && typeof Chart !== 'undefined' ? Chart.getChart(sparklineCanvas) : null;
        if (sparklineChart) {
          sparklineChart.data.labels = [];
          sparklineChart.data.datasets.forEach(dataset => { dataset.data = []; });
          sparklineChart.update();
        }
        const pill = card.querySelector('.severity-pill');
        if (pill) {
          pill.textContent = 'NO SYNCHRONIZED SNAPSHOT';
          pill.className = 'severity-pill';
          pill.title = reason;
        }
        if (unavailableReason) {
          unavailableReason.textContent = reason;
          unavailableReason.hidden = false;
        }
        const sparklineState = card.querySelector('.sparkline-empty-state');
        if (sparklineState) {
          sparklineState.textContent = 'No synchronized same-expiry snapshot to plot.';
          sparklineState.hidden = false;
        }
        card.querySelectorAll('.stat-num, .radial-text').forEach(el => { el.textContent = '—'; });
        card.querySelectorAll('.v-status').forEach(el => { el.textContent = 'Unavailable'; });
        card.querySelectorAll('button').forEach(button => {
          button.disabled = true;
          button.removeAttribute('onclick');
          button.title = reason;
        });
        const unavailableAction = card.querySelector('.card-investigate-btn');
        if (unavailableAction) unavailableAction.textContent = 'Unavailable';
        card.classList.remove('critical', 'high', 'medium', 'no-signal');
        card.setAttribute('data-severity', 'unavailable');
        card.dataset.hasSnapshot = 'false';
        card.dataset.classification = 'unavailable';
        card.dataset.zScore = '';
        card.dataset.liquidityTrap = 'false';
        card.dataset.costBlocked = 'false';
        card.dataset.expiryRisk = 'false';
        return;
      }
      if (unavailableReason) unavailableReason.hidden = true;
      const statValues = card.querySelectorAll('.stat-num');
      const roundedSpread = Number(Number(displayPair.spread).toFixed(2));
      if (statValues[0]) statValues[0].innerHTML = `${roundedSpread > 0 ? '+' : ''}₹${roundedSpread.toFixed(2)} <span class="stat-subtext">/ 10g</span>`;
      if (statValues[1]) statValues[1].textContent = displayPair.z_score == null ? '—' : `${Number(displayPair.z_score) >= 0 ? '+' : ''}${Number(displayPair.z_score).toFixed(2)}σ`;
      if (statValues[2]) statValues[2].textContent = displayPair.percentile_rank == null ? '—' : `${Number(displayPair.percentile_rank).toFixed(1)}%`;
      if (statValues[3]) statValues[3].textContent = '—'; // No duration metric is returned by the API.
      const pairName = card.querySelector('.pair-symbols > span:first-child');
      if (pairName) pairName.textContent = `${displayPair.leg_a} vs ${displayPair.leg_b}`;
      const specs = card.querySelector('.pair-specs-sub');
      if (specs) specs.textContent = `Synchronized historical snapshot · ${displayPair.trade_date || 'date unavailable'} · expiry ${displayPair.expiry_date || 'unavailable'}`;
      const direction = card.querySelector('.pair-direction-tag');
      if (direction) direction.textContent = roundedSpread === 0
        ? 'At normalized parity'
        : `${Number(displayPair.spread) > 0 ? displayPair.leg_a : displayPair.leg_b} normalized premium`;
      const scoreAvailable = displayPair.opportunity_score != null && Number.isFinite(Number(displayPair.opportunity_score));
      const score = scoreAvailable ? Math.round(Number(displayPair.opportunity_score)) : null;
      const radial = card.querySelector('.radial-text');
      if (radial) radial.textContent = score == null ? '—' : String(score);
      const radialCircle = card.querySelector('.circle-val');
      if (radialCircle) radialCircle.setAttribute('stroke-dasharray', `${score ?? 0}, 100`);
      const scoreNote = card.querySelector('.confidence-radial-box > div:last-child span:last-child');
      if (scoreNote) scoreNote.textContent = score == null ? 'Unavailable' : `${score}/100`;
      const confidenceBox = card.querySelector('.confidence-radial-box');
      if (confidenceBox) confidenceBox.title = `Opportunity score ${score == null ? 'unavailable' : `${score}/100 (Heuristic ranking score, not win probability)`} · Trap risk ${displayPair.trap_risk_score == null ? 'unavailable' : `${Math.round(Number(displayPair.trap_risk_score))}/100`} · Status: ${displayPair.classification || 'No Signal'}`;
      const pill = card.querySelector('.severity-pill');
      const isNoSignal = displayPair.classification === 'No Signal';
      if (pill) {
        pill.textContent = isNoSignal ? 'NO SIGNAL · NOT ACTIONABLE' : String(displayPair.classification || 'No Signal').toUpperCase();
        pill.className = `severity-pill ${isNoSignal ? 'pill-no-signal' : displayPair.classification === 'Investigate' ? 'pill-critical' : ['Cost-Blocked', 'Expiry-Risk'].includes(displayPair.classification) ? 'pill-high' : 'pill-medium'}`;
      }
      if (radialCircle) {
        radialCircle.classList.remove('circle-val-critical', 'circle-val-high', 'circle-val-medium');
        radialCircle.classList.add(displayPair.classification === 'Investigate' ? 'circle-val-critical' : ['Cost-Blocked', 'Expiry-Risk'].includes(displayPair.classification) ? 'circle-val-high' : 'circle-val-medium');
      }
      card.classList.remove('critical', 'high', 'medium', 'no-signal');
      if (displayPair.classification === 'Investigate') card.classList.add('critical');
      else if (['Cost-Blocked', 'Expiry-Risk'].includes(displayPair.classification)) card.classList.add('high');
      else if (isNoSignal) card.classList.add('no-signal');
      else card.classList.add('medium');
      const absZ = displayPair.z_score == null ? null : Math.abs(Number(displayPair.z_score));
      card.dataset.zScore = absZ == null || !Number.isFinite(absZ) ? '' : String(absZ);
      card.setAttribute('data-severity', absZ == null || !Number.isFinite(absZ) ? 'unavailable' : absZ >= 2 ? 'critical' : absZ >= 1.5 ? 'high' : absZ >= 1 ? 'medium' : 'low');
      const validationValues = card.querySelectorAll('.v-status');
      const liquidityKnown = displayPair.min_volume != null && displayPair.min_open_interest != null;
      const checks = [
        !liquidityKnown ? 'Volume/OI unavailable' : displayPair.is_liquidity_trap ? 'Below volume/OI threshold' : 'Volume/OI threshold met',
        !liquidityKnown ? 'Liquidity unassessed' : displayPair.is_liquidity_trap ? 'Liquidity risk' : 'Liquidity threshold met',
        displayPair.is_cost_blocked ? 'Cost-blocked' : 'Cost hurdle passed',
      ];
      validationValues.forEach((node, index) => { node.textContent = checks[index] || '—'; });
      const investButton = card.querySelector('.card-investigate-btn');
      if (investButton) {
        investButton.disabled = false;
        investButton.removeAttribute('title');
        investButton.textContent = displayPair.classification === 'Investigate' ? 'Review investigation →' : 'View pair details →';
        investButton.setAttribute('onclick', `openInvestigationModal('${displayPair.pair}')`);
      }
      const bookmarkButton = card.querySelector('.card-footer-actions .clay-btn-outline');
      if (bookmarkButton) { bookmarkButton.disabled = false; bookmarkButton.removeAttribute('title'); bookmarkButton.setAttribute('onclick', `triggerToast('Added ${displayPair.pair} to high-priority watchlist')`); }
      card.dataset.hasSnapshot = 'true';
      card.dataset.classification = displayPair.classification || 'No Signal';
      card.dataset.liquidityTrap = String(Boolean(displayPair.is_liquidity_trap));
      card.dataset.costBlocked = String(Boolean(displayPair.is_cost_blocked));
      card.dataset.expiryRisk = String(Boolean(displayPair.is_expiry_risk));
      const sparklineState = card.querySelector('.sparkline-empty-state');
      if (sparklineState) {
        sparklineState.textContent = 'Loading synchronized spread history…';
        sparklineState.hidden = false;
      }
      loadRadarSparkline(displayPair, card);
    });
  }

  function ensureRadarSignalCards(pairs) {
    const grid = document.querySelector('.signals-grid');
    const template = grid?.querySelector('.signal-card');
    if (!grid || !template) return;

    pairs.forEach(pair => {
      const reverse = pair.pair.split('-').reverse().join('-');
      if (grid.querySelector(`.signal-card[data-pair="${pair.pair}"]`) ||
          grid.querySelector(`.signal-card[data-pair="${reverse}"]`)) return;

      const card = template.cloneNode(true);
      const canvas = card.querySelector('canvas');
      const pairId = pair.pair.toLowerCase().replace(/[^a-z0-9]+/g, '-');
      card.dataset.pair = pair.pair;
      card.dataset.severity = 'unavailable';
      card.dataset.hasSnapshot = 'false';
      card.dataset.classification = 'unavailable';
      card.classList.remove('critical', 'high', 'medium');
      const pairName = card.querySelector('.pair-symbols > span:first-child');
      if (pairName) pairName.textContent = `${pair.leg_a} vs ${pair.leg_b}`;
      const specs = card.querySelector('.pair-specs-sub');
      if (specs) specs.textContent = 'Waiting for a synchronized historical snapshot';
      card.querySelectorAll('button').forEach(button => { button.disabled = true; });
      grid.appendChild(card);
      if (canvas) {
        canvas.id = `sparkline-${pairId}`;
        if (typeof window.createSparkline === 'function') {
          window.createSparkline(canvas.id, [], '#c9a650', 'rgba(201, 166, 80, 0.15)');
        }
      }
    });
  }

  async function loadRadarSparkline(pair, card) {
    const canvas = card.querySelector('.sparkline-box canvas');
    const state = card.querySelector('.sparkline-empty-state');
    if (!canvas || typeof Chart === 'undefined') {
      if (state) { state.textContent = 'Chart visualization is unavailable.'; state.hidden = false; }
      return;
    }
    const chart = Chart.getChart(canvas);
    if (!chart) {
      if (state) { state.textContent = 'Chart visualization is unavailable.'; state.hidden = false; }
      return;
    }
    const requestId = (sparklineRequestIds.get(pair.pair) || 0) + 1;
    sparklineRequestIds.set(pair.pair, requestId);
    chart.data.labels = [];
    chart.data.datasets.forEach(dataset => { dataset.data = []; });
    chart.update();
    try {
      const response = await fetch(`${API_BASE}/api/analytics/spreads?pair=${encodeURIComponent(pair.pair)}&window=14&end_date=${encodeURIComponent(pair.trade_date)}`);
      if (sparklineRequestIds.get(pair.pair) !== requestId) return;
      if (!response.ok) {
        const state = card.querySelector('.sparkline-empty-state');
        if (state) { state.textContent = 'Synchronized spread history unavailable.'; state.hidden = false; }
        return;
      }
      const json = await response.json();
      if (sparklineRequestIds.get(pair.pair) !== requestId) return;
      const points = json?.success && Array.isArray(json?.data?.data_points) ? json.data.data_points : [];
      const plottablePoints = points.filter(point => point?.spread != null && Number.isFinite(Number(point.spread)));
      chart.data.labels = plottablePoints.map(point => point.trade_date);
      chart.data.datasets.forEach(dataset => { dataset.data = plottablePoints.map(point => Number(point.spread)); });
      chart.update();
      if (state) {
        state.textContent = plottablePoints.length ? '' : 'No eligible synchronized spread history returned.';
        state.hidden = plottablePoints.length > 0;
      }
    } catch (error) {
      if (sparklineRequestIds.get(pair.pair) === requestId) {
        console.warn(`AURORA: ${pair.pair} spread history unavailable:`, error);
        const state = card.querySelector('.sparkline-empty-state');
        if (state) { state.textContent = 'Synchronized spread history unavailable.'; state.hidden = false; }
      }
    }
  }

  function renderRadarFunnel(pairs) {
    const totalPairs = pairs.length || 6;
    const observedPairs = pairs.filter(pair => pair && pair.spread != null && Number.isFinite(Number(pair.spread)));
    const observed = observedPairs.length;
    const unavailable = Math.max(0, pairs.length - observed);
    const liquidityAssessed = observedPairs.filter(pair => pair.min_volume != null && pair.min_open_interest != null && pair.is_liquidity_trap != null);
    const liquidPairs = liquidityAssessed.filter(pair => pair.is_liquidity_trap === false);
    const expiryAssessed = liquidPairs.filter(pair => pair.dte_min != null && pair.is_expiry_risk != null);
    const expiryPairs = expiryAssessed.filter(pair => pair.is_expiry_risk === false);
    const costAssessed = expiryPairs.filter(pair => pair.gross_edge != null && pair.estimated_cost_hurdle != null && pair.is_cost_blocked != null);
    const costPairs = costAssessed.filter(pair => pair.is_cost_blocked === false);
    const liquid = liquidPairs.length;
    const expiry = expiryPairs.length;
    const cost = costPairs.length;
    const investigate = costPairs.filter(pair => pair.classification === 'Investigate').length;
    const liquidityUnassessed = observed - liquidityAssessed.length;
    const expiryUnassessed = liquidPairs.length - expiryAssessed.length;
    const costUnassessed = expiryPairs.length - costAssessed.length;
    const set = (id, value) => { const el = document.getElementById(id); if (el) el.textContent = value; };
    const pct = count => observed ? `${(count / observed * 100).toFixed(0)}%` : '—';
    const counts = [observed, liquid, expiry, cost, investigate];
    const names = ['Matched pairs', 'Liquidity pass', 'Expiry pass', 'Cost pass', 'Investigate'];
    const summary = document.getElementById('radarPipelineSummary');
    if (summary) summary.textContent = `${observed}/${totalPairs} matched · ${unavailable} unavailable → ${names.slice(1).map((name, i) => `${name} ${observed ? counts[i + 1] : '—'}`).join(' → ')}`;
    set('radarStageObserved', `${observed}/${totalPairs} matched`);
    set('radarStageLiquidity', `${observed ? liquid : '—'} Passed`);
    set('radarStageLiquidityDrop', `${observed ? liquidityAssessed.length - liquid : '—'} flagged · ${observed ? liquidityUnassessed : '—'} unassessed`);
    set('radarStageExpiry', `${observed ? expiry : '—'} Passed`);
    set('radarStageExpiryDrop', `${observed ? expiryAssessed.length - expiry : '—'} flagged · ${observed ? expiryUnassessed : '—'} unassessed`);
    set('radarStageCost', `${observed ? cost : '—'} Passed`);
    set('radarStageCostDrop', `${observed ? costAssessed.length - cost : '—'} flagged · ${observed ? costUnassessed : '—'} unassessed`);
    set('radarStageInvestigate', `${observed ? investigate : '—'} Investigate`);
    set('radarFunnelObserved', `${observed ? observed : '—'} pairs (${observed ? '100%' : '—'})`);
    set('radarFunnelLiquidity', `${observed ? liquid : '—'} pairs (${observed ? pct(liquid) : '—'})`);
    set('radarFunnelExpiry', `${observed ? expiry : '—'} pairs (${observed ? pct(expiry) : '—'})`);
    set('radarFunnelCost', `${observed ? cost : '—'} pairs (${observed ? pct(cost) : '—'})`);
    set('radarFunnelInvestigate', `${observed ? investigate : '—'} pairs (${observed ? pct(investigate) : '—'})`);
    const setTag = (id, text, isReject, isNeutral) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.textContent = text;
      el.className = 'trap-tag-eliminated' + (isReject ? '' : isNeutral ? ' trap-tag-neutral' : ' trap-tag-pass');
    };
    const setRowState = (rowId, hasFlag) => {
      const row = document.getElementById(rowId);
      if (!row) return;
      row.style.borderLeftColor = hasFlag ? 'var(--danger-red, #ef4444)' : 'var(--success-green, #10b981)';
    };
    const liqFlagged = observedPairs.filter(p => p.is_liquidity_trap === true).length;
    const expFlagged = observedPairs.filter(p => p.is_expiry_risk === true).length;
    const costFlagged = observedPairs.filter(p => p.is_cost_blocked === true).length;
    const noSigCount = observedPairs.filter(p => p.classification === 'No Signal').length;
    set('radarDiagnosticLiquidity', observed ? (liqFlagged + ' flagged · ' + liquidityUnassessed + ' unassessed') : '—');
    set('radarDiagnosticExpiry', observed ? (expFlagged + ' flagged · ' + observedPairs.filter(p => p.dte_min == null || p.is_expiry_risk == null).length + ' unassessed') : '—');
    set('radarDiagnosticCost', observed ? (costFlagged + ' flagged · ' + observedPairs.filter(p => p.gross_edge == null || p.estimated_cost_hurdle == null || p.is_cost_blocked == null).length + ' unassessed') : '—');
    set('radarDiagnosticNoSignal', observed ? String(noSigCount) : '—');
    if (observed) {
      setTag('radarTagLiquidity', liqFlagged > 0 ? ('Stage 2: ' + liqFlagged + ' Flagged') : 'Stage 2: 0 Flagged (Pass)', liqFlagged > 0, false);
      setTag('radarTagExpiry', expFlagged > 0 ? ('Stage 3: ' + expFlagged + ' Flagged') : 'Stage 3: 0 Flagged (Pass)', expFlagged > 0, false);
      setTag('radarTagCost', costFlagged > 0 ? ('Stage 4: ' + costFlagged + ' Flagged') : 'Stage 4: 0 Flagged (Pass)', costFlagged > 0, false);
      setTag('radarTagNoSignal', noSigCount > 0 ? ('Stage 5: ' + noSigCount + ' Inactive') : 'Stage 5: 0 Inactive', false, noSigCount > 0);
      setRowState('radarRowLiquidity', liqFlagged > 0);
      setRowState('radarRowExpiry', expFlagged > 0);
      setRowState('radarRowCost', costFlagged > 0);
    } else {
      setTag('radarTagLiquidity', 'Stage 2: —', false, true);
      setTag('radarTagExpiry', 'Stage 3: —', false, true);
      setTag('radarTagCost', 'Stage 4: —', false, true);
      setTag('radarTagNoSignal', 'Stage 5: —', false, true);
    }
    document.querySelectorAll('.funnel-fill').forEach((bar, index) => { bar.style.width = observed ? `${counts[index] / observed * 100}%` : '0%'; });
  }


  function updateRadarFreshnessIndicator(statusData, errorMsg) {
    const banner = document.getElementById('radarFreshnessBanner');
    if (!banner) return;

    const datasetEl = document.getElementById('radarFreshnessDataset');
    const dateEl = document.getElementById('radarLatestObsDate');
    const ageEl = document.getElementById('radarObsAgeBadge');
    const feedStatusEl = document.getElementById('radarFeedStatus');
    const warningEl = document.getElementById('radarStaleWarning');
    const warningTextEl = document.getElementById('radarStaleWarningText');
    const dotEl = banner.querySelector('.freshness-pulse-dot');
    const sidebarTime = document.getElementById('live-sidebar-time');

    if (!statusData) {
      if (datasetEl) datasetEl.textContent = 'Historical Dataset';
      if (dateEl) dateEl.textContent = 'Unavailable';
      if (ageEl) {
        ageEl.textContent = 'Age -';
        ageEl.className = 'freshness-age-badge';
      }
      if (feedStatusEl) {
        feedStatusEl.textContent = 'UNAVAILABLE';
        feedStatusEl.className = '';
      }
      if (warningEl) {
        warningEl.style.display = 'flex';
        if (warningTextEl) {
          warningTextEl.textContent = errorMsg || 'Market status unavailable. Live feed disconnected.';
        }
      }
      if (dotEl) dotEl.className = 'freshness-pulse-dot stale';
      return;
    }

    const isLive = statusData.feed_status === 'LIVE' && statusData.is_live_connected === true;
    const latestDateStr = statusData.latest_trade_date;
    const dataMode = statusData.data_mode;

    // 1. Clearly label dataset provenance (Historical CSV vs Live)
    let datasetLabel = 'Historical CSV Data (Not Live)';
    if (isLive) {
      datasetLabel = 'Verified Live MCX Feed';
    } else if (dataMode === 'test_data') {
      datasetLabel = 'Test Data (Excluded from Analysis)';
    } else if (dataMode === 'demo_synthetic') {
      datasetLabel = 'Synthetic Demo Data (Excluded)';
    } else if (statusData.data_freshness_label && statusData.data_freshness_label.includes('User-imported historical CSV')) {
      datasetLabel = 'Historical CSV Data (Bhavcopy)';
    }
    if (datasetEl) datasetEl.textContent = datasetLabel;

    // 2. Display latest available market observation date
    if (dateEl) {
      dateEl.textContent = latestDateStr ? latestDateStr : 'No observation dates';
    }
    if (sidebarTime && latestDateStr) {
      sidebarTime.textContent = latestDateStr + ' (Close)';
    }

    // 3. Calculate and display age of latest observation in calendar days
    let ageDays = null;
    if (latestDateStr) {
      try {
        const obsDate = new Date(latestDateStr + 'T00:00:00Z');
        const refDate = statusData.server_time ? new Date(statusData.server_time) : new Date();
        const diffMs = refDate.getTime() - obsDate.getTime();
        ageDays = Math.max(0, Math.floor(diffMs / (1000 * 60 * 60 * 24)));
      } catch (e) {
        ageDays = null;
      }
    }

    // Daily MCX settlement is expected within 1 calendar/business day
    const isStale = !isLive && (ageDays === null || ageDays >= 1);

    if (ageEl) {
      if (ageDays !== null) {
        ageEl.textContent = ageDays === 0 ? 'Today (<24h)' : (ageDays + ' calendar day' + (ageDays === 1 ? '' : 's') + ' old');
        ageEl.className = 'freshness-age-badge' + (isStale ? ' stale' : '');
      } else {
        ageEl.textContent = 'Age unknown';
        ageEl.className = 'freshness-age-badge';
      }
    }

    // 4. Feed status: never imply feed is live or snapshot is live opportunity
    if (feedStatusEl) {
      feedStatusEl.textContent = statusData.feed_status || 'UNAVAILABLE';
      feedStatusEl.className = isLive ? 'live' : '';
    }

    if (dotEl) {
      dotEl.className = 'freshness-pulse-dot ' + (isLive ? 'live' : isStale ? 'stale' : '');
    }

    // 5. Stale-data warning when older than expected reporting period
    if (warningEl) {
      if (isStale || !isLive) {
        warningEl.style.display = 'flex';
        let notice = '';
        if (ageDays !== null && ageDays > 0) {
          notice = 'Stale Data Warning: Latest observation is ' + ageDays + ' calendar day' + (ageDays === 1 ? '' : 's') + ' old (' + latestDateStr + '). ';
        } else {
          notice = 'Historical Snapshot: ';
        }
        notice += 'Feed is UNAVAILABLE. Spreads reflect historical settlement, not live execution opportunities.';
        if (warningTextEl) warningTextEl.textContent = notice;
      } else {
        warningEl.style.display = 'none';
      }
    }
  }

  function ensureLiveBadge(pairCount) {
    const badge = document.querySelector('.live-radar-badge');
    const total = Math.max(6, document.querySelectorAll('.matrix-table tbody tr').length);
    if (badge) badge.textContent = `Historical data · ${pairCount}/${total} pairs with matched snapshots`;
  }
})();
