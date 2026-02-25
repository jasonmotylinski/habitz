// Shared API helper
const api = {
    async request(method, url, body = null) {
        const base = window.SCRIPT_ROOT || '';
        const fullUrl = (url.startsWith('http') || url.startsWith('//')) ? url : base + url;
        const opts = {
            method,
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
        };
        if (body) opts.body = JSON.stringify(body);
        const res = await fetch(fullUrl, opts);
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.error || `Request failed (${res.status})`);
        }
        return data;
    },
    get: (url) => api.request('GET', url),
    post: (url, body) => api.request('POST', url, body),
    put: (url, body) => api.request('PUT', url, body),
    delete: (url) => api.request('DELETE', url),
};

function showToast(message, type = '') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('show'));
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}

function showConfirm(message, confirmLabel = 'Delete', confirmClass = 'btn-danger') {
    return new Promise((resolve) => {
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.innerHTML = `
            <div class="modal">
                <h2>${message}</h2>
                <div class="modal-actions">
                    <button class="btn btn-ghost" id="modal-cancel">Cancel</button>
                    <button class="btn ${confirmClass}" id="modal-confirm">${confirmLabel}</button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
        overlay.querySelector('#modal-cancel').onclick = () => { overlay.remove(); resolve(false); };
        overlay.querySelector('#modal-confirm').onclick = () => { overlay.remove(); resolve(true); };
        overlay.onclick = (e) => { if (e.target === overlay) { overlay.remove(); resolve(false); } };
    });
}

function formatDate(isoStr) {
    if (!isoStr) return '';
    const d = new Date(isoStr);
    return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}

function formatSetsReps(ex) {
    if (ex.exercise_type === 'cardio') {
        return `${ex.default_duration_minutes || '–'} min`;
    }
    const unitLabel = { reps: 'reps', secs: 'secs', mins: 'mins' }[ex.unit] || 'reps';
    return `${ex.default_sets}×${ex.default_reps} ${unitLabel}${ex.default_weight ? ' ' + ex.default_weight + 'lb' : ''}`;
}
