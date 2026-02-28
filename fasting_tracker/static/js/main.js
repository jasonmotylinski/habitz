/* ========================================
   FASTING TRACKER — Main JS
   ======================================== */

document.addEventListener('DOMContentLoaded', () => {
    // Dashboard timer
    initDashboard();

    // History page
    initHistory();
});

/* ---- Dashboard ---- */

const CIRCUMFERENCE = 2 * Math.PI * 90; // matches SVG r=90

let timerInterval = null;
let activeFast = null;
let selectedHours = 16;

function initDashboard() {
    const section = document.getElementById('timer-section');
    if (!section) return;

    // Preset buttons
    document.querySelectorAll('.preset').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.preset').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedHours = parseInt(btn.dataset.hours);
            document.getElementById('custom-hours-input').value = '';
        });
    });

    // Custom hours input
    document.getElementById('custom-hours-input').addEventListener('input', (e) => {
        const val = parseInt(e.target.value);
        if (val >= 1 && val <= 72) {
            document.querySelectorAll('.preset').forEach(b => b.classList.remove('active'));
            selectedHours = val;
        }
    });

    // Start button
    document.getElementById('start-btn').addEventListener('click', startFast);

    // Stop button
    document.getElementById('stop-btn').addEventListener('click', stopFast);

    // Edit start time
    document.getElementById('edit-start-btn').addEventListener('click', openStartEdit);
    document.getElementById('cancel-start-btn').addEventListener('click', closeStartEdit);
    document.getElementById('save-start-btn').addEventListener('click', saveStartTime);

    // Check for active fast
    fetchActiveFast();

    // Load weekly stats
    fetchWeeklyStats();
}

async function fetchActiveFast() {
    try {
        const res = await fetch(window.SCRIPT_ROOT + '/api/fast/active');
        const data = await res.json();
        if (data && data.id) {
            activeFast = data;
            showActiveState();
            startTimer();
        }
    } catch (e) {
        console.error('Failed to fetch active fast:', e);
    }
}

async function startFast() {
    try {
        const res = await fetch(window.SCRIPT_ROOT + '/api/fast/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target_hours: selectedHours }),
        });
        if (!res.ok) {
            const err = await res.json();
            alert(err.error || 'Failed to start fast');
            return;
        }
        activeFast = await res.json();
        showActiveState();
        startTimer();
    } catch (e) {
        console.error('Failed to start fast:', e);
    }
}

async function stopFast() {
    if (!confirm('End your current fast?')) return;

    try {
        const res = await fetch(window.SCRIPT_ROOT + '/api/fast/stop', { method: 'POST' });
        if (!res.ok) {
            const err = await res.json();
            alert(err.error || 'Failed to stop fast');
            return;
        }
        clearInterval(timerInterval);
        activeFast = null;
        showIdleState();
        fetchWeeklyStats();
    } catch (e) {
        console.error('Failed to stop fast:', e);
    }
}

function openStartEdit() {
    const d = new Date(activeFast.started_at);
    // Convert UTC to local datetime-local string (YYYY-MM-DDTHH:MM)
    const local = new Date(d.getTime() - d.getTimezoneOffset() * 60000);
    document.getElementById('start-time-input').value = local.toISOString().slice(0, 16);
    document.getElementById('timer-start-row').classList.add('hidden');
    document.getElementById('timer-start-edit').classList.remove('hidden');
}

function closeStartEdit() {
    document.getElementById('timer-start-edit').classList.add('hidden');
    document.getElementById('timer-start-row').classList.remove('hidden');
}

async function saveStartTime() {
    const input = document.getElementById('start-time-input');
    const localDate = new Date(input.value);
    if (isNaN(localDate.getTime())) {
        alert('Invalid date/time');
        return;
    }

    try {
        const res = await fetch(window.SCRIPT_ROOT + '/api/fast/active', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ started_at: localDate.toISOString() }),
        });
        if (!res.ok) {
            const err = await res.json();
            alert(err.error || 'Failed to update start time');
            return;
        }
        activeFast = await res.json();
        closeStartEdit();
        showActiveState();
    } catch (e) {
        console.error('Failed to update start time:', e);
    }
}

