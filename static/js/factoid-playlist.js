/**
 * Enhanced Factoid System v2.0
 * JavaScript playlist manager with 3D flip animations
 */

class FactoidPlaylist {
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            autoPlay: true,
            duration: 6000,
            apiBaseUrl: '/api',
            enableFlipAnimation: true,
            enableInteractions: true,
            maxRetries: 3,
            ...options
        };
        
        this.factoids = [];
        this.currentIndex = 0;
        this.isPlaying = false;
        this.isFlipping = false;
        this.intervalId = null;
        this.retryCount = 0;
        
        this.init();
    }

    /**
     * Initialize the factoid playlist
     */
    async init() {
        try {
            this.createHTML();
            await this.loadFactoids();
            this.bindEvents();
            
            if (this.factoids.length > 0) {
                this.showFactoid(0);
                if (this.options.autoPlay) {
                    this.play();
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
     * Create the HTML structure for the factoid
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
        const url = `${this.options.apiBaseUrl}/factoids/${counterSlug}/${councilSlug}/${urlSafeYear}/`;
        
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || 'API returned unsuccessful response');
            }
            
            this.factoids = data.factoids || [];
            this.createIndicators();
            this.retryCount = 0; // Reset retry count on success
            
        } catch (error) {
            console.error('Failed to load factoids:', error);
            
            // Retry logic
            if (this.retryCount < this.options.maxRetries) {
                this.retryCount++;
                console.log(`Retrying factoid load (attempt ${this.retryCount}/${this.options.maxRetries})`);
                setTimeout(() => this.loadFactoids(), 1000 * this.retryCount);
                return;
            }
            
            // Fallback to legacy factoids if available
            await this.tryLegacyFactoids();
        }
    }

    /**
     * Try to load legacy factoids as fallback
     */
    async tryLegacyFactoids() {
        const counterSlug = this.container.dataset.counter;
        const scriptId = `factoids-${counterSlug}`;
        const script = document.getElementById(scriptId);
        
        if (script) {
            try {
                const legacyFactoids = JSON.parse(script.textContent);
                this.factoids = legacyFactoids.map(fact => ({
                    type: 'legacy',
                    text: fact.text || fact,
                    emoji: '📊',
                    color: 'blue',
                    animation_duration: 6000,
                    flip_animation: true,
                    priority: 50,
                    is_relevant: true
                }));
                this.createIndicators();
                console.log('Loaded legacy factoids as fallback');
            } catch (error) {
                console.error('Failed to parse legacy factoids:', error);
                this.factoids = [];
            }
        }
    }

    /**
     * Create indicator dots for each factoid
     */
    createIndicators() {
        if (!this.indicators || this.factoids.length <= 1) return;
        
        this.indicators.innerHTML = this.factoids
            .map((_, index) => 
                `<button class="factoid-indicator" 
                         role="tab" 
                         aria-label="View factoid ${index + 1}"
                         data-index="${index}"></button>`
            )
            .join('');
    }

    /**
     * Bind event listeners
     */
    bindEvents() {
        // Card click for manual flip
        if (this.cardElement) {
            this.cardElement.addEventListener('click', () => {
                if (this.options.enableFlipAnimation && !this.isFlipping) {
                    this.flipCard();
                }
            });
            
            // Keyboard navigation
            this.cardElement.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    if (this.options.enableFlipAnimation && !this.isFlipping) {
                        this.flipCard();
                    }
                } else if (e.key === 'ArrowLeft') {
                    e.preventDefault();
                    this.previous();
                } else if (e.key === 'ArrowRight') {
                    e.preventDefault();
                    this.next();
                }
            });
        }

        // Control buttons
        if (this.controls) {
            const playPauseBtn = this.controls.querySelector('.play-pause-btn');
            const nextBtn = this.controls.querySelector('.next-btn');
            
            if (playPauseBtn) {
                playPauseBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.togglePlayPause();
                });
            }
            
            if (nextBtn) {
                nextBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.next();
                });
            }
        }

        // Indicators
        if (this.indicators) {
            this.indicators.addEventListener('click', (e) => {
                if (e.target.classList.contains('factoid-indicator')) {
                    const index = parseInt(e.target.dataset.index);
                    this.showFactoid(index);
                }
            });
        }

        // Pause on hover
        this.container.addEventListener('mouseenter', () => {
            if (this.isPlaying) {
                this.pause(true);
            }
        });
        
        this.container.addEventListener('mouseleave', () => {
            if (this.isPlaying) {
                this.resume();
            }
        });
    }

    /**
     * Show a specific factoid
     */
    async showFactoid(index, animate = true) {
        if (index < 0 || index >= this.factoids.length) return;
        
        const factoid = this.factoids[index];
        this.currentIndex = index;
        
        // Simple fade transition for TV news style
        if (animate) {
            this.factoidContainer.style.opacity = '0';
            setTimeout(() => {
                this.updateFactoidContent(factoid);
                this.factoidContainer.style.opacity = '1';
            }, 200);
        } else {
            this.updateFactoidContent(factoid);
        }
        
        // Auto-advance to next factoid after duration
        if (this.options.autoPlay && factoid.animation_duration) {
            setTimeout(() => {
                this.next();
            }, factoid.animation_duration);
        }
    }

    /**
     * Flip card animation to show new factoid
     */
    async flipToFactoid(factoid) {
        if (this.isFlipping) return;
        
        this.isFlipping = true;
        
        // Prepare back face with new content
        this.updateFactoidContent(this.backFace, factoid);
        
        // Start flip animation
        this.cardElement.classList.add('flipping');
        
        return new Promise(resolve => {
            setTimeout(() => {
                // Update front face and card appearance
                this.updateFactoidContent(this.frontFace, factoid);
                this.updateCardAppearance(factoid);
                
                // Reset flip
                this.cardElement.classList.remove('flipping');
                
                setTimeout(() => {
                    this.isFlipping = false;
                    resolve();
                }, 100);
            }, 400);
        });
    }

    /**
     * Manual flip card for interaction
     */
    async flipCard() {
        if (this.isFlipping) return;
        
        this.isFlipping = true;
        this.cardElement.classList.add('flipping');
        
        setTimeout(() => {
            this.cardElement.classList.remove('flipping');
            setTimeout(() => {
                this.isFlipping = false;
            }, 100);
        }, 800);
    }

    /**
     * Update factoid content in a face element
     */
    updateFactoidContent(factoid) {
        const emoji = factoid.emoji || '📊';
        const text = factoid.text || 'No data available';
        const color = factoid.color || 'blue';
        
        this.factoidContainer.innerHTML = `
            <div class="factoid-text" data-color="${color}">
                <span class="factoid-emoji" role="img" aria-hidden="true">${emoji}</span>
                ${text}
            </div>
        `;
    }

    /**
     * Update card appearance based on factoid properties
     */
    updateCardAppearance(factoid) {
        const color = factoid.color || 'blue';
        this.cardElement.setAttribute('data-color', color);
        
        // Update aria-label for accessibility
        this.cardElement.setAttribute('aria-label', 
            `Factoid: ${factoid.text?.replace(/<[^>]*>/g, '') || 'Loading...'}`
        );
    }

    /**
     * Update indicator states
     */
    updateIndicators() {
        if (!this.indicators) return;
        
        const indicators = this.indicators.querySelectorAll('.factoid-indicator');
        indicators.forEach((indicator, index) => {
            indicator.classList.toggle('active', index === this.currentIndex);
            indicator.setAttribute('aria-selected', index === this.currentIndex ? 'true' : 'false');
        });
    }

    /**
     * Start automatic playback
     */
    play() {
        if (this.factoids.length <= 1) return;
        
        this.pause();
        this.isPlaying = true;
        
        const currentFactoid = this.factoids[this.currentIndex];
        const duration = currentFactoid?.animation_duration || this.options.duration;
        
        this.intervalId = setInterval(() => {
            this.next();
        }, duration);
        
        this.updatePlayPauseButton();
    }

    /**
     * Pause automatic playback
     */
    pause(temporary = false) {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
        
        if (!temporary) {
            this.isPlaying = false;
            this.updatePlayPauseButton();
        }
    }

    /**
     * Resume automatic playback
     */
    resume() {
        if (this.isPlaying && !this.intervalId) {
            this.play();
        }
    }

    /**
     * Toggle play/pause state
     */
    togglePlayPause() {
        if (this.isPlaying) {
            this.pause();
        } else {
            this.play();
        }
    }

    /**
     * Go to next factoid
     */
    next() {
        const nextIndex = (this.currentIndex + 1) % this.factoids.length;
        this.showFactoid(nextIndex);
    }

    /**
     * Go to previous factoid
     */
    previous() {
        const prevIndex = (this.currentIndex - 1 + this.factoids.length) % this.factoids.length;
        this.showFactoid(prevIndex);
    }

    /**
     * Update play/pause button appearance
     */
    updatePlayPauseButton() {
        const btn = this.container.querySelector('.play-pause-btn');
        if (btn) {
            btn.innerHTML = this.isPlaying ? '⏸️' : '▶️';
            btn.setAttribute('aria-label', this.isPlaying ? 'Pause factoids' : 'Play factoids');
            btn.setAttribute('title', this.isPlaying ? 'Pause' : 'Play');
        }
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
     * Destroy the playlist and clean up
     */
    destroy() {
        this.pause();
        if (this.container) {
            this.container.innerHTML = '';
        }
    }

    /**
     * Refresh factoids from API
     */
    async refresh() {
        this.pause();
        this.createHTML();
        await this.loadFactoids();
        
        if (this.factoids.length > 0) {
            this.showFactoid(0);
            if (this.options.autoPlay) {
                this.play();
            }
        } else {
            this.showEmptyState();
        }
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
    // Auto-initialize factoid containers
    createFactoidPlaylist('.counter-factoid[data-counter]', {
        autoPlay: true,
        duration: 6000,
        enableFlipAnimation: true,
        enableInteractions: true
    });
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { FactoidPlaylist, createFactoidPlaylist };
}