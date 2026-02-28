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

  function handleToggle(row) {
    if (row.dataset.pending) return;

    var habitId = row.dataset.id;
    var wasDone = row.classList.contains('is-done');

    // Optimistic update
    row.dataset.pending = '1';
    setRowDone(row, !wasDone);
    updateProgress(wasDone ? -1 : 1);

    fetch('/api/habits/' + habitId + '/toggle', {
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
