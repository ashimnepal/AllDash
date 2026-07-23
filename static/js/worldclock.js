  function updateWorldClock() {
    document.querySelectorAll('.worldclock-tile').forEach(function (tile) {
      const timezone = tile.dataset.timezone;
      const timeEl = document.getElementById('time-' + timezone.replace(/[\/]/g, '-'));
      const dateEl = document.getElementById('date-' + timezone.replace(/[\/]/g, '-'));

      if (!timeEl || !dateEl) return;

      const now = new Date();
      const timeFormatter = new Intl.DateTimeFormat('en-US', {
        timeZone: timezone,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true,
      });

      const dateFormatter = new Intl.DateTimeFormat('en-US', {
        timeZone: timezone,
        weekday: 'short',
        day: '2-digit',
        month: 'short',
        year: 'numeric'
      });

      timeEl.textContent = timeFormatter.format(now);
      dateEl.textContent = dateFormatter.format(now);
    });
  }

  updateWorldClock();
  setInterval(updateWorldClock, 1000);