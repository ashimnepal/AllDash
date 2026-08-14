(function () {
    function formatCAD(amount) {
        const rounded = Math.round(amount * 100) / 100;
        return 'CAD ' + rounded.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
    }

    function getCsrfToken() {
        const input = document.querySelector('[name=csrfmiddlewaretoken]');
        return input ? input.value : '';
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
        const listEl = document.getElementById('money-to-pay-list');
        if (!listEl) return; // Not on a page with this sidebar

        const totalEl = document.getElementById('money-to-pay-total');
        const addForm = document.getElementById('add-money-to-pay-form');
        const addModalEl = document.getElementById('addMoneyToPayModal');
        const editModalEl = document.getElementById('editMoneyToPayModal');
        const editForm = document.getElementById('edit-money-to-pay-form');
        const editIdInput = document.getElementById('edit-money-to-pay-id');
        const editNameLabel = document.getElementById('edit-money-to-pay-name');
        const editAmountInput = document.getElementById('edit-money-to-pay-amount');

        function render(data) {
            listEl.innerHTML = '';
            (data.entries || []).forEach(function (entry) {
                const row = document.createElement('div');
                row.className = 'league-table-row money-owed-row';
                row.setAttribute('data-id', entry.id);

                const nameSpan = document.createElement('span');
                nameSpan.className = 'league-table-team';
                nameSpan.textContent = entry.name;

                const amountGroup = document.createElement('div');
                amountGroup.className = 'money-owed-amount-group';

                const amountSpan = document.createElement('span');
                amountSpan.className = 'league-table-points';
                amountSpan.textContent = formatCAD(entry.amount);

                const actions = document.createElement('div');
                actions.className = 'money-owed-actions';

                const editBtn = document.createElement('button');
                editBtn.type = 'button';
                editBtn.className = 'row-icon-btn edit-amount-btn';
                editBtn.title = 'Edit amount';
                editBtn.setAttribute('aria-label', 'Edit amount for ' + entry.name);
                editBtn.textContent = '\u270E';

                const deleteBtn = document.createElement('button');
                deleteBtn.type = 'button';
                deleteBtn.className = 'row-icon-btn delete-amount-btn';
                deleteBtn.title = 'Delete entry';
                deleteBtn.setAttribute('aria-label', 'Delete entry for ' + entry.name);
                deleteBtn.textContent = '\u2715';

                actions.appendChild(editBtn);
                actions.appendChild(deleteBtn);
                amountGroup.appendChild(amountSpan);
                amountGroup.appendChild(actions);
                row.appendChild(nameSpan);
                row.appendChild(amountGroup);
                listEl.appendChild(row);
            });

            if (totalEl && typeof data.total === 'number') {
                totalEl.textContent = formatCAD(data.total);
            }
        }

        function postJson(url, body) {
            return fetch(url, {
                method: 'POST',
                body: body,
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            }).then(function (response) {
                return response.json().then(function (data) {
                    return { ok: response.ok, data: data };
                });
            });
        }

        function openEditModal(id, name, amount) {
            if (!editModalEl || !window.bootstrap) return;
            editIdInput.value = id;
            editNameLabel.value = name;
            editAmountInput.value = amount;
            window.bootstrap.Modal.getOrCreateInstance(editModalEl).show();
        }

        // Event delegation: rows are (re)rendered dynamically, so bind on the container.
        listEl.addEventListener('click', function (e) {
            const row = e.target.closest('.money-owed-row');
            if (!row) return;
            const id = row.getAttribute('data-id');
            const name = row.querySelector('.league-table-team').textContent;

            if (e.target.closest('.edit-amount-btn')) {
                const amountText = row.querySelector('.league-table-points').textContent.replace(/[^\d.]/g, '');
                openEditModal(id, name, amountText);
            } else if (e.target.closest('.delete-amount-btn')) {
                const confirmed = window.confirm('Remove ' + name + ' from this list?');
                if (!confirmed) return;
                const formData = new FormData();
                formData.set('csrfmiddlewaretoken', getCsrfToken());
                postJson('/expense_tracking/money-to-pay/' + id + '/delete/', formData).then(function (result) {
                    if (result.ok && result.data.success) render(result.data);
                });
            }
        });

        if (addForm) {
            addForm.addEventListener('submit', function (e) {
                e.preventDefault();
                clearFieldErrors(addForm);
                const formData = new FormData(addForm);
                postJson('/expense_tracking/money-to-pay/add/', formData).then(function (result) {
                    if (result.ok && result.data.success) {
                        render(result.data);
                        addForm.reset();
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
                postJson('/expense_tracking/money-to-pay/' + id + '/update/', formData).then(function (result) {
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
