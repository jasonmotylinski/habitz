/**
 * Regression tests for the active workout rest timer.
 *
 * Bug: after the UI polish commit (389fbe2), the #rest-time span was hidden
 * with class="hidden" (CSS: `.hidden { display: none !important }`) instead of
 * an inline style="display: none". _runRestTimer() still revealed it with
 * `el.style.display = ''`, which only clears the inline style — the
 * !important rule kept the element invisible while the timer ticked away.
 *
 * These tests eval the REAL _runRestTimer() source extracted from the Jinja
 * template, so a regression in the template fails here.
 */
const fs = require('fs');
const path = require('path');

const template = fs.readFileSync(
  path.join(__dirname, '..', 'workout_tracker', 'templates', 'active_workout.html'),
  'utf8'
);

function makeRunRestTimer(startedAt) {
  const start = template.indexOf('function _runRestTimer()');
  if (start === -1) throw new Error('_runRestTimer not found in active_workout.html');
  // The function's closing brace is the first unindented `}` after it.
  const end = template.indexOf('\n}', start);
  const src = template.slice(start, end + 2);
  return new Function(
    'restTimerState',
    'var restTimerInterval = null; var restTimerStartedAt = restTimerState.startedAt;' +
      src +
      '; return _runRestTimer;'
  )({ startedAt });
}

describe('rest timer visibility', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    document.body.innerHTML = '<span class="time hidden" id="rest-time">Rest 0:00</span>';
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  test('rest timer reveal removes the hidden class (style.display cannot beat !important)', () => {
    const runRestTimer = makeRunRestTimer(Date.now());
    runRestTimer();
    const el = document.getElementById('rest-time');
    // The failure mode: class still present => `.hidden{display:none!important}`
    // keeps the timer invisible even though it is running.
    expect(el.classList.contains('hidden')).toBe(false);
  });

  test('rest timer renders the ticking text', () => {
    const runRestTimer = makeRunRestTimer(Date.now());
    runRestTimer();
    const el = document.getElementById('rest-time');
    expect(el.textContent).toMatch(/^Rest \d+:\d\d$/);
    jest.advanceTimersByTime(2000);
    expect(el.textContent).toMatch(/^Rest \d+:\d\d$/);
    expect(el.textContent).not.toBe('Rest 0:00');
  });
});
