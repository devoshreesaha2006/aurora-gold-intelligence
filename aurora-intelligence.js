/* AURORA historical intelligence UI. All results are API-sourced and provenance-labelled. */
(() => {
  'use strict';
  if (window.__AURORA_INTELLIGENCE_PANEL__) return;
  window.__AURORA_INTELLIGENCE_PANEL__ = true;

  const API_BASE = (window.AURORA_API_BASE || 'http://127.0.0.1:8000').replace(/\/$/, '');
  const css = `
  #auroraIntelLauncher{position:fixed;right:22px;bottom:22px;z-index:12000;border:1px solid rgba(240,185,11,.55);border-radius:999px;padding:12px 17px;background:linear-gradient(135deg,#f0b90b,#b87908);color:#101323;font:700 12px Inter,Arial,sans-serif;letter-spacing:.3px;box-shadow:0 8px 30px #0008;cursor:pointer}
  #auroraIntelOverlay{position:fixed;inset:0;z-index:12001;background:rgba(3,3,2,.76);backdrop-filter:blur(14px) saturate(115%);display:none;align-items:center;justify-content:center;padding:18px}
  #auroraIntelOverlay.open{display:flex}
  #auroraIntelPanel{position:relative;width:min(1080px,100%);max-height:min(90vh,940px);overflow:auto;background:linear-gradient(145deg,rgba(22,21,17,.94),rgba(7,8,10,.93) 56%,rgba(18,15,9,.95));color:#f4f0e5;border:1px solid rgba(218,183,91,.32);border-radius:22px;box-shadow:0 28px 100px #000b,inset 0 1px rgba(255,255,255,.08);backdrop-filter:blur(22px) saturate(120%);font:14px/1.55 Inter,Arial,sans-serif}
  #auroraIntelPanel:before{content:"";position:absolute;inset:0 0 auto;height:180px;pointer-events:none;background:radial-gradient(ellipse at 78% 0,rgba(220,177,72,.11),transparent 62%)}
  #auroraIntelPanel *{box-sizing:border-box}#auroraIntelPanel [hidden]{display:none!important}
  .ai-head{position:sticky;top:0;background:rgba(13,13,11,.91);backdrop-filter:blur(18px);border-bottom:1px solid rgba(230,198,117,.16);padding:22px 26px;display:flex;align-items:center;justify-content:space-between;gap:12px;z-index:2}
  .ai-eyebrow{color:#d8b85e;font-size:10px;letter-spacing:2px;font-weight:800}.ai-title{font-size:23px;font-weight:750;margin:4px 0;color:#f5f0e3}.ai-muted{color:#b2ac9c;font-size:13px}
  .ai-close{border:1px solid rgba(255,255,255,.16);background:rgba(255,255,255,.055);color:#eee9dc;border-radius:10px;padding:9px 14px;cursor:pointer;transition:background .2s,border-color .2s}.ai-close:hover{background:rgba(255,255,255,.11);border-color:rgba(218,183,91,.42)}
  .ai-tabs{display:flex;gap:9px;padding:16px 26px 0;flex-wrap:wrap}.ai-tab{background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.12);color:#c9c2b3;border-radius:11px;padding:10px 15px;cursor:pointer;transition:all .2s}.ai-tab:hover{border-color:rgba(218,183,91,.42);color:#f4e9c8}.ai-tab.active{color:#17140b;border-color:#e8cf83;background:linear-gradient(135deg,#f4e1a0,#c8a54d);box-shadow:0 5px 18px rgba(201,161,65,.2);font-weight:750}
  .ai-content{padding:20px 26px 26px}.ai-content form{padding:18px;border:1px solid rgba(225,196,119,.16);border-radius:15px;background:linear-gradient(135deg,rgba(255,255,255,.045),rgba(255,255,255,.018));box-shadow:inset 0 1px rgba(255,255,255,.04)}.ai-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:15px}.ai-field{display:flex;flex-direction:column;gap:7px;color:#c2bcad;font-size:12px;font-weight:550}.ai-field input,.ai-field select{min-width:0;width:100%;border:1px solid rgba(255,255,255,.14);background:rgba(4,5,6,.66);color:#f6f0df;border-radius:10px;padding:11px 12px;font:14px Inter,Arial,sans-serif;outline:none;transition:border-color .2s,box-shadow .2s}.ai-field input:focus,.ai-field select:focus{border-color:#d9b95f;box-shadow:0 0 0 3px rgba(217,185,95,.12)}.ai-actions{display:flex;align-items:center;gap:13px;margin:17px 0 0;flex-wrap:wrap}.ai-run{background:linear-gradient(135deg,#f4e19b,#c69c3e);color:#17140b;border:1px solid rgba(255,237,180,.72);border-radius:10px;padding:11px 18px;font-weight:800;cursor:pointer;box-shadow:0 7px 20px rgba(185,143,43,.17);transition:transform .2s,filter .2s,box-shadow .2s}.ai-run:hover:not(:disabled){transform:translateY(-1px);filter:brightness(1.07);box-shadow:0 9px 24px rgba(185,143,43,.25)}.ai-run:disabled{opacity:.62;cursor:wait}.ai-status{padding:12px 14px;background:rgba(255,255,255,.045);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,.12);border-radius:11px;color:#ddd6c7;margin:14px 0}.ai-status.error{border-color:rgba(229,91,86,.55);color:#ffd0ca;background:rgba(95,27,25,.2)}.ai-results{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:11px;margin:15px 0}.ai-metric{padding:14px;border:1px solid rgba(225,196,119,.14);background:linear-gradient(145deg,rgba(255,255,255,.065),rgba(255,255,255,.025));backdrop-filter:blur(12px);border-radius:13px;min-width:0;box-shadow:inset 0 1px rgba(255,255,255,.035)}.ai-metric small{display:block;color:#b6ae9b;font-size:11px;line-height:1.4;margin-bottom:7px}.ai-metric strong{display:block;color:#f2e7c9;font-size:17px;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}.ai-section{border:1px solid rgba(225,196,119,.14);background:linear-gradient(145deg,rgba(255,255,255,.045),rgba(255,255,255,.018));backdrop-filter:blur(12px);border-radius:14px;padding:16px;margin-top:13px}.ai-section h3{font-size:14px;margin:0 0 10px;color:#e3c66d}.ai-table-wrap{overflow:auto}.ai-table{border-collapse:collapse;width:100%;font-size:12px}.ai-table th,.ai-table td{text-align:left;padding:9px;border-bottom:1px solid rgba(255,255,255,.09);vertical-align:top}.ai-table th{color:#e3c66d;font-weight:700}.ai-chip{display:inline-block;border:1px solid rgba(225,196,119,.3);border-radius:999px;padding:4px 9px;color:#e6d39a;font-size:11px}.ai-list{margin:0;padding-left:19px;color:#c9c2b4}.ai-list li{margin:6px 0}.ai-disclaimer{font-size:12px;color:#aaa392;margin-top:14px;line-height:1.65}
  .ai-chart{border:1px solid #ffffff17;background:#0e1629;border-radius:11px;padding:14px;margin-top:12px;overflow:hidden}.ai-chart h3{font-size:13px;margin:0 0 4px;color:#f4d16a}.ai-chart-note{font-size:10px;color:#9ca9bf;margin:0 0 10px}.ai-chart svg{display:block;width:100%;height:auto;min-height:150px}.ai-chart text{font-family:Inter,Arial,sans-serif;fill:#cbd5e1;font-size:11px}.ai-chart .axis{stroke:#64748b;stroke-width:1}.ai-chart .bar{fill:#eabf35}.ai-chart .bar.secondary{fill:#4f8cff}.ai-chart .bar.tertiary{fill:#2dd4bf}
  @media(max-width:700px){#auroraIntelOverlay{padding:7px}#auroraIntelPanel{max-height:94vh;border-radius:16px}.ai-grid,.ai-results{grid-template-columns:repeat(2,minmax(0,1fr))}.ai-head,.ai-content{padding-left:14px;padding-right:14px}.ai-content form{padding:13px}.ai-tabs{padding-left:14px;padding-right:14px}#auroraIntelLauncher{right:12px;bottom:12px}}
  @media(max-width:460px){.ai-grid,.ai-results{grid-template-columns:1fr}.ai-title{font-size:20px}.ai-head{padding-top:16px;padding-bottom:16px}}
  @media(prefers-reduced-motion:reduce){#auroraIntelOverlay *{scroll-behavior:auto!important;animation:none!important;transition:none!important}}
  `;
  const style = document.createElement('style'); style.textContent = css; document.head.appendChild(style);
  const launcher = document.createElement('button'); launcher.id='auroraIntelLauncher'; launcher.type='button'; launcher.textContent='✦ Historical Intelligence';
  launcher.setAttribute('aria-haspopup','dialog');
  const overlay = document.createElement('div'); overlay.id='auroraIntelOverlay'; overlay.innerHTML = `
    <section id="auroraIntelPanel" role="dialog" aria-modal="true" aria-labelledby="aiTitle">
      <header class="ai-head"><div><div class="ai-eyebrow">AURORA · PHASE 2</div><div class="ai-title" id="aiTitle">Historical Intelligence</div><div class="ai-muted">Explainability · What-if scenarios · Walk-forward validation</div></div><button type="button" class="ai-close" id="aiClose">Close ✕</button></header>
      <nav class="ai-tabs" role="tablist" aria-label="Historical intelligence tools">
        <button class="ai-tab active" data-tab="explain" role="tab" aria-selected="true">Explain Radar</button>
        <button class="ai-tab" data-tab="whatif" role="tab" aria-selected="false">What-if</button>
        <button class="ai-tab" data-tab="walk" role="tab" aria-selected="false">Walk-forward</button>
      </nav>
      <div class="ai-content">
        <form id="aiForm">
          <div class="ai-grid">
            <label class="ai-field">Contract pair<select name="pair"><option>GOLDM-GOLDPETAL</option><option>GOLDM-GOLDTEN</option><option>GOLDM-GOLDGUINEA</option><option>GOLDTEN-GOLDPETAL</option><option>GOLDTEN-GOLDGUINEA</option><option>GOLDGUINEA-GOLDPETAL</option></select></label>
            <label class="ai-field">Window (observations)<input name="window" type="number" min="5" max="365" value="30" required></label>
            <label class="ai-field ai-only-explain">Evaluation date (optional)<input name="evaluation_date" type="date"></label>
            <label class="ai-field ai-only-whatif" hidden>Assumed spread move (%)<input name="spread_move_pct" type="number" min="-100" max="100" step=".1" value="2"></label>
            <label class="ai-field ai-only-whatif" hidden>Units<input name="units" type="number" min="1" max="10000" value="1"></label>
            <label class="ai-field ai-only-whatif" hidden>Transaction cost / 10g (₹)<input name="transaction_cost_per_10g" type="number" min="0" step=".01" value="5"></label>
            <label class="ai-field ai-only-whatif" hidden>Slippage / 10g (₹)<input name="slippage_per_10g" type="number" min="0" step=".01" value="2"></label>
            <label class="ai-field ai-only-whatif" hidden>Holding days<input name="holding_days" type="number" min="1" max="365" value="5"></label>
            <label class="ai-field ai-only-walk" hidden>Training fraction<input name="train_fraction" type="number" min=".51" max=".89" step=".01" value=".7"></label>
            <label class="ai-field ai-only-walk" hidden>Entry Z threshold<input name="entry_z" type="number" min=".5" max="5" step=".1" value="2"></label>
            <label class="ai-field ai-only-walk" hidden>Transaction cost / 10g (₹)<input name="transaction_cost_per_10g" type="number" min="0" step=".01" value="10.31"></label>
            <label class="ai-field ai-only-walk" hidden>Slippage / 10g (₹)<input name="slippage_per_10g" type="number" min="0" step=".01" value="15"></label>
            <label class="ai-field ai-only-walk" hidden>Units<input name="units" type="number" min="1" max="10000" value="1"></label>
          </div>
          <div class="ai-actions"><button class="ai-run" id="aiRun" type="submit">Run analysis</button><span class="ai-muted" id="aiSource">Historical CSV only · not provider-verified</span></div>
        </form>
        <div id="aiStatus" class="ai-status" role="status" aria-live="polite">Choose a tool and run it to load backend-calculated results.</div>
        <div id="aiOutput"></div>
        <p class="ai-disclaimer">Research interface only. Historical CSV observations are not live quotes. What-if is a user-defined scenario, not a forecast. Walk-forward results are simplified historical estimates, not a portfolio simulator or a guarantee of future performance. Missing values remain unavailable, never zero.</p>
      </div>
    </section>`;
  document.body.append(launcher, overlay);
  let activeTab='explain', busy=false;
  const $ = (s) => overlay.querySelector(s);
  const form = $('#aiForm'), output=$('#aiOutput'), status=$('#aiStatus'), run=$('#aiRun');
  const tabs=[...overlay.querySelectorAll('.ai-tab')];
  function switchTab(tab){
    activeTab=tab;
    tabs.forEach(b=>{const on=b.dataset.tab===tab;b.classList.toggle('active',on);b.setAttribute('aria-selected',String(on));});
    overlay.querySelectorAll('.ai-only-explain,.ai-only-whatif,.ai-only-walk').forEach(el=>el.hidden=!el.classList.contains('ai-only-'+tab));
    output.replaceChildren(); status.className='ai-status'; status.textContent='Ready. Run this analysis to request the latest eligible historical result.';
    run.textContent=tab==='explain'?'Explain classification':tab==='whatif'?'Calculate scenario':'Validate holdout';
  }
  tabs.forEach(b=>b.addEventListener('click',()=>switchTab(b.dataset.tab)));
  function open(){overlay.classList.add('open');document.body.style.overflow='hidden';}
  function close(){overlay.classList.remove('open');document.body.style.overflow='';launcher.focus();}
  launcher.addEventListener('click',open); $('#aiClose').addEventListener('click',close);
  overlay.addEventListener('click',e=>{if(e.target===overlay)close();});
  window.addEventListener('keydown',e=>{if(e.key==='Escape'&&overlay.classList.contains('open'))close();});
  function escape(value){return String(value??'Unavailable').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
  function displayValue(label,value){
    if(value===null||value===undefined||value==='')return 'Unavailable';
    if(typeof value==='number'&&Number.isFinite(value)){
      const wholeNumber=/observations|units|signals|count|days|window/i.test(label);
      const precision=/p&l|cost|spread|mean|std|score|z-score|percent|threshold|move|ratio/i.test(label)?2:4;
      return value.toLocaleString('en-IN',{maximumFractionDigits:wholeNumber?0:precision});
    }
    return value;
  }
  function metric(label,value){return '<div class="ai-metric"><small>'+escape(label)+'</small><strong>'+escape(displayValue(label,value))+'</strong></div>';}
  function list(items){return '<ul class="ai-list">'+(items||[]).map(x=>'<li>'+escape(x)+'</li>').join('')+'</ul>';}
  function section(title,body){return '<section class="ai-section"><h3>'+escape(title)+'</h3>'+body+'</section>';}
  function table(headers,rows){return '<div class="ai-table-wrap"><table class="ai-table"><thead><tr>'+headers.map(h=>'<th>'+escape(h)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(row=>'<tr>'+row.map(v=>'<td>'+escape(v===null||v===undefined?'Unavailable':v)+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>';}
  function scenarioChart(data){
    const current=Number(data.current_spread), mean=Number(data.rolling_mean), move=Number(data.assumed_spread_change);
    const rows=[['Latest spread',Number.isFinite(current)?current:null,'bar'],['Rolling mean',data.rolling_mean==null?null:mean,'bar secondary'],['Assumed scenario level',Number.isFinite(current)&&Number.isFinite(move)?current+move:null,'bar tertiary']];
    const values=rows.map(r=>r[1]).filter(v=>v!==null&&Number.isFinite(v));
    if(!values.length)return '';
    const maxAbs=Math.max(1,...values.map(Math.abs)); const zero=350, half=270, scale=half/maxAbs;
    const bars=rows.map((r,i)=>{const y=30+i*43; if(r[1]===null||!Number.isFinite(r[1]))return '<text x="8" y="'+(y+13)+'">'+escape(r[0])+'</text><text x="365" y="'+(y+13)+'">Unavailable</text>'; const v=r[1],w=Math.abs(v)*scale,x=v<0?zero-w:zero; return '<text x="8" y="'+(y+13)+'">'+escape(r[0])+'</text><rect class="bar '+r[2].replace('bar ','')+'" x="'+x.toFixed(1)+'" y="'+y+'" width="'+Math.max(1,w).toFixed(1)+'" height="18" rx="4"/><text x="'+(v<0?Math.max(355,x-7):Math.min(635,x+w+7)).toFixed(1)+'" y="'+(y+13)+'" text-anchor="'+(v<0?'end':'start')+'">'+escape(v.toFixed(2))+'</text>';}).join('');
    return '<section class="ai-chart"><h3>Spread comparison</h3><p class="ai-chart-note">Snapshot for the selected window · not a historical time-series chart. Negative values extend left of zero.</p><svg viewBox="0 0 700 165" role="img" aria-label="Bar chart comparing latest spread, rolling mean, and assumed scenario level"><line class="axis" x1="'+zero+'" y1="18" x2="'+zero+'" y2="150"/><text x="'+(zero+4)+'" y="13">0</text>'+bars+'</svg></section>';
  }
  function render(data){
    if(activeTab==='explain'){
      output.innerHTML='<div class="ai-results">'+[
        metric('Classification',data.classification),metric('Heuristic opportunity score (not a probability)',data.opportunity_score),metric('Heuristic trap risk score',data.trap_risk_score),metric('Evaluation snapshot date',data.evaluation_date),metric('Matched trade date',data.trade_date),
        metric('Expiry date',data.expiry_date),metric('Spread (₹/10g)',data.spread),metric('Z-score',data.z_score),metric('Historical percentile',data.percentile_rank),
        metric('Gross edge (₹/10g)',data.gross_edge),metric('Net edge (₹/10g)',data.net_edge),metric('Cost hurdle (₹/10g)',data.estimated_cost_hurdle),metric('Data mode',data.data_mode)
      ].join('')+'</div>'+section('Classification reason','<p>'+escape(data.reason||'No reason supplied')+'</p>')+section('Rule evidence',table(['Factor','Value','Unit','Effect','Available'],(data.evidence||[]).map(e=>[e.factor,e.value,e.unit,e.effect,e.available?'Yes':'No'])))+section('Caveats',list(data.caveats||[]));
    } else if(activeTab==='whatif'){
      output.innerHTML='<div class="ai-results">'+[metric('Evaluation date',data.evaluation_date),metric('Latest historical spread',data.current_spread),metric('Window requested',data.window),metric('Observations in window',data.window_observations),metric('Rolling mean (₹/10g)',data.rolling_mean),metric('Rolling std. dev. (₹/10g)',data.rolling_std),metric('Window Z-score',data.z_score),metric('Historical percentile',data.percentile_rank),metric('Assumed spread change (₹)',data.assumed_spread_change),metric('Units',data.units),metric('Gross P&L (₹)',data.gross_pnl),metric('Estimated costs (₹)',data.estimated_costs),metric('Net P&L (₹)',data.estimated_net_pnl),metric('Break-even move (%)',data.break_even_move_pct),metric('Expiry date',data.expiry_date),metric('Holding days',data.holding_days)].join('')+'</div>'+scenarioChart(data)+section('Scenario assumptions',list(data.assumptions||[]));
    } else {
      output.innerHTML='<div class="ai-results">'+[metric('Status',data.status),metric('Data mode',data.data_mode),metric('Observations',data.observations),metric('Training / holdout',String(data.training_observations)+' / '+String(data.holdout_observations)),metric('Training period',(data.training_start||'Unavailable')+' → '+(data.training_end||'Unavailable')),metric('Holdout period',(data.holdout_start||'Unavailable')+' → '+(data.holdout_end||'Unavailable')),metric('Selected threshold',data.entry_threshold_selected_from_training),metric('Holdout signals',data.holdout_signal_count),metric('Gross P&L (₹)',data.gross_pnl),metric('Estimated costs (₹)',data.estimated_costs),metric('Net P&L (₹)',data.net_pnl),metric('Win rate (%)',data.win_rate_pct)].join('')+'</div>'+section('Holdout outcomes',table(['Signal date','Next date','Z-score','Gross P&L','Costs','Net P&L'],(data.holdout_outcomes||[]).map(x=>[x.date,x.next_date,x.z_score,x.gross_pnl,x.estimated_costs,x.net_pnl])))+section('Methodology & limitations',list(data.assumptions||[]));
    }
  }
  function num(name){const els=[...form.querySelectorAll('[name="'+name+'"]')];const el=els.find(node=>!node.closest('[hidden]'));return el&&el.value!==''?Number(el.value):undefined;}
  form.addEventListener('submit',async e=>{
    e.preventDefault();if(busy)return;
    const pair=form.elements.pair.value, windowDays=num('window');
    if(!pair||!Number.isFinite(windowDays)||windowDays<5||windowDays>365){status.className='ai-status error';status.textContent='Enter a supported pair and a window between 5 and 365.';return;}
    let url=API_BASE+'/api/intelligence/'+(activeTab==='explain'?'explain':activeTab==='whatif'?'what-if':'walk-forward'), method=activeTab==='explain'?'GET':'POST', body;
    if(activeTab==='explain'){const params=new URLSearchParams({pair,window:String(windowDays)});const d=form.elements.evaluation_date.value;if(d)params.set('evaluation_date',d);url+='?'+params.toString();}
    if(activeTab==='whatif')body={pair,window:windowDays,units:num('units')||1,spread_move_pct:num('spread_move_pct')??2,transaction_cost_per_10g:num('transaction_cost_per_10g')??5,slippage_per_10g:num('slippage_per_10g')??2,holding_days:num('holding_days')||5};
    if(activeTab==='walk')body={pair,window:windowDays,train_fraction:num('train_fraction')??.7,entry_z:num('entry_z')??2,transaction_cost_per_10g:num('transaction_cost_per_10g')??10.31,slippage_per_10g:num('slippage_per_10g')??15,units:num('units')||1};
    busy=true;run.disabled=true;status.className='ai-status';status.textContent='Loading backend-calculated historical analysis…';output.replaceChildren();
    try{
      const response=await fetch(url,{method,headers:body?{'Content-Type':'application/json','Accept':'application/json'}:{'Accept':'application/json'},body:body?JSON.stringify(body):undefined});
      let payload;try{payload=await response.json();}catch{const error=new Error('The API returned a non-JSON response.');error.status=response.status;throw error;}
      if(!response.ok){const error=new Error(payload.detail?typeof payload.detail==='string'?payload.detail:JSON.stringify(payload.detail):'The request was rejected.');error.status=response.status;throw error;}
      if(payload.success===false)throw new Error(payload.message||'The API reported that the request failed.');
      const data=payload.data;if(!data||typeof data!=='object')throw new Error('The API response did not contain a data object.');
      status.textContent='Analysis received · '+(data.data_mode||'historical observations')+' · '+(data.evaluation_date||data.trade_date||data.holdout_end||'date unavailable');
      render(data);
    }catch(err){
      status.className='ai-status error';
      if(Number.isInteger(err.status))status.textContent='Analysis unavailable (HTTP '+err.status+'): '+err.message+(err.status===422?' Check the selected pair, date, and eligible historical observations.':'');
      else if(err instanceof TypeError)status.textContent='Could not reach the analysis service. Check that the backend is running and that this frontend origin is allowed.';
      else status.textContent='Could not load analysis: '+err.message;
      output.replaceChildren();
    }
    finally{busy=false;run.disabled=false;}
  });
  switchTab('explain');
})();
