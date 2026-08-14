(function () {
    function formatCAD(amount) {
        const rounded = Math.round(amount * 100) / 100;
        return 'CAD ' + rounded.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
    }

    function clearFieldErrors(form) {
        form.querySelectorAll('[data-error-for]').forEach(function (el) {
            el.textContent = '';
        });
    }

    function showFieldErrors(form, errors) {
        Object.keys(errors || {}).forEach(function (field) {
            const el = form.querySelector('[data-error-for="' + field + '"]');
            if (el) el.textContent = errors[field].join(' ');
        });
    }

    function showAlert(message, isError) {
        const container = document.getElementById('expense-tracking-alerts');
        if (!container) return;
        container.innerHTML = '';
        const alert = document.createElement('div');
        alert.className = 'alert ' + (isError ? 'alert-danger' : 'alert-success');
        alert.setAttribute('role', 'alert');
        alert.textContent = message;
        container.appendChild(alert);
    }

    function hideModal(modalEl) {
        if (modalEl && window.bootstrap && window.bootstrap.Modal) {
            window.bootstrap.Modal.getOrCreateInstance(modalEl).hide();
        }
    }

    function renderExpenses(expenses, emptyMessage) {
        const body = document.getElementById('recent-expenses-body');
        if (!body) return;
        body.innerHTML = '';

        if (!expenses.length) {
            const row = document.createElement('tr');
            const cell = document.createElement('td');
            cell.colSpan = 4;
            cell.className = 'text-muted text-center';
            cell.textContent = emptyMessage || 'No expenses yet. Add your first expense to get started.';
            row.appendChild(cell);
            body.appendChild(row);
            return;
        }

        expenses.forEach(function (expense) {
            const row = document.createElement('tr');

            const nameCell = document.createElement('td');
            nameCell.textContent = expense.name;

            const categoryCell = document.createElement('td');
            const chip = document.createElement('span');
            chip.className = 'chip ' + expense.chip_class;
            chip.textContent = expense.category_name;
            categoryCell.appendChild(chip);

            const amountCell = document.createElement('td');
            amountCell.textContent = formatCAD(expense.amount);

            const dateCell = document.createElement('td');
            dateCell.textContent = expense.date;

            row.appendChild(nameCell);
            row.appendChild(categoryCell);
            row.appendChild(amountCell);
            row.appendChild(dateCell);
            body.appendChild(row);
        });
    }

    function renderDistribution(distribution) {
        const list = document.getElementById('spending-distribution-list');
        if (!list) return;
        list.innerHTML = '';

        if (!distribution.length) {
            const item = document.createElement('li');
            item.className = 'text-muted';
            item.textContent = 'No spending recorded this month yet.';
            list.appendChild(item);
            return;
        }

        distribution.forEach(function (entry) {
            const item = document.createElement('li');

            const legend = document.createElement('span');
            legend.className = 'legend ' + entry.legend_class;

            const strong = document.createElement('strong');
            strong.textContent = entry.percent + '%';

            item.appendChild(legend);
            item.appendChild(document.createTextNode(entry.name + ' '));
            item.appendChild(strong);
            list.appendChild(item);
        });
    }

    function applyStats(data) {
        const budgetEl = document.getElementById('stat-budget-amount');
        if (budgetEl) budgetEl.textContent = formatCAD(data.budget_amount);

        const spentEl = document.getElementById('stat-spent-so-far');
        if (spentEl) spentEl.textContent = formatCAD(data.spent_so_far);

        const remainingEl = document.getElementById('stat-remaining');
        if (remainingEl) remainingEl.textContent = formatCAD(data.remaining);

        const savingsEl = document.getElementById('stat-savings-goal');
        if (savingsEl) savingsEl.textContent = data.savings_goal_percent + '%';

        const badgeEl = document.getElementById('stat-budget-used-badge');
        if (badgeEl) badgeEl.textContent = data.budget_used_percent + '% used';

        const fillEl = document.getElementById('summary-fill-bar');
        if (fillEl) fillEl.style.width = data.budget_used_percent + '%';

        renderExpenses(data.expenses || []);
        renderDistribution(data.distribution || []);
    }

    function submitForm(form, extraFields) {
        const formData = new FormData(form);
        Object.keys(extraFields || {}).forEach(function (key) {
            formData.set(key, extraFields[key]);
        });
        return fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        }).then(function (response) {
            return response.json().then(function (data) {
                return { ok: response.ok, data: data };
            });
        });
    }

    function monthLabelFromValue(value) {
        const parts = value.split('-');
        const d = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, 1);
        return d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
    }

    function previousMonthValue(value) {
        let year, month;
        if (!value || value === 'all') {
            const now = new Date();
            year = now.getFullYear();
            month = now.getMonth() + 1;
        } else {
            const parts = value.split('-');
            year = parseInt(parts[0], 10);
            month = parseInt(parts[1], 10);
        }
        month -= 1;
        if (month < 1) {
            month = 12;
            year -= 1;
        }
        return year + '-' + String(month).padStart(2, '0');
    }

    function initMonthNavigation() {
        const select = document.getElementById('month-filter');
        const prevBtn = document.getElementById('month-prev-btn');
        const badge = document.getElementById('recent-expenses-badge');
        if (!select || !prevBtn) return;

        function loadMonth(value) {
            const url = window.location.pathname + '?month=' + encodeURIComponent(value);
            fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(function (response) { return response.json(); })
                .then(function (data) {
                    if (!data.success) return;
                    const emptyMessage = value === 'all'
                        ? undefined
                        : 'No expenses recorded for ' + data.month_label + '.';
                    renderExpenses(data.expenses, emptyMessage);
                    if (badge) badge.textContent = value === 'all' ? 'Auto-updated' : data.month_label;
                });
        }

        function ensureOption(value) {
            let option = select.querySelector('option[value="' + value + '"]');
            if (!option) {
                option = document.createElement('option');
                option.value = value;
                option.textContent = monthLabelFromValue(value);
                select.appendChild(option);
            }
            return option;
        }

        select.addEventListener('change', function () {
            loadMonth(select.value);
        });

        prevBtn.addEventListener('click', function () {
            const target = previousMonthValue(select.value);
            ensureOption(target);
            select.value = target;
            loadMonth(target);
        });
    }

    function initSummaryFill() {
        const fillEl = document.getElementById('summary-fill-bar');
        if (fillEl) fillEl.style.width = (fillEl.dataset.percent || 0) + '%';
    }

    document.addEventListener('DOMContentLoaded', function () {
        initMonthNavigation();
        initSummaryFill();

        const expenseForm = document.getElementById('add-expense-form');
        if (expenseForm) {
            expenseForm.addEventListener('submit', function (e) {
                e.preventDefault();
                clearFieldErrors(expenseForm);
                submitForm(expenseForm, { expense_submit: '1' }).then(function (result) {
                    if (result.ok && result.data.success) {
                        applyStats(result.data);
                        const monthSelect = document.getElementById('month-filter');
                        const badge = document.getElementById('recent-expenses-badge');
                        if (monthSelect) monthSelect.value = 'all';
                        if (badge) badge.textContent = 'Auto-updated';
                        expenseForm.reset();
                        showAlert(result.data.message, false);
                    } else {
                        showFieldErrors(expenseForm, result.data.errors);
                        showAlert(result.data.message || 'Could not save expense.', true);
                    }
                }).catch(function () {
                    showAlert('Something went wrong while saving the expense.', true);
                });
            });
        }

        const converterForm = document.getElementById('currency-converter-form');
        const converterPanel = document.getElementById('converter-result-panel');
        const converterIcon = document.getElementById('converter-result-icon');
        const converterResult = document.getElementById('converter-result');
        if (converterForm && converterPanel && converterResult) {
            function setConverterState(state, icon, text) {
                converterPanel.classList.remove('is-loading', 'is-success', 'is-error');
                converterPanel.classList.add(state);
                converterIcon.textContent = icon;
                converterResult.textContent = text;
            }

            converterForm.addEventListener('submit', function (e) {
                e.preventDefault();
                setConverterState('is-loading', '⏳', 'Converting…');
                submitForm(converterForm).then(function (result) {
                    if (result.ok && result.data.success) {
                        setConverterState('is-success', '✓', result.data.message);
                    } else {
                        setConverterState('is-error', '!', result.data.message || 'Could not convert currency.');
                    }
                }).catch(function () {
                    setConverterState('is-error', '!', 'Something went wrong while converting currency.');
                });
            });
        }

        const incomeForm = document.getElementById('add-income-form');
        if (incomeForm) {
            const incomeModalEl = document.getElementById('addIncomeModal');
            incomeForm.addEventListener('submit', function (e) {
                e.preventDefault();
                clearFieldErrors(incomeForm);
                submitForm(incomeForm, { income_submit: '1' }).then(function (result) {
                    if (result.ok && result.data.success) {
                        applyStats(result.data);
                        incomeForm.reset();
                        hideModal(incomeModalEl);
                        showAlert(result.data.message, false);
                    } else {
                        showFieldErrors(incomeForm, result.data.errors);
                        showAlert(result.data.message || 'Could not save income.', true);
                    }
                }).catch(function () {
                    showAlert('Something went wrong while saving the income.', true);
                });
            });
        }
    });
})();
