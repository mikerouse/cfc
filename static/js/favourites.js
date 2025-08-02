/**
 * Favourites Management System
 * 
 * Handles adding/removing councils from user's favourites
 * using the existing My Lists functionality
 */

class FavouritesManager {
    constructor() {
        this.initializeFavouriteButtons();
    }
    
    initializeFavouriteButtons() {
        // Initialize favourite buttons on page load
        console.log('🔍 FavouritesManager: Looking for favourite-btn element');
        const favouriteBtn = document.getElementById('favourite-btn');
        console.log('🔍 FavouritesManager: favourite-btn element found:', favouriteBtn);
        if (favouriteBtn) {
            console.log('✅ FavouritesManager: Initializing favourite button');
            this.updateFavouriteButton(favouriteBtn);
            favouriteBtn.addEventListener('click', (e) => {
                console.log('🖱️ FavouritesManager: Button clicked!', e);
                this.toggleFavourite(e.target.closest('button'));
            });
        } else {
            console.log('❌ FavouritesManager: No favourite-btn element found');
        }
    }
    
    async toggleFavourite(button) {
        const councilSlug = button.dataset.slug;
        const isFavourited = button.dataset.favourited === 'true';
        
        // Show loading state
        const originalContent = button.innerHTML;
        button.disabled = true;
        button.innerHTML = `
            <svg class="w-4 h-4 mr-2 animate-spin flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
            </svg>
            <span>${isFavourited ? 'Removing...' : 'Adding...'}</span>
        `;
        
        try {
            let response;
            
            if (isFavourited) {
                // Remove from favourites
                response = await fetch('/lists/favourites/remove/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCSRFToken()
                    },
                    body: JSON.stringify({
                        council_slug: councilSlug
                    })
                });
            } else {
                // Add to favourites
                response = await fetch('/lists/favourites/add/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCSRFToken()
                    },
                    body: JSON.stringify({
                        council_slug: councilSlug
                    })
                });
            }
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    // Update button state
                    button.dataset.favourited = (!isFavourited).toString();
                    this.updateFavouriteButton(button);
                    
                    // Show success message
                    this.showNotification(
                        isFavourited ? 'Removed from favourites' : 'Added to favourites',
                        'success'
                    );
                } else {
                    throw new Error(data.error || 'Operation failed');
                }
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
        } catch (error) {
            console.error('Favourites operation failed:', error);
            this.showNotification(
                'Failed to update favourites. Please try again.',
                'error'
            );
            
            // Restore original content
            button.innerHTML = originalContent;
        } finally {
            button.disabled = false;
        }
    }
    
    updateFavouriteButton(button) {
        const isFavourited = button.dataset.favourited === 'true';
        
        if (isFavourited) {
            button.innerHTML = `
                <svg class="w-4 h-4 mr-2 flex-shrink-0" fill="currentColor" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/>
                </svg>
                <span>Remove from Favourites</span>
            `;
            button.classList.add('gov-uk-button--warning');
            button.classList.remove('gov-uk-button--secondary');
        } else {
            button.innerHTML = `
                <svg class="w-4 h-4 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/>
                </svg>
                <span>Add to Favourites</span>
            `;
            button.classList.add('gov-uk-button--secondary');
            button.classList.remove('gov-uk-button--warning');
        }
    }
    
    getCSRFToken() {
        // Get CSRF token from cookie or meta tag
        const token = document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
                     document.querySelector('meta[name=csrf-token]')?.content ||
                     this.getCookie('csrftoken');
        return token;
    }
    
    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    showNotification(message, type = 'success') {
        // Create and show a temporary notification
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg transition-all duration-300 ${
            type === 'success' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
        }`;
        notification.innerHTML = `
            <div class="flex items-center">
                <svg class="w-5 h-5 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    ${type === 'success' 
                        ? '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>'
                        : '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>'
                    }
                </svg>
                <span>${message}</span>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
            notification.style.opacity = '1';
        }, 100);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            notification.style.opacity = '0';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new FavouritesManager();
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FavouritesManager;
}