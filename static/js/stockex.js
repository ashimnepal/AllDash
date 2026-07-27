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
    '1D': generateSeries(48, 2170, 3.2, 11),
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
  setInterval(tick, 4000);

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
      tick();
      renderChart();
      refreshBtn.classList.add('spinning');
      setTimeout(() => refreshBtn.classList.remove('spinning'), 600);
    });
  }
})();
