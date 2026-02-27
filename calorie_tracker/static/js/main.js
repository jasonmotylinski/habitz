/* ========================================
   CALORIE TRACKER — Client-Side JS
   ======================================== */

document.addEventListener('DOMContentLoaded', () => {
    initFlashMessages();
    initDashboard();
    initFoodSearch();
    initFoodLog();
    initQuickAdd();
    initSettings();
});

/* ---- Flash Messages ---- */
function initFlashMessages() {
    document.querySelectorAll('.flash').forEach(flash => {
        setTimeout(() => {
            flash.style.transition = 'opacity 0.3s, transform 0.3s';
            flash.style.opacity = '0';
            flash.style.transform = 'translateY(-8px)';
            setTimeout(() => flash.remove(), 300);
        }, 3000);
    });
}

/* ---- Dashboard ---- */
function initDashboard() {
    document.querySelectorAll('.meal-entry-delete').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            const logId = btn.dataset.logId;
            if (!logId) return;

            btn.style.opacity = '0.3';
            btn.style.pointerEvents = 'none';

            try {
                const resp = await fetch(window.SCRIPT_ROOT + `/api/log/${logId}`, { method: 'DELETE' });
                if (resp.ok) {
                    const entry = btn.closest('.meal-entry');
                    entry.style.transition = 'opacity 0.2s, transform 0.2s';
                    entry.style.opacity = '0';
                    entry.style.transform = 'translateX(20px)';
                    setTimeout(() => location.reload(), 250);
                }
            } catch (err) {
                btn.style.opacity = '1';
                btn.style.pointerEvents = '';
            }
        });
    });
}

/* ---- Food Search ---- */
function initFoodSearch() {
    const page = document.querySelector('.search-page');
    if (!page) return;

    const input = document.getElementById('food-search-input');
    const clearBtn = document.getElementById('search-clear');
    const resultsSection = document.getElementById('search-results');
    const resultsList = document.getElementById('search-results-list');
    const searchLoading = document.getElementById('search-loading');
    const searchEmpty = document.getElementById('search-empty');
    const recentSection = document.getElementById('recent-foods');
    const recentList = document.getElementById('recent-foods-list');
    const recentEmpty = document.getElementById('recent-empty');

    const mealType = page.dataset.mealType;
    const date = page.dataset.date;

    let debounceTimer = null;
    let searchSeq = 0;  // incremented on every new search; used to discard stale responses

    // Load recent foods
    loadRecent();

    input.addEventListener('input', () => {
        const q = input.value.trim();
        clearBtn.classList.toggle('hidden', !q);

        clearTimeout(debounceTimer);

        if (!q) {
            searchSeq++;
            resultsList.innerHTML = '';
            resultsSection.classList.add('hidden');
            recentSection.classList.remove('hidden');
            return;
        }

        // Immediately clear stale results and show loading state
        resultsList.innerHTML = '';
        searchEmpty.classList.add('hidden');
        recentSection.classList.add('hidden');
        resultsSection.classList.remove('hidden');
        searchLoading.classList.remove('hidden');

        debounceTimer = setTimeout(() => searchFoods(q), 300);
    });

    clearBtn.addEventListener('click', () => {
        searchSeq++;
        input.value = '';
        input.focus();
        clearBtn.classList.add('hidden');
        resultsList.innerHTML = '';
        resultsSection.classList.add('hidden');
        recentSection.classList.remove('hidden');
    });

    async function loadRecent() {
        try {
            const resp = await fetch(window.SCRIPT_ROOT + '/api/foods/recent');
            const data = await resp.json();
            if (data.items && data.items.length > 0) {
                recentEmpty.classList.add('hidden');
                recentList.innerHTML = data.items.map(item => foodCardHTML(item, true)).join('');
                attachFoodCardListeners(recentList);
            }
        } catch (err) {
            // silently fail
        }
    }

    async function searchFoods(query) {
        const seq = ++searchSeq;
        try {
            const resp = await fetch(window.SCRIPT_ROOT + `/api/foods/search?q=${encodeURIComponent(query)}`);
            const data = await resp.json();

            if (seq !== searchSeq) return;  // a newer search has already started

            searchLoading.classList.add('hidden');
            if (data.results && data.results.length > 0) {
                searchEmpty.classList.add('hidden');
                resultsList.innerHTML = data.results.map(item => foodCardHTML(item, false)).join('');
                attachFoodCardListeners(resultsList);
            } else {
                searchEmpty.classList.remove('hidden');
                resultsList.innerHTML = '';
            }
        } catch (err) {
            if (seq !== searchSeq) return;
            searchLoading.classList.add('hidden');
            searchEmpty.classList.remove('hidden');
            resultsList.innerHTML = '';
        }
    }

    function foodCardHTML(item, isCached) {
        const cal = Math.round(item.calories || 0);
        const brand = item.brand ? `<span class="food-card-brand">${escapeHtml(item.brand)}</span>` : '';
        return `
            <div class="food-card" data-food='${JSON.stringify(item).replace(/'/g, "&#39;")}' data-cached="${isCached}">
                <div class="food-card-info">
                    <span class="food-card-name">${escapeHtml(item.name)}</span>
                    ${brand}
                </div>
                <span class="food-card-cal">${cal} <span>cal</span></span>
            </div>
        `;
    }

    function attachFoodCardListeners(container) {
        container.querySelectorAll('.food-card').forEach(card => {
            card.addEventListener('click', async () => {
                const foodData = JSON.parse(card.dataset.food);
                const isCached = card.dataset.cached === 'true';

                if (isCached && foodData.id) {
                    window.location.href = window.SCRIPT_ROOT + `/food/log/${foodData.id}?meal=${mealType}&date=${date}`;
                    return;
                }

                // Create/cache the food item first
                try {
                    card.style.opacity = '0.5';
                    card.style.pointerEvents = 'none';
                    const resp = await fetch(window.SCRIPT_ROOT + '/api/log', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            food_item: foodData,
                            meal_type: mealType,
                            date: date,
                            servings: 1,
                        }),
                    });
                    if (resp.ok) {
                        // Logged directly, go to dashboard
                        window.location.href = window.SCRIPT_ROOT + `/dashboard?date=${date}`;
                    }
                } catch (err) {
                    card.style.opacity = '1';
                    card.style.pointerEvents = '';
                }
            });
        });
    }
}

