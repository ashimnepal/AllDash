(function () {
  const chartCanvas = document.getElementById('nepseChart');
  if (!chartCanvas) return; // Only run on the stock exchange dashboard

  /* ---------------- Market status (Kathmandu trading hours) ---------------- */
  function updateMarketStatus() {
    const dot = document.getElementById('market-status-dot');
    const text = document.getElementById('market-status-text');
    const hoursText = document.getElementById('market-hours-status');

    const formatter = new Intl.DateTimeFormat('en-US', {
      timeZone: 'Asia/Kathmandu',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      weekday: 'short',
    });
    const parts = formatter.formatToParts(new Date());
    const map = {};
    parts.forEach((p) => { map[p.type] = p.value; });

    const hour = parseInt(map.hour, 10);
    const minute = parseInt(map.minute, 10);
    const weekday = map.weekday;
    const minutesNow = hour * 60 + minute;
    const openMin = 11 * 60;
    const closeMin = 15 * 60;
    const isClosedDay = weekday === 'Sat';
    const isOpen = !isClosedDay && minutesNow >= openMin && minutesNow < closeMin;

    if (text) {
      text.textContent = isOpen ? 'Market Open' : 'Market Closed';
    }
    if (dot) {
      dot.classList.toggle('is-open', isOpen);
    }
    if (hoursText) {
      hoursText.textContent = isOpen
        ? 'Live trading until 3:00 PM NPT'
        : 'Opens 11:00 AM NPT (Sun–Fri)';
    }
  }
  updateMarketStatus();
  setInterval(updateMarketStatus, 60000);

  /* ---------------- Last updated timestamp ---------------- */
  const lastUpdatedEl = document.getElementById('last-updated');
  function updateTimestamp() {
    if (!lastUpdatedEl) return;
    const formatter = new Intl.DateTimeFormat('en-US', {
      timeZone: 'Asia/Kathmandu',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
    });
    lastUpdatedEl.textContent = 'Updated ' + formatter.format(new Date());
  }
  updateTimestamp();
  setInterval(updateTimestamp, 1000);

  /* ---------------- Deterministic pseudo-random series ---------------- */
  function seededRandom(seed) {
    let s = seed;
    return function next() {
      s = (s * 9301 + 49297) % 233280;
      return s / 233280;
    };
  }

  function generateSeries(points, base, volatility, seed) {
    const rand = seededRandom(seed);
    const data = [];
    let value = base;
    for (let i = 0; i < points; i += 1) {
      value += (rand() - 0.47) * volatility;
      data.push(Math.max(value, base * 0.82));
    }
    return data;
  }

  const datasets = {
    // NEPSE trading session is ~5 hours, not a full 24hr day - 5min interval over 5h = 60 points.
    '1D': generateSeries(60, 2170, 3.2, 11),
    '1W': generateSeries(35, 2140, 8, 22),
    '1M': generateSeries(30, 2080, 14, 33),
    '3M': generateSeries(60, 2020, 22, 44),
    '1Y': generateSeries(52, 1850, 40, 55),
    ALL: generateSeries(80, 1600, 55, 66),
  };

  /* ---------------- Main index chart (canvas) ---------------- */
  function drawChart(canvas, data) {
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const width = rect.width || canvas.parentElement.clientWidth || 600;
    const height = rect.height || 260;

    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, width, height);

    const max = Math.max(...data);
    const min = Math.min(...data);
    const range = max - min || 1;
    const stepX = width / (data.length - 1);
    const padY = 16;

    const pointY = (val) => height - ((val - min) / range) * (height - padY * 2) - padY;

    const isUp = data[data.length - 1] >= data[0];
    const lineColor = isUp ? '#34d399' : '#fb7185';
    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, isUp ? 'rgba(52, 211, 153, 0.35)' : 'rgba(251, 113, 133, 0.35)');
    gradient.addColorStop(1, 'rgba(15, 23, 42, 0)');

    ctx.beginPath();
    data.forEach((val, i) => {
      const x = i * stepX;
      const y = pointY(val);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.lineTo(width, height);
    ctx.lineTo(0, height);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    ctx.beginPath();
    data.forEach((val, i) => {
      const x = i * stepX;
      const y = pointY(val);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.lineWidth = 2.5;
    ctx.strokeStyle = lineColor;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    ctx.stroke();

    const lastY = pointY(data[data.length - 1]);
    ctx.beginPath();
    ctx.arc(width - 3, lastY, 4, 0, Math.PI * 2);
    ctx.fillStyle = lineColor;
    ctx.fill();
    ctx.beginPath();
    ctx.arc(width - 3, lastY, 7, 0, Math.PI * 2);
    ctx.strokeStyle = lineColor;
    ctx.globalAlpha = 0.35;
    ctx.stroke();
    ctx.globalAlpha = 1;
  }

  let currentFrame = '1D';
  function renderChart() {
    drawChart(chartCanvas, datasets[currentFrame]);
  }
  renderChart();
  window.addEventListener('resize', renderChart);

  document.querySelectorAll('.timeframe-pill').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.timeframe-pill').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      currentFrame = btn.dataset.frame;
      renderChart();
    });
  });

  /* ---------------- Watchlist category + search filter ---------------- */
  const watchlistSearchInput = document.querySelector('.watchlist-search');
  let watchlistCategory = 'all';

  function applyWatchlistFilters() {
    const query = (watchlistSearchInput?.value || '').trim().toLowerCase();
    document.querySelectorAll('.watchlist-card tbody tr[data-symbol]').forEach((row) => {
      const matchesCategory = watchlistCategory === 'all' || row.dataset.category === watchlistCategory;
      const company = row.querySelector('.stock-sub')?.textContent || '';
      const matchesSearch = !query
        || row.dataset.symbol.toLowerCase().includes(query)
        || company.toLowerCase().includes(query);
      row.classList.toggle('is-hidden', !(matchesCategory && matchesSearch));
    });
  }

  document.querySelectorAll('.watchlist-category-pill').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.watchlist-category-pill').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      watchlistCategory = btn.dataset.category;
      applyWatchlistFilters();
    });
  });

  watchlistSearchInput?.addEventListener('input', applyWatchlistFilters);

  /* ---------------- Sparklines (mini SVG) ---------------- */
  function drawSparkline(svg, points) {
    const w = 100;
    const h = 32;
    const max = Math.max(...points);
    const min = Math.min(...points);
    const range = max - min || 1;
    const stepX = w / (points.length - 1);
    const path = points
      .map((p, i) => `${i === 0 ? 'M' : 'L'}${(i * stepX).toFixed(1)},${(h - ((p - min) / range) * h).toFixed(1)}`)
      .join(' ');
    const isUp = points[points.length - 1] >= points[0];
    svg.innerHTML = `<path d="${path}" fill="none" stroke="${isUp ? '#34d399' : '#fb7185'}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />`;
  }

  function renderAllSparklines() {
    document.querySelectorAll('.sparkline[data-points]').forEach((svg) => {
      const raw = svg.getAttribute('data-points');
      const points = raw.split(',').map(Number);
      drawSparkline(svg, points);
    });
  }
  renderAllSparklines();

  /* ---------------- Live price ticking simulation ---------------- */
  const priceRows = document.querySelectorAll('[data-base-price]');
  function tick() {
    priceRows.forEach((row) => {
      const base = parseFloat(row.dataset.basePrice);
      const drift = (Math.random() - 0.48) * (base * 0.006);
      const newPrice = Math.max(base + drift, base * 0.5);
      row.dataset.basePrice = newPrice.toFixed(2);

      const priceCell = row.querySelector('.live-price');
      if (priceCell) {
        priceCell.textContent = 'Rs ' + newPrice.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        priceCell.classList.remove('flash-up', 'flash-down');
        void priceCell.offsetWidth;
        priceCell.classList.add(drift >= 0 ? 'flash-up' : 'flash-down');
      }

      const sparkline = row.querySelector('.sparkline[data-points]');
      if (sparkline) {
        const points = sparkline.getAttribute('data-points').split(',').map(Number);
        points.shift();
        points.push(Math.max(1, points[points.length - 1] + (drift >= 0 ? 1 : -1) * Math.random() * 2));
        sparkline.setAttribute('data-points', points.join(','));
        drawSparkline(sparkline, points);
      }
    });
  }
  let simInterval = setInterval(tick, 4000);

  /* ---------------- Live data feed: websocket push, REST as bootstrap/fallback ---------------- */
  // Django view `nepse_live_data` proxies the LAN NEPSE REST API and reshapes it into
  // the payload consumed below. Used once on load and again whenever the websocket
  // (real-time push feed) is down.
  const LIVE_DATA_URL = '/stockex_dash/live-data/';
  const LIVE_DATA_POLL_MS = 15000;
  const WS_URL = chartCanvas.dataset.wsUrl || '';
  /*
    Expected JSON payload shape - every top-level key is optional; only the
    fields that are present get applied to the dashboard:
    {
      "index":   { "value": 2187.42, "change": 18.64, "changePercent": 0.86,
                   "high": 2193.55, "low": 2168.20, "prevClose": 2168.78 },
      "market":  { "turnover": "Rs 4.82 Arba", "marketCap": "Rs 42.6 Kharba",
                   "advances": 182, "declines": 96, "unchanged": 41 },
      "gainers": [{ "symbol": "SHIVM", "company": "Shivam Cements", "price": 812.00, "changePercent": 6.42 }],
      "losers":  [{ "symbol": "NLIC", "company": "Nepal Life Insurance", "price": 985.00, "changePercent": -3.62 }],
      "watchlist": [{ "symbol": "NABIL", "price": 1102.00, "changePercent": -1.34, "volume": 184320 }]
    }
    The websocket server is expected to broadcast the same shape. If it instead sends
    something unrecognized, normalizeLivePayload() returns null and the message is
    dropped safely (logged to the console) instead of crashing the dashboard.
  */
  const feedStatusEl = document.getElementById('ws-feed-status');
  function setFeedStatus(state) {
    if (!feedStatusEl) return;
    const config = {
      connecting: ['Connecting…', 'chip chip-soft-secondary'],
      live: ['● Live feed', 'chip chip-soft-success'],
      offline: ['○ Feed offline — retrying…', 'chip chip-soft-danger'],
    };
    const [text, className] = config[state] || config.connecting;
    feedStatusEl.textContent = text;
    feedStatusEl.className = className;
  }

  function fmtNum(value) {
    return Number(value).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  function fmtRs(value) {
    return 'Rs ' + fmtNum(value);
  }
  function chipText(changePercent) {
    const up = Number(changePercent) >= 0;
    return `${up ? '▲' : '▼'} ${Math.abs(changePercent).toFixed(2)}%`;
  }

  function applyIndexUpdate(index) {
    if (!index) return;
    const priceEl = document.getElementById('chart-price-value');
    const statValueEl = document.getElementById('stat-index-value');
    const statChipEl = document.getElementById('stat-index-chip');
    const chartChipEl = document.getElementById('chart-change-chip');

    if (index.value != null) {
      const formatted = fmtNum(index.value);
      if (priceEl) priceEl.textContent = formatted;
      if (statValueEl) statValueEl.textContent = formatted;
    }
    if (index.changePercent != null) {
      const up = Number(index.changePercent) >= 0;
      if (statChipEl) {
        statChipEl.textContent = chipText(index.changePercent);
        statChipEl.className = 'chip ' + (up ? 'chip-soft-success' : 'chip-soft-danger');
      }
      if (chartChipEl) {
        chartChipEl.textContent = index.change != null
          ? `${up ? '+' : '-'}${Math.abs(index.change).toFixed(2)} (${Math.abs(index.changePercent).toFixed(2)}%)`
          : chipText(index.changePercent);
        chartChipEl.className = 'chip ' + (up ? 'chip-soft-success' : 'chip-soft-danger');
      }
    }

    const openEl = document.getElementById('stat-open');
    const highEl = document.getElementById('stat-high');
    const lowEl = document.getElementById('stat-low');
    const prevEl = document.getElementById('stat-prevclose');
    if (openEl && index.open != null) openEl.textContent = fmtNum(index.open);
    if (highEl && index.high != null) highEl.textContent = fmtNum(index.high);
    if (lowEl && index.low != null) lowEl.textContent = fmtNum(index.low);
    if (prevEl && index.prevClose != null) prevEl.textContent = fmtNum(index.prevClose);

    if (index.value != null && currentFrame === '1D') {
      const series = datasets['1D'];
      series.shift();
      series.push(Number(index.value));
      renderChart();
    }
  }

  function applyMarketUpdate(market) {
    if (!market) return;
    const turnoverEl = document.getElementById('stat-turnover');
    const turnoverChipEl = document.getElementById('stat-turnover-chip');
    const marketCapEl = document.getElementById('stat-marketcap');
    const marketCapChipEl = document.getElementById('stat-marketcap-chip');
    const advDecEl = document.getElementById('stat-advdec');
    const unchangedEl = document.getElementById('stat-unchanged');

    if (turnoverEl && market.turnover != null) turnoverEl.textContent = market.turnover;
    if (turnoverChipEl && market.turnoverChangePercent != null) {
      turnoverChipEl.textContent = chipText(market.turnoverChangePercent);
      turnoverChipEl.className = 'chip ' + (market.turnoverChangePercent >= 0 ? 'chip-soft-success' : 'chip-soft-danger');
    }
    if (marketCapEl && market.marketCap != null) marketCapEl.textContent = market.marketCap;
    if (marketCapChipEl && market.marketCapChangePercent != null) {
      marketCapChipEl.textContent = chipText(market.marketCapChangePercent);
      marketCapChipEl.className = 'chip ' + (market.marketCapChangePercent >= 0 ? 'chip-soft-success' : 'chip-soft-danger');
    }
    if (advDecEl && market.advances != null && market.declines != null) {
      advDecEl.textContent = `${market.advances} / ${market.declines}`;
    }
    if (unchangedEl && market.unchanged != null) unchangedEl.textContent = `${market.unchanged} unchanged`;
  }

  function moverRowHTML(item) {
    const up = Number(item.changePercent) >= 0;
    return `<li class="mover-row">
      <div class="mover-info">
        <strong>${item.symbol}</strong>
        <span class="text-muted stock-sub">${item.company || ''}</span>
      </div>
      <svg class="sparkline" viewBox="0 0 100 32" data-points="${item.sparkline || '10,12,14,16,18,20,22'}"></svg>
      <div class="mover-figures text-end">
        <p class="mb-0 mover-price">${fmtRs(item.price)}</p>
        <span class="chip ${up ? 'chip-soft-success' : 'chip-soft-danger'}">${chipText(item.changePercent)}</span>
      </div>
    </li>`;
  }

  function applyMoversUpdate(gainers, losers) {
    const gainersList = document.getElementById('gainers-list');
    const losersList = document.getElementById('losers-list');
    if (gainersList && Array.isArray(gainers)) {
      gainersList.innerHTML = gainers.map(moverRowHTML).join('');
    }
    if (losersList && Array.isArray(losers)) {
      losersList.innerHTML = losers.map(moverRowHTML).join('');
    }
    if (Array.isArray(gainers) || Array.isArray(losers)) renderAllSparklines();
  }

  function applyWatchlistUpdate(watchlist) {
    if (!Array.isArray(watchlist)) return;
    watchlist.forEach((item) => {
      const row = document.querySelector(`[data-symbol="${item.symbol}"]`);
      if (!row) return;
      if (item.price != null) {
        row.dataset.basePrice = item.price;
        const priceCell = row.querySelector('.live-price');
        if (priceCell) {
          priceCell.textContent = fmtRs(item.price);
          priceCell.classList.remove('flash-up', 'flash-down');
          void priceCell.offsetWidth;
          priceCell.classList.add(item.changePercent >= 0 ? 'flash-up' : 'flash-down');
        }
      }
      if (item.changePercent != null) {
        const changeCell = row.querySelector('.live-change');
        if (changeCell) {
          const up = Number(item.changePercent) >= 0;
          changeCell.innerHTML = `<span class="chip ${up ? 'chip-soft-success' : 'chip-soft-danger'}">${chipText(item.changePercent)}</span>`;
        }
      }
      if (item.volume != null) {
        const volumeCell = row.querySelectorAll('td')[4];
        if (volumeCell) volumeCell.textContent = Number(item.volume).toLocaleString('en-US');
      }
    });
  }

  let liveFeedEngaged = false;

  function applyLivePayload(payload) {
    if (!liveFeedEngaged) {
      liveFeedEngaged = true;
      if (simInterval) {
        clearInterval(simInterval);
        simInterval = null;
      }
    }
    setFeedStatus('live');
    applyIndexUpdate(payload.index);
    applyMarketUpdate(payload.market);
    applyMoversUpdate(payload.gainers, payload.losers);
    applyWatchlistUpdate(payload.watchlist);
    updateTimestamp();
  }

  function fetchLiveData() {
    if (!liveFeedEngaged) setFeedStatus('connecting');
    return fetch(LIVE_DATA_URL)
      .then((res) => {
        if (!res.ok) throw new Error('Live data request failed');
        return res.json();
      })
      .then((payload) => {
        if (payload.error) throw new Error(payload.error);
        applyLivePayload(payload);
      })
      .catch(() => {
        setFeedStatus('offline');
      });
  }

  /* ---------------- REST fallback polling (only runs while the websocket is down) ---------------- */
  let restPollTimer = null;
  function startRestFallbackPolling() {
    if (restPollTimer) return; // already polling, avoid duplicate timers
    restPollTimer = setInterval(fetchLiveData, LIVE_DATA_POLL_MS);
  }
  function stopRestFallbackPolling() {
    if (!restPollTimer) return;
    clearInterval(restPollTimer);
    restPollTimer = null;
  }

  /* ---------------- Websocket push feed (primary), with reconnect + REST fallback ---------------- */
  // Accepts a message only if it already matches the /stockex_dash/live-data/ shape.
  // Anything else is logged and dropped rather than guessed at, since the exact
  // websocket payload format has not been confirmed against a live market message.
  function normalizeLivePayload(raw) {
    if (!raw || typeof raw !== 'object') return null;
    if ('index' in raw || 'market' in raw || 'gainers' in raw || 'losers' in raw || 'watchlist' in raw) {
      return raw;
    }
    return null;
  }

  let ws = null;
  let wsReconnectTimer = null;
  let wsReconnectAttempts = 0;
  const WS_RECONNECT_BASE_MS = 1000;
  const WS_RECONNECT_MAX_MS = 30000;

  function scheduleReconnect() {
    if (wsReconnectTimer) return; // reconnect already scheduled, avoid stacking timers
    const delay = Math.min(WS_RECONNECT_BASE_MS * (2 ** wsReconnectAttempts), WS_RECONNECT_MAX_MS);
    wsReconnectAttempts += 1;
    wsReconnectTimer = setTimeout(() => {
      wsReconnectTimer = null;
      connectWebSocket();
    }, delay);
  }

  function connectWebSocket() {
    if (!WS_URL) {
      startRestFallbackPolling();
      return;
    }
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      return; // connection already live/in-flight, don't open a second one
    }

    setFeedStatus('connecting');
    try {
      ws = new WebSocket(WS_URL);
    } catch (err) {
      console.error('NEPSE websocket could not be created', err);
      startRestFallbackPolling();
      scheduleReconnect();
      return;
    }

    ws.onopen = () => {
      wsReconnectAttempts = 0;
      stopRestFallbackPolling();
    };

    ws.onmessage = (event) => {
      let raw;
      try {
        raw = JSON.parse(event.data);
      } catch (err) {
        console.warn('Ignoring malformed NEPSE websocket message', err);
        return;
      }
      const payload = normalizeLivePayload(raw);
      if (!payload) {
        console.warn('Unrecognized NEPSE websocket message shape, ignoring', raw);
        return;
      }
      applyLivePayload(payload);
    };

    ws.onerror = (err) => {
      console.error('NEPSE websocket error', err);
    };

    ws.onclose = () => {
      ws = null;
      setFeedStatus('offline');
      startRestFallbackPolling();
      scheduleReconnect();
    };
  }

  window.addEventListener('beforeunload', () => {
    if (wsReconnectTimer) clearTimeout(wsReconnectTimer);
    if (ws) ws.close();
  });

  fetchLiveData(); // populate immediately via REST
  connectWebSocket(); // then switch to real-time push updates

  /* ---------------- Movers tabs ---------------- */
  const moversTabs = document.querySelectorAll('.movers-tab');
  moversTabs.forEach((btn) => {
    btn.addEventListener('click', () => {
      moversTabs.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      const target = btn.dataset.target;
      document.querySelectorAll('.movers-list').forEach((list) => {
        list.classList.toggle('d-none', list.id !== target);
      });
    });
  });

  /* ---------------- Watchlist star toggle ---------------- */
  document.querySelectorAll('.watch-star').forEach((star) => {
    star.addEventListener('click', () => star.classList.toggle('active'));
  });

  /* ---------------- Refresh button ---------------- */
  const refreshBtn = document.getElementById('refresh-btn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      fetchLiveData();
      renderChart();
      refreshBtn.classList.add('spinning');
      setTimeout(() => refreshBtn.classList.remove('spinning'), 600);
    });
  }
})();
