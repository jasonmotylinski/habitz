(function () {
    'use strict';

    const SCRIPT_ROOT = window.SCRIPT_ROOT || '';
    const DEFAULT_MINUTES = window.DEFAULT_MICRO_FAST_MINUTES || 180;
    const CIRCUMFERENCE = 2 * Math.PI * 90; // matches SVG r=90

    let activeFast = null;
    let uiTick = null;
    let selectedLabel = null;
    let selectedMinutes = DEFAULT_MINUTES;
    let editingMF = null;

    // ── Format helpers ────────────────────────────────────────────────────────

    function fmtElapsed(seconds) {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = Math.floor(seconds % 60);
        if (h > 0) {
            return h + ':' + String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
        }
        return String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
    }

    function fmtMinutes(minutes) {
        const h = Math.floor(minutes / 60);
        const m = minutes % 60;
        if (h > 0 && m > 0) return h + 'h ' + m + 'm';
        if (h > 0) return h + 'h';
        return m + 'm';
    }

    function fmtDuration(seconds) {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        if (h > 0 && m > 0) return h + 'h ' + m + 'm';
        if (h > 0) return h + 'h';
        return m + 'm';
    }

    function fmtLabel(label) {
        return label ? label.replace(/-/g, ' → ') : '';
    }

    function toLocalDatetimeValue(isoStr) {
        const d = new Date(isoStr);
        return new Date(d.getTime() - d.getTimezoneOffset() * 60000)
            .toISOString().slice(0, 16);
    }

    // ── Ring ──────────────────────────────────────────────────────────────────

    function updateRing(progress) {
        const offset = CIRCUMFERENCE * (1 - Math.min(1, progress));
        document.getElementById('micro-progress-ring').style.strokeDashoffset = offset;
    }

    // ── Timer tick (every second) ─────────────────────────────────────────────

    function tickTimer() {
        if (!activeFast) return;
        const elapsed = (Date.now() - new Date(activeFast.started_at).getTime()) / 1000;
        const target = activeFast.target_minutes * 60;
        const progress = elapsed / target;
        const pct = Math.round(Math.min(100, progress * 100));

        document.getElementById('micro-elapsed').textContent = fmtElapsed(elapsed);
        document.getElementById('micro-pct').textContent = pct + '%';
        updateRing(progress);

        const ring = document.getElementById('micro-progress-ring');
        const pctEl = document.getElementById('micro-pct');
        if (elapsed >= target) {
            ring.classList.add('completed');
            pctEl.classList.add('completed');
        } else {
            ring.classList.remove('completed');
            pctEl.classList.remove('completed');
        }
    }

    // ── Show/hide states ──────────────────────────────────────────────────────

    function showActive(mf) {
        activeFast = mf;

        document.getElementById('micro-idle-ring').classList.add('hidden');
        document.getElementById('micro-active-ring').classList.remove('hidden');
        document.getElementById('micro-active-meta').classList.remove('hidden');
        document.getElementById('micro-stop-btn').classList.remove('hidden');
        document.getElementById('micro-windows-section').classList.add('hidden');
        document.getElementById('micro-targets-section').classList.add('hidden');

        document.getElementById('micro-active-label').textContent = fmtLabel(mf.label) || '—';
        document.getElementById('micro-of').textContent = 'of ' + fmtMinutes(mf.target_minutes);

        const endAt = new Date(new Date(mf.started_at).getTime() + mf.target_minutes * 60000);
        document.getElementById('micro-end-time').textContent =
            endAt.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });

        tickTimer();
        if (!uiTick) {
            uiTick = setInterval(tickTimer, 1000);
        }
    }

    function showIdle() {
        activeFast = null;
        if (uiTick) { clearInterval(uiTick); uiTick = null; }

        document.getElementById('micro-active-ring').classList.add('hidden');
        document.getElementById('micro-idle-ring').classList.remove('hidden');
        document.getElementById('micro-active-meta').classList.add('hidden');
        document.getElementById('micro-stop-btn').classList.add('hidden');
        document.getElementById('micro-windows-section').classList.remove('hidden');
        document.getElementById('micro-targets-section').classList.remove('hidden');

        updateRing(0);
        document.getElementById('micro-progress-ring').classList.remove('completed');
        document.getElementById('micro-pct').classList.remove('completed');
    }

    // ── Today's log ───────────────────────────────────────────────────────────

    var editSVG = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>';
    var trashSVG = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>';

    function renderLog(records) {
        var logEl = document.getElementById('micro-log');
        var listEl = document.getElementById('micro-today-list');
        var done = records.filter(function (mf) { return mf.ended_at !== undefined; });

        if (!done.length) {
            logEl.classList.add('hidden');
            return;
        }

        logEl.classList.remove('hidden');
        listEl.innerHTML = '';

        done.forEach(function (mf) {
            var item = document.createElement('div');
            item.className = 'micro-log-item';
            item.dataset.id = mf.id;

            var label = fmtLabel(mf.label) || 'Unlabeled';
            var dur = fmtDuration(mf.duration_seconds || 0);
            var dotClass = mf.completed ? 'micro-log-dot completed' : 'micro-log-dot';

            item.innerHTML =
                '<div class="' + dotClass + '"></div>' +
                '<span class="micro-log-label">' + label + '</span>' +
                '<span class="micro-log-meta">' + dur + '</span>' +
                '<div class="history-actions">' +
                    '<button class="history-edit" title="Edit">' + editSVG + '</button>' +
                    '<button class="history-delete" title="Delete">' + trashSVG + '</button>' +
                '</div>';

            item.querySelector('.history-edit').addEventListener('click', function () {
                openEditModal(mf);
            });
            item.querySelector('.history-delete').addEventListener('click', function () {
                deleteMicroFast(mf.id, item);
            });

            listEl.appendChild(item);
        });
    }

    // ── Edit modal ────────────────────────────────────────────────────────────

    function openEditModal(mf) {
        editingMF = mf;

        var startValue = toLocalDatetimeValue(mf.started_at);
        var endValue = mf.ended_at ? toLocalDatetimeValue(mf.ended_at) : '';

        var labelOptions = [
            ['', 'No label'],
            ['breakfast-lunch', 'Breakfast → Lunch'],
            ['lunch-dinner', 'Lunch → Dinner'],
            ['dinner-bedtime', 'Dinner → Bedtime'],
        ].map(function (opt) {
            var sel = opt[0] === (mf.label || '') ? ' selected' : '';
            return '<option value="' + opt[0] + '"' + sel + '>' + opt[1] + '</option>';
        }).join('');

        var modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.id = 'edit-micro-modal';
        modal.innerHTML =
            '<div class="modal-content">' +
                '<div class="modal-header">' +
                    '<h2>Edit Micro Fast</h2>' +
                    '<button class="modal-close" aria-label="Close">&times;</button>' +
                '</div>' +
                '<form id="edit-micro-form">' +
                    '<div class="form-group">' +
                        '<label for="em-started">Started</label>' +
                        '<input type="datetime-local" id="em-started" value="' + startValue + '" required />' +
                    '</div>' +
                    '<div class="form-group">' +
                        '<label for="em-ended">Ended</label>' +
                        '<input type="datetime-local" id="em-ended" value="' + endValue + '" />' +
                    '</div>' +
                    '<div class="form-group">' +
                        '<label for="em-target">Target (minutes)</label>' +
                        '<input type="number" id="em-target" value="' + mf.target_minutes + '" min="30" max="360" />' +
                    '</div>' +
                    '<div class="form-group">' +
                        '<label for="em-label">Meal gap</label>' +
                        '<select id="em-label">' + labelOptions + '</select>' +
                    '</div>' +
                    '<div class="form-group">' +
                        '<label><input type="checkbox" id="em-completed"' + (mf.completed ? ' checked' : '') + ' /> Mark as completed</label>' +
                    '</div>' +
                    '<div class="modal-actions">' +
                        '<button type="button" class="btn btn--ghost" id="em-cancel">Cancel</button>' +
                        '<button type="submit" class="btn btn--primary">Save</button>' +
                    '</div>' +
                '</form>' +
            '</div>';

        document.body.appendChild(modal);
        modal.querySelector('.modal-close').addEventListener('click', closeEditModal);
        modal.querySelector('#em-cancel').addEventListener('click', closeEditModal);
        modal.querySelector('#edit-micro-form').addEventListener('submit', saveEditMicro);
        modal.addEventListener('click', function (e) {
            if (e.target === modal) closeEditModal();
        });
    }

    function closeEditModal() {
        var modal = document.getElementById('edit-micro-modal');
        if (modal) {
            modal.style.opacity = '0';
            modal.style.transition = 'opacity 0.2s';
            setTimeout(function () { modal.remove(); }, 200);
        }
        editingMF = null;
    }

    function saveEditMicro(e) {
        e.preventDefault();
        if (!editingMF) return;

        var startDate = new Date(document.getElementById('em-started').value);
        var endVal = document.getElementById('em-ended').value;
        var endDate = endVal ? new Date(endVal) : null;

        if (isNaN(startDate.getTime())) { alert('Invalid start date/time'); return; }

        var payload = {
            started_at: startDate.toISOString(),
            target_minutes: parseInt(document.getElementById('em-target').value, 10),
            label: document.getElementById('em-label').value || null,
            completed: document.getElementById('em-completed').checked,
        };
        if (endDate && !isNaN(endDate.getTime())) {
            payload.ended_at = endDate.toISOString();
        }

        fetch(SCRIPT_ROOT + '/api/micro/' + editingMF.id, {
            method: 'PATCH',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        })
        .then(function (r) { return r.json(); })
        .then(function (result) {
            if (result.error) { alert(result.error); return; }
            closeEditModal();
            fetchToday();
        });
    }

    function deleteMicroFast(id, item) {
        if (!confirm('Delete this micro fast? This cannot be undone.')) return;
        fetch(SCRIPT_ROOT + '/api/micro/' + id, {
            method: 'DELETE',
            credentials: 'same-origin',
        })
        .then(function (r) { return r.json(); })
        .then(function (result) {
            if (result.error) { alert(result.error); return; }
            item.style.opacity = '0';
            item.style.transform = 'translateX(20px)';
            item.style.transition = 'all 0.25s';
            setTimeout(function () {
                item.remove();
                // hide log section if now empty
                var list = document.getElementById('micro-today-list');
                if (!list.children.length) {
                    document.getElementById('micro-log').classList.add('hidden');
                }
            }, 250);
        });
    }

    // ── API ───────────────────────────────────────────────────────────────────

    function fetchActive() {
        return fetch(SCRIPT_ROOT + '/api/micro/active', { credentials: 'same-origin' })
            .then(function (r) { return r.json(); })
            .then(function (mf) {
                if (mf) {
                    if (!activeFast || activeFast.id !== mf.id) {
                        showActive(mf);
                    } else {
                        activeFast = mf;
                    }
                } else if (activeFast) {
                    showIdle();
                    fetchToday();
                }
            });
    }

    function fetchToday() {
        return fetch(SCRIPT_ROOT + '/api/micro/today', { credentials: 'same-origin' })
            .then(function (r) { return r.json(); })
            .then(renderLog);
    }

    // ── Preset interactions ───────────────────────────────────────────────────

    document.querySelectorAll('.micro-window').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var isActive = btn.classList.contains('active');
            document.querySelectorAll('.micro-window').forEach(function (b) {
                b.classList.remove('active');
            });
            if (!isActive) {
                btn.classList.add('active');
                selectedLabel = btn.dataset.label;
            } else {
                selectedLabel = null;
            }
        });
    });

    var customInput = document.getElementById('micro-custom-input');

    document.querySelectorAll('.micro-target-btn').forEach(function (btn) {
        if (btn.dataset.minutes !== 'custom' &&
                parseInt(btn.dataset.minutes, 10) === DEFAULT_MINUTES) {
            btn.classList.add('active');
        }
        btn.addEventListener('click', function () {
            document.querySelectorAll('.micro-target-btn').forEach(function (b) {
                b.classList.remove('active');
            });
            btn.classList.add('active');
            if (btn.dataset.minutes === 'custom') {
                customInput.classList.remove('hidden');
                customInput.focus();
                selectedMinutes = parseInt(customInput.value, 10) || DEFAULT_MINUTES;
            } else {
                customInput.classList.add('hidden');
                selectedMinutes = parseInt(btn.dataset.minutes, 10);
            }
        });
    });

    customInput.addEventListener('input', function () {
        selectedMinutes = parseInt(this.value, 10) || DEFAULT_MINUTES;
    });

    // ── Start / Stop ──────────────────────────────────────────────────────────

    document.getElementById('micro-start-btn').addEventListener('click', function () {
        fetch(SCRIPT_ROOT + '/api/micro/start', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                label: selectedLabel || null,
                target_minutes: selectedMinutes || DEFAULT_MINUTES,
            }),
        })
        .then(function (r) { return r.json(); })
        .then(function (mf) {
            if (mf.error) { alert(mf.error); return; }
            showActive(mf);
        });
    });

    document.getElementById('micro-stop-btn').addEventListener('click', function () {
        if (!confirm('End your micro fast?')) return;
        fetch(SCRIPT_ROOT + '/api/micro/stop', {
            method: 'POST',
            credentials: 'same-origin',
        })
        .then(function (r) { return r.json(); })
        .then(function (mf) {
            if (mf.error) { alert(mf.error); return; }
            showIdle();
            fetchToday();
        });
    });

    // ── Init ──────────────────────────────────────────────────────────────────

    fetchActive();
    fetchToday();
    setInterval(fetchActive, 5000);
}());
