  (function updateNepalTime() {
    const pill = document.getElementById('nepal-time-pill');
    if (!pill) return;

    const now = new Date();
    const formatter = new Intl.DateTimeFormat('en-US', {
      timeZone: 'Asia/Kathmandu',
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
    });

    pill.textContent = formatter.format(now).replace(',', '');
  })();

  setInterval(updateNepalTime, 1000);
