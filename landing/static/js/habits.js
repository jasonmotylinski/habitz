// ── Date Navigation ────────────────────────────────────────────────────────────
(function () {
  'use strict';

  var dateNav = document.getElementById('date-nav');
  if (!dateNav) return;

  var prevBtn = document.getElementById('date-prev-btn');
  var nextBtn = document.getElementById('date-next-btn');
  var currentDateEl = document.getElementById('current-date');
  var dateNavDay = dateNav.querySelector('.date-nav-day');
  var dateNavFull = dateNav.querySelector('.date-nav-full');

  var currentDate = new Date().toISOString().split('T')[0];

  function getURLDate() {
    var params = new URLSearchParams(window.location.search);
    return params.get('date') || currentDate;
  }

  function navigateToDate(newDate) {
    var url = window.location.pathname;
    if (newDate !== currentDate) {
      url += '?date=' + newDate;
    }
    window.location.href = url;
  }

  prevBtn.addEventListener('click', function () {
    var viewDate = new Date(getURLDate());
    viewDate.setDate(viewDate.getDate() - 1);
    navigateToDate(viewDate.toISOString().split('T')[0]);
  });

  nextBtn.addEventListener('click', function () {
    var viewDate = new Date(getURLDate());
    viewDate.setDate(viewDate.getDate() + 1);
    navigateToDate(viewDate.toISOString().split('T')[0]);
  });

  // Disable next button if at today
  function updateNavButtons() {
    var viewDate = getURLDate();
    nextBtn.disabled = viewDate === currentDate;
  }

  updateNavButtons();
})();

// ── Habit Progress ────────────────────────────────────────────────────────────
(function () {
  'use strict';

  var progressSection = document.querySelector('.daily-progress');
  var progressFill    = document.querySelector('.progress-fill');
  var progressCount   = document.querySelector('.progress-count');
  var progressPct     = document.querySelector('.progress-pct');

  var completed = progressSection ? parseInt(progressSection.dataset.completed, 10) : 0;
  var total     = progressSection ? parseInt(progressSection.dataset.total, 10) : 0;

  function updateProgress(delta) {
    completed = Math.max(0, Math.min(total, completed + delta));
    var pct = total > 0 ? Math.round(completed / total * 100) : 0;
    if (progressFill)  progressFill.style.width = pct + '%';
    if (progressCount) progressCount.textContent = completed + ' of ' + total + ' done';
    if (progressPct)   progressPct.textContent = pct + '%';
  }

  function setRowDone(row, done) {
    var check = row.querySelector('.habit-check');
    var inner = row.querySelector('.habit-row-inner');

    if (done) {
      row.classList.add('is-done');
      check.classList.add('done');
      if (inner) inner.setAttribute('aria-pressed', 'true');
    } else {
      row.classList.remove('is-done');
      check.classList.remove('done');
      if (inner) inner.setAttribute('aria-pressed', 'false');
    }

    // Restart pop animation
    check.classList.remove('pop');
    void check.offsetWidth;
    check.classList.add('pop');
  }

  function getURLDate() {
    var params = new URLSearchParams(window.location.search);
    return params.get('date') || new Date().toISOString().split('T')[0];
  }

  function handleToggle(row) {
    if (row.dataset.pending) return;

    var habitId = row.dataset.id;
    var wasDone = row.classList.contains('is-done');
    var dateParam = '?date=' + getURLDate();

    // Optimistic update
    row.dataset.pending = '1';
    setRowDone(row, !wasDone);
    updateProgress(wasDone ? -1 : 1);

    fetch('/api/habits/' + habitId + '/toggle' + dateParam, {
      method: 'POST',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'same-origin',
    })
      .then(function (resp) {
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        return resp.json();
      })
      .then(function (data) {
        // Reconcile if server state differs from our optimistic guess
        var expectedDone = !wasDone;
        if (data.done !== expectedDone) {
          setRowDone(row, data.done);
          updateProgress(wasDone ? -1 : 1);  // undo optimistic
          updateProgress(data.done ? 1 : -1); // apply real
        }
      })
      .catch(function () {
        // Rollback on network error
        setRowDone(row, wasDone);
        updateProgress(wasDone ? 1 : -1);
      })
      .finally(function () {
        delete row.dataset.pending;
      });
  }

  document.querySelectorAll('.habit-row[data-manual]').forEach(function (row) {
    var inner = row.querySelector('.habit-row-inner');
    if (!inner) return;

    inner.addEventListener('click', function () {
      handleToggle(row);
    });

    inner.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        handleToggle(row);
      }
    });
  });
})();

