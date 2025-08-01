/**
 * Site-wide Factoid Display System
 * 
 * Displays AI-generated cross-council comparisons on the homepage.
 * Integrates with existing counter display but shows site-wide insights.
 */

class SitewideFactoidDisplay {
    constructor(options = {}) {
        this.options = {
            apiEndpoint: '/api/factoids/sitewide/',
            refreshInterval: 300000, // 5 minutes
            displayDuration: 10000, // 10 seconds per factoid
            maxRetries: 3,
            animationDuration: 500,
            ...options
        };
        
        this.factoids = [];
        this.currentIndex = 0;
        this.timeoutId = null;
        this.refreshTimeoutId = null;
        this.retryCount = 0;
        this.isVisible = false;
        this.displayContainers = [];
        
        this.init();
    }

    /**
     * Initialize the site-wide factoid display system
     */
    async init() {
        try {
            console.log('🔍 Initializing site-wide factoid display');
            
            // Create display containers
            this.createDisplayContainers();
            
            // Load initial factoids
            await this.loadFactoids();
            
            // Start display cycle if factoids are available
            if (this.factoids.length > 0) {
                this.startDisplayCycle();
                this.scheduleRefresh();
            } else {
                this.showEmptyState();
            }
            
        } catch (error) {
            console.error('❌ Site-wide factoid display initialization failed:', error);
            this.showErrorState();
        }
    }

    /**
     * Create HTML containers for factoid display
     */
    createDisplayContainers() {  
        try {
            // Find all counter containers on homepage
            const counterContainers = document.querySelectorAll('#homepage-counters .counter-value');
            
            if (counterContainers.length === 0) {
                console.warn('⚠️ No counter containers found on homepage');
                return;
            }
            
            counterContainers.forEach(counterEl => {
                const container = counterEl.closest('[id^="counter-"]');
                if (!container) {
                    console.warn('⚠️ Counter element has no container parent');
                    return;
                }
            
            // Create factoid display area below the counter
            const factoidDisplay = document.createElement('div');
            factoidDisplay.className = 'sitewide-factoid-display mt-3 text-sm text-gray-600 min-h-[2.5rem] flex items-center justify-center';
            factoidDisplay.innerHTML = `
                <div class="factoid-content hidden opacity-0 transition-all duration-500 text-center">
                    <div class="factoid-text"></div>
                </div>
                <div class="loading-state text-gray-400">
                    <svg class="animate-spin h-4 w-4 mx-auto" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"/>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                    </svg>
                </div>
                <div class="error-state hidden text-red-500 text-xs">
                    Cross-council insights temporarily unavailable
                </div>
                <div class="empty-state hidden text-gray-400 text-xs">
                    Preparing cross-council comparisons...
                </div>
            `;
            
            // Insert after the counter value - find a good insertion point
            const counterValue = container.querySelector('.counter-value');
            if (counterValue && counterValue.parentNode === container) {
                // Insert after the counter value element
                const nextSibling = counterValue.nextElementSibling;
                if (nextSibling && nextSibling.parentNode === container) {
                    container.insertBefore(factoidDisplay, nextSibling);
                } else {
                    container.appendChild(factoidDisplay);
                }
            } else {
                // Fallback: just append to container
                container.appendChild(factoidDisplay);
            }
            });
            
            this.displayContainers = document.querySelectorAll('.sitewide-factoid-display');
            console.log(`✅ Created ${this.displayContainers.length} factoid display containers`);
            
        } catch (error) {
            console.error('❌ Error creating factoid display containers:', error);
            this.displayContainers = [];
        }
    }