function showActiveState() {
    document.getElementById('timer-idle').classList.add('hidden');
    document.getElementById('timer-active').classList.remove('hidden');
    document.getElementById('stop-btn').classList.remove('hidden');
    document.getElementById('timer-times').classList.remove('hidden');
    document.getElementById('presets').classList.add('hidden');
    document.getElementById('timer-target').textContent = `of ${activeFast.target_hours}h`;

    const startedAt = new Date(activeFast.started_at);
    const endAt = new Date(startedAt.getTime() + activeFast.target_hours * 3600 * 1000);
    const timeOpts = { hour: 'numeric', minute: '2-digit' };
    document.getElementById('timer-start-time').textContent = startedAt.toLocaleTimeString([], timeOpts);
    document.getElementById('timer-end-time').textContent = endAt.toLocaleTimeString([], timeOpts);
}

function showIdleState() {
    document.getElementById('timer-idle').classList.remove('hidden');
    document.getElementById('timer-active').classList.add('hidden');
    document.getElementById('stop-btn').classList.add('hidden');
    document.getElementById('timer-times').classList.add('hidden');
    document.getElementById('presets').classList.remove('hidden');
    updateRing(0);
    document.getElementById('progress-ring').classList.remove('completed');
    document.getElementById('timer-pct').classList.remove('completed');
}

function startTimer() {
    if (timerInterval) clearInterval(timerInterval);
    updateTimerDisplay();
    timerInterval = setInterval(updateTimerDisplay, 1000);
}

function updateTimerDisplay() {
    if (!activeFast) return;

    const startedAt = new Date(activeFast.started_at).getTime();
    const now = Date.now();
    const elapsed = Math.floor((now - startedAt) / 1000);
    const target = activeFast.target_hours * 3600;
    const progress = Math.min(1, elapsed / target);
    const pct = Math.round((elapsed / target) * 100);

    // Update time display
    document.getElementById('timer-elapsed').textContent = formatDuration(elapsed);
    document.getElementById('timer-pct').textContent = `${pct}%`;

    // Update ring
    updateRing(progress);

    // Completed state
    const ring = document.getElementById('progress-ring');
    const pctEl = document.getElementById('timer-pct');
    if (elapsed >= target) {
        ring.classList.add('completed');
        pctEl.classList.add('completed');
    } else {
        ring.classList.remove('completed');
        pctEl.classList.remove('completed');
    }
}

function updateRing(progress) {
    const offset = CIRCUMFERENCE * (1 - progress);
    document.getElementById('progress-ring').style.strokeDashoffset = offset;
}

function formatDuration(totalSeconds) {
    const h = Math.floor(totalSeconds / 3600);
    const m = Math.floor((totalSeconds % 3600) / 60);
    const s = totalSeconds % 60;
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

const DAILY_RING_R = 22;
const DAILY_CIRCUMFERENCE = 2 * Math.PI * DAILY_RING_R;

async function fetchWeeklyStats() {
    try {
        const res = await fetch(window.SCRIPT_ROOT + '/api/stats/weekly');
        const data = await res.json();
        renderDailyRings(data.days);
    } catch (e) {
        console.error('Failed to fetch weekly stats:', e);
    }
}

function renderDailyRings(days) {
    const container = document.getElementById('daily-rings');
    if (!container) return;

    const today = new Date().toISOString().split('T')[0];
    container.innerHTML = '';

    days.forEach(day => {
        const isToday = day.date === today;
        const hasData = day.hours > 0;
        const offset = hasData
            ? DAILY_CIRCUMFERENCE * (1 - day.progress)
            : DAILY_CIRCUMFERENCE;
        const exceededClass = day.exceeded ? ' exceeded' : '';
        const hoursDisplay = hasData ? `${day.hours}h` : '·';

        const wrap = document.createElement('div');
        wrap.className = `daily-ring-wrap${isToday ? ' today' : ''}`;
        wrap.innerHTML = `
            <svg class="daily-ring-svg" viewBox="0 0 60 60">
                <circle class="daily-ring-bg" cx="30" cy="30" r="${DAILY_RING_R}" />
                <circle class="daily-ring-progress${exceededClass}"
                    cx="30" cy="30" r="${DAILY_RING_R}"
                    stroke-dasharray="${DAILY_CIRCUMFERENCE.toFixed(2)}"
                    stroke-dashoffset="${offset.toFixed(2)}" />
            </svg>
            <span class="daily-ring-label">${day.label}</span>
            <span class="daily-ring-hours">${hoursDisplay}</span>
        `;
        container.appendChild(wrap);
    });
}

/* ---- History ---- */

let historyPage = 1;
let historyTotalPages = 1;

// Calendar state
let calendarYear = null;
let calendarMonth = null;

const MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June',
                     'July', 'August', 'September', 'October', 'November', 'December'];

