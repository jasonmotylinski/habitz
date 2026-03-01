/**
 * Shopping List - AJAX checkbox toggling
 */

document.addEventListener('DOMContentLoaded', function() {
    // Toggle shopping item checkbox
    $$('.shopping-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', function(e) {
            toggleShoppingItem(this, e);
        });
    });

    // Update progress bar on page load
    updateProgressBar();
});

/**
 * Toggle shopping item and update progress
 */
function toggleShoppingItem(checkbox, event) {
    const itemId = checkbox.getAttribute('data-item-id');
    const shoppingItem = checkbox.closest('.shopping-item');

    // Optimistic UI update
    const isChecked = checkbox.checked;
    shoppingItem.classList.toggle('checked', isChecked);
    shoppingItem.style.opacity = isChecked ? '0.6' : '1';

    // AJAX request to toggle on server
    fetch(window.SCRIPT_ROOT + `/shopping/item/${itemId}/toggle`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) throw new Error('Network response was not ok');
        return response.json();
    })
    .then(data => {
        if (!data.success) {
            // Revert on failure
            shoppingItem.classList.toggle('checked', !isChecked);
            checkbox.checked = !isChecked;
            shoppingItem.style.opacity = !isChecked ? '0.6' : '1';
            new Toast('Failed to update item', 'danger');
        } else {
            // Update progress bar
            updateProgressBar();

            // Optional: Move checked items to bottom after a brief delay
            setTimeout(() => {
                moveCheckedToBottom();
            }, 300);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        // Revert on error
        shoppingItem.classList.toggle('checked', !isChecked);
        checkbox.checked = !isChecked;
        shoppingItem.style.opacity = !isChecked ? '0.6' : '1';
        new Toast('Error updating item', 'danger');
    });
}

/**
 * Update progress bar
 */
function updateProgressBar() {
    const total = $$('.shopping-item').length;
    const checked = $$('.shopping-item.checked').length;
    const percent = total > 0 ? (checked / total) * 100 : 0;

    const progressBar = $('.progress-bar-fill');
    const progressText = $('.progress-text');

    if (progressBar) {
        progressBar.style.width = percent + '%';
    }

    if (progressText) {
        progressText.textContent = `${checked} of ${total} items`;
    }

    // Show celebration at 100%
    if (percent === 100 && total > 0) {
        celebrateCompletion();
    }
}

/**
 * Move checked items to bottom
 */
function moveCheckedToBottom() {
    const itemsContainer = $('.shopping-items');
    if (!itemsContainer) return;

    const checkedItems = $$('.shopping-item.checked');
    checkedItems.forEach(item => {
        itemsContainer.appendChild(item);
    });
}

/**
 * Celebrate when shopping list is complete
 */
function celebrateCompletion() {
    // Confetti effect
    createConfetti(window.innerWidth / 2, window.innerHeight / 2, 50);

    // Toast notification
    setTimeout(() => {
        new Toast('🎉 You\'ve completed your shopping list!', 'success', 5000);
    }, 200);
}

/**
 * Add new shopping item (if form exists)
 */
document.addEventListener('DOMContentLoaded', function() {
    const addItemForm = $('#addItemForm');
    if (addItemForm) {
        addItemForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const input = $('input[name="item"]');
            const itemName = input.value.trim();

            if (!itemName) {
                new Toast('Please enter an item name', 'warning');
                return;
            }

            // Show loading state
            setButtonLoading($('button[type="submit"]'), true);

            fetch(window.SCRIPT_ROOT + '/shopping/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: new URLSearchParams({ 'item': itemName })
            })
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    // Clear input
                    input.value = '';

                    // Add new item to list
                    const newItem = createShoppingItemElement(data.item);
                    const itemsContainer = $('.shopping-items');
                    if (itemsContainer) {
                        itemsContainer.insertBefore(newItem, itemsContainer.firstChild);
                    }

                    new Toast('Item added!', 'success');
                    updateProgressBar();
                } else {
                    new Toast(data.message || 'Failed to add item', 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                new Toast('Error adding item', 'danger');
            })
            .finally(() => {
                setButtonLoading($('button[type="submit"]'), false);
            });
        });
    }
});

/**
 * Create shopping item HTML element
 */
function createShoppingItemElement(item) {
    const li = document.createElement('li');
    li.className = 'shopping-item';
    li.innerHTML = `
        <div class="shopping-checkbox" data-item-id="${item.id}"></div>
        <span class="item-text">${item.name}</span>
        ${item.quantity ? `<span class="item-quantity">${item.quantity}</span>` : ''}
    `;

    // Add event listener to new checkbox
    const checkbox = li.querySelector('.shopping-checkbox');
    checkbox.addEventListener('change', function(e) {
        toggleShoppingItem(checkbox, e);
    });

    return li;
}

/**
 * Delete shopping item
 */
function deleteItem(itemId, event) {
    event.preventDefault();

    if (!confirm('Remove this item from the list?')) {
        return;
    }

    const shoppingItem = event.target.closest('.shopping-item');

    // Optimistic UI update - fade out
    shoppingItem.style.opacity = '0.5';
    shoppingItem.style.pointerEvents = 'none';

    // AJAX request to delete on server
    fetch(window.SCRIPT_ROOT + `/shopping/item/${itemId}/delete`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) throw new Error('Network response was not ok');
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Animate removal
            shoppingItem.style.transform = 'translateX(100%)';
            shoppingItem.style.transition = 'all 0.3s ease';

            setTimeout(() => {
                shoppingItem.remove();
                updateProgressBar();
                new Toast('Item removed', 'success');
            }, 300);
        } else {
            // Revert on failure
            shoppingItem.style.opacity = '1';
            shoppingItem.style.pointerEvents = 'auto';
            new Toast(data.message || 'Failed to remove item', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        // Revert on error
        shoppingItem.style.opacity = '1';
        shoppingItem.style.pointerEvents = 'auto';
        new Toast('Error removing item', 'danger');
    });
}

console.log('✓ Shopping.js loaded');
