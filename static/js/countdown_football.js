
    function updateMatchCountdowns() {
        document.querySelectorAll('.team-countdown').forEach(function (card) {
            const kickoff = new Date(card.dataset.kickoff);
            const daysEl = card.querySelector('[data-unit="days"]');
            const hoursEl = card.querySelector('[data-unit="hours"]');
            const minsEl = card.querySelector('[data-unit="mins"]');
            const secsEl = card.querySelector('[data-unit="secs"]');

            let diff = kickoff - new Date();
            if (diff < 0) diff = 0;

            const days = Math.floor(diff / (1000 * 60 * 60 * 24));
            diff -= days * (1000 * 60 * 60 * 24);
            const hours = Math.floor(diff / (1000 * 60 * 60));
            diff -= hours * (1000 * 60 * 60);
            const mins = Math.floor(diff / (1000 * 60));
            diff -= mins * (1000 * 60);
            const secs = Math.floor(diff / 1000);

            daysEl.textContent = String(days).padStart(2, '0');
            hoursEl.textContent = String(hours).padStart(2, '0');
            minsEl.textContent = String(mins).padStart(2, '0');
            secsEl.textContent = String(secs).padStart(2, '0');
        });
    }

    updateMatchCountdowns();
    setInterval(updateMatchCountdowns, 1000);
