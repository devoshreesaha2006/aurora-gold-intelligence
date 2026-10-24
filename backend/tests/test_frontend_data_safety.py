from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_opportunity_radar_does_not_ship_seeded_live_badge_or_signal_metrics():
    page = (ROOT / "opportunity-radar.html").read_text(encoding="utf-8")
    pipeline = (ROOT / "aurora-pipeline.js").read_text(encoding="utf-8")

    assert "3 Live" not in page
    assert 'id="radarPairStatusBadge"' in page
    assert "function renderRadarPair(pair)" in pipeline
    assert "ensureLiveBadge(usablePairs.length, pairs.length)" in pipeline
    assert "pairs with matched snapshots`" in pipeline
    assert "Live`" not in pipeline[pipeline.index("function ensureLiveBadge"):]
    assert "CRITICAL DISLOCATION" not in page
    assert "+2.47σ" not in page
    assert "97.3%" not in page
    assert "₹74,850.00" not in page
    assert "₹141.34" not in page
    assert "420 Lots (High Liquidity)" not in page


def test_frontend_api_failure_paths_clear_to_unavailable_states():
    pipeline = (ROOT / "aurora-pipeline.js").read_text(encoding="utf-8")
    dashboard = (ROOT / "dashboard-live.js").read_text(encoding="utf-8")

    assert "clearRadarSampleData('Backend data unavailable')" in pipeline
    assert "clearRadarSampleData('No synchronized backend snapshots')" in pipeline
    assert "if (liveBadge) liveBadge.textContent" in pipeline
    assert "document.querySelectorAll('.signal-card').forEach(card =>" in pipeline
    assert "document.querySelectorAll('.matrix-table tbody tr').forEach(row =>" in pipeline
    assert "radarChart.data.datasets.forEach(dataset => { dataset.data = radarChart.data.labels.map(() => null); })" in pipeline
    assert "['test_data', 'demo_synthetic'].includes(statusJson.data.data_mode)" in pipeline
    assert "? 'Test-only data excluded from analysis'" in pipeline
    assert "'Synthetic demo data excluded from analysis'" in pipeline
    assert "distributionRequestId += 1;" in pipeline
    assert "clearDistributionSampleData();" in pipeline
    assert "Promise.allSettled([" in dashboard
    assert "const hasSpread = pair => pair?.spread !== null && pair?.spread !== undefined" in dashboard
    assert "if (!rows.length)" in dashboard
    assert "['test_data', 'demo_synthetic'].includes(model.status?.data_mode)" in dashboard
    assert "model.prices = [];" in dashboard
    assert "model.radar = [];" in dashboard


def test_opportunity_radar_fails_closed_for_demo_synthetic_status():
    pipeline = (ROOT / "aurora-pipeline.js").read_text(encoding="utf-8")

    assert "['test_data', 'demo_synthetic'].includes(statusJson.data.data_mode)" in pipeline
    assert "Synthetic demo data excluded from analysis" in pipeline
    assert "clearRadarSampleData('No synchronized backend snapshots')" in pipeline


def test_market_detective_empty_events_clear_old_dossier_and_disable_actions():
    page = (ROOT / "market-detective.html").read_text(encoding="utf-8")
    pipeline = (ROOT / "aurora-pipeline.js").read_text(encoding="utf-8")

    assert '<select id="eventSelector" disabled>' in page
    assert '<div class="investigation-grid" hidden style="display:none">' in page
    assert '<section class="ai-explanation-panel" hidden style="display:none">' in page
    assert 'No valid backend investigation selected.' in page
    assert 'Event #247' not in page
    assert '2.47σ' not in page
    assert '97.3%' not in page
    assert '7 analogue instances' not in page
    assert '12,450</span>' not in page
    assert '36,907</span>' not in page
    assert 'id="detectiveFeedLabel">Feed status unavailable</span>' in page
    assert 'id="detectiveSignalConfidence"' in page
    assert "const EVENT_PRESETS" not in page
    assert "Math.random()" not in page
    assert "window.AURORA_SELECTED_EVENT = null;" in pipeline
    assert "window.AURORA_LIVE_EVENTS = {};" in pipeline
    assert "summary.style.display = 'none';" in pipeline
    assert "clearDetectiveDossier();" in pipeline
    assert "if (!events.length)" in pipeline
    assert "setDetectiveUnavailable('No backend investigations are available for the current data.')" in pipeline
    assert "if (feedLabel) feedLabel.textContent = detectiveFeedLabel || 'Feed status unavailable'" in pipeline
    assert "function setDetectiveFeedStatus(status)" in pipeline
    assert "detectiveFeedLabel = `${state} · ${provenance}`" in pipeline


