/**
 * AURORA Commodity Intelligence — Data Pipeline & Ingestion Client (Phase 1)
 * Preserves all existing styles, animations, and pages.
 * Connects frontend to FastAPI backend:
 * - Real backend health & market status surveillance
 * - Interactive CSV Bhavcopy ingestion modal with validation diagnostics
 * - Real-time contract & normalized price inspection
 */

(function () {
  const API_BASE = 'http://127.0.0.1:8000';
  let backendOnline = false;

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
    setTimeout(initPhase2AnalyticsSync, 400);
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
        statusChip.style.background = 'rgba(16, 185, 129, 0.15)';
        statusChip.style.borderColor = 'rgba(16, 185, 129, 0.4)';
        statusChip.style.color = '#34d399';
        statusChip.title = `Backend Connected: ${payload.provider_name || 'Static DB'}`;
        statusChip.innerHTML = `
          <div class="live-pulse-dot" style="background:#10b981;box-shadow:0 0 10px #10b981;"></div>
          <span>API LIVE &bull; ${formatDataMode(payload.data_mode)}</span>
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

  function formatDataMode(mode) {
    if (mode === 'staged_csv') return 'Staged CSV Data';
    if (mode === 'live_feed_authorized') return 'Authorized Live Feed';
    return 'Demo Mode (Synthetic)';
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
    feedbackBox.className = 'feedback-box loading';
    feedbackBox.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Ingesting and validating ${file.name}...`;
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

      container.innerHTML = `
        <table class="aurora-pipeline-table">
          <thead>
            <tr>
              <th>Batch #</th>
              <th>Filename</th>
              <th>Accepted</th>
              <th>Rejected</th>
              <th>Total Rows</th>
              <th>Checksum (SHA-256)</th>
              <th>Import Timestamp</th>
            </tr>
          </thead>
          <tbody>
            ${batches.map(b => `
              <tr>
                <td><b>#${b.id}</b></td>
                <td><code>${b.filename}</code></td>
                <td style="color:#34d399;font-weight:600;">${b.accepted_rows}</td>
                <td style="color:${b.rejected_rows > 0 ? '#f87171' : 'var(--text-dim)'};">${b.rejected_rows}</td>
                <td>${b.total_rows}</td>
                <td><small style="font-family:monospace;">${b.file_hash.slice(0, 16)}...</small></td>
                <td>${new Date(b.created_at).toLocaleString()}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
    } catch (e) {
      container.innerHTML = `<div class="table-empty" style="color:#f87171;">Error loading batches: ${e.message}</div>`;
    }
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
        background: rgba(56, 189, 248, 0.12);
        border: 1px solid rgba(56, 189, 248, 0.35);
        color: #7dd3fc;
      }
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
    `;
    document.head.appendChild(style);
  }

  /* --------------------------------------------------------------------------
     4. Phase 2 Relative-Value Intelligence Engine Frontend Integration
     -------------------------------------------------------------------------- */
  function initPhase2AnalyticsSync() {
    if (document.getElementById('radarChartCanvas')) {
      setupOpportunityRadarSync();
    }
    if (document.getElementById('eventSelector')) {
      setupMarketDetectiveSync();
    }
  }

  async function setupOpportunityRadarSync() {
    await loadLiveRadarData();
    await loadLiveDistributionData('GOLDM-GOLDPETAL');

    const refreshBtn = document.getElementById('refresh-radar-btn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => {
        loadLiveRadarData();
        const activeTab = document.querySelector('.dist-tab-btn.active');
        const activePair = activeTab ? (activeTab.id === 'tab-guinea-ten' ? 'GOLDGUINEA-GOLDTEN' : (activeTab.id === 'tab-goldm-ten' ? 'GOLDM-GOLDTEN' : 'GOLDM-GOLDPETAL')) : 'GOLDM-GOLDPETAL';
        loadLiveDistributionData(activePair);
      });
    }

    const tabPetal = document.getElementById('tab-goldm-petal');
    const tabGuinea = document.getElementById('tab-guinea-ten');
    const tabTen = document.getElementById('tab-goldm-ten');

    if (tabPetal) tabPetal.addEventListener('click', () => loadLiveDistributionData('GOLDM-GOLDPETAL'));
    if (tabGuinea) tabGuinea.addEventListener('click', () => loadLiveDistributionData('GOLDGUINEA-GOLDTEN'));
    if (tabTen) tabTen.addEventListener('click', () => loadLiveDistributionData('GOLDM-GOLDTEN'));
  }

  async function loadLiveRadarData() {
    try {
      const res = await fetch(`${API_BASE}/api/analytics/radar?window=30`);
      if (!res.ok) return;
      const json = await res.json();
      if (!json.success || !json.data || !json.data.pairs || json.data.pairs.length === 0) return;

      const pairs = json.data.pairs;
      const pairMap = {};
      pairs.forEach(p => {
        pairMap[p.pair] = p;
        const inv = p.pair.split('-').reverse().join('-');
        pairMap[inv] = p;
      });

      // Update Radar Polar Chart
      if (typeof Chart !== 'undefined') {
        const radarChart = Chart.getChart('radarChartCanvas');
        if (radarChart && radarChart.data && radarChart.data.labels) {
          const newData = radarChart.data.labels.map(lbl => {
            const p = pairMap[lbl];
            return p ? Math.round(p.deviation_intensity) : 30;
          });
          radarChart.data.datasets[0].data = newData;
          radarChart.update();
        }
      }

      // Update Top Anomaly in Hero Stat Claybox
      const sorted = [...pairs].filter(p => p.spread !== null).sort((a, b) => (b.opportunity_score || 0) - (a.opportunity_score || 0));
      const top = sorted[0];
      if (top && top.spread !== null) {
        const titleEl = document.querySelector('.headline-pair-title');
        if (titleEl) titleEl.textContent = `${top.leg_a} vs ${top.leg_b}`;

        const spreadSub = document.querySelector('.hero-stat-claybox .mono');
        if (spreadSub) {
          spreadSub.innerHTML = `<span style="color: var(--gold-bright); font-weight: 700;">${top.spread >= 0 ? '+' : ''}₹${top.spread.toFixed(2)}/10g</span>`;
        }

        const metricsCells = document.querySelectorAll('.headline-metric-cell .value');
        if (metricsCells.length >= 3) {
          if (top.z_score !== null) metricsCells[0].textContent = `${top.z_score >= 0 ? '+' : ''}${top.z_score.toFixed(2)}σ`;
          if (top.percentile_rank !== null) metricsCells[1].textContent = `${top.percentile_rank.toFixed(1)}%`;
          metricsCells[2].textContent = `${Math.round(top.opportunity_score)}%`;
        }
      }

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
            if (p && p.spread !== null) {
              const sign = (p.leg_a === rowContract) ? 1 : -1;
              const cellSpread = (p.spread * sign).toFixed(2);
              const cellZ = p.z_score !== null ? (p.z_score * sign).toFixed(2) : 'N/A';
              td.innerHTML = `${cellSpread > 0 ? '+' : ''}${cellSpread}<br><span style="font-size:0.6rem;">${cellZ}σ</span>`;
              td.title = `Spread: ₹${cellSpread} | Z: ${cellZ}σ (${p.classification})`;
            }
          });
        });
      }

      // Update Active Signal Cards
      pairs.forEach(p => {
        if (p.spread === null) return;
        const card = document.querySelector(`.signal-card[data-pair="${p.pair}"]`) ||
                     document.querySelector(`.signal-card[data-pair="${p.pair.split('-').reverse().join('-')}"]`);
        if (card) {
          const spreadEl = card.querySelector('.stat-num');
          if (spreadEl) spreadEl.innerHTML = `₹${p.spread.toFixed(2)} <span class="stat-subtext">/ 10g</span>`;

          const zCell = card.querySelectorAll('.stat-num')[1];
          if (zCell && p.z_score !== null) {
            zCell.innerHTML = `${p.z_score >= 0 ? '+' : ''}${p.z_score.toFixed(2)}σ <span class="stat-subtext">${Math.abs(p.z_score) > 2 ? 'extreme' : 'moderate'}</span>`;
          }

          const pctCell = card.querySelectorAll('.stat-num')[2];
          if (pctCell && p.percentile_rank !== null) {
            pctCell.innerHTML = `${p.percentile_rank.toFixed(1)}% <span class="stat-subtext">30d</span>`;
          }

          const radialText = card.querySelector('.radial-text');
          if (radialText) radialText.textContent = `${Math.round(p.opportunity_score)}%`;

          const pill = card.querySelector('.severity-pill');
          if (pill) {
            pill.innerHTML = `<i class="fa-solid fa-satellite-dish"></i> ${p.classification.toUpperCase()}`;
            if (p.classification === 'Investigate') {
              pill.className = 'severity-pill pill-critical';
            } else if (p.classification === 'Cost-Blocked' || p.classification === 'Expiry-Risk') {
              pill.className = 'severity-pill pill-high';
            } else {
              pill.className = 'severity-pill pill-medium';
            }
          }
        }
      });

      ensureLiveBadge();
    } catch (e) {
      console.warn('AURORA: Error syncing live radar data:', e);
    }
  }

  async function loadLiveDistributionData(pairKey) {
    try {
      const res = await fetch(`${API_BASE}/api/analytics/distribution?pair=${encodeURIComponent(pairKey)}&window=365&bins=15`);
      if (!res.ok) return;
      const json = await res.json();
      if (!json.success || !json.data || json.data.sample_size === 0) return;

      const d = json.data;
      const meanEl = document.getElementById('stat-mean');
      const sigmaEl = document.getElementById('stat-sigma');
      const medEl = document.getElementById('stat-median');
      const kurtEl = document.getElementById('stat-kurtosis');
      const skewEl = document.getElementById('stat-skewness');
      const zEl = document.getElementById('stat-current-z');

      if (meanEl && d.mean !== null) meanEl.textContent = `₹${d.mean.toFixed(2)}`;
      if (sigmaEl && d.sigma !== null) sigmaEl.textContent = `₹${d.sigma.toFixed(2)}`;
      if (medEl && d.median !== null) medEl.textContent = `₹${d.median.toFixed(2)}`;
      if (kurtEl && d.kurtosis !== null) kurtEl.textContent = d.kurtosis;
      if (skewEl && d.skewness !== null) skewEl.textContent = `${d.skewness >= 0 ? '+' : ''}${d.skewness.toFixed(2)}`;
      if (zEl && d.current_z_score) zEl.textContent = d.current_z_score;

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
      console.warn('AURORA: Error syncing live distribution data:', e);
    }
  }

  async function setupMarketDetectiveSync() {
    try {
      const res = await fetch(`${API_BASE}/api/analytics/events?limit=30`);
      if (!res.ok) return;
      const json = await res.json();
      if (!json.success || !json.data || !json.data.items || json.data.items.length === 0) return;

      const events = json.data.items;
      const selector = document.getElementById('eventSelector');
      if (!selector) return;

      window.AURORA_LIVE_EVENTS = {};
      const optGroup = document.createElement('optgroup');
      optGroup.label = '⚡ Live MCX Relative-Value Investigations';

      events.forEach((evt, idx) => {
        window.AURORA_LIVE_EVENTS[evt.event_id] = evt;
        const opt = document.createElement('option');
        opt.value = evt.event_id;
        opt.textContent = `${evt.event_id} — ${evt.pair} (${evt.classification} | Z=${evt.evidence.z_score >= 0 ? '+' : ''}${evt.evidence.z_score}σ)`;
        if (idx === 0) opt.selected = true;
        optGroup.appendChild(opt);
      });

      selector.insertBefore(optGroup, selector.firstChild);

      selector.addEventListener('change', (e) => {
        const evtId = e.target.value;
        if (window.AURORA_LIVE_EVENTS && window.AURORA_LIVE_EVENTS[evtId]) {
          renderLiveEventDossier(window.AURORA_LIVE_EVENTS[evtId]);
        }
      });

      renderLiveEventDossier(events[0]);
    } catch (e) {
      console.warn('AURORA: Error loading live detective events:', e);
    }
  }

  async function renderLiveEventDossier(evt) {
    if (!evt) return;

    const scoreVal = document.getElementById('verdictScoreVal');
    const badgeText = document.getElementById('verdictBadgeText');
    const keyFinding = document.getElementById('verdictKeyFinding');
    const recommendation = document.getElementById('verdictRecommendation');
    const circle = document.getElementById('scoreProgressCircle');

    if (scoreVal) scoreVal.textContent = Math.round(evt.opportunity_score);
    if (badgeText) badgeText.textContent = evt.classification.toUpperCase();
    if (circle) {
      const offset = 240 - (240 * (evt.opportunity_score / 100));
      circle.style.strokeDashoffset = String(offset);
    }
    if (keyFinding) {
      keyFinding.innerHTML = `<strong>${evt.pair}</strong> spread dislocated to <strong>₹${evt.evidence.spread.toFixed(2)}/10g</strong> (${evt.evidence.z_score >= 0 ? '+' : ''}${evt.evidence.z_score}σ, ${evt.evidence.percentile_rank}th %ile). Rule triggered: ${evt.evidence.rule_triggered}`;
    }
    if (recommendation) {
      if (evt.classification === 'Investigate') {
        recommendation.innerHTML = `<strong>Actionable Opportunity:</strong> Spread divergence survives estimated transaction friction (Net Edge: ₹${(evt.evidence.net_edge || 0).toFixed(2)}/10g). Maintain active surveillance.`;
      } else if (evt.classification === 'Cost-Blocked') {
        recommendation.innerHTML = `<strong>Cost Trap Warning:</strong> Gross edge (₹${(evt.evidence.gross_edge || 0).toFixed(2)}/10g) is below the ₹${evt.evidence.cost_hurdle.toFixed(2)}/10g execution hurdle. Dismiss execution.`;
      } else if (evt.classification === 'Expiry-Risk') {
        recommendation.innerHTML = `<strong>Lifecycle Boundary:</strong> Contract is entering delivery roll period. Physical delivery and tender noise dominate spread. Avoid position.`;
      } else {
        recommendation.innerHTML = `<strong>Watch Status:</strong> Spread deviation under active algorithmic observation. Awaiting liquidity confirmation.`;
      }
    }

    const s1 = document.getElementById('step1Card');
    if (s1) {
      const vals = s1.querySelectorAll('.detail-val');
      if (vals.length >= 2) vals[1].textContent = evt.trade_date;
    }

    const s2 = document.getElementById('step2Card');
    if (s2) {
      const vals = s2.querySelectorAll('.detail-val.gold');
      if (vals.length >= 2) {
        vals[0].textContent = `${evt.leg_a} Standardized`;
        vals[1].textContent = `${evt.leg_b} Standardized`;
      }
    }

    const s3 = document.getElementById('step3Card');
    if (s3) {
      const rawVal = s3.querySelector('.detail-val.gold');
      if (rawVal) rawVal.textContent = `₹${evt.evidence.spread.toFixed(2)} / 10g`;
      const allVals = s3.querySelectorAll('.detail-val');
      if (allVals.length >= 2) {
        const pct = ((evt.evidence.spread / 62500) * 100).toFixed(3);
        allVals[1].textContent = `${pct}%`;
      }
    }

    const s4 = document.getElementById('step4Card');
    if (s4) {
      const goldVals = s4.querySelectorAll('.detail-val.gold');
      if (goldVals.length >= 2) {
        goldVals[0].textContent = `${evt.evidence.z_score >= 0 ? '+' : ''}${evt.evidence.z_score.toFixed(2)}σ (30d)`;
        goldVals[1].textContent = `${evt.evidence.percentile_rank.toFixed(1)}%`;
      }
      const meterFill = s4.querySelector('.z-meter-fill');
      if (meterFill) {
        const pctPos = Math.min(100, Math.max(0, ((evt.evidence.z_score + 3) / 6) * 100));
        meterFill.style.width = `${pctPos}%`;
      }
    }

    const s5 = document.getElementById('step5Card');
    if (s5) {
      const vals = s5.querySelectorAll('.detail-val');
      if (vals.length >= 3) {
        vals[0].textContent = `${evt.evidence.volume_a.toLocaleString()} lots`;
        vals[1].textContent = `${evt.evidence.volume_b.toLocaleString()} lots`;
        vals[2].textContent = `${(evt.evidence.open_interest_a + evt.evidence.open_interest_b).toLocaleString()} contracts`;
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
      if (goldVal) goldVal.textContent = `₹${(evt.evidence.net_edge || 0).toFixed(2)} / 10g`;
    }

    const aiText = document.getElementById('aiParagraphText');
    if (aiText) {
      aiText.innerHTML = `
        <p>
          Quantitative surveillance of MCX gold derivatives has detected a relative-value event for <strong>${evt.pair}</strong> on <strong>${evt.trade_date}</strong>. Following fine-gold purity normalization to a 995 benchmark basis, the normalized spread closed at <strong>₹${evt.evidence.spread.toFixed(2)} per 10g</strong> against a 30-day rolling mean of <strong>₹${(evt.evidence.rolling_mean || 0).toFixed(2)}</strong>.
        </p>
        <p>
          This represents a gross dislocation of <strong>₹${(evt.evidence.gross_edge || 0).toFixed(2)}/10g</strong>, placing the pair at <strong>${evt.evidence.z_score >= 0 ? '+' : ''}${evt.evidence.z_score.toFixed(2)} standard deviations</strong> (${evt.evidence.percentile_rank.toFixed(1)}th empirical percentile). Transaction cost modeling calculates round-trip trading friction (STT, exchange turnover fees, SEBI charges, and bid-ask slippage) at <strong>₹${evt.evidence.cost_hurdle.toFixed(2)} per 10g</strong>. Estimated net edge is <strong>₹${(evt.evidence.net_edge || 0).toFixed(2)}/10g</strong>. Event classification: <strong style="color:var(--gold-bright);">${evt.classification}</strong>.
        </p>
      `;
    }

    const rawPre = document.getElementById('rawPayloadBlock');
    if (rawPre) {
      rawPre.textContent = JSON.stringify(evt, null, 2);
    }

    try {
      const spreadRes = await fetch(`${API_BASE}/api/analytics/spreads?pair=${encodeURIComponent(evt.pair)}&window=30`);
      if (spreadRes.ok) {
        const spreadJson = await spreadRes.json();
        if (spreadJson.success && spreadJson.data && spreadJson.data.data_points) {
          const pts = spreadJson.data.data_points;
          const chart = Chart.getChart('spreadChartCanvas');
          if (chart && pts.length > 0) {
            chart.data.labels = pts.map(p => p.trade_date);
            if (chart.data.datasets[0]) chart.data.datasets[0].data = pts.map(p => p.upper_2sigma);
            if (chart.data.datasets[1]) chart.data.datasets[1].data = pts.map(p => p.rolling_mean);
            if (chart.data.datasets[2]) chart.data.datasets[2].data = pts.map(p => p.lower_2sigma);
            if (chart.data.datasets[3]) chart.data.datasets[3].data = pts.map(p => p.spread);
            chart.update();
          }

          const voiChart = Chart.getChart('volumeOIChartCanvas');
          if (voiChart && pts.length > 0) {
            voiChart.data.labels = pts.map(p => p.trade_date);
            if (voiChart.data.datasets[0]) voiChart.data.datasets[0].data = pts.map(p => p.volume_a);
            if (voiChart.data.datasets[1]) voiChart.data.datasets[1].data = pts.map(p => p.volume_b);
            voiChart.update();
          }
        }
      }
    } catch (e) {
      console.warn('AURORA: Error updating detective chart series:', e);
    }
  }

  function ensureLiveBadge() {
    if (document.querySelector('.live-radar-badge')) return;
    const headerRight = document.querySelector('.header-right');
    if (headerRight) {
      const badge = document.createElement('div');
      badge.className = 'live-radar-badge';
      badge.style.cssText = 'display:inline-flex; align-items:center; gap:6px; font-size:11.5px; padding:5px 12px; border-radius:20px; background:rgba(16,185,129,0.14); border:1px solid rgba(16,185,129,0.35); color:#34d399; font-family:var(--font-mono); font-weight:600;';
      badge.innerHTML = '<span style="width:7px;height:7px;border-radius:50%;background:#10b981;box-shadow:0 0 8px #10b981;"></span>RV ENGINE SYNCED (6 PAIRS)';
      headerRight.insertBefore(badge, headerRight.firstChild);
    }
  }
})();