    /**
     * Load factoids from the API
     */
    async loadFactoids() {
        try {
            const response = await fetch(`${this.options.apiEndpoint}?limit=5`);
            
            if (!response.ok) {
                throw new Error(`API request failed: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success && data.factoids && data.factoids.length > 0) {
                this.factoids = data.factoids;
                this.retryCount = 0; // Reset retry count on success
                
                console.log(`✅ Loaded ${this.factoids.length} site-wide factoids`);
                return true;
            } else {
                console.warn('⚠️ No factoids received from API');
                return false;
            }
            
        } catch (error) {
            console.error('❌ Failed to load site-wide factoids:', error);
            
            // Retry logic
            if (this.retryCount < this.options.maxRetries) {
                this.retryCount++;
                console.log(`🔄 Retrying... (${this.retryCount}/${this.options.maxRetries})`);
                
                // Exponential backoff
                const delay = Math.pow(2, this.retryCount) * 1000;
                setTimeout(() => this.loadFactoids(), delay);
            }
            
            return false;
        }
    }

    /**
     * Start the factoid display cycle
     */
    startDisplayCycle() {
        if (this.factoids.length === 0) return;
        
        // Hide loading states
        if (this.displayContainers && this.displayContainers.length > 0) {
            this.displayContainers.forEach(container => {
                const loadingState = container.querySelector('.loading-state');
                if (loadingState) loadingState.classList.add('hidden');
            });
        }
        
        // Show first factoid
        this.showFactoid(0);
        
        // Start cycling if multiple factoids
        if (this.factoids.length > 1) {
            this.timeoutId = setTimeout(() => {
                this.cycleTo(1);
            }, this.options.displayDuration);
        }
        
        console.log('✅ Started site-wide factoid display cycle');
    }

    /**
     * Display a specific factoid
     */
    showFactoid(index) {
        if (!this.factoids[index] || !this.displayContainers || this.displayContainers.length === 0) return;
        
        const factoid = this.factoids[index];
        this.currentIndex = index;
        
        this.displayContainers.forEach(container => {
            const contentEl = container.querySelector('.factoid-content');
            const textEl = container.querySelector('.factoid-text');
            
            if (!contentEl || !textEl) return;
            
            // Hide current content
            contentEl.classList.add('opacity-0');
            
            setTimeout(() => {
                // Update content
                textEl.innerHTML = factoid.text;
                
                // Show new content
                contentEl.classList.remove('hidden');
                contentEl.classList.remove('opacity-0');
                contentEl.classList.add('opacity-100');
                
                this.isVisible = true;
            }, this.options.animationDuration / 2);
        });
        
        console.log(`📰 Displaying factoid ${index + 1}/${this.factoids.length}: ${factoid.insight_type}`);
    }

    /**
     * Cycle to the next factoid
     */
    cycleTo(index) {
        if (!this.factoids[index]) {
            // Loop back to beginning
            index = 0;
        }
        
        // Clear existing timeout
        if (this.timeoutId) {
            clearTimeout(this.timeoutId);
            this.timeoutId = null;
        }
        
        // Hide current factoid with animation
        if (this.displayContainers && this.displayContainers.length > 0) {
            this.displayContainers.forEach(container => {
                const contentEl = container.querySelector('.factoid-content');
                if (contentEl) contentEl.classList.add('opacity-0');
            });
        }
        
        // Show next factoid after animation
        setTimeout(() => {
            this.showFactoid(index);
            
            // Schedule next cycle
            this.timeoutId = setTimeout(() => {
                this.cycleTo(index + 1);
            }, this.options.displayDuration);
        }, this.options.animationDuration);
    }

    /**
     * Schedule factoid refresh
     */
    scheduleRefresh() {
        this.refreshTimeoutId = setTimeout(async () => {
            console.log('🔄 Refreshing site-wide factoids');
            
            const success = await this.loadFactoids();
            if (success) {
                // Restart display cycle with new factoids
                this.startDisplayCycle();
            }
            
            // Schedule next refresh
            this.scheduleRefresh();
        }, this.options.refreshInterval);
    }

    /**
     * Show loading state
     */
    showLoadingState() {
        if (!this.displayContainers || this.displayContainers.length === 0) {
            return;
        }
        
        this.displayContainers.forEach(container => {
            const factoidContent = container.querySelector('.factoid-content');
            const loadingState = container.querySelector('.loading-state');
            const emptyState = container.querySelector('.empty-state');
            const errorState = container.querySelector('.error-state');
            
            if (factoidContent) factoidContent.classList.add('hidden');
            if (errorState) errorState.classList.add('hidden');
            if (emptyState) emptyState.classList.add('hidden');
            if (loadingState) loadingState.classList.remove('hidden');
        });
    }

    /**
     * Show error state
     */
    showErrorState() {
        if (!this.displayContainers || this.displayContainers.length === 0) {
            console.warn('⚠️ No display containers available for error state');
            return;
        }
        
        this.displayContainers.forEach(container => {
            const factoidContent = container.querySelector('.factoid-content');
            const loadingState = container.querySelector('.loading-state');
            const emptyState = container.querySelector('.empty-state');
            const errorState = container.querySelector('.error-state');
            
            if (factoidContent) factoidContent.classList.add('hidden');
            if (loadingState) loadingState.classList.add('hidden');
            if (emptyState) emptyState.classList.add('hidden');
            if (errorState) errorState.classList.remove('hidden');
        });
    }

    /**
     * Show empty state
     */
    showEmptyState() {
        if (!this.displayContainers || this.displayContainers.length === 0) {
            return;
        }
        
        this.displayContainers.forEach(container => {
            const factoidContent = container.querySelector('.factoid-content');
            const loadingState = container.querySelector('.loading-state');
            const errorState = container.querySelector('.error-state');
            const emptyState = container.querySelector('.empty-state');
            
            if (factoidContent) factoidContent.classList.add('hidden');
            if (loadingState) loadingState.classList.add('hidden');
            if (errorState) errorState.classList.add('hidden');
            if (emptyState) emptyState.classList.remove('hidden');
        });
    }

    /**
     * Cleanup and destroy the display system
     */
    destroy() {
        if (this.timeoutId) {
            clearTimeout(this.timeoutId);
            this.timeoutId = null;
        }
        
        if (this.refreshTimeoutId) {
            clearTimeout(this.refreshTimeoutId);
            this.refreshTimeoutId = null;
        }
        
        // Remove display containers
        if (this.displayContainers && this.displayContainers.length > 0) {
            this.displayContainers.forEach(container => {
                if (container && container.remove) {
                    container.remove();
                }
            });
        }
        
        console.log('🗑️ Site-wide factoid display destroyed');
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize on homepage with counters
    if (document.getElementById('homepage-counters')) {
        window.sitewideFactoidDisplay = new SitewideFactoidDisplay();
    }
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SitewideFactoidDisplay;
}