/**
 * Main JavaScript - Global utilities and interactions
 */

// ===== DOM UTILITIES =====

function $(selector) {
    return document.querySelector(selector);
}

function $$(selector) {
    return document.querySelectorAll(selector);
}

// ===== NAVIGATION =====

document.addEventListener('DOMContentLoaded', function() {
    // Mobile menu toggle
    const mobileMenuToggle = $('#mobileMenuToggle');
    const navbarNav = $('#navbarNav');

    if (mobileMenuToggle) {
        mobileMenuToggle.addEventListener('click', function() {
            navbarNav.classList.toggle('active');
        });

        // Close menu when a link is clicked
        $$('#navbarNav .nav-link').forEach(link => {
            link.addEventListener('click', function() {
                navbarNav.classList.remove('active');
            });
        });
    }

    // User dropdown menu
    const userDropdown = $('#userDropdown');
    const userDropdownMenu = $('#userDropdownMenu');

    if (userDropdown && userDropdownMenu) {
        const userDropdownContainer = userDropdown.closest('.nav-dropdown');

        userDropdown.addEventListener('click', function(e) {
            e.preventDefault();
            userDropdownContainer.classList.toggle('active');
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (!userDropdownContainer.contains(e.target)) {
                userDropdownContainer.classList.remove('active');
            }
        });

        // Close dropdown when a menu item is clicked
        $$('.nav-dropdown-item').forEach(item => {
            item.addEventListener('click', function() {
                userDropdownContainer.classList.remove('active');
            });
        });
    }

    // Alert dismissal
    $$('.alert-close').forEach(closeBtn => {
        closeBtn.addEventListener('click', function() {
            const alert = this.closest('.alert');
            alert.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => {
                alert.remove();
            }, 300);
        });
    });
});

// ===== TOAST NOTIFICATIONS =====

class Toast {
    constructor(message, type = 'success', duration = 3000) {
        this.message = message;
        this.type = type;
        this.duration = duration;
        this.element = null;
    }

    show() {
        const container = document.body;

        // Create toast element
        this.element = document.createElement('div');
        this.element.className = `toast toast-${this.type}`;

        const icon = this.getIcon();
        this.element.innerHTML = `
            <span class="toast-icon">${icon}</span>
            <span>${this.message}</span>
        `;

        container.appendChild(this.element);

        // Force reflow to trigger animation
        this.element.offsetHeight;

        // Auto-dismiss
        if (this.duration > 0) {
            setTimeout(() => this.dismiss(), this.duration);
        }

        return this;
    }

    dismiss() {
        if (this.element) {
            this.element.classList.add('exit');
            setTimeout(() => {
                this.element.remove();
            }, 300);
        }
    }

    getIcon() {
        const icons = {
            success: '✓',
            danger: '✕',
            warning: '⚠',
            info: 'ℹ'
        };
        return icons[this.type] || icons.info;
    }
}

// Make Toast globally available
window.Toast = Toast;

// ===== FORM UTILITIES =====

function showFormError(inputElement, errorMessage) {
    inputElement.classList.add('is-invalid');

    let errorEl = inputElement.nextElementSibling;
    if (!errorEl || !errorEl.classList.contains('form-error')) {
        errorEl = document.createElement('span');
        errorEl.className = 'form-error';
        inputElement.parentNode.insertBefore(errorEl, inputElement.nextSibling);
    }
    errorEl.textContent = errorMessage;
}

function clearFormError(inputElement) {
    inputElement.classList.remove('is-invalid');
    const errorEl = inputElement.nextElementSibling;
    if (errorEl && errorEl.classList.contains('form-error')) {
        errorEl.remove();
    }
}

// ===== LOADING STATES =====

function setButtonLoading(button, isLoading = true) {
    if (isLoading) {
        button.disabled = true;
        button.classList.add('loading');
        button.setAttribute('aria-busy', 'true');
    } else {
        button.disabled = false;
        button.classList.remove('loading');
        button.setAttribute('aria-busy', 'false');
    }
}

// ===== LOCAL STORAGE UTILITIES =====

const Storage = {
    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (e) {
            console.warn('Storage.set failed:', e);
            return false;
        }
    },

    get(key) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : null;
        } catch (e) {
            console.warn('Storage.get failed:', e);
            return null;
        }
    },

    remove(key) {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (e) {
            console.warn('Storage.remove failed:', e);
            return false;
        }
    },

    clear() {
        try {
            localStorage.clear();
            return true;
        } catch (e) {
            console.warn('Storage.clear failed:', e);
            return false;
        }
    }
};

window.Storage = Storage;

// ===== CONFETTI ANIMATION =====

function createConfetti(x, y, count = 30) {
    const colors = ['#87A878', '#E07A5F', '#F4A261', '#3D3D3D'];

    for (let i = 0; i < count; i++) {
        const confetti = document.createElement('div');
        confetti.className = 'confetti';
        confetti.style.left = x + 'px';
        confetti.style.top = y + 'px';
        confetti.style.background = colors[Math.floor(Math.random() * colors.length)];
        confetti.style.setProperty('--duration', (2 + Math.random()) + 's');

        const angle = (i / count) * Math.PI * 2;
        const velocity = 5 + Math.random() * 5;
        const vx = Math.cos(angle) * velocity;
        const vy = Math.sin(angle) * velocity - 5;

        confetti.style.transform = `translate(${vx * 100}px, ${vy * 100}px) rotate(${Math.random() * 360}deg)`;

        document.body.appendChild(confetti);

        setTimeout(() => confetti.remove(), 3000);
    }
}

window.createConfetti = createConfetti;

// ===== FORM VALIDATION =====

function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

function validatePassword(password) {
    return password && password.length >= 6;
}

window.validateEmail = validateEmail;
window.validatePassword = validatePassword;

// ===== ACCESSIBILITY =====

// Skip to main content link
document.addEventListener('keydown', function(e) {
    if (e.key === 'Tab' && e.shiftKey === false) {
        const activeElement = document.activeElement;
        if (activeElement.classList.contains('nav-link')) {
            // Allow tabbing through navigation
        }
    }
});

// ===== INITIALIZATION =====

console.log('✓ Main.js loaded');