function initHistory() {
    const list = document.getElementById('history-list');
    if (!list) return;

    const loadMoreBtn = document.getElementById('load-more-btn');
    if (loadMoreBtn) {
        loadMoreBtn.addEventListener('click', () => {
            historyPage++;
            fetchHistory(true);
        });
    }

    // Initialize calendar + list for current month
    const now = new Date();
    calendarYear = now.getFullYear();
    calendarMonth = now.getMonth() + 1;
    fetchMonthlyStats(calendarYear, calendarMonth);
    fetchHistory();

    // Calendar nav
    document.getElementById('cal-prev').addEventListener('click', () => {
        calendarMonth--;
        if (calendarMonth < 1) {
            calendarMonth = 12;
            calendarYear--;
        }
        fetchMonthlyStats(calendarYear, calendarMonth);
        resetHistory();
        updateCalNavButtons();
    });

    document.getElementById('cal-next').addEventListener('click', () => {
        calendarMonth++;
        if (calendarMonth > 12) {
            calendarMonth = 1;
            calendarYear++;
        }
        fetchMonthlyStats(calendarYear, calendarMonth);
        resetHistory();
        updateCalNavButtons();
    });
}

function resetHistory() {
    historyPage = 1;
    historyTotalPages = 1;
    const list = document.getElementById('history-list');
    list.innerHTML = '';
    document.getElementById('history-empty').classList.add('hidden');
    document.getElementById('history-pagination').classList.add('hidden');
    fetchHistory();
}

function updateCalNavButtons() {
    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth() + 1;
    const nextBtn = document.getElementById('cal-next');
    const atCurrent = calendarYear === currentYear && calendarMonth === currentMonth;
    nextBtn.disabled = atCurrent;
}

async function fetchMonthlyStats(year, month) {
    const monthStr = `${year}-${String(month).padStart(2, '0')}`;
    try {
        const res = await fetch(window.SCRIPT_ROOT + `/api/stats/monthly?month=${monthStr}`);
        const data = await res.json();
        renderCalendar(data);
        updateCalNavButtons();
    } catch (e) {
        console.error('Failed to fetch monthly stats:', e);
    }
}

