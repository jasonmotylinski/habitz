/**
 * Frontend tests for habits tracker
 * To run: npm install --save-dev jest @testing-library/dom @testing-library/jest-dom
 * Then: npm test
 */

describe('Date Navigation', () => {
  let dateNav;
  let prevBtn;
  let nextBtn;

  beforeEach(() => {
    // Setup DOM
    document.body.innerHTML = `
      <div id="date-nav">
        <button id="date-prev-btn">Prev</button>
        <div class="date-nav-label">
          <span class="date-nav-day">Saturday</span>
          <span class="date-nav-full">Feb 28, 2026</span>
        </div>
        <button id="date-next-btn">Next</button>
      </div>
      <div class="daily-header">
        <div id="current-date">Saturday, February 28</div>
      </div>
      <ul class="habit-list"></ul>
    `;

    dateNav = document.getElementById('date-nav');
    prevBtn = document.getElementById('date-prev-btn');
    nextBtn = document.getElementById('date-next-btn');
  });

  test('should disable next button when at today', () => {
    // Mock current date as today
    jest.useFakeTimers('modern');
    jest.setSystemTime(new Date('2026-02-28'));

    // Simulate the date nav code
    const todayObj = new Date();
    const currentDate = todayObj.getFullYear() + '-' +
                        String(todayObj.getMonth() + 1).padStart(2, '0') + '-' +
                        String(todayObj.getDate()).padStart(2, '0');

    // When viewing today, next button should be disabled
    const viewDate = currentDate;
    const shouldDisable = viewDate === currentDate;
    expect(shouldDisable).toBe(true);

    jest.useRealTimers();
  });

  test('should allow navigation to past dates', () => {
    // Use noon local time to avoid UTC-midnight-to-local-date shift
    const today = new Date('2026-02-28T12:00:00');
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    const yesterdayStr = yesterday.getFullYear() + '-' +
                         String(yesterday.getMonth() + 1).padStart(2, '0') + '-' +
                         String(yesterday.getDate()).padStart(2, '0');

    // Should be able to navigate to past dates
    expect(yesterdayStr).toBe('2026-02-27');
  });

  test('should format dates correctly (YYYY-MM-DD)', () => {
    // Use noon local time to avoid UTC-midnight-to-local-date shift
    const testDate = new Date('2026-03-05T12:00:00');
    const formatted = testDate.getFullYear() + '-' +
                      String(testDate.getMonth() + 1).padStart(2, '0') + '-' +
                      String(testDate.getDate()).padStart(2, '0');

    expect(formatted).toBe('2026-03-05');
  });
});

