/**
 * Onboarding - First-time user guidance
 */

class Onboarding {
    constructor() {
        this.SEEN_KEY = 'meal-planner-onboarding-seen';
        this.HOUSEHOLD_CREATED_KEY = 'meal-planner-household-created';
        this.RECIPE_ADDED_KEY = 'meal-planner-recipe-added';
        this.WEEK_PLANNED_KEY = 'meal-planner-week-planned';
    }

    /**
     * Check if this is first time visiting
     */
    isFirstTime() {
        return !Storage.get(this.SEEN_KEY);
    }

    /**
     * Mark onboarding as seen
     */
    markAsSeen() {
        Storage.set(this.SEEN_KEY, true);
    }

    /**
     * Show welcome toast for first-time users
     */
    showWelcome() {
        if (this.isFirstTime()) {
            setTimeout(() => {
                new Toast('Welcome to Meal Planner! 👋 Let\'s get started.', 'success', 5000);
            }, 500);
            this.markAsSeen();
        }
    }

    /**
     * Track household creation
     */
    markHouseholdCreated() {
        Storage.set(this.HOUSEHOLD_CREATED_KEY, true);
    }

    hasCreatedHousehold() {
        return Storage.get(this.HOUSEHOLD_CREATED_KEY);
    }

    /**
     * Track recipe added
     */
    markRecipeAdded() {
        Storage.set(this.RECIPE_ADDED_KEY, true);
    }

    hasAddedRecipe() {
        return Storage.get(this.RECIPE_ADDED_KEY);
    }

    /**
     * Track week planning
     */
    markWeekPlanned() {
        Storage.set(this.WEEK_PLANNED_KEY, true);
    }

    hasPlannedWeek() {
        return Storage.get(this.WEEK_PLANNED_KEY);
    }

    /**
     * Get progress percentage (0-100)
     */
    getProgress() {
        let progress = 0;
        if (this.hasCreatedHousehold()) progress += 33;
        if (this.hasAddedRecipe()) progress += 33;
        if (this.hasPlannedWeek()) progress += 34;
        return progress;
    }

    /**
     * Show contextual tips based on current page
     */
    showContextualTip(page) {
        const tips = {
            'home': {
                title: '👋 Welcome to Meal Planner',
                message: 'Stop wondering "what\'s for dinner" at 5pm. Plan your week on Sunday.',
                duration: 6000
            },
            'dashboard': {
                title: '🎯 Let\'s get started',
                message: 'Complete the onboarding steps to set up your household, add recipes, and plan your week.',
                duration: 5000
            },
            'meals-library': {
                title: '📖 Your Recipe Collection',
                message: 'Add your favorite recipes here. You can add photos and organize them however you like.',
                duration: 5000
            },
            'meals-create': {
                title: '✍️ Add a Recipe',
                message: 'Write recipes like you\'d tell a friend. No fancy formatting needed!',
                duration: 5000
            },
            'planner': {
                title: '📅 Plan Your Week',
                message: 'Pick recipes from your collection and assign them to days. Then generate a shopping list.',
                duration: 5000
            },
            'shopping': {
                title: '🛒 Shopping List',
                message: 'Check items off as you shop. No more forgetting anything!',
                duration: 5000
            }
        };

        if (tips[page] && this.isFirstTime()) {
            setTimeout(() => {
                new Toast(`${tips[page].title} - ${tips[page].message}`, 'info', tips[page].duration);
            }, 1000);
        }
    }

    /**
     * Reset all onboarding data (for testing)
     */
    reset() {
        Storage.remove(this.SEEN_KEY);
        Storage.remove(this.HOUSEHOLD_CREATED_KEY);
        Storage.remove(this.RECIPE_ADDED_KEY);
        Storage.remove(this.WEEK_PLANNED_KEY);
    }
}

// Global instance
window.onboarding = new Onboarding();

// Initialize on load
document.addEventListener('DOMContentLoaded', function() {
    // Show welcome message for first-time users
    onboarding.showWelcome();

    // Log progress
    const progress = onboarding.getProgress();
    if (progress > 0 && progress < 100) {
        console.log(`Setup progress: ${progress}%`);
    }
});

console.log('✓ Onboarding.js loaded');