// ── Weekly stats for dashboard ────────────────────────────────────────────────
(function () {
  'use strict';

  var dailyRings = document.getElementById('daily-rings');
  if (!dailyRings) return;

  var RING_R    = 22;
  var RING_CIRC = 2 * Math.PI * RING_R;

  function fetchWeeklyStats() {
    fetch('/api/habits/weekly', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(renderWeekly)
      .catch(function (e) { console.error('Weekly fetch failed', e); });
  }

  function renderWeekly(data) {
    if (!data.days || data.days.length === 0) return;

    dailyRings.innerHTML = '';
    var today = new Date().toISOString().split('T')[0];

    data.days.forEach(function (day) {
      var isToday = day.date === today;
      var offset = day.total > 0
        ? RING_CIRC * (1 - day.completed / day.total)
        : RING_CIRC;
      var completeClass = day.total > 0 && day.completed === day.total ? ' ring-complete' : '';

      var wrap = document.createElement('div');
      wrap.className = 'daily-ring-wrap' + (isToday ? ' today' : '');

      wrap.innerHTML =
        '<svg class="ring-svg daily-ring-svg" viewBox="0 0 60 60">' +
          '<circle class="ring-bg" cx="30" cy="30" r="' + RING_R + '" />' +
          '<circle class="ring-progress' + completeClass + '"' +
            ' cx="30" cy="30" r="' + RING_R + '"' +
            ' stroke-dasharray="' + RING_CIRC.toFixed(2) + '"' +
            ' stroke-dashoffset="' + offset.toFixed(2) + '" />' +
          '<text class="daily-ring-day" x="30" y="30" text-anchor="middle" dominant-baseline="central" transform="rotate(90,30,30)">' +
            day.label +
          '</text>' +
        '</svg>' +
        '<span class="daily-ring-count">' + day.completed + '/' + day.total + '</span>';

      dailyRings.appendChild(wrap);
    });
  }

  fetchWeeklyStats();
})();

// ── Habit calendar (history page) ────────────────────────────────────────────────
(function () {
  'use strict';

  var calGrid = document.getElementById('cal-grid');
  if (!calGrid) return;

  var RING_R    = 22;
  var RING_CIRC = 2 * Math.PI * RING_R;

  var MONTH_NAMES = [
    'January','February','March','April','May','June',
    'July','August','September','October','November','December'
  ];

  var calYear, calMonth;

  // ── Fetch & render ──────────────────────────────────────────────────────────

  function fetchCalendar(year, month) {
    var monthStr = year + '-' + String(month).padStart(2, '0');
    fetch('/api/habits/calendar?month=' + monthStr, { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(renderCalendar)
      .catch(function (e) { console.error('Calendar fetch failed', e); });
  }

  function renderCalendar(data) {
    var label = document.getElementById('cal-month-label');
    if (label) label.textContent = MONTH_NAMES[data.month - 1] + ' ' + data.year;

    calGrid.innerHTML = '';

    var today = new Date().toISOString().split('T')[0];

    // Blank cells before the 1st
    var firstWeekday = data.days[0].weekday; // 0=Mon
    for (var i = 0; i < firstWeekday; i++) {
      var empty = document.createElement('div');
      empty.className = 'cal-day cal-day--empty';
      calGrid.appendChild(empty);
    }

    data.days.forEach(function (day) {
      var isToday  = day.date === today;
      var isFuture = day.date > today;
      var offset   = isFuture ? RING_CIRC : RING_CIRC * (1 - day.progress);
      var completeClass = (!isFuture && day.all_done) ? ' ring-complete' : '';

      var cell = document.createElement('div');
      cell.className = 'cal-day' + (isToday ? ' cal-day--today' : '');
      cell.title = day.total > 0
        ? day.completed + ' / ' + day.total + ' habits'
        : '';

      cell.innerHTML =
        '<svg class="ring-svg" viewBox="0 0 60 60">' +
          '<circle class="ring-bg" cx="30" cy="30" r="' + RING_R + '" />' +
          '<circle class="ring-progress' + completeClass + '"' +
            ' cx="30" cy="30" r="' + RING_R + '"' +
            ' stroke-dasharray="' + RING_CIRC.toFixed(2) + '"' +
            ' stroke-dashoffset="' + offset.toFixed(2) + '" />' +
          '<text class="cal-day-num" x="30" y="30"' +
            ' transform="rotate(90,30,30)"' +
            ' text-anchor="middle" dominant-baseline="central">' +
            day.day +
          '</text>' +
        '</svg>';

      calGrid.appendChild(cell);
    });

    updateCalNav();
  }

  // ── Navigation ──────────────────────────────────────────────────────────────

  function updateCalNav() {
    var now      = new Date();
    var nextBtn  = document.getElementById('cal-next');
    var atNow    = calYear === now.getFullYear() && calMonth === now.getMonth() + 1;
    if (nextBtn) nextBtn.disabled = atNow;
  }

  var prevBtn = document.getElementById('cal-prev');
  var nextBtn = document.getElementById('cal-next');

  if (prevBtn) {
    prevBtn.addEventListener('click', function () {
      calMonth--;
      if (calMonth < 1) { calMonth = 12; calYear--; }
      fetchCalendar(calYear, calMonth);
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener('click', function () {
      calMonth++;
      if (calMonth > 12) { calMonth = 1; calYear++; }
      fetchCalendar(calYear, calMonth);
    });
  }

  // ── Init ────────────────────────────────────────────────────────────────────

  var now  = new Date();
  calYear  = now.getFullYear();
  calMonth = now.getMonth() + 1;
  fetchCalendar(calYear, calMonth);

})();
