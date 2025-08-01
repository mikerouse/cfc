/**
 * Site-wide Factoid Display System
 * 
 * Displays AI-generated cross-council comparisons at the top of the homepage.
 * Uses GOV.UK notification banner style similar to council detail pages.
 */

class SitewideFactoidDisplay {
    constructor(options = {}) {
        this.options = {
            apiEndpoint: '/api/factoids/sitewide/',
            refreshInterval: 300000, // 5 minutes
            displayDuration: 12000, // 12 seconds per factoid
            maxRetries: 3,
            animationDuration: 600,
            ...options
        };
        
        this.factoids = [];
        this.currentIndex = 0;
        this.timeoutId = null;
        this.refreshTimeoutId = null;
        this.retryCount = 0;
        this.isVisible = false;
        this.container = null;
        
        this.init();
    }

    /**
     * Initialize the site-wide factoid display system
     */
    async init() {
        try {
            console.log('🔍 Initializing site-wide factoid display');
            
            // Find the factoid container
            this.container = document.querySelector('.sitewide-ai-factoid-playlist');
            
            if (!this.container) {
                console.warn('⚠️ Site-wide factoid container not found on this page');
                return;
            }
            
            // Get references to state elements
            this.setupStateElements();
            
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
     * Setup references to state elements within the container
     */
    setupStateElements() {
        if (!this.container) return;
        
        this.elements = {
            loadingSpinner: this.container.querySelector('.loading-spinner'),
            loadingText: this.container.querySelector('.loading-text'),
            factoidContent: this.container.querySelector('.factoid-content'),
            factoidText: this.container.querySelector('.factoid-text'),
            errorState: this.container.querySelector('.error-state'),
            emptyState: this.container.querySelector('.empty-state')
        };
        
        console.log('✅ State elements setup complete');
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
        if (this.factoids.length === 0 || !this.container) return;
        
        // Hide loading state
        this.hideLoadingState();
        
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
        if (!this.factoids[index] || !this.elements) return;
        
        const factoid = this.factoids[index];
        this.currentIndex = index;
        
        // Hide all states first
        this.hideAllStates();
        
        // Update content
        if (this.elements.factoidText) {
            this.elements.factoidText.innerHTML = factoid.text;
        }
        
        // Show factoid content with fade-in effect
        if (this.elements.factoidContent) {
            this.elements.factoidContent.classList.remove('hidden');
            this.elements.factoidContent.style.opacity = '0';
            
            // Also ensure factoid text is visible
            if (this.elements.factoidText) {
                this.elements.factoidText.style.opacity = '0';
                this.elements.factoidText.style.transform = 'translateY(20px)';
            }
            
            // Fade in
            setTimeout(() => {
                this.elements.factoidContent.style.transition = 'opacity 0.6s ease-in-out';
                this.elements.factoidContent.style.opacity = '1';
                
                // Animate factoid text
                if (this.elements.factoidText) {
                    this.elements.factoidText.style.transition = 'opacity 0.6s ease-in-out, transform 0.6s ease-in-out';
                    this.elements.factoidText.style.opacity = '1';
                    this.elements.factoidText.style.transform = 'translateY(0)';
                }
                
                this.isVisible = true;
            }, 50);
        }
        
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
        
        // Fade out current factoid
        if (this.elements.factoidContent) {
            this.elements.factoidContent.style.opacity = '0';
        }
        
        // Also fade out factoid text
        if (this.elements.factoidText) {
            this.elements.factoidText.style.opacity = '0';
            this.elements.factoidText.style.transform = 'translateY(-10px)';
        }
        
        // Show next factoid after fade out
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
     * Hide loading state
     */
    hideLoadingState() {
        if (this.elements.loadingSpinner) {
            this.elements.loadingSpinner.classList.add('hidden');
        }
        if (this.elements.loadingText) {
            this.elements.loadingText.classList.add('hidden');
        }
    }

    /**
     * Hide all states
     */
    hideAllStates() {
        if (this.elements.loadingSpinner) this.elements.loadingSpinner.classList.add('hidden');
        if (this.elements.loadingText) this.elements.loadingText.classList.add('hidden');
        if (this.elements.errorState) this.elements.errorState.classList.add('hidden');
        if (this.elements.emptyState) this.elements.emptyState.classList.add('hidden');
        if (this.elements.factoidContent) this.elements.factoidContent.classList.add('hidden');
    }

    /**
     * Show error state
     */
    showErrorState() {
        if (!this.elements) return;
        
        this.hideAllStates();
        
        if (this.elements.errorState) {
            this.elements.errorState.classList.remove('hidden');
        }
        
        console.log('❌ Showing error state');
    }

    /**
     * Show empty state
     */
    showEmptyState() {
        if (!this.elements) return;
        
        this.hideAllStates();
        
        if (this.elements.emptyState) {
            this.elements.emptyState.classList.remove('hidden');
        }
        
        console.log('📭 Showing empty state');
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
        
        console.log('🗑️ Site-wide factoid display destroyed');
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize if the site-wide factoid container is present
    if (document.querySelector('.sitewide-ai-factoid-playlist')) {
        window.sitewideFactoidDisplay = new SitewideFactoidDisplay();
    }
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SitewideFactoidDisplay;
}