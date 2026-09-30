document.addEventListener('DOMContentLoaded', function () {
    const select = document.getElementById('past-race-select');
    if (!select) {
        return;
    }

    const panels = document.querySelectorAll('.past-race-result');

    select.addEventListener('change', function () {
        const key = select.value;
        panels.forEach(function (panel) {
            panel.classList.toggle('d-none', panel.dataset.raceKey !== key);
        });
    });
});