def test_market_detective_shows_actionable_backend_events_and_preserves_status_on_events_error():
    pipeline = (ROOT / "aurora-pipeline.js").read_text(encoding="utf-8")

    assert "const actionable = ['investigate', 'watch', 'cost-blocked', 'expiry-risk']" in pipeline
    assert "actionable.includes(evt.classification.toLowerCase())" in pipeline
    assert "setDetectiveFeedStatus(statusJson.data)" in pipeline
    assert pipeline.index("setDetectiveFeedStatus(statusJson.data)") < pipeline.index("if (!eventsRes.ok)")
    assert "const events = json?.success && Array.isArray(json?.data?.items)" in pipeline


def test_market_detective_chart_legend_and_step_states_follow_selected_backend_event():
    page = (ROOT / "market-detective.html").read_text(encoding="utf-8")
    pipeline = (ROOT / "aurora-pipeline.js").read_text(encoding="utf-8")

    assert 'id="volumeLegALabel"' in page
    assert 'id="volumeLegBLabel"' in page
    assert "if (legALabel) legALabel.textContent = evt.leg_a" in pipeline
    assert "if (legBLabel) legBLabel.textContent = evt.leg_b" in pipeline
    assert "Contracts traded vs. Open Commitment · ${evt.leg_a} / ${evt.leg_b}" in pipeline
    assert "const stepStates = ['EVENT DATA', 'NORMALIZED EVENT', 'BACKEND SPREAD'" in pipeline
    assert "if (!points.length) {" in pipeline
    assert "evt.evidence.volume_a == null ? 'Unavailable'" in pipeline
    assert "evt.evidence.open_interest_a == null || evt.evidence.open_interest_b == null ? 'Unavailable'" in pipeline
    assert "clearDetectiveCharts();\n        document.querySelectorAll('.chart-footer-metrics .chart-metric-value')" in pipeline


def test_dashboard_and_detective_label_snapshot_versus_dated_backend_events():
    dashboard = (ROOT / "dashboard-live.js").read_text(encoding="utf-8")
    pipeline = (ROOT / "aurora-pipeline.js").read_text(encoding="utf-8")

    assert "radarDate: null" in dashboard
    assert "Latest radar snapshot · ${model.radarDate || 'date unavailable'}" in dashboard
    assert "model.radarDate = radar.status === 'fulfilled' ? radar.value?.evaluation_date || null : null" in dashboard
    assert "observation date shown (historical events may differ from the latest radar snapshot)" in pipeline
    assert "${evt.trade_date} · ${evt.event_id}" in pipeline


def test_radar_cards_show_backend_unavailability_reason_and_distribution_context():
    radar = (ROOT / "opportunity-radar.html").read_text(encoding="utf-8")
    pipeline = (ROOT / "aurora-pipeline.js").read_text(encoding="utf-8")

    assert radar.count('class="pair-data-reason" role="status" hidden') == 3
    assert "NO SYNCHRONIZED SNAPSHOT" in pipeline
    assert "unavailableReason.textContent = reason" in pipeline
    assert 'id="distributionContext"' in radar
    assert "Distribution-Window Z-Score" in radar
    assert "d.current_z_score || '—'" in pipeline
    assert "d.evaluation_date" in pipeline and "d.expiry_date" in pipeline
    assert "Trading Sessions (365d Window)" not in radar


def test_market_detective_uses_readable_shared_typography():
    page = (ROOT / "market-detective.html").read_text(encoding="utf-8")
    shared = (ROOT / "analytics-premium.css").read_text(encoding="utf-8")

    assert '<body class="aurora-market-detective">' in page
    assert "body.aurora-market-detective .step-name" in shared
    assert "font-family: Manrope, Inter, ui-sans-serif, sans-serif !important" in shared
    assert "body.aurora-market-detective .detail-label { font-size: 13px; }" in shared


def test_market_detective_actions_require_current_backend_selection():
    page = (ROOT / "market-detective.html").read_text(encoding="utf-8")

    for action in ("openRawModal", "exportDossier", "copySummaryText", "simulateEventInPlayground"):
        start = page.index(f"function {action}()")
        end = page.find("\n    function ", start + 1)
        body = page[start:end if end >= 0 else None]
        assert "selectedBackendEvent()" in body
        assert "if (!evt) return;" in body


