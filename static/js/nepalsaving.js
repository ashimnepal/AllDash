(function () {
    const STORAGE_KEY = 'nepalSavingsData';

    function loadData() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (raw) {
                const parsed = JSON.parse(raw);
                if (parsed && Array.isArray(parsed.transactions)) {
                    return parsed;
                }
            }
        } catch (err) {
            console.warn('Could not read Nepal savings data', err);
        }
        return {
            transactions: [
                { type: 'added', amount: 45000, note: 'Initial savings from home', date: '2026-07-01' },
                { type: 'added', amount: 15000, note: 'Sent through remittance', date: '2026-07-10' },
                { type: 'used', amount: 8000, note: 'Family medical expense', date: '2026-07-18' }
            ]
        };
    }

    function saveData(data) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    }

    function formatNPR(amount) {
        const rounded = Math.round(amount * 100) / 100;
        return 'NPR ' + rounded.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
    }

    function formatDate(dateStr) {
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return dateStr;
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }

    function computeTotal(transactions) {
        return transactions.reduce(function (sum, tx) {
            return sum + (tx.type === 'added' ? tx.amount : -tx.amount);
        }, 0);
    }

    function render(data) {
        const total = computeTotal(data.transactions);
        const totalEl = document.getElementById('nepal-total-amount');
        if (totalEl) {
            totalEl.textContent = formatNPR(total);
            totalEl.classList.toggle('is-negative', total < 0);
        }

        const countEl = document.getElementById('nepal-transaction-count');
        if (countEl) {
            const count = data.transactions.length;
            countEl.textContent = count + (count === 1 ? ' entry' : ' entries');
        }

        const listEl = document.getElementById('nepal-transaction-list');
        const emptyEl = document.getElementById('nepal-empty-state');
        if (!listEl) return;

        listEl.innerHTML = '';

        if (!data.transactions.length) {
            if (emptyEl) emptyEl.classList.remove('d-none');
            return;
        }
        if (emptyEl) emptyEl.classList.add('d-none');

        const sorted = data.transactions.slice().sort(function (a, b) {
            return new Date(b.date) - new Date(a.date);
        });

        sorted.forEach(function (tx) {
            const row = document.createElement('tr');

            const typeCell = document.createElement('td');
            const chip = document.createElement('span');
            chip.className = 'chip ' + (tx.type === 'added' ? 'chip-soft-success' : 'chip-soft-danger');
            chip.textContent = tx.type === 'added' ? 'Savings Added' : 'Money Used';
            typeCell.appendChild(chip);

            const noteCell = document.createElement('td');
            noteCell.textContent = tx.note || '—';

            const amountCell = document.createElement('td');
            amountCell.textContent = (tx.type === 'added' ? '+ ' : '\u2212 ') + formatNPR(tx.amount);
            amountCell.className = tx.type === 'added' ? 'amount-added' : 'amount-used';

            const dateCell = document.createElement('td');
            dateCell.textContent = formatDate(tx.date);

            row.appendChild(typeCell);
            row.appendChild(noteCell);
            row.appendChild(amountCell);
            row.appendChild(dateCell);
            listEl.appendChild(row);
        });
    }

    function addTransaction(data, type, amount, note) {
        data.transactions.push({
            type: type,
            amount: amount,
            note: (note || '').trim(),
            date: new Date().toISOString().slice(0, 10)
        });
        saveData(data);
    }

    function hideModal(modalEl) {
        if (modalEl && window.bootstrap && window.bootstrap.Modal) {
            const instance = window.bootstrap.Modal.getOrCreateInstance(modalEl);
            instance.hide();
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        const totalEl = document.getElementById('nepal-total-amount');
        if (!totalEl) return; // Not on the Nepal Savings page

        const data = loadData();
        render(data);

        const addForm = document.getElementById('add-savings-form');
        const addModalEl = document.getElementById('addSavingsModal');
        if (addForm) {
            addForm.addEventListener('submit', function (e) {
                e.preventDefault();
                const amountInput = document.getElementById('savings-amount');
                const noteInput = document.getElementById('savings-note');
                const amount = parseFloat(amountInput.value);
                if (!amount || amount <= 0) {
                    amountInput.focus();
                    return;
                }
                addTransaction(data, 'added', amount, noteInput.value || 'Savings added');
                render(data);
                addForm.reset();
                hideModal(addModalEl);
            });
        }

        const useForm = document.getElementById('use-money-form');
        const useModalEl = document.getElementById('useMoneyModal');
        if (useForm) {
            useForm.addEventListener('submit', function (e) {
                e.preventDefault();
                const amountInput = document.getElementById('usage-amount');
                const noteInput = document.getElementById('usage-note');
                const amount = parseFloat(amountInput.value);
                if (!amount || amount <= 0) {
                    amountInput.focus();
                    return;
                }
                addTransaction(data, 'used', amount, noteInput.value || 'Money used');
                render(data);
                useForm.reset();
                hideModal(useModalEl);
            });
        }
    });
})();
