// Home dashboard's slow widgets (sports events, NEPSE summary, F1/MotoGP/League cards) all
// depend on third-party APIs. The page renders instantly without them, then this fetches
// them in the background and drops the rendered HTML into place once ready.
document.addEventListener('DOMContentLoaded', function () {
    const mapping = {
        'widget-events': 'events',
        'widget-stockmarket': 'stockmarket',
        'widget-f1': 'f1',
        'widget-motogp': 'motogp',
        'widget-premier': 'premier',
        'widget-champions': 'champions',
    };
    const targets = Object.keys(mapping).filter((id) => document.getElementById(id));
    if (!targets.length) return; // not on the home dashboard page

    fetch('/dashboard/widgets/')
        .then((res) => {
            if (!res.ok) throw new Error('Dashboard widgets request failed');
            return res.json();
        })
        .then((data) => {
            targets.forEach((id) => {
                const el = document.getElementById(id);
                const html = data[mapping[id]];
                if (el && typeof html === 'string') {
                    el.innerHTML = html;
                }
            });
        })
        .catch((err) => {
            console.error('Failed to load dashboard widgets', err);
        });
});
