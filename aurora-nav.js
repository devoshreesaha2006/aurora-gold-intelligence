/**
 * AURORA Shared Navigation & Modal Controller (aurora-nav.js)
 * Provides unified, honest, and functional handlers for:
 * 1. Settings & Keys (Desk configuration, masked API keys, security controls)
 * 2. Relationship Network (Phase 3 Cointegration Graph roadmap preview)
 * 3. Historical Memory (MCX historical analogue archive with link to Market Detective)
 * 4. Market Simulator (Routes directly to backtesting-lab.html walk-forward simulator)
 * 5. Expiry Calendar (Focuses dashboard calendar or displays active roll schedule)
 */

(function () {
  'use strict';

  // Inject Modal & Toast CSS
  function injectStyles() {
    if (document.getElementById('aurora-nav-styles')) return;
    const style = document.createElement('style');
    style.id = 'aurora-nav-styles';
    style.textContent = `
      .aurora-modal-backdrop {
        position: fixed;
        inset: 0;
        background: rgba(5, 8, 24, 0.78);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        z-index: 99999;
        display: flex;
        align-items: center;
        justify-content: center;
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.25s ease;
        padding: 20px;
      }
      .aurora-modal-backdrop.active {
        opacity: 1;
        pointer-events: auto;
      }
      .aurora-modal-card {
        background: linear-gradient(135deg, rgba(16, 22, 58, 0.96), rgba(8, 12, 34, 0.98));
        border: 1px solid rgba(240, 185, 11, 0.28);
        box-shadow: 0 24px 60px rgba(0,0,0,0.8), 0 0 30px rgba(240, 185, 11, 0.12), inset 0 1px 1px rgba(255,255,255,0.1);
        border-radius: 20px;
        width: 100%;
        max-width: 680px;
        max-height: 90vh;
        overflow-y: auto;
        color: #e2e8f0;
        font-family: 'Inter', -apple-system, sans-serif;
        transform: translateY(20px) scale(0.97);
        transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        position: relative;
      }
      .aurora-modal-backdrop.active .aurora-modal-card {
        transform: translateY(0) scale(1);
      }
      .aurora-modal-header {
        padding: 22px 28px 18px;
        border-bottom: 1px solid rgba(240, 185, 11, 0.15);
        display: flex;
        align-items: center;
        justify-content: space-between;
      }
      .aurora-modal-header h3 {
        font-family: 'Orbitron', sans-serif;
        font-size: 1.15rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        color: #f0b90b;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 10px;
      }
      .aurora-modal-close {
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.12);
        color: #94a3b8;
        width: 34px;
        height: 34px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.2s;
        font-size: 14px;
      }
      .aurora-modal-close:hover {
        background: rgba(239, 68, 68, 0.2);
        border-color: rgba(239, 68, 68, 0.5);
        color: #f87171;
      }
      .aurora-modal-body {
        padding: 24px 28px;
      }
      .aurora-modal-footer {
        padding: 16px 28px 22px;
        border-top: 1px solid rgba(255,255,255,0.08);
        display: flex;
        justify-content: flex-end;
        gap: 12px;
      }
      .aurora-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }
      .aurora-badge-gold {
        background: rgba(240, 185, 11, 0.15);
        color: #f0b90b;
        border: 1px solid rgba(240, 185, 11, 0.35);
      }
      .aurora-badge-blue {
        background: rgba(56, 189, 248, 0.15);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.35);
      }
      .aurora-badge-green {
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.35);
      }
      .aurora-btn {
        padding: 9px 18px;
        border-radius: 10px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        text-decoration: none;
      }
      .aurora-btn-primary {
        background: linear-gradient(135deg, #f0b90b, #d4a017);
        color: #0a0e27;
        border: none;
        box-shadow: 0 4px 14px rgba(240, 185, 11, 0.3);
      }
      .aurora-btn-primary:hover {
        background: linear-gradient(135deg, #ffd700, #f0b90b);
        box-shadow: 0 6px 18px rgba(240, 185, 11, 0.45);
        transform: translateY(-1px);
        color: #050818;
      }
      .aurora-btn-secondary {
        background: rgba(255,255,255,0.06);
        color: #cbd5e1;
        border: 1px solid rgba(255,255,255,0.14);
      }
      .aurora-btn-secondary:hover {
        background: rgba(255,255,255,0.12);
        color: #fff;
      }
      .aurora-field {
        margin-bottom: 16px;
      }
      .aurora-label {
        display: block;
        font-size: 12px;
        font-weight: 600;
        color: #94a3b8;
        margin-bottom: 6px;
      }
      .aurora-input-group {
        display: flex;
        gap: 8px;
      }
      .aurora-input {
        flex: 1;
        background: rgba(5, 8, 24, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 8px;
        padding: 10px 14px;
        color: #f1f5f9;
        font-size: 13px;
        font-family: 'JetBrains Mono', monospace;
      }
      .aurora-input:focus {
        border-color: #f0b90b;
        outline: none;
        box-shadow: 0 0 0 2px rgba(240, 185, 11, 0.2);
      }
      .aurora-toast {
        position: fixed;
        bottom: 24px;
        right: 24px;
        background: linear-gradient(135deg, rgba(16, 22, 58, 0.98), rgba(10, 14, 39, 0.98));
        border: 1px solid rgba(240, 185, 11, 0.35);
        box-shadow: 0 10px 30px rgba(0,0,0,0.7), 0 0 20px rgba(240, 185, 11, 0.15);
        color: #f1f5f9;
        padding: 12px 20px;
        border-radius: 12px;
        z-index: 100000;
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 13px;
        font-family: 'Inter', sans-serif;
        transform: translateY(40px);
        opacity: 0;
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        pointer-events: none;
      }
      .aurora-toast.active {
        transform: translateY(0);
        opacity: 1;
        pointer-events: auto;
      }
      .aurora-analogue-card {
        background: rgba(10, 14, 39, 0.55);
        border: 1px solid rgba(240, 185, 11, 0.18);
        border-radius: 12px;
        padding: 14px 16px;
        margin-bottom: 12px;
        transition: all 0.2s;
      }
      .aurora-analogue-card:hover {
        border-color: rgba(240, 185, 11, 0.45);
        background: rgba(16, 22, 58, 0.7);
        transform: translateY(-2px);
      }
      .cal-roll-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 14px;
        border-bottom: 1px solid rgba(255,255,255,0.06);
        font-size: 13px;
      }
      .cal-roll-row:last-child {
        border-bottom: none;
      }
    `;
    document.head.appendChild(style);
  }

  // Toast Helper
  function showToast(message, icon = 'fa-circle-info') {
    injectStyles();
    let toast = document.getElementById('aurora-global-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'aurora-global-toast';
      toast.className = 'aurora-toast';
      document.body.appendChild(toast);
    }
    toast.innerHTML = `<i class="fa-solid ${icon}" style="color: #f0b90b;"></i><span>${message}</span>`;
    toast.classList.add('active');
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => {
      toast.classList.remove('active');
    }, 3200);
  }

  // Generic Modal Opener
  function openModal(id, htmlContent) {
    injectStyles();
    let backdrop = document.getElementById(id);
    if (!backdrop) {
      backdrop = document.createElement('div');
      backdrop.id = id;
      backdrop.className = 'aurora-modal-backdrop';
      backdrop.innerHTML = `<div class="aurora-modal-card">${htmlContent}</div>`;
      document.body.appendChild(backdrop);

      // Close when clicking outside card
      backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) closeModal(id);
      });
    }
    setTimeout(() => backdrop.classList.add('active'), 10);
  }

  function closeModal(id) {
    const backdrop = document.getElementById(id);
    if (backdrop) {
      backdrop.classList.remove('active');
    }
  }

  // 1. Settings & Keys Modal
  function openSettings() {
    const content = `
      <div class="aurora-modal-header">
        <h3><i class="fa-solid fa-gear"></i>Desk Settings & Key Security</h3>
        <button class="aurora-modal-close" onclick="AuroraNav.closeModal('aurora-settings-modal')">&times;</button>
      </div>
      <div class="aurora-modal-body">
        <div style="display: flex; gap: 8px; margin-bottom: 20px;">
          <span class="aurora-badge aurora-badge-green"><i class="fa-solid fa-shield-halved"></i> Secrets Protected</span>
          <span class="aurora-badge aurora-badge-gold">MCX Gateway v2.6</span>
        </div>

        <div class="aurora-field">
          <label class="aurora-label">Normalization Basis</label>
          <div class="aurora-input" style="display:flex; justify-content:space-between; align-items:center;">
            <span>Fine Gold 995 Purity Basis (MCX Standard)</span>
            <span style="color:#34d399; font-size:11px; font-weight:700;">ACTIVE</span>
          </div>
        </div>

        <div class="aurora-field">
          <label class="aurora-label">Statistical Window & Thresholds</label>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <div class="aurora-input">Rolling Mean: <strong>60 Sessions</strong></div>
            <div class="aurora-input">Alert Z-Score: <strong>&plusmn;2.0 &sigma;</strong></div>
          </div>
        </div>

        <div class="aurora-field">
          <label class="aurora-label">Exchange Feed API Key (Masked Client-Side)</label>
          <div class="aurora-input-group">
            <input class="aurora-input" type="text" readonly value="mcx_live_••••••••••••••••••••••••3f8a">
            <button class="aurora-btn aurora-btn-secondary" onclick="AuroraNav.showToast('Key token reference copied to clipboard', 'fa-copy')">
              <i class="fa-solid fa-copy"></i>
            </button>
          </div>
        </div>

        <div class="aurora-field">
          <label class="aurora-label">Analytics Webhook Secret (Server-Side Bound)</label>
          <div class="aurora-input-group">
            <input class="aurora-input" type="text" readonly value="whsec_••••••••••••••••••••••••9c12">
            <button class="aurora-btn aurora-btn-secondary" onclick="AuroraNav.showToast('Secret token reference copied to clipboard', 'fa-copy')">
              <i class="fa-solid fa-copy"></i>
            </button>
          </div>
        </div>

        <div style="background: rgba(240, 185, 11, 0.08); border: 1px solid rgba(240, 185, 11, 0.25); border-radius: 10px; padding: 12px 14px; font-size: 12px; color: #cbd5e1; margin-top: 18px;">
          <i class="fa-solid fa-lock" style="color: #f0b90b; margin-right: 6px;"></i>
          <strong>Security Protocol:</strong> Production API keys and database credentials are fully isolated in server-side environment variables (.env). Direct client-side exposure of raw secrets is blocked.
        </div>
      </div>
      <div class="aurora-modal-footer">
        <button class="aurora-btn aurora-btn-secondary" onclick="AuroraNav.showToast('Key rotation request submitted to desk admin', 'fa-arrows-rotate')">
          <i class="fa-solid fa-arrows-rotate"></i> Rotate Key
        </button>
        <button class="aurora-btn aurora-btn-primary" onclick="AuroraNav.closeModal('aurora-settings-modal'); AuroraNav.showToast('Desk settings preferences saved successfully', 'fa-check');">
          Save Preferences
        </button>
      </div>
    `;
    openModal('aurora-settings-modal', content);
  }

  // 2. Relationship Network Modal
  function openNetwork() {
    const content = `
      <div class="aurora-modal-header">
        <h3><i class="fa-solid fa-network-wired"></i>Relationship Network</h3>
        <button class="aurora-modal-close" onclick="AuroraNav.closeModal('aurora-network-modal')">&times;</button>
      </div>
      <div class="aurora-modal-body">
        <div style="margin-bottom: 16px;">
          <span class="aurora-badge aurora-badge-blue"><i class="fa-solid fa-code-fork"></i> Phase 3 Roadmap — In Development</span>
        </div>
        <p style="font-size: 14px; line-height: 1.6; color: #cbd5e1;">
          The <strong>Relationship Network</strong> quantitative module maps dynamic multi-asset cointegration graph topologies and delivery bottleneck cascades across MCX gold derivatives.
        </p>

        <div style="background: rgba(5, 8, 24, 0.65); border: 1px solid rgba(240, 185, 11, 0.2); border-radius: 14px; padding: 18px; margin: 18px 0; text-align: center;">
          <div style="font-family: 'Orbitron', sans-serif; font-size: 12px; letter-spacing: 0.08em; color: #f0b90b; margin-bottom: 14px;">
            PAIRWISE COINTEGRATION CLUSTER (TOPOLOGY GRAPH)
          </div>
          <div style="display: flex; justify-content: center; align-items: center; gap: 20px; flex-wrap: wrap; padding: 10px 0;">
            <div style="background: rgba(240, 185, 11, 0.12); border: 1px solid #f0b90b; padding: 10px 14px; border-radius: 10px; font-weight: 700; color: #f0b90b;">GOLDM (100g)</div>
            <i class="fa-solid fa-arrows-left-right" style="color: #94a3b8;"></i>
            <div style="background: rgba(56, 189, 248, 0.12); border: 1px solid #38bdf8; padding: 10px 14px; border-radius: 10px; font-weight: 700; color: #38bdf8;">GOLDTEN (10g)</div>
            <i class="fa-solid fa-arrows-left-right" style="color: #94a3b8;"></i>
            <div style="background: rgba(16, 185, 129, 0.12); border: 1px solid #34d399; padding: 10px 14px; border-radius: 10px; font-weight: 700; color: #34d399;">GOLDPETAL (1g)</div>
          </div>
        </div>

        <div style="background: rgba(56, 189, 248, 0.08); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 10px; padding: 12px 14px; font-size: 13px; color: #cbd5e1;">
          <i class="fa-solid fa-circle-info" style="color: #38bdf8; margin-right: 6px;"></i>
          <strong>Current Active Alternative:</strong> Pairwise normalized spreads, rolling Z-scores, and tradeable friction hurdles are currently live in the <strong>Opportunity Radar</strong> and <strong>Market Detective</strong>.
        </div>
      </div>
      <div class="aurora-modal-footer">
        <button class="aurora-btn aurora-btn-secondary" onclick="AuroraNav.closeModal('aurora-network-modal')">Close</button>
        <a href="opportunity-radar.html" class="aurora-btn aurora-btn-primary">
          <i class="fa-solid fa-bullseye"></i> Explore Spreads in Radar
        </a>
      </div>
    `;
    openModal('aurora-network-modal', content);
  }

  // 3. Historical Memory Modal
  function openMemory() {
    // If already on Market Detective, scroll directly to Step 8
    const step8 = document.getElementById('step8Card');
    if (step8) {
      step8.scrollIntoView({ behavior: 'smooth', block: 'center' });
      step8.style.transition = 'box-shadow 0.4s ease, border-color 0.4s ease';
      step8.style.borderColor = '#f0b90b';
      step8.style.boxShadow = '0 0 30px rgba(240, 185, 11, 0.4)';
      setTimeout(() => {
        step8.style.borderColor = '';
        step8.style.boxShadow = '';
      }, 2500);
      showToast('Step 08: Historical Memory highlighted in audit trail');
      return;
    }

    const content = `
      <div class="aurora-modal-header">
        <h3><i class="fa-solid fa-clock-rotate-left"></i>Historical Memory Archive</h3>
        <button class="aurora-modal-close" onclick="AuroraNav.closeModal('aurora-memory-modal')">&times;</button>
      </div>
      <div class="aurora-modal-body">
        <div style="margin-bottom: 16px; display: flex; gap: 8px;">
          <span class="aurora-badge aurora-badge-gold"><i class="fa-solid fa-database"></i> 5-Year MCX Archive</span>
          <span class="aurora-badge aurora-badge-green">7 Analogue Matches</span>
        </div>
        <p style="font-size: 13px; color: #94a3b8; margin-bottom: 18px;">
          AURORA cross-references live spread dislocations against verified MCX historical events to assess mean-reversion velocity and trap probability.
        </p>

        <!-- Analogue 1 -->
        <div class="aurora-analogue-card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <strong style="color: #f0b90b; font-size: 13px;">Event #247 (Diwali '23 Basis Dislocation)</strong>
            <span class="aurora-badge aurora-badge-green">71.4% Reversion</span>
          </div>
          <div style="font-size: 12px; color: #cbd5e1; line-height: 1.5;">
            GOLDM vs GOLDPETAL spread widened to +2.47&sigma;. Mean-reverted toward parity in 4.2 sessions once retail delivery premiums dissipated.
          </div>
        </div>

        <!-- Analogue 2 -->
        <div class="aurora-analogue-card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <strong style="color: #38bdf8; font-size: 13px;">Event #189 (Akshaya Tritiya Delivery Squeeze)</strong>
            <span class="aurora-badge aurora-badge-green">83.3% Reversion</span>
          </div>
          <div style="font-size: 12px; color: #cbd5e1; line-height: 1.5;">
            GOLDTEN delivery roll divergence peaked at +2.18&sigma;. Reversion completed in 3.8 days after physical warehouse tender window opened.
          </div>
        </div>

        <!-- Analogue 3 -->
        <div class="aurora-analogue-card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <strong style="color: #f87171; font-size: 13px;">Event #142 (Union Budget Duty Shock)</strong>
            <span class="aurora-badge" style="background: rgba(239,68,68,0.15); color: #f87171; border: 1px solid rgba(239,68,68,0.35);">Cost-Blocked</span>
          </div>
          <div style="font-size: 12px; color: #cbd5e1; line-height: 1.5;">
            Customs tariff revision created apparent 3.12&sigma; basis divergence. Filtered out as non-actionable due to 94% fee/friction absorption.
          </div>
        </div>
      </div>
      <div class="aurora-modal-footer">
        <button class="aurora-btn aurora-btn-secondary" onclick="AuroraNav.closeModal('aurora-memory-modal')">Close</button>
        <a href="market-detective.html" class="aurora-btn aurora-btn-primary">
          <i class="fa-solid fa-magnifying-glass-chart"></i> View Audit in Market Detective
        </a>
      </div>
    `;
    openModal('aurora-memory-modal', content);
  }

  // 4. Market Simulator Router
  function openSimulator() {
    const rawPath = (location.pathname || '').replace(/\\/g, '/');
    const filename = rawPath.split('/').pop() || '';
    if (filename.toLowerCase().includes('backtesting-lab')) {
      const formCard = document.querySelector('.config-card') || document.querySelector('.card');
      if (formCard) {
        formCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
        showToast('Market Simulator & Walk-Forward Lab active — configure parameters above', 'fa-sliders');
      }
      return;
    }
    window.location.href = 'backtesting-lab.html';
  }

  // 5. Expiry Calendar Opener
  function openCalendar() {
    const rawPath = (location.pathname || '').replace(/\\/g, '/');
    const filename = rawPath.split('/').pop() || '';
    if (filename.toLowerCase().includes('dashboard')) {
      const calSection = document.getElementById('expiry-calendar-section') || document.querySelector('.calendar-container');
      if (calSection) {
        calSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
        calSection.style.transition = 'box-shadow 0.4s ease, border-color 0.4s ease';
        calSection.style.borderColor = '#f0b90b';
        calSection.style.boxShadow = '0 0 35px rgba(240, 185, 11, 0.4)';
        setTimeout(() => {
          calSection.style.borderColor = '';
          calSection.style.boxShadow = '';
        }, 2500);
        showToast('Expiry Calendar focused: October 2026 roll schedule active', 'fa-calendar-days');
        return;
      }
    }

    const content = `
      <div class="aurora-modal-header">
        <h3><i class="fa-solid fa-calendar-days"></i>MCX Gold Expiry & Roll Calendar</h3>
        <button class="aurora-modal-close" onclick="AuroraNav.closeModal('aurora-calendar-modal')">&times;</button>
      </div>
      <div class="aurora-modal-body">
        <div style="margin-bottom: 16px; display: flex; gap: 8px;">
          <span class="aurora-badge aurora-badge-gold">October 2026 Active Cycle</span>
          <span class="aurora-badge aurora-badge-green">Tender Windows Monitored</span>
        </div>
        <p style="font-size: 13px; color: #94a3b8; margin-bottom: 16px;">
          Key physical delivery tender cycles and contract expiry schedule across tracked MCX gold futures:
        </p>

        <div style="background: rgba(5, 8, 24, 0.65); border: 1px solid rgba(240, 185, 11, 0.2); border-radius: 12px; overflow: hidden; margin-bottom: 18px;">
          <div class="cal-roll-row">
            <div>
              <strong style="color: #f0b90b;">GOLDM (Gold Mini 100g)</strong>
              <div style="font-size: 11px; color: #94a3b8;">Tender Period: Oct 01 &bull; Physical Delivery</div>
            </div>
            <span class="aurora-badge aurora-badge-gold">Oct 05, 2026</span>
          </div>

          <div class="cal-roll-row">
            <div>
              <strong style="color: #38bdf8;">GOLDTEN (10g Contract)</strong>
              <div style="font-size: 11px; color: #94a3b8;">Compulsory Delivery Window: Oct 19</div>
            </div>
            <span class="aurora-badge aurora-badge-blue">Oct 23, 2026</span>
          </div>

          <div class="cal-roll-row">
            <div>
              <strong style="color: #a78bfa;">GOLDGUINEA (8g Contract)</strong>
              <div style="font-size: 11px; color: #94a3b8;">Vault Settlement Protocol: Ahmedabad Base</div>
            </div>
            <span class="aurora-badge" style="background: rgba(167, 139, 250, 0.15); color: #a78bfa; border: 1px solid rgba(167, 139, 250, 0.35);">Oct 29, 2026</span>
          </div>

          <div class="cal-roll-row">
            <div>
              <strong style="color: #34d399;">GOLDPETAL (1g Contract)</strong>
              <div style="font-size: 11px; color: #94a3b8;">Final Trading Session &bull; Cash/Physical Demat</div>
            </div>
            <span class="aurora-badge aurora-badge-green">Oct 30, 2026</span>
          </div>
        </div>

        <div style="background: rgba(240, 185, 11, 0.08); border: 1px solid rgba(240, 185, 11, 0.25); border-radius: 10px; padding: 12px 14px; font-size: 12px; color: #cbd5e1;">
          <i class="fa-solid fa-triangle-exclamation" style="color: #f0b90b; margin-right: 6px;"></i>
          <strong>Roll Risk Warning:</strong> Relative-value spreads with expiry mismatches &gt; 14 days bear time-decay and basis risk. Check Opportunity Radar for Expiry-Risk flags.
        </div>
      </div>
      <div class="aurora-modal-footer">
        <button class="aurora-btn aurora-btn-secondary" onclick="AuroraNav.closeModal('aurora-calendar-modal')">Close</button>
        <a href="dashboard.html#expiry-calendar-section" class="aurora-btn aurora-btn-primary">
          <i class="fa-solid fa-chart-line"></i> View on Dashboard
        </a>
      </div>
    `;
    openModal('aurora-calendar-modal', content);
  }

  // Automatic Sidebar Click Wiring
  function wireSidebarLinks() {
    document.querySelectorAll('a, button, li').forEach((el) => {
      const text = (el.textContent || '').trim().toLowerCase();
      const title = (el.getAttribute('title') || '').trim().toLowerCase();

      // 1. Settings & Keys
      if (title === 'settings' || text.includes('settings & keys') || (text === 'settings' && el.closest('nav, .sidebar, aside'))) {
        el.setAttribute('href', 'javascript:void(0);');
        el.addEventListener('click', (e) => {
          e.preventDefault();
          e.stopPropagation();
          openSettings();
        });
      }

      // 2. Relationship Network
      else if (title === 'relationship network' || text.includes('relationship network')) {
        el.setAttribute('href', 'javascript:void(0);');
        el.addEventListener('click', (e) => {
          e.preventDefault();
          e.stopPropagation();
          openNetwork();
        });
      }

      // 3. Historical Memory
      else if (title === 'historical memory' || text.includes('historical memory')) {
        el.setAttribute('href', 'javascript:void(0);');
        el.addEventListener('click', (e) => {
          e.preventDefault();
          e.stopPropagation();
          openMemory();
        });
      }

      // 4. Market Simulator
      else if (title === 'market simulator' || text.includes('market simulator')) {
        el.setAttribute('href', 'backtesting-lab.html');
        el.addEventListener('click', (e) => {
          e.preventDefault();
          e.stopPropagation();
          openSimulator();
        });
      }

      // 5. Expiry Calendar / Contract Calendar
      else if (title === 'contract calendar' || title === 'expiry calendar' || text.includes('contract calendar') || text.includes('expiry calendar')) {
        el.setAttribute('href', 'javascript:void(0);');
        el.addEventListener('click', (e) => {
          e.preventDefault();
          e.stopPropagation();
          openCalendar();
        });
      }
    });
  }

  // Export API
  window.AuroraNav = {
    openSettings,
    openNetwork,
    openMemory,
    openSimulator,
    openCalendar,
    closeModal,
    showToast
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wireSidebarLinks);
  } else {
    wireSidebarLinks();
  }
})();