function renderCalendar(data) {
    const grid = document.getElementById('cal-grid');
    const label = document.getElementById('cal-month-label');
    if (!grid || !label) return;

    label.textContent = `${MONTH_NAMES[data.month - 1]} ${data.year}`;
    grid.innerHTML = '';

    const today = new Date().toISOString().split('T')[0];

    // Offset: first day weekday (0=Mon). Add empty cells.
    const firstWeekday = data.days[0].weekday;
    for (let i = 0; i < firstWeekday; i++) {
        const empty = document.createElement('div');
        empty.className = 'cal-day cal-day--empty';
        grid.appendChild(empty);
    }

    data.days.forEach(day => {
        const isToday = day.date === today;
        const hasData = day.hours > 0;
        const offset = hasData
            ? DAILY_CIRCUMFERENCE * (1 - day.progress)
            : DAILY_CIRCUMFERENCE;
        const exceededClass = day.exceeded ? ' exceeded' : '';

        const cell = document.createElement('div');
        cell.className = `cal-day${isToday ? ' cal-day--today' : ''}`;

        cell.innerHTML = `
            <svg class="daily-ring-svg" viewBox="0 0 60 60">
                <circle class="daily-ring-bg" cx="30" cy="30" r="${DAILY_RING_R}" />
                <circle class="daily-ring-progress${exceededClass}"
                    cx="30" cy="30" r="${DAILY_RING_R}"
                    stroke-dasharray="${DAILY_CIRCUMFERENCE.toFixed(2)}"
                    stroke-dashoffset="${offset.toFixed(2)}" />
                <text class="cal-day-num" x="30" y="30"
                    transform="rotate(90, 30, 30)"
                    text-anchor="middle" dominant-baseline="central">${day.day}</text>
            </svg>
        `;
        grid.appendChild(cell);
    });
}

async function fetchHistory(append = false) {
    const loading = document.getElementById('history-loading');
    const emptyState = document.getElementById('history-empty');
    const pagination = document.getElementById('history-pagination');

    if (!append && loading) loading.classList.remove('hidden');

    try {
        const monthStr = `${calendarYear}-${String(calendarMonth).padStart(2, '0')}`;
        const res = await fetch(window.SCRIPT_ROOT + `/api/fast/history?page=${historyPage}&month=${monthStr}`);
        const data = await res.json();

        if (loading) loading.classList.add('hidden');

        historyTotalPages = data.total_pages;

        if (data.fasts.length === 0 && !append) {
            emptyState.classList.remove('hidden');
            return;
        }

        const list = document.getElementById('history-list');
        data.fasts.forEach(fast => {
            list.appendChild(createHistoryCard(fast));
        });

        if (historyPage < historyTotalPages) {
            pagination.classList.remove('hidden');
        } else {
            pagination.classList.add('hidden');
        }
    } catch (e) {
        console.error('Failed to fetch history:', e);
        if (loading) loading.classList.add('hidden');
    }
}

function createHistoryCard(fast) {
    const card = document.createElement('div');
    card.className = 'history-card';
    card.dataset.id = fast.id;

    const date = new Date(fast.started_at);
    const dateStr = date.toLocaleDateString('en-US', {
        weekday: 'short', month: 'short', day: 'numeric'
    });
    const timeStr = date.toLocaleTimeString('en-US', {
        hour: 'numeric', minute: '2-digit'
    });

    const hours = Math.floor(fast.duration_seconds / 3600);
    const minutes = Math.floor((fast.duration_seconds % 3600) / 60);
    const durationStr = hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;

    const checkIcon = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>`;
    const xIcon = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`;

    card.innerHTML = `
        <div class="history-status ${fast.completed ? 'success' : 'incomplete'}">
            ${fast.completed ? checkIcon : xIcon}
        </div>
        <div class="history-details">
            <div class="history-date">${dateStr} at ${timeStr}</div>
            <div class="history-meta">${durationStr} / ${fast.target_hours}h target</div>
        </div>
        <button class="history-delete" title="Delete" data-id="${fast.id}">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
        </button>
    `;

    card.querySelector('.history-delete').addEventListener('click', () => deleteFast(fast.id, card));

    return card;
}

async function deleteFast(id, card) {
    if (!confirm('Delete this fast? This cannot be undone.')) return;

    try {
        const res = await fetch(window.SCRIPT_ROOT + `/api/fast/${id}`, { method: 'DELETE' });
        if (res.ok) {
            card.style.opacity = '0';
            card.style.transform = 'translateX(20px)';
            card.style.transition = 'all 0.3s';
            setTimeout(() => card.remove(), 300);
        } else {
            const err = await res.json();
            alert(err.error || 'Failed to delete');
        }
    } catch (e) {
        console.error('Failed to delete fast:', e);
    }
}