def test_empty_radar_wedge_is_css_sweep_not_a_plotted_data_value():
    page = (ROOT / "opportunity-radar.html").read_text(encoding="utf-8")
    pipeline = (ROOT / "aurora-pipeline.js").read_text(encoding="utf-8")

    assert ".radar-sweep-beam" in page
    assert "const currentDeviationData = [];" in page
    assert "dataset.data = radarChart.data.labels.map(() => null)" in pipeline
    assert "p.spread != null && p.deviation_intensity != null" in pipeline


def test_dashboard_live_label_requires_a_connected_verified_feed():
    dashboard = (ROOT / "dashboard-live.js").read_text(encoding="utf-8")

    assert "feed === 'LIVE' && status.is_live_connected === true ? 'Verified MCX live feed'" in dashboard
    assert "mode === 'test_data' ? 'Test data · excluded from analysis'" in dashboard
    assert "feed === 'DELAYED' ? 'Authorized delayed MCX feed'" in dashboard
    assert "feed === 'STALE' ? 'Provider feed stale'" in dashboard


def test_radar_selection_preserves_pair_direction_and_distribution_uses_its_own_window():
    page = (ROOT / "opportunity-radar.html").read_text(encoding="utf-8")
    pipeline = (ROOT / "aurora-pipeline.js").read_text(encoding="utf-8")

    assert "function orientRadarPair(pair, requestedPair)" in pipeline
    assert "spread: pair.spread == null ? null : -Number(pair.spread)" in pipeline
    assert "z_score: pair.z_score == null ? null : -Number(pair.z_score)" in pipeline
    assert "percentile_rank: pair.percentile_rank == null ? null : 100 - Number(pair.percentile_rank)" in pipeline
    assert "switchDistributionPair(pairName)" in page
    assert "const currentZ = document.getElementById('stat-current-z')" in pipeline
    assert "currentZ.textContent = d.current_z_score || '—'" in pipeline
    assert "d.evaluation_date" in pipeline and "d.expiry_date" in pipeline


def test_radar_cards_and_dashboard_kpis_do_not_seed_snapshot_values():
    page = (ROOT / "opportunity-radar.html").read_text(encoding="utf-8")
    pipeline = (ROOT / "aurora-pipeline.js").read_text(encoding="utf-8")
    dashboard = (ROOT / "dashboard-live.js").read_text(encoding="utf-8")

    assert "function updateRadarSignalCards(pairs)" in pipeline
    assert "const displayPair = orientRadarPair(pair, card.getAttribute('data-pair'))" in pipeline
    assert "if (scoreNote) scoreNote.textContent = score == null ? 'Unavailable' : `${score}%`" in pipeline
    assert "displayPair.trap_risk_score == null ? 'unavailable'" in pipeline
    for sample in ("3 Live", "CRITICAL DISLOCATION", "-1.29", "12.5%", "60%"):
        assert sample not in page
    assert "const validPairs = model.radar.filter(hasSpread)" in dashboard
    assert "const scoredPairs = validPairs.filter(p => p.opportunity_score != null" in dashboard
    assert "const best = scoredPairs.reduce" in dashboard
    assert "model.prices.filter(item => symbols.includes(item.symbol))" in dashboard


def test_opportunity_radar_cards_and_pair_selection_cover_all_canonical_pairs():
    page = (ROOT / "opportunity-radar.html").read_text(encoding="utf-8")
    pipeline = (ROOT / "aurora-pipeline.js").read_text(encoding="utf-8")

    assert "function ensureRadarSignalCards(pairs)" in pipeline
    assert "ensureRadarSignalCards(pairs);" in pipeline
    assert "Historical data" in pipeline and "pairs with matched snapshots`" in pipeline
    assert "${usablePairs.length}/${pairs.length} pairs have synchronized snapshots" in pipeline
    assert "td.title = p?.reason ? `Unavailable: ${p.reason}`" in pipeline
    assert "const scoreA = a.opportunity_score == null ? -Infinity : Number(a.opportunity_score)" in pipeline
    for pair in (
        "GOLDM-GOLDPETAL", "GOLDGUINEA-GOLDTEN", "GOLDM-GOLDTEN",
        "GOLDM-GOLDGUINEA", "GOLDTEN-GOLDPETAL", "GOLDGUINEA-GOLDPETAL",
    ):
        assert f"switchDistributionPair('{pair}')" in page
    assert "Synchronized historical snapshot" in pipeline
    assert "${displayPair.trade_date || 'date unavailable'}" in pipeline
    assert "${displayPair.expiry_date || 'unavailable'}" in pipeline


