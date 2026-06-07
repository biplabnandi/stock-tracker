/* ═══════════════════════════════════════════════════════════
   StockPulse — Dashboard Application Logic
   ═══════════════════════════════════════════════════════════ */

const DATA_URL = 'data/results.json';

let allStocks = [];
let filteredStocks = [];
let currentFilters = { category: 'all', tier: null, search: '', sort: 'composite_desc', sector: 'all' };

// ─── Init ──────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  try {
    const res = await fetch(DATA_URL);
    if (!res.ok) throw new Error('Failed to load data');
    const data = await res.json();
    allStocks = data.stocks || [];
    renderDashboard(data);
    renderTrendingAlerts();
    setupFilters();
    applyFilters();
  } catch (err) {
    console.error('Load error:', err);
    document.getElementById('loading-overlay').innerHTML =
      '<div class="loader-content"><div class="loader-icon">⚠️</div><p class="loader-text">Could not load data. Run the scanner first:<br><code style="color:#6c5ce7">python scanner.py --test</code></p></div>';
  }
});

// ─── Dashboard ─────────────────────────────────────────────
function renderDashboard(data) {
  const s = data.summary || {};
  setText('stat-total', s.total || 0);
  setText('stat-strong-buy', s.strong_buy || 0);
  setText('stat-buy', s.buy || 0);
  setText('stat-watch', s.watch || 0);
  setText('stat-avoid', s.avoid || 0);
  setText('stat-avg-score', s.avg_score || 0);

  // Scan date
  if (data.scan_date) {
    const d = new Date(data.scan_date);
    setText('scan-date', d.toLocaleDateString('en-IN', { day:'numeric', month:'short', year:'numeric', hour:'2-digit', minute:'2-digit' }));
  }

  // Top sectors
  const bar = document.getElementById('sectors-bar');
  bar.innerHTML = '';
  (s.top_sectors || []).forEach(sec => {
    const el = document.createElement('div');
    el.className = 'sector-chip';
    el.innerHTML = `<span>${sec.sector}</span><span class="sector-score">${sec.avg_score}</span><span class="sector-count">(${sec.count})</span>`;
    bar.appendChild(el);
  });

  // Populate sector dropdown
  const sectors = [...new Set(allStocks.map(s => s.sector))].sort();
  const sel = document.getElementById('sector-select');
  sectors.forEach(sec => {
    const opt = document.createElement('option');
    opt.value = sec; opt.textContent = sec;
    sel.appendChild(opt);
  });

  // Hide loading
  document.getElementById('loading-overlay').classList.add('hidden');
}

// ─── Filters ───────────────────────────────────────────────
function setupFilters() {
  // Category chips
  document.querySelectorAll('#category-filters .chip').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#category-filters .chip').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentFilters.category = btn.dataset.filter;
      applyFilters();
    });
  });

  // Tier chips (toggle)
  document.querySelectorAll('#tier-filters .chip').forEach(btn => {
    btn.addEventListener('click', () => {
      if (btn.classList.contains('active')) {
        btn.classList.remove('active');
        currentFilters.tier = null;
      } else {
        document.querySelectorAll('#tier-filters .chip').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentFilters.tier = btn.dataset.tier;
      }
      applyFilters();
    });
  });

  // Search
  document.getElementById('search-input').addEventListener('input', (e) => {
    currentFilters.search = e.target.value.toLowerCase();
    applyFilters();
  });

  // Sort
  document.getElementById('sort-select').addEventListener('change', (e) => {
    currentFilters.sort = e.target.value;
    applyFilters();
  });

  // Sector
  document.getElementById('sector-select').addEventListener('change', (e) => {
    currentFilters.sector = e.target.value;
    applyFilters();
  });
}