/* ---- Food Log Page ---- */
function initFoodLog() {
    const page = document.querySelector('.log-page');
    if (!page) return;

    const foodId = page.dataset.foodId;
    const mealType = page.dataset.mealType;
    const date = page.dataset.date;

    const nameEl = document.getElementById('food-name');
    const loadingEl = document.getElementById('log-loading');
    const contentEl = document.getElementById('log-content');
    const servingLabel = document.getElementById('serving-label');
    const servingInput = document.getElementById('serving-input');
    const minusBtn = document.getElementById('serving-minus');
    const plusBtn = document.getElementById('serving-plus');
    const submitBtn = document.getElementById('log-submit');

    let foodItem = null;

    // Load food detail
    loadFood();

    async function loadFood() {
        try {
            const resp = await fetch(window.SCRIPT_ROOT + `/api/foods/${foodId}`);
            foodItem = await resp.json();

            nameEl.textContent = foodItem.name;
            servingLabel.textContent = foodItem.serving_size || '1 serving';
            loadingEl.classList.add('hidden');
            contentEl.classList.remove('hidden');
            updateNutrition();
        } catch (err) {
            nameEl.textContent = 'Error loading food';
            loadingEl.classList.add('hidden');
        }
    }

    function updateNutrition() {
        if (!foodItem) return;
        const s = parseFloat(servingInput.value) || 1;
        document.getElementById('nut-calories').textContent = Math.round(foodItem.calories * s);
        document.getElementById('nut-protein').textContent = Math.round(foodItem.protein_g * s * 10) / 10;
        document.getElementById('nut-carbs').textContent = Math.round(foodItem.carbs_g * s * 10) / 10;
        document.getElementById('nut-fat').textContent = Math.round(foodItem.fat_g * s * 10) / 10;
    }

    minusBtn.addEventListener('click', () => {
        const val = parseFloat(servingInput.value) || 1;
        if (val > 0.5) {
            servingInput.value = (val - 0.5).toFixed(1);
            updateNutrition();
        }
    });

    plusBtn.addEventListener('click', () => {
        const val = parseFloat(servingInput.value) || 1;
        servingInput.value = (val + 0.5).toFixed(1);
        updateNutrition();
    });

    servingInput.addEventListener('input', updateNutrition);

    submitBtn.addEventListener('click', async () => {
        if (!foodItem) return;

        const selectedMeal = document.querySelector('input[name="meal_type"]:checked');
        const mt = selectedMeal ? selectedMeal.value : mealType;

        submitBtn.disabled = true;
        submitBtn.textContent = 'Logging...';

        try {
            const resp = await fetch(window.SCRIPT_ROOT + '/api/log', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    food_item_id: foodItem.id,
                    meal_type: mt,
                    servings: parseFloat(servingInput.value) || 1,
                    date: date,
                }),
            });

            if (resp.ok) {
                window.location.href = window.SCRIPT_ROOT + `/dashboard?date=${date}`;
            } else {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Log Food';
            }
        } catch (err) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Log Food';
        }
    });
}