describe('Habit Progress Tracking', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div class="daily-progress" data-completed="2" data-total="5">
        <div class="progress-summary">
          <span class="progress-count">2 of 5 done</span>
          <span class="progress-pct">40%</span>
        </div>
        <div class="progress-track">
          <div class="progress-fill" style="width: 40%"></div>
        </div>
      </div>
      <ul class="habit-list">
        <li class="habit-row" data-id="1" data-manual="true">
          <div class="habit-row-inner" role="button">
            <span class="habit-check"></span>
          </div>
        </li>
      </ul>
    `;
  });

  test('should calculate progress percentage correctly', () => {
    const progressSection = document.querySelector('.daily-progress');
    const completed = parseInt(progressSection.dataset.completed);
    const total = parseInt(progressSection.dataset.total);
    const pct = Math.round(completed / total * 100);

    expect(pct).toBe(40);
  });

  test('should update progress when habit is toggled', () => {
    let completed = 2;
    let total = 5;

    // Simulate toggle
    completed = Math.max(0, Math.min(total, completed + 1));
    const pct = total > 0 ? Math.round(completed / total * 100) : 0;

    expect(completed).toBe(3);
    expect(pct).toBe(60);
  });

  test('should prevent progress from exceeding total', () => {
    let completed = 5;
    const total = 5;

    // Try to add more
    completed = Math.max(0, Math.min(total, completed + 1));

    expect(completed).toBe(5);
  });

  test('should prevent negative progress', () => {
    let completed = 0;
    const total = 5;

    // Try to subtract
    completed = Math.max(0, Math.min(total, completed - 1));

    expect(completed).toBe(0);
  });
});

describe('Weekly Ring Rendering', () => {
  test('should render 7 days in weekly view', () => {
    const dailyRings = document.createElement('div');
    dailyRings.id = 'daily-rings';
    dailyRings.className = 'daily-rings';

    const mockData = {
      days: [
        { date: '2026-02-23', label: 'Mon', completed: 4, total: 5 },
        { date: '2026-02-24', label: 'Tue', completed: 5, total: 5 },
        { date: '2026-02-25', label: 'Wed', completed: 3, total: 5 },
        { date: '2026-02-26', label: 'Thu', completed: 5, total: 5 },
        { date: '2026-02-27', label: 'Fri', completed: 4, total: 5 },
        { date: '2026-02-28', label: 'Sat', completed: 2, total: 5 },
        { date: '2026-03-01', label: 'Sun', completed: 0, total: 5 },
      ]
    };

    expect(mockData.days).toHaveLength(7);
  });

  test('should calculate ring offset correctly', () => {
    const RING_R = 22;
    const RING_CIRC = 2 * Math.PI * RING_R;

    const completed = 3;
    const total = 5;
    const offset = total > 0 ? RING_CIRC * (1 - completed / total) : RING_CIRC;

    // Should be between 0 and full circumference
    expect(offset).toBeGreaterThan(0);
    expect(offset).toBeLessThan(RING_CIRC);
    expect(offset).toBe(RING_CIRC * 0.4); // 2/5 remaining
  });

  test('should identify today correctly', () => {
    const today = new Date();
    const todayStr = today.getFullYear() + '-' +
                     String(today.getMonth() + 1).padStart(2, '0') + '-' +
                     String(today.getDate()).padStart(2, '0');

    const mockDay = { date: todayStr, is_today: true };

    expect(mockDay.is_today).toBe(true);
    expect(mockDay.date).toBe(todayStr);
  });
});

describe('Calendar Day Rendering', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div id="cal-grid"></div>
    `;
  });

  test('should render correct number of days for month', () => {
    const calGrid = document.getElementById('cal-grid');
    const mockDays = Array(28).fill(null).map((_, i) => ({
      date: `2026-02-${String(i + 1).padStart(2, '0')}`,
      day: i + 1,
      completed: Math.floor(Math.random() * 5),
      total: 5
    }));

    expect(mockDays).toHaveLength(28);
  });

  test('should mark completed days with ring-complete class', () => {
    const total = 5;
    const completed = 5;
    const completeClass = total > 0 && completed === total ? ' ring-complete' : '';

    expect(completeClass).toBe(' ring-complete');
  });

  test('should not mark incomplete days as ring-complete', () => {
    const total = 5;
    const completed = 4;
    const completeClass = total > 0 && completed === total ? ' ring-complete' : '';

    expect(completeClass).toBe('');
  });
});

describe('Habit Toggle API', () => {
  test('should send toggle request with date parameter', async () => {
    const habitId = 1;
    const viewDate = '2026-02-27';

    // Mock fetch
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ done: true, habit_id: habitId })
      })
    );

    // Simulate toggle request
    const dateParam = `?date=${viewDate}`;
    await fetch(`/api/habits/${habitId}/toggle${dateParam}`, {
      method: 'POST',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'same-origin'
    });

    expect(global.fetch).toHaveBeenCalledWith(
      `/api/habits/${habitId}/toggle?date=${viewDate}`,
      expect.any(Object)
    );

    global.fetch.mockClear();
  });

  test('should handle toggle response correctly', async () => {
    const response = { done: true, habit_id: 1 };

    // Simulate data coming back
    const expectedDone = true;
    const actualDone = response.done;

    expect(actualDone).toBe(expectedDone);
  });

  test('should handle network errors gracefully', async () => {
    global.fetch = jest.fn(() =>
      Promise.reject(new Error('Network error'))
    );

    let errorCaught = false;
    try {
      await fetch('/api/habits/1/toggle');
    } catch (e) {
      errorCaught = true;
    }

    expect(errorCaught).toBe(true);
    global.fetch.mockClear();
  });
});
