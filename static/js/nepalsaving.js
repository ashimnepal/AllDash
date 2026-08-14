(function () {
    function formatNPR(amount) {
        const rounded = Math.round(amount * 100) / 100;
        return 'NPR ' + rounded.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
    }

    function formatDate(dateStr) {
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return dateStr;
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
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

    function showModal(modalEl) {
        if (!modalEl) return;
        if (window.bootstrap && window.bootstrap.Modal) {
            window.bootstrap.Modal.getOrCreateInstance(modalEl).show();
            return;
        }
        modalEl.classList.add('show');
        modalEl.style.display = 'block';
        modalEl.removeAttribute('aria-hidden');
        modalEl.setAttribute('aria-modal', 'true');
        modalEl.setAttribute('role', 'dialog');
        document.body.classList.add('modal-open');
        if (!document.querySelector('[data-nepal-modal-backdrop]')) {
            const backdrop = document.createElement('div');
            backdrop.className = 'modal-backdrop fade show';
            backdrop.setAttribute('data-nepal-modal-backdrop', 'true');
            document.body.appendChild(backdrop);
        }
    }

    function hideModal(modalEl) {
        if (!modalEl) return;
        if (window.bootstrap && window.bootstrap.Modal) {
            const instance = window.bootstrap.Modal.getOrCreateInstance(modalEl);
            instance.hide();
            return;
        }
        modalEl.classList.remove('show');
        modalEl.style.display = 'none';
        modalEl.setAttribute('aria-hidden', 'true');
        modalEl.removeAttribute('aria-modal');
        document.body.classList.remove('modal-open');
        const backdrop = document.querySelector('[data-nepal-modal-backdrop]');
        if (backdrop) backdrop.remove();
    }

    function render(data) {
        const totalEl = document.getElementById('nepal-total-amount');
        if (totalEl && typeof data.total === 'number') {
            totalEl.textContent = formatNPR(data.total);
            totalEl.classList.toggle('is-negative', data.total < 0);
        }

        const countEl = document.getElementById('nepal-transaction-count');
        if (countEl) {
            const count = (data.transactions || []).length;
            countEl.textContent = count + (count === 1 ? ' entry' : ' entries');
        }

        const listEl = document.getElementById('nepal-transaction-list');
        const emptyEl = document.getElementById('nepal-empty-state');
        if (!listEl) return;

        listEl.innerHTML = '';

        if (!(data.transactions || []).length) {
            if (emptyEl) emptyEl.classList.remove('d-none');
            return;
        }
        if (emptyEl) emptyEl.classList.add('d-none');

        data.transactions.forEach(function (tx) {
            const row = document.createElement('tr');
            row.setAttribute('data-id', tx.id);

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

            const actionsCell = document.createElement('td');
            const actionsWrap = document.createElement('div');
            actionsWrap.className = 'd-flex gap-2';

            const editBtn = document.createElement('button');
            editBtn.type = 'button';
            editBtn.className = 'row-icon-btn edit-nepal-btn';
            editBtn.setAttribute('aria-label', 'Edit transaction');
            editBtn.textContent = '\u270E';

            const deleteBtn = document.createElement('button');
            deleteBtn.type = 'button';
            deleteBtn.className = 'row-icon-btn delete-nepal-btn';
            deleteBtn.setAttribute('aria-label', 'Delete transaction');
            deleteBtn.textContent = '\u2715';

            actionsWrap.appendChild(editBtn);
            actionsWrap.appendChild(deleteBtn);
            actionsCell.appendChild(actionsWrap);

            row.appendChild(typeCell);
            row.appendChild(noteCell);
            row.appendChild(amountCell);
            row.appendChild(dateCell);
            row.appendChild(actionsCell);
            listEl.appendChild(row);
        });
    }

    function postJson(url, body) {
        return fetch(url, {
            method: 'POST',
            body: body,
            credentials: 'same-origin',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCsrfToken(),
            },
        }).then(function (response) {
            return response.json().then(function (data) {
                return { ok: response.ok, data: data };
            });
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        const totalEl = document.getElementById('nepal-total-amount');
        if (!totalEl) return; // Not on the Nepal Savings page
        const listEl = document.getElementById('nepal-transaction-list');
        if (!listEl) return;

        const initialRows = Array.from(listEl.querySelectorAll('tr')).map(function (row) {
            const cells = row.querySelectorAll('td');
            const typeText = cells[0].textContent.trim();
            const amountText = cells[2].textContent.replace(/[^\d.]/g, '');
            return {
                id: row.getAttribute('data-id'),
                type: typeText === 'Savings Added' ? 'added' : 'used',
                amount: parseFloat(amountText) || 0,
                note: cells[1] ? cells[1].textContent.trim() : '',
                date: cells[3] ? cells[3].textContent.trim() : '',
            };
        });
        const totalText = totalEl.textContent.replace(/[^\d.-]/g, '');
        render({ transactions: initialRows, total: parseFloat(totalText) || 0 });

        const addForm = document.getElementById('add-savings-form');
        const addModalEl = document.getElementById('addSavingsModal');
        const editModalEl = document.getElementById('editNepalSavingsModal');
        const editForm = document.getElementById('edit-nepal-form');
        const editIdInput = document.getElementById('edit-nepal-id');
        const editAmountInput = document.getElementById('edit-nepal-amount');
        const editNoteInput = document.getElementById('edit-nepal-note');

        function openEditModal(tx) {
            if (!editModalEl || !editForm || !editIdInput) return;
            const txId = tx && (tx.id ?? tx.pk ?? tx.transaction_id ?? tx.record_id);
            if (txId === undefined || txId === null || txId === '') {
                console.warn('Nepal savings edit modal opened without a valid transaction id.', tx);
                return;
            }
            editForm.dataset.transactionId = String(txId);
            editIdInput.value = String(txId);
            editAmountInput.value = tx.amount ?? '';
            editNoteInput.value = tx.note || '';
            showModal(editModalEl);
        }

        function deleteTransaction(id) {
            const txId = String(id ?? '').trim();
            if (!txId) {
                console.warn('Nepal savings delete attempted without a valid transaction id.', id);
                return;
            }
            const confirmed = window.confirm('Delete this Nepal savings entry?');
            if (!confirmed) return;
            const formData = new FormData();
            formData.set('csrfmiddlewaretoken', getCsrfToken());
            postJson('/expense_tracking/nepal-savings/' + txId + '/delete/', formData).then(function (result) {
                if (result.ok && result.data.success) {
                    render(result.data);
                }
            });
        }

        window.NepalSavingsUI = {
            openEdit: function (id, amount, note) {
                openEditModal({ id: id, amount: amount, note: note });
            },
            deleteEntry: function (id) {
                deleteTransaction(id);
            }
        };

        function getTransactionFromRow(row) {
            const cells = row.querySelectorAll('td');
            return {
                id: row.getAttribute('data-id'),
                type: cells[0].textContent.trim() === 'Savings Added' ? 'added' : 'used',
                amount: parseFloat(cells[2].textContent.replace(/[^\d.]/g, '')) || 0,
                note: cells[1] ? cells[1].textContent.trim() : '',
                date: cells[3] ? cells[3].textContent.trim() : '',
            };
        }

        listEl.addEventListener('click', function (e) {
            const row = e.target.closest('tr[data-id]');
            if (!row) return;

            if (e.target.closest('.edit-nepal-btn')) {
                openEditModal(getTransactionFromRow(row));
            } else if (e.target.closest('.delete-nepal-btn')) {
                deleteTransaction(row.getAttribute('data-id'));
            }
        });

        if (editForm) {
            editForm.addEventListener('submit', function (e) {
                e.preventDefault();
                clearFieldErrors(editForm);
                const id = String(editForm.dataset.transactionId || editIdInput.value || '').trim();
                if (!id) {
                    console.warn('Nepal savings update attempted without a valid transaction id.');
                    return;
                }
                editForm.dataset.transactionId = id;
                editIdInput.value = id;
                const formData = new FormData(editForm);
                formData.set('transaction_id', id);
                formData.set('csrfmiddlewaretoken', getCsrfToken());
                postJson('/expense_tracking/nepal-savings/' + id + '/update/', formData).then(function (result) {
                    if (result.ok && result.data.success) {
                        render(result.data);
                        hideModal(editModalEl);
                    } else {
                        showFieldErrors(editForm, result.data.errors);
                    }
                });
            });
        }

        if (addForm) {
            addForm.addEventListener('submit', function (e) {
                e.preventDefault();
                clearFieldErrors(addForm);
                const formData = new FormData(addForm);
                formData.set('csrfmiddlewaretoken', getCsrfToken());
                postJson('/expense_tracking/nepal-savings/add/', formData).then(function (result) {
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

        const useForm = document.getElementById('use-money-form');
        const useModalEl = document.getElementById('useMoneyModal');
        if (useForm) {
            useForm.addEventListener('submit', function (e) {
                e.preventDefault();
                clearFieldErrors(useForm);
                const formData = new FormData(useForm);
                formData.set('csrfmiddlewaretoken', getCsrfToken());
                postJson('/expense_tracking/nepal-savings/use/', formData).then(function (result) {
                    if (result.ok && result.data.success) {
                        render(result.data);
                        useForm.reset();
                        hideModal(useModalEl);
                    } else {
                        showFieldErrors(useForm, result.data.errors);
                    }
                });
            });
        }
    });
})();
