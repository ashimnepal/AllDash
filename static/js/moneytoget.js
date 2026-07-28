(function () {
    const STORAGE_KEY = 'moneyToGetData';

    function loadEntries() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (raw) {
                const parsed = JSON.parse(raw);
                if (Array.isArray(parsed)) {
                    return parsed;
                }
            }
        } catch (err) {
            console.warn('Could not read Money To Get data', err);
        }
        return [
            { id: 'aashim', name: 'Aashim', amount: 1250 },
            { id: 'samira', name: 'Samira', amount: 920 },
            { id: 'rohit', name: 'Rohit', amount: 2500 },
            { id: 'nisha', name: 'Nisha', amount: 760 },
            { id: 'priya', name: 'Priya', amount: 1100 }
        ];
    }

    function saveEntries(entries) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
    }

    function formatCAD(amount) {
        const rounded = Math.round(amount * 100) / 100;
        return 'CAD ' + rounded.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
    }

    function hideModal(modalEl) {
        if (modalEl && window.bootstrap && window.bootstrap.Modal) {
            window.bootstrap.Modal.getOrCreateInstance(modalEl).hide();
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        const listEl = document.getElementById('money-to-get-list');
        if (!listEl) return; // Not on a page with this sidebar

        let entries = loadEntries();

        const totalEl = document.getElementById('money-to-get-total');
        const editModalEl = document.getElementById('editMoneyToGetModal');
        const editForm = document.getElementById('edit-money-to-get-form');
        const editIdInput = document.getElementById('edit-money-to-get-id');
        const editNameLabel = document.getElementById('edit-money-to-get-name');
        const editAmountInput = document.getElementById('edit-money-to-get-amount');

        function openEditModal(id) {
            const entry = entries.find(function (e) { return e.id === id; });
            if (!entry || !editModalEl || !window.bootstrap) return;
            editIdInput.value = entry.id;
            editNameLabel.textContent = entry.name;
            editAmountInput.value = entry.amount;
            window.bootstrap.Modal.getOrCreateInstance(editModalEl).show();
        }

        function deleteEntry(id) {
            const entry = entries.find(function (e) { return e.id === id; });
            if (!entry) return;
            const confirmed = window.confirm('Remove ' + entry.name + ' (' + formatCAD(entry.amount) + ') from this list?');
            if (!confirmed) return;
            entries = entries.filter(function (e) { return e.id !== id; });
            saveEntries(entries);
            render();
        }

        function render() {
            listEl.innerHTML = '';
            entries.forEach(function (entry) {
                const row = document.createElement('div');
                row.className = 'league-table-row money-bar-row';
                row.setAttribute('data-id', entry.id);

                const nameSpan = document.createElement('span');
                nameSpan.className = 'league-table-team';
                nameSpan.textContent = entry.name;

                const amountGroup = document.createElement('div');
                amountGroup.className = 'money-bar-amount-group';

                const amountSpan = document.createElement('span');
                amountSpan.className = 'league-table-points';
                amountSpan.textContent = formatCAD(entry.amount);

                const actions = document.createElement('div');
                actions.className = 'money-bar-actions';

                const editBtn = document.createElement('button');
                editBtn.type = 'button';
                editBtn.className = 'row-icon-btn edit-amount-btn';
                editBtn.title = 'Edit amount';
                editBtn.setAttribute('aria-label', 'Edit amount for ' + entry.name);
                editBtn.textContent = '\u270E';
                editBtn.addEventListener('click', function () {
                    openEditModal(entry.id);
                });

                const deleteBtn = document.createElement('button');
                deleteBtn.type = 'button';
                deleteBtn.className = 'row-icon-btn delete-amount-btn';
                deleteBtn.title = 'Delete entry';
                deleteBtn.setAttribute('aria-label', 'Delete entry for ' + entry.name);
                deleteBtn.textContent = '\u2715';
                deleteBtn.addEventListener('click', function () {
                    deleteEntry(entry.id);
                });

                actions.appendChild(editBtn);
                actions.appendChild(deleteBtn);
                amountGroup.appendChild(amountSpan);
                amountGroup.appendChild(actions);
                row.appendChild(nameSpan);
                row.appendChild(amountGroup);
                listEl.appendChild(row);
            });

            if (totalEl) {
                const total = entries.reduce(function (sum, e) { return sum + e.amount; }, 0);
                totalEl.textContent = formatCAD(total);
            }
        }

        if (editForm) {
            editForm.addEventListener('submit', function (e) {
                e.preventDefault();
                const id = editIdInput.value;
                const amount = parseFloat(editAmountInput.value);
                if (!amount || amount <= 0) {
                    editAmountInput.focus();
                    return;
                }
                const entry = entries.find(function (e2) { return e2.id === id; });
                if (entry) {
                    entry.amount = amount;
                    saveEntries(entries);
                    render();
                }
                hideModal(editModalEl);
            });
        }

        render();
    });
})();
