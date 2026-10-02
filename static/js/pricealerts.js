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
        const listEl = document.getElementById('price-alerts-list');
        if (!listEl) return; // Not on a page with this sidebar

        const activeBadgeEl = document.getElementById('price-alerts-active-badge');
        const toastContainerEl = document.getElementById('price-alert-toast-container');
        const testBtn = document.getElementById('test-price-alerts-btn');

        const addForm = document.getElementById('add-price-alert-form');
        const addModalEl = document.getElementById('addPriceAlertModal');
        const addSymbolSelect = document.getElementById('price-alert-add-symbol');
        const addCompanyNameInput = document.getElementById('price-alert-add-company-name');
        const addHolderSelect = document.getElementById('price-alert-add-holder');
        const addRecipientSelect = document.getElementById('price-alert-add-recipient');
        const addNewRecipientFields = document.getElementById('price-alert-add-new-recipient-fields');

        const editForm = document.getElementById('edit-price-alert-form');
        const editModalEl = document.getElementById('editPriceAlertModal');
        const editIdInput = document.getElementById('edit-price-alert-id');
        const editSymbolSelect = document.getElementById('price-alert-edit-symbol');
        const editCompanyNameInput = document.getElementById('price-alert-edit-company-name');
        const editActionSelect = document.getElementById('price-alert-edit-action');
        const editTargetPriceInput = document.getElementById('price-alert-edit-target-price');
        const editHolderSelect = document.getElementById('price-alert-edit-holder');
        const editRecipientSelect = document.getElementById('price-alert-edit-recipient');
        const editNewRecipientFields = document.getElementById('price-alert-edit-new-recipient-fields');

        function toggleNewRecipientFields(selectEl, fieldsEl) {
            if (!selectEl || !fieldsEl) return;
            selectEl.addEventListener('change', function () {
                fieldsEl.classList.toggle('d-none', selectEl.value !== '__new__');
            });
        }
        toggleNewRecipientFields(addRecipientSelect, addNewRecipientFields);
        toggleNewRecipientFields(editRecipientSelect, editNewRecipientFields);

        function populateRecipientSelect(selectEl, recipients, selectedId) {
            if (!selectEl) return;
            selectEl.innerHTML = '<option value="">Default number</option>';
            recipients.forEach(function (r) {
                const option = document.createElement('option');
                option.value = r.id;
                option.textContent = r.name;
                selectEl.appendChild(option);
            });
            const newOption = document.createElement('option');
            newOption.value = '__new__';
            newOption.textContent = '+ Add new recipient\u2026';
            selectEl.appendChild(newOption);
            selectEl.value = selectedId ? String(selectedId) : '';
        }

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

        // Reuse the same tradable symbol list the portfolio card fetches.
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

        function buildAlertRow(alert) {
            const row = document.createElement('li');
            row.className = 'alert-row';
            row.setAttribute('data-id', alert.id);
            row.setAttribute('data-symbol', alert.symbol);
            row.setAttribute('data-target-price', alert.target_price);
            row.setAttribute('data-action', alert.action);
            row.setAttribute('data-recipient-id', alert.recipient_id || '');
            row.setAttribute('data-holder-id', alert.holder_id || '');

            const actionChipClass = alert.action === 'buy' ? 'chip-soft-success' : 'chip-soft-danger';
            const chipClass = alert.is_triggered ? 'chip-soft-warning' : 'chip-soft-secondary';
            const chipText = alert.is_triggered ? 'Triggered' : 'Watching';

            row.innerHTML =
                '<div>' +
                    '<strong></strong>' +
                    '<p class="mb-0 text-muted stock-sub"></p>' +
                    '<p class="mb-0 text-muted stock-sub alert-holder-line d-none"></p>' +
                    '<p class="mb-0 text-muted stock-sub alert-recipient-line"></p>' +
                '</div>' +
                '<span class="chip ' + actionChipClass + '"></span>' +
                '<span class="chip ' + chipClass + '">' + chipText + '</span>' +
                '<div class="holding-actions">' +
                    '<button type="button" class="row-icon-btn edit-amount-btn" title="Edit alert">\u270E</button>' +
                    '<button type="button" class="row-icon-btn delete-amount-btn" title="Delete alert">\u2715</button>' +
                '</div>';

            row.querySelector('strong').textContent = alert.symbol;
            row.querySelector('.stock-sub').textContent = alert.status_text;
            const holderLineEl = row.querySelector('.alert-holder-line');
            if (alert.holder_name) {
                holderLineEl.textContent = 'Holds: ' + alert.holder_name;
                holderLineEl.classList.remove('d-none');
            }
            row.querySelector('.alert-recipient-line').textContent = 'Notifies: ' + (alert.recipient_name || 'Default number');
            row.querySelector('.chip.' + actionChipClass).textContent = alert.action_display || '';
            return row;
        }

        function render(data) {
            listEl.innerHTML = '';
            const alerts = data.price_alerts || [];
            if (!alerts.length) {
                const empty = document.createElement('li');
                empty.className = 'text-muted stock-sub mb-0';
                empty.textContent = "No alerts yet — create one to watch a stock's price.";
                listEl.appendChild(empty);
            } else {
                alerts.forEach(function (alert) {
                    listEl.appendChild(buildAlertRow(alert));
                });
            }
            if (activeBadgeEl && typeof data.price_alerts_active_count === 'number') {
                activeBadgeEl.textContent = data.price_alerts_active_count + ' active';
            }
            if (data.alert_recipients) {
                const addCurrent = addRecipientSelect ? addRecipientSelect.value : '';
                const editCurrent = editRecipientSelect ? editRecipientSelect.value : '';
                populateRecipientSelect(addRecipientSelect, data.alert_recipients, addCurrent);
                populateRecipientSelect(editRecipientSelect, data.alert_recipients, editCurrent);
            }
        }

        function showToast(alert) {
            if (!toastContainerEl) return;
            const toast = document.createElement('div');
            toast.className = 'price-alert-toast' + (alert.direction === 'down' ? ' is-down' : '');

            const body = document.createElement('div');
            const title = document.createElement('strong');
            title.textContent = '\uD83D\uDD14 ' + alert.symbol + ' price alert';
            const message = document.createElement('span');
            message.textContent = alert.status_text + ' (now ' + formatRs(alert.current_price) + ')';
            body.appendChild(title);
            body.appendChild(message);

            const closeBtn = document.createElement('button');
            closeBtn.type = 'button';
            closeBtn.className = 'price-alert-toast-close';
            closeBtn.setAttribute('aria-label', 'Dismiss');
            closeBtn.textContent = '\u2715';
            closeBtn.addEventListener('click', function () { toast.remove(); });

            toast.appendChild(body);
            toast.appendChild(closeBtn);
            toastContainerEl.appendChild(toast);
            setTimeout(function () { toast.remove(); }, 8000);
        }

        function showInfoToast(title, message, isError) {
            if (!toastContainerEl) return;
            const toast = document.createElement('div');
            toast.className = 'price-alert-toast' + (isError ? ' is-down' : '');

            const body = document.createElement('div');
            const titleEl = document.createElement('strong');
            titleEl.textContent = title;
            const messageEl = document.createElement('span');
            messageEl.textContent = message;
            body.appendChild(titleEl);
            body.appendChild(messageEl);

            const closeBtn = document.createElement('button');
            closeBtn.type = 'button';
            closeBtn.className = 'price-alert-toast-close';
            closeBtn.setAttribute('aria-label', 'Dismiss');
            closeBtn.textContent = '\u2715';
            closeBtn.addEventListener('click', function () { toast.remove(); });

            toast.appendChild(body);
            toast.appendChild(closeBtn);
            toastContainerEl.appendChild(toast);
            setTimeout(function () { toast.remove(); }, 8000);
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

        function openEditModal(row) {
            if (!editModalEl || !window.bootstrap) return;
            const symbol = row.getAttribute('data-symbol');
            const recipientId = row.getAttribute('data-recipient-id') || '';
            const holderId = row.getAttribute('data-holder-id') || '';

            editIdInput.value = row.getAttribute('data-id');
            editTargetPriceInput.value = row.getAttribute('data-target-price');
            editCompanyNameInput.value = '';
            if (editActionSelect) editActionSelect.value = row.getAttribute('data-action') || 'buy';
            if (editHolderSelect) editHolderSelect.value = holderId;
            if (editRecipientSelect) editRecipientSelect.value = recipientId;
            if (editNewRecipientFields) editNewRecipientFields.classList.add('d-none');

            symbolsPromise.then(function () {
                if (editSymbolSelect) editSymbolSelect.value = symbol;
            });

            window.bootstrap.Modal.getOrCreateInstance(editModalEl).show();
        }

        listEl.addEventListener('click', function (e) {
            const row = e.target.closest('.alert-row');
            if (!row) return;
            const id = row.getAttribute('data-id');
            const symbol = row.getAttribute('data-symbol');
            if (!id) return;

            if (e.target.closest('.edit-amount-btn')) {
                openEditModal(row);
            } else if (e.target.closest('.delete-amount-btn')) {
                const confirmed = window.confirm('Remove the alert for ' + symbol + '?');
                if (!confirmed) return;
                const formData = new FormData();
                formData.set('csrfmiddlewaretoken', getCsrfToken());
                postJson('/stockex_dash/alerts/' + id + '/delete/', formData).then(function (result) {
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
                if (formData.get('recipient') === '__new__') formData.set('recipient', '');
                formData.set('csrfmiddlewaretoken', getCsrfToken());
                postJson('/stockex_dash/alerts/add/', formData).then(function (result) {
                    if (result.ok && result.data.success) {
                        render(result.data);
                        addForm.reset();
                        if (addSymbolSelect) addSymbolSelect.selectedIndex = 0;
                        if (addHolderSelect) addHolderSelect.selectedIndex = 0;
                        if (addNewRecipientFields) addNewRecipientFields.classList.add('d-none');
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
                if (formData.get('recipient') === '__new__') formData.set('recipient', '');
                formData.set('csrfmiddlewaretoken', getCsrfToken());
                postJson('/stockex_dash/alerts/' + id + '/update/', formData).then(function (result) {
                    if (result.ok && result.data.success) {
                        render(result.data);
                        if (editNewRecipientFields) editNewRecipientFields.classList.add('d-none');
                        hideModal(editModalEl);
                    } else {
                        showFieldErrors(editForm, result.data.errors);
                    }
                });
            });
        }

        if (testBtn) {
            testBtn.addEventListener('click', function () {
                testBtn.disabled = true;
                const originalText = testBtn.textContent;
                testBtn.textContent = 'Sending test messages…';
                const formData = new FormData();
                formData.set('csrfmiddlewaretoken', getCsrfToken());
                postJson('/stockex_dash/alerts/test/', formData).then(function (result) {
                    const data = result.data || {};
                    (data.results || []).forEach(function (r) {
                        showInfoToast(
                            r.sent ? '\u2705 Test sent' : '\u274C Test failed',
                            r.label + ' (' + r.phone_number + ')' + (r.sent ? ' received the test message.' : ' did not receive it.'),
                            !r.sent
                        );
                    });
                    showInfoToast(result.ok && data.success ? 'Test complete' : 'Test failed', data.message || 'No response from server.', !(result.ok && data.success));
                }).catch(function () {
                    showInfoToast('Test failed', 'Could not reach the server.', true);
                }).then(function () {
                    testBtn.disabled = false;
                    testBtn.textContent = originalText;
                });
            });
        }

        const CHECK_POLL_MS = 15000;
        function checkAlerts() {
            fetch('/stockex_dash/alerts/check/', { credentials: 'same-origin' })
                .then(function (response) { return response.json(); })
                .then(function (data) {
                    render(data);
                    (data.triggered || []).forEach(showToast);
                })
                .catch(function () { /* silently retry on the next poll */ });
        }
        setInterval(checkAlerts, CHECK_POLL_MS);
    });
})();