function applyFilters() {
  let stocks = [...allStocks];

  // Category
  if (currentFilters.category !== 'all') {
    stocks = stocks.filter(s => s.category === currentFilters.category);
  }

  // Tier
  if (currentFilters.tier) {
    stocks = stocks.filter(s => s.tier === currentFilters.tier);
  }

  // Search
  if (currentFilters.search) {
    const q = currentFilters.search;
    stocks = stocks.filter(s =>
      s.name.toLowerCase().includes(q) ||
      s.ticker.toLowerCase().includes(q) ||
      (s.sector || '').toLowerCase().includes(q)
    );
  }

  // Sector
  if (currentFilters.sector !== 'all') {
    stocks = stocks.filter(s => s.sector === currentFilters.sector);
  }

  // Sort
  const [field, dir] = currentFilters.sort.split('_');
  const asc = dir === 'asc';
  stocks.sort((a, b) => {
    let va, vb;
    if (field === 'composite') { va = a.scores.composite; vb = b.scores.composite; }
    else if (field === 'fundamental') { va = a.scores.fundamental; vb = b.scores.fundamental; }
    else if (field === 'technical') { va = a.scores.technical; vb = b.scores.technical; }
    else if (field === 'event') { va = a.scores.event; vb = b.scores.event; }
    else if (field === 'scoredelta') { va = a.score_change || 0; vb = b.score_change || 0; }
    else if (field === 'streak') { va = a.score_streak || 0; vb = b.score_streak || 0; }
    else if (field === 'change') {
      const period = currentFilters.sort.includes('1m') ? 'change_1m' : 'change_3m';
      va = a[period] || 0; vb = b[period] || 0;
    }
    else if (field === 'name') { va = a.name; vb = b.name; return asc ? va.localeCompare(vb) : vb.localeCompare(va); }
    else { va = a.scores.composite; vb = b.scores.composite; }
    return asc ? va - vb : vb - va;
  });

  filteredStocks = stocks;
  setText('results-count', `${stocks.length} stock${stocks.length !== 1 ? 's' : ''}`);
  renderGrid(stocks);
}

