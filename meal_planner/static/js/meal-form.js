/**
 * Meal Form - Multi-step form logic
 */

class MealForm {
    constructor(formSelector = 'form.meal-form') {
        this.form = $(formSelector);
        if (!this.form) return;

        this.currentStep = 1;
        this.totalSteps = 4;
        this.formData = {};

        this.steps = $$('.form-step');
        this.progressDots = $$('.progress-dot');
        this.nextButtons = $$('[data-next-step]');
        this.prevButtons = $$('[data-prev-step]');
        this.submitButton = $('[data-submit-form]');

        this.init();
    }

    init() {
        // Show first step
        this.showStep(1);

        // Next buttons
        this.nextButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                if (this.validateStep(this.currentStep)) {
                    this.saveStepData();
                    this.showStep(this.currentStep + 1);
                }
            });
        });

        // Previous buttons
        this.prevButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                this.saveStepData();
                this.showStep(this.currentStep - 1);
            });
        });

        // Form submission
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            if (this.validateStep(this.currentStep)) {
                this.saveStepData();
                this.submitForm();
            }
        });

        // Input change listener
        $$('input, textarea, select').forEach(input => {
            input.addEventListener('change', () => {
                this.saveStepData();
            });
        });
    }

    showStep(step) {
        // Validate step number
        if (step < 1 || step > this.totalSteps) return;

        // Hide all steps
        this.steps.forEach(s => s.classList.remove('active'));

        // Show current step
        const currentStepEl = $(`.form-step[data-step="${step}"]`);
        if (currentStepEl) {
            currentStepEl.classList.add('active');
        }

        // Update progress indicator
        this.updateProgress(step);

        // Update buttons visibility
        this.updateButtons(step);

        // Scroll to form
        this.form.scrollIntoView({ behavior: 'smooth', block: 'start' });

        this.currentStep = step;
    }

    updateProgress(step) {
        this.progressDots.forEach((dot, index) => {
            dot.classList.remove('active', 'completed');
            if (index < step) {
                dot.classList.add('completed');
            }
            if (index === step - 1) {
                dot.classList.add('active');
            }
        });
    }

    updateButtons(step) {
        const prevBtn = $('[data-prev-step]');
        const nextBtn = $('[data-next-step]');

        // Show/hide previous button
        if (prevBtn) {
            prevBtn.style.display = step > 1 ? 'flex' : 'none';
        }

        // Show/hide next button and submit
        if (nextBtn && this.submitButton) {
            if (step < this.totalSteps) {
                nextBtn.style.display = 'flex';
                this.submitButton.style.display = 'none';
            } else {
                nextBtn.style.display = 'none';
                this.submitButton.style.display = 'flex';
            }
        }
    }

    saveStepData() {
        const inputs = $$('.form-step.active input, .form-step.active textarea, .form-step.active select');
        inputs.forEach(input => {
            if (input.type === 'checkbox') {
                this.formData[input.name] = input.checked;
            } else if (input.type === 'file') {
                if (input.files.length > 0) {
                    this.formData[input.name] = input.files[0];
                }
            } else {
                this.formData[input.name] = input.value;
            }
        });
    }

    validateStep(step) {
        const currentStepEl = $(`.form-step[data-step="${step}"]`);
        if (!currentStepEl) return true;

        const requiredFields = $$('.form-step.active [required]');
        let isValid = true;

        requiredFields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });

        return isValid;
    }

    validateField(field) {
        let isValid = true;
        let errorMessage = '';

        if (field.type === 'email') {
            isValid = validateEmail(field.value);
            errorMessage = 'Please enter a valid email address';
        } else if (field.type === 'text' || field.tagName === 'TEXTAREA') {
            isValid = field.value.trim().length > 0;
            errorMessage = `${field.getAttribute('data-label') || field.name} is required`;
        } else if (field.value.trim().length === 0) {
            errorMessage = `${field.getAttribute('data-label') || field.name} is required`;
        }

        if (!isValid) {
            showFormError(field, errorMessage);
        } else {
            clearFormError(field);
        }

        return isValid;
    }

    submitForm() {
        this.saveStepData();
        setButtonLoading(this.submitButton, true);

        // Slight delay to show loading state
        setTimeout(() => {
            this.form.submit();
        }, 300);
    }

    reset() {
        this.currentStep = 1;
        this.formData = {};
        this.form.reset();
        this.showStep(1);
    }
}

// Image Preview Handler
class ImagePreview {
    constructor(inputSelector = 'input[type="file"]') {
        this.inputs = $$(inputSelector);
        this.init();
    }

    init() {
        this.inputs.forEach(input => {
            input.addEventListener('change', (e) => {
                this.previewImage(e.target);
            });
        });
    }

    previewImage(input) {
        if (!input.files || input.files.length === 0) return;

        const file = input.files[0];
        const reader = new FileReader();

        reader.onload = (e) => {
            let preview = $(`[data-preview-for="${input.name}"]`);

            if (!preview) {
                preview = document.createElement('div');
                preview.setAttribute('data-preview-for', input.name);
                preview.style.cssText = `
                    margin-top: var(--spacing-md);
                    border-radius: var(--radius-md);
                    overflow: hidden;
                    box-shadow: var(--shadow-sm);
                `;
                input.parentNode.insertBefore(preview, input.nextSibling);
            }

            preview.innerHTML = `
                <img src="${e.target.result}"
                     style="width: 100%; height: auto; display: block; max-height: 300px; object-fit: cover;"
                     alt="Image preview">
                <small style="display: block; padding: var(--spacing-sm); background-color: var(--cream); color: #666;">
                    ${file.name} (${(file.size / 1024 / 1024).toFixed(2)}MB)
                </small>
            `;
        };

        reader.readAsDataURL(file);
    }
}

// Initialize on document ready
document.addEventListener('DOMContentLoaded', function() {
    new MealForm('form.meal-form');
    new ImagePreview('input[type="file"]');

    console.log('✓ Meal form initialized');
});
