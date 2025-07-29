/**
 * Minimal Factoid System - TV News Style
 * Simple playlist manager with smooth transitions
 */

class FactoidPlaylist {
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            autoPlay: true,
            duration: 8000, // 8 seconds per factoid for better readability
            apiBaseUrl: '/api',
            maxRetries: 3,
            ...options
        };
        
        this.factoids = [];
        this.currentIndex = 0;
        this.timeoutId = null;
        this.retryCount = 0;
        this.isTransitioning = false;
        
        this.init();
    }

    /**
     * Initialize the factoid playlist
     */
    async init() {
        try {
            this.createHTML();
            
            // Check for "no data" state first - this takes priority over factoids
            if (this.hasNoData()) {
                this.showContributionPrompt();
                return;
            }
            
            await this.loadFactoids();
            
            if (this.factoids.length > 0) {
                this.showFactoid(0, false);
                if (this.options.autoPlay && this.factoids.length > 1) {
                    this.startCycling();
                }
            } else {
                this.showEmptyState();
            }
        } catch (error) {
            console.error('FactoidPlaylist initialization failed:', error);
            this.showError('Failed to initialize factoids');
        }
    }

    /**
     * Create the simple HTML structure
     */
    createHTML() {
        const counterSlug = this.container.dataset.counter;
        const councilSlug = this.container.dataset.council;
        const year = this.container.dataset.year;
        
        // Debug logging when needed
        if (window.DEBUG) {
            console.log('FactoidPlaylist Debug Info:', {
                container: this.container,
                counterSlug: counterSlug,
                councilSlug: councilSlug,
                year: year,
                dataset: this.container.dataset,
                attributes: Array.from(this.container.attributes).map(attr => ({name: attr.name, value: attr.value}))
            });
        }
        
        if (!counterSlug || !councilSlug || !year) {
            console.error('Missing data attributes:', {counterSlug, councilSlug, year});
            throw new Error('Missing required data attributes: counter, council, year');
        }

        this.container.innerHTML = `
            <div class="factoid-container">
                <div class="factoid-loading">
                    <div class="factoid-spinner"></div>
                    Loading factoids...
                </div>
            </div>
        `;

        this.factoidContainer = this.container.querySelector('.factoid-container');
    }

    /**
     * Load factoids from the API
     */
    async loadFactoids() {
        const counterSlug = this.container.dataset.counter;
        const councilSlug = this.container.dataset.council;
        const year = this.container.dataset.year;
        
        // Replace forward slash with dash for URL compatibility  
        const urlSafeYear = year.replace(/\//g, '-');
        
        // Add force_refresh parameter if this is a refresh (not initial load)
        const forceRefresh = this.container.dataset.forceRefresh === 'true';
        const refreshParam = forceRefresh ? '?force_refresh=true' : '';
        const url = `${this.options.apiBaseUrl}/factoids/counter/${counterSlug}/${councilSlug}/${urlSafeYear}/${refreshParam}`;
        
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || 'API returned unsuccessful response');
            }

            // Transform API response to expected format
            this.factoids = (data.factoids || []).map(factoid => ({
                text: factoid.rendered_text,
                emoji: factoid.emoji || '📊',
                color: factoid.color || 'blue',
                id: factoid.id,
                template_name: factoid.template_name,
                relevance_score: factoid.relevance_score
            }));
            this.retryCount = 0;        } catch (error) {
            console.error('Failed to load factoids:', error);
            
            if (this.retryCount < this.options.maxRetries) {
                this.retryCount++;
                console.log(`Retrying factoid load (attempt ${this.retryCount}/${this.options.maxRetries})`);
                setTimeout(() => {
                    this.loadFactoids().then(() => {
                        if (this.factoids.length > 0) {
                            this.showFactoid(0, false);
                            if (this.options.autoPlay && this.factoids.length > 1) {
                                this.startCycling();
                            }
                        } else {
                            this.showEmptyState();
                        }
                    }).catch(() => {
                        this.showError('Failed to load factoids');
                    });
                }, 2000 * this.retryCount);
                return;
            }
            
            // Fallback to legacy factoids if available
            console.log('Loaded legacy factoids as fallback');
            this.factoids = this.loadLegacyFactoids();
            if (this.factoids.length === 0) {
                throw error;
            }
        }
    }

    /**
     * Show a specific factoid with slide-up animation
     */
    async showFactoid(index, animate = true) {
        if (index < 0 || index >= this.factoids.length || this.isTransitioning) return;
        
        const factoid = this.factoids[index];
        this.currentIndex = index;
        
        if (animate && this.factoidContainer) {
            this.isTransitioning = true;
            
            const currentFactoid = this.factoidContainer.querySelector('.factoid-text');
            
            if (currentFactoid) {
                // Slide out current factoid
                currentFactoid.classList.add('slide-out');
                
                setTimeout(() => {
                    this.updateFactoidContent(factoid);
                    const newFactoid = this.factoidContainer.querySelector('.factoid-text');
                    if (newFactoid) {
                        // Slide in new factoid
                        newFactoid.classList.add('slide-in');
                    }
                    
                    setTimeout(() => {
                        this.isTransitioning = false;
                    }, 600); // Match CSS animation duration
                }, 400); // Match slide-out duration
            } else {
                // First factoid - just slide in
                this.updateFactoidContent(factoid);
                const newFactoid = this.factoidContainer.querySelector('.factoid-text');
                if (newFactoid) {
                    newFactoid.classList.add('slide-in');
                }
                
                setTimeout(() => {
                    this.isTransitioning = false;
                }, 600);
            }
        } else {
            this.updateFactoidContent(factoid);
            // For initial load, add slide-in class without animation guard
            const newFactoid = this.factoidContainer.querySelector('.factoid-text');
            if (newFactoid) {
                newFactoid.classList.add('slide-in');
            }
        }
    }

    /**
     * Update factoid content
     */
    updateFactoidContent(factoid) {
        const emoji = factoid.emoji || '📊';
        const text = factoid.text || 'No data available';
        const color = factoid.color || 'blue';
        
        // Simple markdown processing for bold text
        const processedText = this.processMarkdown(text);
        
        this.factoidContainer.innerHTML = `
            <div class="factoid-text" data-color="${color}">
                <span class="factoid-emoji" role="img" aria-hidden="true">${emoji}</span>
                ${processedText}
            </div>
        `;
    }

    /**
     * Simple markdown processing for factoid text
     */
    processMarkdown(text) {
        // Convert **bold** to <strong>bold</strong>
        return text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    }

    /**
     * Start the cycling through factoids
     */
    startCycling() {
        this.stopCycling(); // Clear any existing cycle
        
        if (this.factoids.length > 1) {
            this.timeoutId = setTimeout(() => {
                this.nextFactoid();
            }, this.options.duration);
        }
    }

    /**
     * Stop the cycling
     */
    stopCycling() {
        if (this.timeoutId) {
            clearTimeout(this.timeoutId);
            this.timeoutId = null;
        }
    }

    /**
     * Go to next factoid
     */
    nextFactoid() {
        if (this.factoids.length <= 1) return;
        
        const nextIndex = (this.currentIndex + 1) % this.factoids.length;
        this.showFactoid(nextIndex);
        
        // Schedule the next transition
        this.startCycling();
    }

    /**
     * Load legacy factoids as fallback
     */
    loadLegacyFactoids() {
        const scriptId = `factoids-${this.container.dataset.counter}`;
        const scriptElement = document.getElementById(scriptId);
        
        if (scriptElement) {
            try {
                const data = JSON.parse(scriptElement.textContent);
                return Array.isArray(data) ? data : [];
            } catch (error) {
                console.error('Failed to parse legacy factoids:', error);
            }
        }
        
        return [];
    }

    /**
     * Show error state
     */
    showError(message) {
        this.container.innerHTML = `
            <div class="factoid-container">
                <div class="factoid-error">
                    <span class="factoid-error-icon">⚠️</span>
                    ${message}
                </div>
            </div>
        `;
    }

    /**
     * Check if counter has no data
     */
    hasNoData() {
        // Find the actual counter container (parent of the factoid div)
        const counterContainer = this.container.parentElement?.closest('[data-counter]');
        const counterValue = counterContainer?.querySelector('.counter-value');
        
        // Multiple ways to detect "No data" state
        const noData = counterValue && (
            counterValue.textContent.trim() === 'No data' ||
            !counterValue.hasAttribute('data-value') ||
            counterValue.dataset.value === 'null' ||
            counterValue.dataset.value === '' ||
            counterValue.dataset.value === undefined
        );
        
        return noData;
    }

    /**
     * Show empty state when no factoids are available
     */
    showEmptyState() {
        this.container.innerHTML = `
            <div class="factoid-container">
                <div class="factoid-empty">
                    No factoids available
                </div>
            </div>
        `;
    }

    /**
     * Show contribution prompt when counter has no data
     */
    showContributionPrompt() {
        const councilSlug = this.container.dataset.council;
        const editUrl = `/council/${councilSlug}/?tab=edit`;
        
        this.container.innerHTML = `
            <div class="factoid-container">
                <div class="contribution-prompt">
                    <a href="${editUrl}" class="contribution-link">
                        <span class="contribution-text">Contribute this data</span>
                        <span class="contribution-points">+2pts</span>
                    </a>
                </div>
            </div>
        `;
    }

    /**
     * Destroy the playlist and clean up
     */
    destroy() {
        this.stopCycling();
        this.container.innerHTML = '';
    }
}

/**
 * Factory function to create factoid playlists
 */
function createFactoidPlaylist(selector, options = {}) {
    const containers = document.querySelectorAll(selector);
    const playlists = [];
    
    containers.forEach(container => {
        try {
            const playlist = new FactoidPlaylist(container, options);
            // Store reference on container for later access
            container._factoidPlaylist = playlist;
            playlists.push(playlist);
        } catch (error) {
            console.error('Failed to create factoid playlist:', error);
        }
    });
    
    return playlists;
}

/**
 * Initialize factoid playlists when DOM is ready
 */
document.addEventListener('DOMContentLoaded', function() {
    // Delay initialization slightly to ensure counter values are loaded
    setTimeout(() => {
        // Auto-initialize factoid containers
        createFactoidPlaylist('.counter-factoid[data-counter]', {
            autoPlay: true,
            duration: 8000, // 8 seconds for better readability
            enableFlipAnimation: false,
            enableInteractions: false
        });
    }, 100); // Small delay to ensure counter values are populated
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { FactoidPlaylist, createFactoidPlaylist };
}