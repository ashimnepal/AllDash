(function () {
    function formatRs(amount) {
        const rounded = Math.round((Number(amount) + Number.EPSILON) * 100) / 100;
        return 'Rs ' + rounded.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
    }

    function getCsrfToken() {
        const cookie = document.cookie.split('; ').find(function (part) {
            return part.indexOf('csrftoken=') === 0;
        });
        return cookie ? decodeURIComponent(cookie.split('=')[1]) : '';
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

    function hideModal(modalEl) {
        if (modalEl && window.bootstrap && window.bootstrap.Modal) {
            window.bootstrap.Modal.getOrCreateInstance(modalEl).hide();
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        const listEl = document.getElementById('portfolio-holdings-list');
        if (!listEl) return; // Not on a page with this sidebar

        const totalCurrentEl = document.getElementById('portfolio-total-current');
        const totalInvestedEl = document.getElementById('portfolio-total-invested');
        const totalProfitEl = document.getElementById('portfolio-total-profit');
        const totalChipEl = document.getElementById('portfolio-total-chip');

        const addForm = document.getElementById('add-portfolio-form');
        const addModalEl = document.getElementById('addPortfolioModal');
        const addSymbolSelect = document.getElementById('portfolio-add-symbol');
        const addCompanyNameInput = document.getElementById('portfolio-add-company-name');

        const editForm = document.getElementById('edit-portfolio-form');
        const editModalEl = document.getElementById('editPortfolioModal');
        const editIdInput = document.getElementById('edit-portfolio-id');
        const editSymbolSelect = document.getElementById('portfolio-edit-symbol');
        const editCompanyNameInput = document.getElementById('portfolio-edit-company-name');
        const editQuantityInput = document.getElementById('portfolio-edit-quantity');
        const editBuyPriceInput = document.getElementById('portfolio-edit-buy-price');
        const editBuyDateInput = document.getElementById('portfolio-edit-buy-date');

        function populateSymbolSelect(selectEl, symbols) {
            if (!selectEl) return;
            selectEl.innerHTML = '<option value="">Select a stock…</option>';
            symbols.forEach(function (item) {
                const option = document.createElement('option');
                option.value = item.symbol;
                option.setAttribute('data-name', item.name || '');
                option.textContent = item.name ? (item.symbol + ' — ' + item.name) : item.symbol;
                selectEl.appendChild(option);
            });
        }

        // Fetch the tradable symbol list once and reuse it for both modals.
        const symbolsPromise = fetch('/stockex_dash/portfolio/symbols/', { credentials: 'same-origin' })
            .then(function (response) { return response.json(); })
            .then(function (data) {
                const symbols = data.symbols || [];
                populateSymbolSelect(addSymbolSelect, symbols);
                populateSymbolSelect(editSymbolSelect, symbols);
                return symbols;
            })
            .catch(function () {
                const fallback = '<option value="">Stock list unavailable</option>';
                if (addSymbolSelect) addSymbolSelect.innerHTML = fallback;
                if (editSymbolSelect) editSymbolSelect.innerHTML = fallback;
                return [];
            });

        function syncCompanyName(selectEl, hiddenInput) {
            if (!selectEl || !hiddenInput) return;
            selectEl.addEventListener('change', function () {
                const option = selectEl.options[selectEl.selectedIndex];
                hiddenInput.value = option ? (option.getAttribute('data-name') || '') : '';
            });
        }
        syncCompanyName(addSymbolSelect, addCompanyNameInput);
        syncCompanyName(editSymbolSelect, editCompanyNameInput);

        function buildHoldingItem(holding) {
            const item = document.createElement('div');
            item.className = 'holding-item ' + (holding.is_up ? 'is-up' : 'is-down');
            item.setAttribute('data-id', holding.id);
            item.setAttribute('data-symbol', holding.symbol);
            item.setAttribute('data-company-name', holding.company_name || '');
            item.setAttribute('data-quantity', holding.quantity);
            item.setAttribute('data-buy-price', holding.buy_price);
            item.setAttribute('data-buy-date', holding.buy_date);

            const chipClass = holding.is_up ? 'chip-soft-success' : 'chip-soft-danger';
            const arrow = holding.is_up ? '\u25b2' : '\u25bc';
            const sign = holding.is_up ? '+' : '';

            item.innerHTML =
                '<div class="holding-top">' +
                    '<strong></strong>' +
                    '<span class="chip ' + chipClass + '">' + arrow + ' ' + holding.profit_percent.toFixed(2) + '%</span>' +
                    '<div class="holding-actions">' +
                        '<button type="button" class="row-icon-btn edit-amount-btn" title="Edit holding">\u270E</button>' +
                        '<button type="button" class="row-icon-btn delete-amount-btn" title="Delete holding">\u2715</button>' +
                    '</div>' +
                '</div>' +
                '<p class="holding-sub"></p>' +
                '<div class="holding-prices">' +
                    '<span>Bought <strong>' + formatRs(holding.buy_price) + '</strong></span>' +
                    '<span>Now <strong>' + formatRs(holding.current_price) + '</strong></span>' +
                '</div>' +
                '<div class="holding-meta">' +
                    '<span class="holding-date"></span>' +
                    '<span class="holding-profit ' + (holding.is_up ? 'text-up' : 'text-down') + '">' + sign + formatRs(holding.profit) + '</span>' +
                '</div>';

            item.querySelector('.holding-top strong').textContent = holding.symbol;
            item.querySelector('.holding-sub').textContent = holding.company_name || '';
            item.querySelector('.holding-date').textContent = 'Bought ' + holding.buy_date + ' \u00b7 Qty ' + holding.quantity;

            return item;
        }

        function render(data) {
            listEl.innerHTML = '';
            const holdings = data.holdings || [];
            if (!holdings.length) {
                const empty = document.createElement('p');
                empty.className = 'text-muted stock-sub mb-0';
                empty.textContent = 'No holdings yet — add the first stock you bought.';
                listEl.appendChild(empty);
            } else {
                holdings.forEach(function (holding) {
                    listEl.appendChild(buildHoldingItem(holding));
                });
            }

            const totalProfit = data.total_profit || 0;
            const isUp = totalProfit >= 0;

            if (totalCurrentEl) totalCurrentEl.textContent = formatRs(data.total_current || 0);
            if (totalInvestedEl) totalInvestedEl.textContent = formatRs(data.total_invested || 0);
            if (totalProfitEl) {
                totalProfitEl.textContent = (isUp ? '+' : '') + formatRs(totalProfit);
                totalProfitEl.className = isUp ? 'text-up' : 'text-down';
            }
            if (totalChipEl) {
                totalChipEl.className = 'chip ' + (isUp ? 'chip-soft-success' : 'chip-soft-danger');
                totalChipEl.textContent = (isUp ? '\u25b2' : '\u25bc') + ' ' + (data.total_profit_percent || 0).toFixed(2) + '%';
            }
        }

        function postJson(url, body) {
            const csrfToken = getCsrfToken();
            return fetch(url, {
                method: 'POST',
                body: body,
                credentials: 'same-origin',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken,
                },
            }).then(function (response) {
                return response.json().then(function (data) {
                    return { ok: response.ok, data: data };
                });
            });
        }

        function openEditModal(item) {
            if (!editModalEl || !window.bootstrap) return;
            const symbol = item.getAttribute('data-symbol');

            editIdInput.value = item.getAttribute('data-id');
            editQuantityInput.value = item.getAttribute('data-quantity');
            editBuyPriceInput.value = item.getAttribute('data-buy-price');
            editBuyDateInput.value = item.getAttribute('data-buy-date');
            editCompanyNameInput.value = item.getAttribute('data-company-name');

            symbolsPromise.then(function () {
                if (editSymbolSelect) editSymbolSelect.value = symbol;
            });

            window.bootstrap.Modal.getOrCreateInstance(editModalEl).show();
        }

        listEl.addEventListener('click', function (e) {
            const item = e.target.closest('.holding-item');
            if (!item) return;
            const id = item.getAttribute('data-id');
            const symbol = item.getAttribute('data-symbol');

            if (e.target.closest('.edit-amount-btn')) {
                openEditModal(item);
            } else if (e.target.closest('.delete-amount-btn')) {
                const confirmed = window.confirm('Remove ' + symbol + ' from your portfolio?');
                if (!confirmed) return;
                const formData = new FormData();
                formData.set('csrfmiddlewaretoken', getCsrfToken());
                postJson('/stockex_dash/portfolio/' + id + '/delete/', formData).then(function (result) {
                    if (result.ok && result.data.success) {
                        render(result.data);
                    }
                });
            }
        });

        if (addForm) {
            addForm.addEventListener('submit', function (e) {
                e.preventDefault();
                clearFieldErrors(addForm);
                const formData = new FormData(addForm);
                formData.set('csrfmiddlewaretoken', getCsrfToken());
                postJson('/stockex_dash/portfolio/add/', formData).then(function (result) {
                    if (result.ok && result.data.success) {
                        render(result.data);
                        addForm.reset();
                        if (addSymbolSelect) addSymbolSelect.selectedIndex = 0;
                        hideModal(addModalEl);
                    } else {
                        showFieldErrors(addForm, result.data.errors);
                    }
                });
            });
        }

        if (editForm) {
            editForm.addEventListener('submit', function (e) {
                e.preventDefault();
                clearFieldErrors(editForm);
                const id = editIdInput.value;
                const formData = new FormData(editForm);
                formData.set('csrfmiddlewaretoken', getCsrfToken());
                postJson('/stockex_dash/portfolio/' + id + '/update/', formData).then(function (result) {
                    if (result.ok && result.data.success) {
                        render(result.data);
                        hideModal(editModalEl);
                    } else {
                        showFieldErrors(editForm, result.data.errors);
                    }
                });
            });
        }
    });
})();