/* ---- Quick Add ---- */
function initQuickAdd() {
    const page = document.querySelector('.quick-add-page');
    if (!page) return;

    const mealType = page.dataset.mealType;
    const date = page.dataset.date;
    const caloriesInput = document.getElementById('quick-calories');
    const nameInput = document.getElementById('quick-name');
    const submitBtn = document.getElementById('quick-add-submit');
    const errorEl = document.getElementById('quick-add-error');
    const macrosToggle = document.getElementById('macros-toggle');
    const macrosFields = document.getElementById('macros-fields');
    const macrosIcon = document.getElementById('macros-toggle-icon');
    const proteinInput = document.getElementById('quick-protein');
    const carbsInput = document.getElementById('quick-carbs');
    const fatInput = document.getElementById('quick-fat');

    if (!submitBtn || !caloriesInput || !errorEl) {
        console.error('Quick add: missing required DOM elements');
        return;
    }

    let macrosOpen = false;
    macrosToggle.addEventListener('click', () => {
        macrosOpen = !macrosOpen;
        macrosFields.classList.toggle('hidden', !macrosOpen);
        macrosIcon.innerHTML = macrosOpen
            ? '<line x1="5" y1="12" x2="19" y2="12"/>'
            : '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>';
        if (macrosOpen) proteinInput.focus();
    });

    submitBtn.addEventListener('click', async () => {
        const calories = parseFloat(caloriesInput.value);
        if (!calories || calories <= 0) {
            errorEl.textContent = 'Please enter a calories amount greater than 0.';
            errorEl.classList.remove('hidden');
            caloriesInput.focus();
            return;
        }
        errorEl.classList.add('hidden');

        const selectedMeal = document.querySelector('input[name="meal_type"]:checked');
        const mt = selectedMeal ? selectedMeal.value : mealType;
        const name = nameInput.value.trim();
        const protein = macrosOpen ? (parseFloat(proteinInput.value) || 0) : 0;
        const carbs = macrosOpen ? (parseFloat(carbsInput.value) || 0) : 0;
        const fat = macrosOpen ? (parseFloat(fatInput.value) || 0) : 0;

        submitBtn.disabled = true;
        submitBtn.textContent = 'Adding...';

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000);

            const resp = await fetch(window.SCRIPT_ROOT + '/api/log/quick', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ calories, name, meal_type: mt, date, protein_g: protein, carbs_g: carbs, fat_g: fat }),
                signal: controller.signal,
            });

            clearTimeout(timeoutId);

            if (resp.ok) {
                window.location.href = window.SCRIPT_ROOT + `/dashboard?date=${date}`;
            } else {
                let errorMsg = 'Something went wrong.';
                try {
                    const err = await resp.json();
                    errorMsg = err.error || errorMsg;
                } catch (e) {
                    // response wasn't JSON, use default
                }
                errorEl.textContent = errorMsg;
                errorEl.classList.remove('hidden');
                submitBtn.disabled = false;
                submitBtn.textContent = 'Add Calories';
            }
        } catch (err) {
            if (err.name === 'AbortError') {
                errorEl.textContent = 'Request timed out. Please try again.';
            } else {
                errorEl.textContent = 'Network error. Please try again.';
            }
            errorEl.classList.remove('hidden');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Add Calories';
        }
    });
}

/* ---- Settings ---- */
function initSettings() {
    const page = document.querySelector('.settings-page');
    if (!page) return;

    const calGoal = document.getElementById('daily_calorie_goal');
    const proteinPct = document.getElementById('protein_goal_pct');
    const carbPct = document.getElementById('carb_goal_pct');
    const fatPct = document.getElementById('fat_goal_pct');
    const proteinGrams = document.getElementById('protein-grams');
    const carbGrams = document.getElementById('carb-grams');
    const fatGrams = document.getElementById('fat-grams');
    const totalEl = document.getElementById('macro-total');
    const warningEl = document.getElementById('macro-total-warning');

    function update() {
        const cal = parseInt(calGoal.value) || 0;
        const p = parseInt(proteinPct.value) || 0;
        const c = parseInt(carbPct.value) || 0;
        const f = parseInt(fatPct.value) || 0;

        proteinGrams.textContent = Math.round((cal * p / 100) / 4) + 'g';
        carbGrams.textContent = Math.round((cal * c / 100) / 4) + 'g';
        fatGrams.textContent = Math.round((cal * f / 100) / 9) + 'g';

        const total = p + c + f;
        totalEl.textContent = total + '%';
        totalEl.style.color = total === 100 ? 'var(--green-600)' : 'var(--red-500)';
        warningEl.classList.toggle('hidden', total === 100);
    }

    [calGoal, proteinPct, carbPct, fatPct].forEach(el => {
        el.addEventListener('input', update);
    });

    update();
}

/* ---- Helpers ---- */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ===== APP SWITCHER =====
(function() {
    var btn = document.getElementById("appSwitcherBtn");
    if (!btn) return;
    var switcher = document.getElementById("appSwitcher");
    btn.addEventListener("click", function(e) {
        e.stopPropagation();
        var isOpen = switcher.classList.toggle("open");
        btn.setAttribute("aria-expanded", String(isOpen));
    });
    document.addEventListener("click", function(e) {
        if (!switcher.contains(e.target)) {
            switcher.classList.remove("open");
            btn.setAttribute("aria-expanded", "false");
        }
    });
    document.addEventListener("keydown", function(e) {
        if (e.key === "Escape") {
            switcher.classList.remove("open");
            btn.setAttribute("aria-expanded", "false");
        }
    });
})();

