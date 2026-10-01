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
        const containerEl = document.getElementById('family-portfolio-accordion');
        if (!containerEl) return; // Not on the stock exchange dashboard

        // Which member ids are currently expanded, kept in sync via bootstrap collapse events
        // so a full re-render (after any add/edit/delete) doesn't collapse panels the user had open.
        const expandedMemberIds = new Set();
        containerEl.querySelectorAll('.accordion-collapse.show').forEach(function (el) {
            expandedMemberIds.add(el.id.replace('family-collapse-', ''));
        });
        containerEl.addEventListener('shown.bs.collapse', function (e) {
            expandedMemberIds.add(e.target.id.replace('family-collapse-', ''));
        });
        containerEl.addEventListener('hidden.bs.collapse', function (e) {
            expandedMemberIds.delete(e.target.id.replace('family-collapse-', ''));
        });

        const addMemberForm = document.getElementById('add-family-member-form');
        const addMemberModalEl = document.getElementById('addFamilyMemberModal');
        const addMemberNameInput = document.getElementById('family-member-add-name');

        const addHoldingForm = document.getElementById('add-family-holding-form');
        const addHoldingModalEl = document.getElementById('addFamilyHoldingModal');
        const addHoldingMemberIdInput = document.getElementById('family-add-holding-member-id');
        const addHoldingMemberNameEl = document.getElementById('family-add-holding-member-name');
        const addHoldingSymbolSelect = document.getElementById('family-holding-add-symbol');
        const addHoldingCompanyNameInput = document.getElementById('family-holding-add-company-name');

        const editHoldingForm = document.getElementById('edit-family-holding-form');
        const editHoldingModalEl = document.getElementById('editFamilyHoldingModal');
        const editHoldingIdInput = document.getElementById('edit-family-holding-id');
        const editHoldingMemberIdInput = document.getElementById('family-edit-holding-member-id');
        const editHoldingSymbolSelect = document.getElementById('family-holding-edit-symbol');
        const editHoldingCompanyNameInput = document.getElementById('family-holding-edit-company-name');
        const editHoldingQuantityInput = document.getElementById('family-holding-edit-quantity');

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
                populateSymbolSelect(addHoldingSymbolSelect, symbols);
                populateSymbolSelect(editHoldingSymbolSelect, symbols);
                return symbols;
            })
            .catch(function () {
                const fallback = '<option value="">Stock list unavailable</option>';
                if (addHoldingSymbolSelect) addHoldingSymbolSelect.innerHTML = fallback;
                if (editHoldingSymbolSelect) editHoldingSymbolSelect.innerHTML = fallback;
                return [];
            });

        function syncCompanyName(selectEl, hiddenInput) {
            if (!selectEl || !hiddenInput) return;
            selectEl.addEventListener('change', function () {
                const option = selectEl.options[selectEl.selectedIndex];
                hiddenInput.value = option ? (option.getAttribute('data-name') || '') : '';
            });
        }
        syncCompanyName(addHoldingSymbolSelect, addHoldingCompanyNameInput);
        syncCompanyName(editHoldingSymbolSelect, editHoldingCompanyNameInput);

        function buildHoldingItem(holding, memberId) {
            const item = document.createElement('div');
            item.className = 'holding-item ' + (holding.is_day_up ? 'is-up' : 'is-down');
            item.setAttribute('data-id', holding.id);
            item.setAttribute('data-member-id', memberId);
            item.setAttribute('data-symbol', holding.symbol);
            item.setAttribute('data-company-name', holding.company_name || '');
            item.setAttribute('data-quantity', holding.quantity);

            const chipClass = holding.is_day_up ? 'chip-soft-success' : 'chip-soft-danger';
            const arrow = holding.is_day_up ? '\u25b2' : '\u25bc';
            const sign = holding.is_day_up ? '+' : '';

            item.innerHTML =
                '<div class="holding-top">' +
                    '<strong></strong>' +
                    '<span class="chip ' + chipClass + '">' + arrow + ' ' + holding.day_change_percent.toFixed(2) + '%</span>' +
                    '<div class="holding-actions">' +
                        '<button type="button" class="row-icon-btn edit-amount-btn" title="Edit holding">\u270E</button>' +
                        '<button type="button" class="row-icon-btn delete-amount-btn" title="Delete holding">\u2715</button>' +
                    '</div>' +
                '</div>' +
                '<p class="holding-sub"></p>' +
                '<div class="holding-prices">' +
                    '<span>Price <strong>' + formatRs(holding.current_price) + '</strong></span>' +
                    '<span>Total <strong>' + formatRs(holding.current_value) + '</strong></span>' +
                '</div>' +
                '<div class="holding-meta">' +
                    '<span class="holding-date"></span>' +
                    '<span class="holding-profit ' + (holding.is_day_up ? 'text-up' : 'text-down') + '">' + sign + formatRs(holding.day_change) + '</span>' +
                '</div>';

            item.querySelector('.holding-top strong').textContent = holding.symbol;
            item.querySelector('.holding-sub').textContent = holding.company_name || '';
            item.querySelector('.holding-date').textContent = 'Qty ' + holding.quantity;

            return item;
        }

        function buildMemberItem(member) {
            const isExpanded = expandedMemberIds.has(String(member.id));
            const wrapper = document.createElement('div');
            wrapper.className = 'accordion-item';
            wrapper.setAttribute('data-member-id', member.id);

            const headingId = 'family-heading-' + member.id;
            const collapseId = 'family-collapse-' + member.id;
            const dayChipClass = member.is_day_up ? 'chip-soft-success' : 'chip-soft-danger';
            const dayArrow = member.is_day_up ? '\u25b2' : '\u25bc';
            const daySign = member.is_day_up ? '+' : '';

            wrapper.innerHTML =
                '<h2 class="accordion-header" id="' + headingId + '">' +
                    '<button class="accordion-button' + (isExpanded ? '' : ' collapsed') + '" type="button" data-bs-toggle="collapse" data-bs-target="#' + collapseId + '" aria-expanded="' + (isExpanded ? 'true' : 'false') + '" aria-controls="' + collapseId + '">' +
                        '<div class="family-member-summary">' +
                            '<strong></strong>' +
                            '<span class="chip ' + dayChipClass + '">' + dayArrow + ' ' + Math.abs(member.day_change_percent).toFixed(2) + '%</span>' +
                            '<span class="family-member-value"></span>' +
                        '</div>' +
                    '</button>' +
                '</h2>' +
                '<div id="' + collapseId + '" class="accordion-collapse collapse' + (isExpanded ? ' show' : '') + '" aria-labelledby="' + headingId + '" data-bs-parent="#family-portfolio-accordion">' +
                    '<div class="accordion-body">' +
                        '<div class="family-portfolio-stats">' +
                            '<div><span>Yesterday\u2019s Value</span><strong>' + formatRs(member.total_yesterday_value) + '</strong></div>' +
                            '<div><span>Today\u2019s Value</span><strong>' + formatRs(member.total_current) + '</strong></div>' +
                            '<div><span>Day Change</span><strong class="' + (member.is_day_up ? 'text-up' : 'text-down') + '">' + daySign + formatRs(member.day_change) + '</strong></div>' +
                        '</div>' +
                        '<div class="d-flex align-items-center justify-content-between mt-3 mb-2">' +
                            '<h6 class="mb-0 thisiswhite">Holdings</h6>' +
                            '<div class="d-flex align-items-center gap-2">' +
                                '<button type="button" class="btn btn-sm btn-primary family-add-holding-btn" data-member-id="' + member.id + '">+ Add Stock</button>' +
                                '<button type="button" class="row-icon-btn family-delete-member-btn" data-member-id="' + member.id + '" title="Remove member">\u2715</button>' +
                            '</div>' +
                        '</div>' +
                        '<div class="holdings-list family-holdings-list" data-member-id="' + member.id + '"></div>' +
                    '</div>' +
                '</div>';

            wrapper.querySelector('.family-member-summary strong').textContent = member.name;
            wrapper.querySelector('.family-member-value').textContent = formatRs(member.total_current);
            const addBtn = wrapper.querySelector('.family-add-holding-btn');
            addBtn.setAttribute('data-member-name', member.name);
            const deleteBtn = wrapper.querySelector('.family-delete-member-btn');
            deleteBtn.setAttribute('data-member-name', member.name);
            deleteBtn.setAttribute('aria-label', 'Remove ' + member.name);
            deleteBtn.title = 'Remove ' + member.name;

            const holdingsListEl = wrapper.querySelector('.family-holdings-list');
            const holdings = member.holdings || [];
            if (!holdings.length) {
                const empty = document.createElement('p');
                empty.className = 'text-muted stock-sub mb-0';
                empty.textContent = 'No stocks yet \u2014 add ' + member.name + "'s first holding.";
                holdingsListEl.appendChild(empty);
            } else {
                holdings.forEach(function (holding) {
                    holdingsListEl.appendChild(buildHoldingItem(holding, member.id));
                });
            }

            return wrapper;
        }

        function render(data) {
            const members = data.family_members || [];
            containerEl.innerHTML = '';
            if (!members.length) {
                const empty = document.createElement('p');
                empty.className = 'text-muted stock-sub mb-0';
                empty.id = 'family-portfolio-empty';
                empty.textContent = 'No family members yet \u2014 add one to start tracking their portfolio.';
                containerEl.appendChild(empty);
                return;
            }
            members.forEach(function (member, index) {
                if (expandedMemberIds.size === 0 && index === 0) {
                    expandedMemberIds.add(String(member.id));
                }
                containerEl.appendChild(buildMemberItem(member));
            });
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

        function openAddHoldingModal(memberId, memberName) {
            if (!addHoldingModalEl || !window.bootstrap) return;
            addHoldingForm.reset();
            clearFieldErrors(addHoldingForm);
            addHoldingMemberIdInput.value = memberId;
            addHoldingMemberNameEl.textContent = memberName || '';
            if (addHoldingSymbolSelect) addHoldingSymbolSelect.selectedIndex = 0;
            window.bootstrap.Modal.getOrCreateInstance(addHoldingModalEl).show();
        }

        function openEditHoldingModal(item) {
            if (!editHoldingModalEl || !window.bootstrap) return;
            const symbol = item.getAttribute('data-symbol');

            editHoldingIdInput.value = item.getAttribute('data-id');
            editHoldingMemberIdInput.value = item.getAttribute('data-member-id');
            editHoldingQuantityInput.value = item.getAttribute('data-quantity');
            editHoldingCompanyNameInput.value = item.getAttribute('data-company-name');

            symbolsPromise.then(function () {
                if (editHoldingSymbolSelect) editHoldingSymbolSelect.value = symbol;
            });

            window.bootstrap.Modal.getOrCreateInstance(editHoldingModalEl).show();
        }

        containerEl.addEventListener('click', function (e) {
            const addHoldingBtn = e.target.closest('.family-add-holding-btn');
            if (addHoldingBtn) {
                openAddHoldingModal(addHoldingBtn.getAttribute('data-member-id'), addHoldingBtn.getAttribute('data-member-name'));
                return;
            }

            const deleteMemberBtn = e.target.closest('.family-delete-member-btn');
            if (deleteMemberBtn) {
                const memberId = deleteMemberBtn.getAttribute('data-member-id');
                const memberName = deleteMemberBtn.getAttribute('data-member-name');
                const confirmed = window.confirm('Remove ' + memberName + ' and their entire portfolio?');
                if (!confirmed) return;
                const formData = new FormData();
                formData.set('csrfmiddlewaretoken', getCsrfToken());
                postJson('/stockex_dash/family/' + memberId + '/delete/', formData).then(function (result) {
                    if (result.ok && result.data.success) {
                        expandedMemberIds.delete(String(memberId));
                        render(result.data);
                    }
                });
                return;
            }

            const holdingItem = e.target.closest('.holding-item');
            if (holdingItem) {
                const id = holdingItem.getAttribute('data-id');
                const symbol = holdingItem.getAttribute('data-symbol');
                if (e.target.closest('.edit-amount-btn')) {
                    openEditHoldingModal(holdingItem);
                } else if (e.target.closest('.delete-amount-btn')) {
                    const confirmed = window.confirm('Remove ' + symbol + ' from this portfolio?');
                    if (!confirmed) return;
                    const formData = new FormData();
                    formData.set('csrfmiddlewaretoken', getCsrfToken());
                    postJson('/stockex_dash/family/holdings/' + id + '/delete/', formData).then(function (result) {
                        if (result.ok && result.data.success) {
                            render(result.data);
                        }
                    });
                }
            }
        });

        if (addMemberForm) {
            addMemberForm.addEventListener('submit', function (e) {
                e.preventDefault();
                clearFieldErrors(addMemberForm);
                const submittedName = (addMemberNameInput.value || '').trim();
                const formData = new FormData(addMemberForm);
                formData.set('csrfmiddlewaretoken', getCsrfToken());
                postJson('/stockex_dash/family/add/', formData).then(function (result) {
                    if (result.ok && result.data.success) {
                        const added = (result.data.family_members || []).find(function (m) { return m.name === submittedName; });
                        if (added) expandedMemberIds.add(String(added.id));
                        render(result.data);
                        addMemberForm.reset();
                        hideModal(addMemberModalEl);
                    } else {
                        showFieldErrors(addMemberForm, result.data.errors);
                    }
                });
            });
        }

        if (addHoldingForm) {
            addHoldingForm.addEventListener('submit', function (e) {
                e.preventDefault();
                clearFieldErrors(addHoldingForm);
                const formData = new FormData(addHoldingForm);
                formData.set('csrfmiddlewaretoken', getCsrfToken());
                postJson('/stockex_dash/family/holdings/add/', formData).then(function (result) {
                    if (result.ok && result.data.success) {
                        render(result.data);
                        addHoldingForm.reset();
                        if (addHoldingSymbolSelect) addHoldingSymbolSelect.selectedIndex = 0;
                        hideModal(addHoldingModalEl);
                    } else {
                        showFieldErrors(addHoldingForm, result.data.errors);
                    }
                });
            });
        }

        if (editHoldingForm) {
            editHoldingForm.addEventListener('submit', function (e) {
                e.preventDefault();
                clearFieldErrors(editHoldingForm);
                const id = editHoldingIdInput.value;
                const formData = new FormData(editHoldingForm);
                formData.set('csrfmiddlewaretoken', getCsrfToken());
                postJson('/stockex_dash/family/holdings/' + id + '/update/', formData).then(function (result) {
                    if (result.ok && result.data.success) {
                        render(result.data);
                        hideModal(editHoldingModalEl);
                    } else {
                        showFieldErrors(editHoldingForm, result.data.errors);
                    }
                });
            });
        }
    });
})();