// ─── Grid ──────────────────────────────────────────────────
function renderGrid(stocks) {
  const grid = document.getElementById('stocks-grid');
  const empty = document.getElementById('empty-state');

  if (!stocks.length) {
    grid.innerHTML = '';
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';

  grid.innerHTML = stocks.map((s, i) => {
    const change1m = s.change_1m || 0;
    const changeClass = change1m >= 0 ? 'positive' : 'negative';
    const changeStr = (change1m >= 0 ? '+' : '') + change1m.toFixed(1) + '%';

    const fScore = s.scores.fundamental || 0;
    const tScore = s.scores.technical || 0;
    const eScore = s.scores.event || 0;

    const scDelta = s.score_change;
    const scDeltaHtml = scDelta !== null && scDelta !== undefined
      ? `<span class="card-score-delta ${scDelta >= 0 ? 'positive' : 'negative'}">${scDelta >= 0 ? '▲' : '▼'}${Math.abs(scDelta).toFixed(1)}</span>`
      : '';

    return `
      <div class="stock-card tier-${s.tier}" onclick="openModal('${s.ticker}')" style="animation-delay:${Math.min(i * 0.03, 0.5)}s">
        <div class="card-header">
          <div>
            <div class="card-name">${s.name}</div>
            <div class="card-ticker">${s.ticker} ${scDeltaHtml}</div>
          </div>
          <div class="card-score-badge tier-${s.tier}">${s.scores.composite}</div>
        </div>
        <div class="card-meta">
          <span class="card-tag">${s.category}</span>
          <span class="card-tag">${s.sector}</span>
        </div>
        <div class="card-price-row">
          <span class="card-price">₹${formatPrice(s.current_price)}</span>
          <span class="card-change ${changeClass}">${changeStr}</span>
        </div>
        <div class="card-scores">
          ${scoreBar('Fund', fScore)}
          ${scoreBar('Tech', tScore)}
          ${scoreBar('Event', eScore)}
        </div>
        ${renderSparkline(s.score_history || [], s.tier)}
        ${renderStreakBadge(s.score_streak || 0)}
      </div>`;
  }).join('');
}

function scoreBar(label, score) {
  const cls = score >= 70 ? 'good' : score >= 55 ? 'ok' : score >= 40 ? 'neutral' : 'bad';
  return `<div class="card-score-item">
    <div class="card-score-label">${label}</div>
    <div class="card-score-bar"><div class="card-score-fill ${cls}" style="width:${score}%"></div></div>
  </div>`;
}

// ─── Modal ─────────────────────────────────────────────────
function openModal(ticker) {
  const stock = allStocks.find(s => s.ticker === ticker);
  if (!stock) return;

  const overlay = document.getElementById('modal-overlay');
  overlay.classList.add('active');
  document.body.style.overflow = 'hidden';

  setText('modal-stock-name', stock.name);
  setText('modal-ticker', stock.ticker);
  setText('modal-sector', stock.sector);
  setText('modal-category', stock.category.toUpperCase());

  const badge = document.getElementById('modal-tier-badge');
  badge.textContent = stock.tier.replace('_', ' ').toUpperCase();
  badge.className = `modal-tier-badge ${stock.tier}`;

  setText('modal-price', `₹${formatPrice(stock.current_price)}`);
  const ch = document.getElementById('modal-change-1d');
  const c1d = stock.change_1d || 0;
  ch.textContent = (c1d >= 0 ? '+' : '') + c1d.toFixed(2) + '%';
  ch.className = `modal-change ${c1d >= 0 ? 'positive' : 'negative'}`;
  ch.style.color = c1d >= 0 ? 'var(--green)' : 'var(--red)';
  ch.style.background = c1d >= 0 ? 'var(--green-bg)' : 'var(--red-bg)';

  // Score bars
  setScoreBar('fundamental', stock.scores.fundamental);
  setScoreBar('technical', stock.scores.technical);
  setScoreBar('event', stock.scores.event);

  // Score ring
  drawScoreRing(stock.scores.composite, stock.tier);

  // Tabs
  document.querySelectorAll('.modal-tab').forEach(t => t.classList.remove('active'));
  document.getElementById('tab-fundamentals').classList.add('active');
  renderTabContent('fundamentals', stock);

  document.querySelectorAll('.modal-tab').forEach(tab => {
    tab.onclick = () => {
      document.querySelectorAll('.modal-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      renderTabContent(tab.dataset.tab, stock);
    };
  });
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('active');
  document.body.style.overflow = '';
}

document.getElementById('modal-close').addEventListener('click', closeModal);
document.getElementById('modal-overlay').addEventListener('click', (e) => {
  if (e.target === e.currentTarget) closeModal();
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(); });

function setScoreBar(type, score) {
  const bar = document.getElementById(`bar-${type}`);
  const val = document.getElementById(`val-${type}`);
  const color = score >= 70 ? 'var(--green)' : score >= 55 ? 'var(--blue)' : score >= 40 ? 'var(--yellow)' : 'var(--red)';
  bar.style.width = score + '%';
  bar.style.background = color;
  val.textContent = score;
  val.style.color = color;
}

function drawScoreRing(score, tier) {
  const canvas = document.getElementById('score-ring-canvas');
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  canvas.width = 160 * dpr; canvas.height = 160 * dpr;
  ctx.scale(dpr, dpr);

  const cx = 80, cy = 80, r = 62, lw = 8;
  const colors = { strong_buy: '#00d68f', buy: '#4da6ff', watch: '#ffc048', avoid: '#ff6b6b' };
  const color = colors[tier] || '#6c5ce7';

  // Background arc
  ctx.beginPath();
  ctx.arc(cx, cy, r, -0.5 * Math.PI, 1.5 * Math.PI);
  ctx.strokeStyle = 'rgba(255,255,255,0.06)';
  ctx.lineWidth = lw; ctx.lineCap = 'round'; ctx.stroke();

  // Score arc
  const angle = (score / 100) * 2 * Math.PI;
  ctx.beginPath();
  ctx.arc(cx, cy, r, -0.5 * Math.PI, -0.5 * Math.PI + angle);
  ctx.strokeStyle = color;
  ctx.lineWidth = lw; ctx.lineCap = 'round'; ctx.stroke();

  // Glow
  ctx.shadowColor = color; ctx.shadowBlur = 12;
  ctx.beginPath();
  ctx.arc(cx, cy, r, -0.5 * Math.PI, -0.5 * Math.PI + angle);
  ctx.strokeStyle = color; ctx.lineWidth = 3; ctx.stroke();
  ctx.shadowBlur = 0;

  setText('score-ring-value', score);
  document.getElementById('score-ring-value').style.color = color;
}

// ─── Tab Content ───────────────────────────────────────────
function renderTabContent(tab, stock) {
  const el = document.getElementById('modal-tab-content');

  if (tab === 'fundamentals') {
    const f = stock.fundamentals || {};
    el.innerHTML = `<div class="detail-grid">
      ${detailItem('P/E Ratio', f.pe_ratio, v => v < 25 ? 'good' : v < 40 ? 'neutral' : 'bad')}
      ${detailItem('P/B Ratio', f.pb_ratio, v => v < 3 ? 'good' : v < 5 ? 'neutral' : 'bad')}
      ${detailItem('ROE', f.roe, v => v > 15 ? 'good' : v > 8 ? 'neutral' : 'bad', '%')}
      ${detailItem('Revenue Growth', f.revenue_growth, v => v > 10 ? 'good' : v > 0 ? 'neutral' : 'bad', '%')}
      ${detailItem('Profit Growth', f.profit_growth, v => v > 12 ? 'good' : v > 0 ? 'neutral' : 'bad', '%')}
      ${detailItem('Debt/Equity', f.debt_to_equity, v => v < 0.5 ? 'good' : v < 1 ? 'neutral' : 'bad')}
      ${detailItem('Promoter Hold', f.promoter_holding, v => v > 50 ? 'good' : v > 30 ? 'neutral' : 'bad', '%')}
      ${detailItem('Current Ratio', f.current_ratio, v => v > 1.5 ? 'good' : v > 1 ? 'neutral' : 'bad')}
      ${detailItem('EPS', f.eps, v => v > 20 ? 'good' : v > 5 ? 'neutral' : 'bad', '')}
      ${detailItem('PEG Ratio', f.peg_ratio, v => v <= 1 ? 'good' : v <= 2 ? 'neutral' : 'bad')}
      ${detailItem('P/S Ratio', f.ps_ratio, v => v < 3 ? 'good' : v < 10 ? 'neutral' : 'bad')}
      ${detailItem('Oper. Margin', f.operating_margin, v => v > 15 ? 'good' : v > 5 ? 'neutral' : 'bad', '%')}
      ${detailItem('ROA', f.roa, v => v > 8 ? 'good' : v > 3 ? 'neutral' : 'bad', '%')}
      ${detailItem('FCF Yield', f.fcf_yield, v => v > 4 ? 'good' : v > 0 ? 'neutral' : 'bad', '%')}
      ${detailItem('Interest Cov.', f.interest_coverage, v => v > 3 ? 'good' : v > 1.5 ? 'neutral' : 'bad', 'x')}
    </div>`;
  } else if (tab === 'technicals') {
    const t = stock.technicals || {};
    el.innerHTML = `<div class="detail-grid">
      ${detailItem('RSI (14)', t.rsi, v => (v >= 40 && v <= 65) ? 'good' : v < 30 ? 'bad' : v > 70 ? 'bad' : 'neutral')}
      ${detailItem('MACD Signal', t.macd_signal, v => v?.includes('bullish') ? 'good' : v?.includes('bearish') ? 'bad' : 'neutral', '', true)}
      ${detailItem('SMA50 > SMA200', t.sma50_above_sma200, v => v ? 'good' : 'bad', '', true)}
      ${detailItem('Price vs EMA20', t.price_vs_ema20, v => v === 'above' ? 'good' : 'bad', '', true)}
      ${detailItem('Bollinger Pos', t.bollinger_position, v => v === 'near_lower' ? 'good' : v === 'near_upper' ? 'bad' : 'neutral', '', true)}
      ${detailItem('ADX', t.adx, v => v > 25 ? 'good' : v > 20 ? 'neutral' : 'bad')}
      ${detailItem('Volume Trend', t.volume_trend, v => v?.includes('accumulation') ? 'good' : v === 'distribution' ? 'bad' : 'neutral', '', true)}
      ${detailItem('From 52W High', t.pct_from_52w_high, v => v < 15 ? 'good' : v < 30 ? 'neutral' : 'bad', '%')}
    </div>`;
  } else if (tab === 'events') {
    const e = stock.events || {};
    el.innerHTML = `<div class="detail-grid">
      ${detailItem('Revenue Trend', e.revenue_trend, v => v?.includes('growth') ? 'good' : v?.includes('decline') ? 'bad' : 'neutral', '', true)}
      ${detailItem('Profit Trend', e.profit_trend, v => v?.includes('growth') ? 'good' : v?.includes('decline') ? 'bad' : 'neutral', '', true)}
      ${detailItem('Result Surprise', e.result_surprise, v => v === 'positive' ? 'good' : v === 'negative' ? 'bad' : 'neutral', '', true)}
      ${detailItem('Recent Dividend', e.recent_dividend, v => v ? 'good' : 'neutral', '', true)}
      ${detailItem('Split/Bonus', e.recent_split_bonus, v => v ? 'good' : 'neutral', '', true)}
      ${detailItem('Near 52W High', e.near_52w_high, v => v ? 'good' : 'neutral', '', true)}
      ${detailItem('Recent Breakout', e.recent_breakout, v => v ? 'good' : 'neutral', '', true)}
    </div>`;
  } else if (tab === 'history') {
    const hist = stock.score_history || [];
    const streak = stock.score_streak || 0;
    const streakText = streak > 0 ? `🔥 ${streak} scan${streak > 1 ? 's' : ''} improving` : streak < 0 ? `❄️ ${Math.abs(streak)} scan${Math.abs(streak) > 1 ? 's' : ''} declining` : '— Stable';
    const streakClass = streak > 0 ? 'good' : streak < 0 ? 'bad' : 'neutral';

    el.innerHTML = `
      <div class="history-streak-banner ${streakClass}">
        <span class="streak-label">Streak</span>
        <span class="streak-value">${streakText}</span>
      </div>
      ${renderHistoryChart(hist, stock.tier)}
      <div class="history-data-row">
        ${hist.length >= 2 ? `<div class="detail-item"><span class="detail-label">First recorded</span><span class="detail-value neutral">${hist[0]}</span></div>
        <div class="detail-item"><span class="detail-label">Latest</span><span class="detail-value neutral">${hist[hist.length-1]}</span></div>
        <div class="detail-item"><span class="detail-label">Min</span><span class="detail-value bad">${Math.min(...hist).toFixed(1)}</span></div>
        <div class="detail-item"><span class="detail-label">Max</span><span class="detail-value good">${Math.max(...hist).toFixed(1)}</span></div>
        <div class="detail-item"><span class="detail-label">Net Change</span><span class="detail-value ${hist[hist.length-1]-hist[0] >= 0 ? 'good':'bad'}">${(hist[hist.length-1]-hist[0] >= 0 ? '+' : '')}${(hist[hist.length-1]-hist[0]).toFixed(1)}</span></div>
        <div class="detail-item"><span class="detail-label">Scans Tracked</span><span class="detail-value neutral">${hist.length}</span></div>` : '<p style="color:var(--text-muted);text-align:center;padding:2rem;">Not enough history yet. Score trends appear after 2+ scans.</p>'}
      </div>`;
  } else if (tab === 'changes') {
    el.innerHTML = `
      <div class="changes-row">
        ${changeItem('1 Day', stock.change_1d)}
        ${changeItem('1 Week', stock.change_1w)}
        ${changeItem('1 Month', stock.change_1m)}
        ${changeItem('3 Months', stock.change_3m)}
        ${changeItem('6 Months', stock.change_6m)}
      </div>
      <div class="detail-grid" style="margin-top:1rem">
        ${detailItem('Market Cap', stock.market_cap ? formatLargeNumber(stock.market_cap) : null, () => 'neutral', '', true)}
        ${detailItem('Industry', stock.industry, () => 'neutral', '', true)}
      </div>`;
  }
}

function detailItem(label, value, colorFn, suffix = '', isText = false) {
  let display, cls;
  if (value === null || value === undefined) {
    display = '—'; cls = '';
  } else if (typeof value === 'boolean') {
    display = value ? 'Yes ✓' : 'No'; cls = colorFn(value);
  } else if (isText) {
    display = String(value).replace(/_/g, ' ');
    cls = colorFn(value);
  } else {
    display = Number(value).toFixed(2) + suffix;
    cls = colorFn(Number(value));
  }
  return `<div class="detail-item"><span class="detail-label">${label}</span><span class="detail-value ${cls}">${display}</span></div>`;
}

function changeItem(period, value) {
  const v = value || 0;
  const cls = v >= 0 ? 'good' : 'bad';
  return `<div class="change-item"><div class="change-period">${period}</div><div class="change-val ${cls}">${v >= 0 ? '+' : ''}${v.toFixed(1)}%</div></div>`;
}

// ─── Helpers ───────────────────────────────────────────────
function setText(id, text) { document.getElementById(id).textContent = text; }

function formatPrice(p) {
  if (!p) return '0';
  return Number(p).toLocaleString('en-IN', { maximumFractionDigits: 2 });
}

function formatLargeNumber(n) {
  if (!n) return '—';
  if (n >= 1e12) return (n / 1e12).toFixed(1) + 'T';
  if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B';
  if (n >= 1e7) return (n / 1e7).toFixed(1) + 'Cr';
  if (n >= 1e5) return (n / 1e5).toFixed(1) + 'L';
  return n.toLocaleString('en-IN');
}

// ─── Sparklines ────────────────────────────────────────────
function renderSparkline(history, tier) {
  if (!history || history.length < 2) return '';
  const w = 100, h = 28, pad = 2;
  const min = Math.min(...history) - 1;
  const max = Math.max(...history) + 1;
  const range = max - min || 1;
  const stepX = (w - pad * 2) / (history.length - 1);

  const points = history.map((v, i) => {
    const x = pad + i * stepX;
    const y = h - pad - ((v - min) / range) * (h - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const tierColors = { strong_buy: '#00d68f', buy: '#4da6ff', watch: '#ffc048', avoid: '#ff6b6b' };
  const color = tierColors[tier] || '#6c5ce7';
  const last = history[history.length - 1];
  const first = history[0];
  const trendColor = last >= first ? '#00d68f' : '#ff6b6b';

  // Gradient fill
  const fillPoints = `${pad.toFixed(1)},${(h - pad).toFixed(1)} ${points.join(' ')} ${(pad + (history.length - 1) * stepX).toFixed(1)},${(h - pad).toFixed(1)}`;

  return `
    <div class="card-sparkline">
      <svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
        <defs>
          <linearGradient id="sparkGrad-${tier}" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="${trendColor}" stop-opacity="0.3"/>
            <stop offset="100%" stop-color="${trendColor}" stop-opacity="0.02"/>
          </linearGradient>
        </defs>
        <polygon points="${fillPoints}" fill="url(#sparkGrad-${tier})" />
        <polyline points="${points.join(' ')}" fill="none" stroke="${trendColor}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
        <circle cx="${points[points.length-1].split(',')[0]}" cy="${points[points.length-1].split(',')[1]}" r="2" fill="${trendColor}" />
      </svg>
    </div>`;
}

function renderStreakBadge(streak) {
  if (streak === 0) return '';
  if (streak >= 2) {
    return `<div class="card-streak-badge improving" title="${streak} consecutive scans improving">🔥 ${streak} scan streak</div>`;
  } else if (streak <= -2) {
    return `<div class="card-streak-badge declining" title="${Math.abs(streak)} consecutive scans declining">❄️ ${Math.abs(streak)} scan streak</div>`;
  }
  return '';
}

// ─── Trending Alerts ───────────────────────────────────────
function renderTrendingAlerts() {
  const improving = allStocks.filter(s => (s.score_streak || 0) >= 2)
    .sort((a, b) => b.score_streak - a.score_streak)
    .slice(0, 8);
  const declining = allStocks.filter(s => (s.score_streak || 0) <= -2)
    .sort((a, b) => a.score_streak - b.score_streak)
    .slice(0, 8);

  const section = document.getElementById('trending-section');
  if (improving.length === 0 && declining.length === 0) {
    section.style.display = 'none';
    return;
  }
  section.style.display = '';

  const impEl = document.getElementById('trending-improving');
  const decEl = document.getElementById('trending-declining');

  impEl.innerHTML = improving.length ? improving.map(s => trendingChip(s, 'improving')).join('') : '<span class="trending-empty">No stocks with 2+ scan improvement streak</span>';
  decEl.innerHTML = declining.length ? declining.map(s => trendingChip(s, 'declining')).join('') : '<span class="trending-empty">No stocks with 2+ scan decline streak</span>';
}

function trendingChip(stock, type) {
  const streak = Math.abs(stock.score_streak || 0);
  const icon = type === 'improving' ? '🔥' : '❄️';
  const cls = type === 'improving' ? 'improving' : 'declining';
  return `<div class="trending-chip ${cls}" onclick="openModal('${stock.ticker}')">
    <span class="trending-chip-name">${stock.ticker}</span>
    <span class="trending-chip-score">${stock.scores.composite}</span>
    <span class="trending-chip-streak">${icon} ${streak}</span>
    ${renderMiniSparkline(stock.score_history || [], type)}
  </div>`;
}

function renderMiniSparkline(history, type) {
  if (!history || history.length < 2) return '';
  const w = 48, h = 16, pad = 1;
  const min = Math.min(...history) - 1;
  const max = Math.max(...history) + 1;
  const range = max - min || 1;
  const stepX = (w - pad * 2) / (history.length - 1);
  const points = history.map((v, i) => {
    const x = pad + i * stepX;
    const y = h - pad - ((v - min) / range) * (h - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const color = type === 'improving' ? '#00d68f' : '#ff6b6b';
  return `<svg class="trending-mini-spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
    <polyline points="${points.join(' ')}" fill="none" stroke="${color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
  </svg>`;
}

// ─── Modal History Chart ───────────────────────────────────
function renderHistoryChart(history, tier) {
  if (!history || history.length < 2) return '<div class="history-chart-empty">Not enough data for chart</div>';
  const w = 580, h = 180, padX = 40, padY = 25;
  const chartW = w - padX * 2;
  const chartH = h - padY * 2;
  const min = Math.min(...history) - 2;
  const max = Math.max(...history) + 2;
  const range = max - min || 1;
  const stepX = chartW / (history.length - 1);

  const tierColors = { strong_buy: '#00d68f', buy: '#4da6ff', watch: '#ffc048', avoid: '#ff6b6b' };
  const color = tierColors[tier] || '#6c5ce7';
  const last = history[history.length - 1];
  const first = history[0];
  const trendColor = last >= first ? '#00d68f' : '#ff6b6b';

  const points = history.map((v, i) => {
    const x = padX + i * stepX;
    const y = padY + chartH - ((v - min) / range) * chartH;
    return { x, y, v };
  });

  const polyline = points.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  const fillPoly = `${padX},${padY + chartH} ${polyline} ${points[points.length-1].x.toFixed(1)},${padY + chartH}`;

  // Y-axis labels
  const ySteps = 4;
  const yLabels = Array.from({length: ySteps + 1}, (_, i) => {
    const v = min + (range / ySteps) * i;
    const y = padY + chartH - (i / ySteps) * chartH;
    return `<text x="${padX - 6}" y="${y + 3}" text-anchor="end" fill="#505a78" font-size="10" font-family="JetBrains Mono, monospace">${v.toFixed(0)}</text>
    <line x1="${padX}" y1="${y}" x2="${w - padX}" y2="${y}" stroke="rgba(255,255,255,0.04)" stroke-width="1" />`;
  }).join('');

  // Data points with hover circles
  const dots = points.map((p, i) =>
    `<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="3.5" fill="${trendColor}" stroke="var(--bg-secondary)" stroke-width="1.5" opacity="0.85">
      <title>Scan ${i + 1}: ${p.v.toFixed(1)}</title>
    </circle>`
  ).join('');

  return `
  <div class="history-chart-container">
    <svg viewBox="0 0 ${w} ${h}" class="history-chart-svg">
      <defs>
        <linearGradient id="histGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="${trendColor}" stop-opacity="0.25" />
          <stop offset="100%" stop-color="${trendColor}" stop-opacity="0.02" />
        </linearGradient>
      </defs>
      ${yLabels}
      <polygon points="${fillPoly}" fill="url(#histGrad)" />
      <polyline points="${polyline}" fill="none" stroke="${trendColor}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
      ${dots}
    </svg>
  </div>`;
}
