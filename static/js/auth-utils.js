/**
 * Authentication Utilities
 * 
 * Shared authentication helper functions used across the application
 * to eliminate code duplication and ensure consistent behavior.
 */

(function(window) {
    'use strict';

    /**
     * Check if the current user is authenticated
     * Uses multiple detection methods for reliability
     * 
     * @returns {boolean} True if user is authenticated, false otherwise
     */
    function checkAuthentication() {
        // Use Django-provided authentication status if available
        if (window.djangoContext && typeof window.djangoContext.isAuthenticated === 'boolean') {
            return window.djangoContext.isAuthenticated;
        }
        
        // Fallback: Check if user is authenticated by looking for authenticated user indicators
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        const logoutLink = document.querySelector('a[href*="logout"]');
        const userDropdown = document.querySelector('.user-dropdown, [data-dropdown="user"]');
        const authUserElement = document.querySelector('.auth-user, .user-info');
        
        // If we have CSRF token and logout link, user is likely authenticated
        return !!(csrfToken && csrfToken.value && logoutLink) || 
               !!(userDropdown || authUserElement);
    }

    /**
     * Show login prompt modal for unauthenticated users
     * Provides consistent login/registration flow across the application
     * 
     * @param {string} action - Description of the action requiring authentication
     */
    function showLoginPrompt(action) {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white rounded-xl max-w-md w-full mx-4 p-6">
                <div class="text-center">
                    <div class="mx-auto w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mb-4">
                        <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
                        </svg>
                    </div>
                    <h3 class="text-lg font-semibold text-gray-900 mb-2">Sign in required</h3>
                    <p class="text-gray-600 mb-6">You need to be logged in to ${action}.</p>
                    
                    <div class="space-y-3">
                        <a href="/login/" class="block w-full bg-blue-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-blue-700 transition-colors">
                            Log In
                        </a>
                        <a href="/register/" class="block w-full border border-gray-300 text-gray-700 py-2 px-4 rounded-lg font-medium hover:bg-gray-50 transition-colors">
                            Create Account
                        </a>
                        <button onclick="this.closest('.fixed').remove()" 
                                class="block w-full text-gray-500 hover:text-gray-700 transition-colors">
                            Cancel
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Close on backdrop click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }

    // Export functions to the global window object for use by any script
    window.checkAuthentication = checkAuthentication;
    window.showLoginPrompt = showLoginPrompt;

    // Also create an AuthUtils object for more structured access
    window.AuthUtils = {
        checkAuthentication: checkAuthentication,
        showLoginPrompt: showLoginPrompt
    };

})(window);