def test_opportunity_radar_filters_use_backend_status_and_risk_flags():
    page = (ROOT / "opportunity-radar.html").read_text(encoding="utf-8")
    pipeline = (ROOT / "aurora-pipeline.js").read_text(encoding="utf-8")

    assert '<option value="risk">Risk / Friction Flags</option>' in page
    assert "selectedStatus === 'active' && hasSnapshot && ['Investigate', 'Watch', 'Cost-Blocked', 'Expiry-Risk'].includes(classification)" in page
    assert "selectedStatus === 'investigating' && classification === 'Investigate'" in page
    assert "selectedStatus === 'risk' && hasSnapshot && hasRisk" in page
    assert "const observedPairs = pairs.filter(pair => pair && pair.spread != null" in pipeline
    assert "const unavailable = Math.max(0, pairs.length - observed)" in pipeline
    assert "const liquidityAssessed = observedPairs.filter(pair => pair.min_volume != null && pair.min_open_interest != null && pair.is_liquidity_trap != null)" in pipeline
    assert "const expiryAssessed = liquidPairs.filter(pair => pair.dte_min != null && pair.is_expiry_risk != null)" in pipeline
    assert "const costAssessed = expiryPairs.filter(pair => pair.gross_edge != null && pair.estimated_cost_hurdle != null && pair.is_cost_blocked != null)" in pipeline
    assert "pair.is_expiry_risk === false" in pipeline
    assert "pair.is_cost_blocked === false" in pipeline
    assert "const investigate = costPairs.filter(pair => pair.classification === 'Investigate').length" in pipeline
    assert 'id="radarCardsEmpty"' in page
    assert "fetch(`${API_BASE}/api/analytics/radar?window=${encodeURIComponent(windowDays)}`)" in pipeline


def test_opportunity_radar_severity_uses_z_thresholds_and_discloses_filtered_selection():
    page = (ROOT / "opportunity-radar.html").read_text(encoding="utf-8")
    pipeline = (ROOT / "aurora-pipeline.js").read_text(encoding="utf-8")

    assert "absZ >= 2 ? 'critical' : absZ >= 1.5 ? 'high' : absZ >= 1 ? 'medium' : 'low'" in pipeline
    assert "Selected pair is outside the active Status / Severity filters." in pipeline
    assert "window.AURORA_SYNC_RADAR_FILTER_STATE();" in page
    assert 'id="radarSelectionFilterNotice"' in page
    assert "absZ >= 2 ? 'critical'" in pipeline
    assert "classification === 'No Signal'" not in page[page.index("function applySignalFilters"):page.index("statusFilter.addEventListener")]


def test_distribution_expiry_roll_rule_is_explicit_in_api_and_radar_context():
    pipeline = (ROOT / "aurora-pipeline.js").read_text(encoding="utf-8")
    schema = (ROOT / "backend" / "app" / "schemas" / "analytics.py").read_text(encoding="utf-8")

    assert "expiry_policy: str =" in schema
    assert "Each point matches trade date and expiry" in pipeline
    assert "Rolling-contract history:" in pipeline
    assert "Radar uses ${radarWindow} synchronized sessions" in pipeline

def test_opportunity_radar_historical_freshness_indicator():
    page = (ROOT / "opportunity-radar.html").read_text(encoding="utf-8")
    pipeline = (ROOT / "aurora-pipeline.js").read_text(encoding="utf-8")

    assert 'id="radarFreshnessBanner"' in page
    assert 'id="radarFreshnessDataset"' in page
    assert 'id="radarLatestObsDate"' in page
    assert 'id="radarObsAgeBadge"' in page
    assert 'id="radarFeedStatus"' in page
    assert 'id="radarStaleWarning"' in page
    assert "function updateRadarFreshnessIndicator(statusData, errorMsg)" in pipeline
    assert "Historical CSV Data (Not Live)" in pipeline
    assert "Stale Data Warning: Latest observation is" in pipeline
    assert "Feed is UNAVAILABLE. Spreads reflect historical settlement, not live execution opportunities." in pipeline
