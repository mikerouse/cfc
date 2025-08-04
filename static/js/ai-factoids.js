/**
 * AI Factoid Playlist Component
 * 
 * Displays AI-generated council insights in a rotating news ticker format.
 * Replaces counter-based factoid system with single council-wide playlist.
 * 
 * Features:
 * - Loads AI factoids via REST API
 * - Rotates through insights every 8 seconds
 * - Smooth fade transitions between factoids
 * - Error handling with fallback content
 * - Insight type icons and styling
 */

class AIFactoidPlaylist {
    constructor(container) {
        this.container = container;
        this.council = container.dataset.council;
        this.factoids = [];
        this.currentIndex = 0;
        this.interval = null;
        this.isLoading = false;
        this.hasError = false;
        
        // Configuration
        this.rotationInterval = 8000; // 8 seconds between factoids
        this.fadeTransitionTime = 300; // 300ms fade transition
        this.retryDelay = 5000; // 5 seconds before retry on error
        
        console.log(`🤖 Initializing AI factoid playlist for ${this.council}`);
        this.init();
    }
    
    async init() {
        // Initialize the AI factoid playlist
        try {
            this.showLoadingState();
            await this.loadFactoids();
            
            if (this.factoids.length > 0) {
                this.startPlaylist();
            } else {
                this.showEmptyState();
            }
        } catch (error) {
            console.error('❌ AI factoid playlist initialization failed:', error);
            this.showErrorState();
        }
    }
    
    async loadFactoids() {
        // Load AI factoids from the API with client-side caching
        if (this.isLoading) {
            return;
        }
        
        // Check browser cache first (10 minutes cache)
        const cacheKey = `ai_factoids_${this.council}`;
        const cached = this.getFromBrowserCache(cacheKey, 600000); // 10 minutes
        if (cached) {
            console.log(`✅ Using browser cache for ${this.council} factoids`);
            this.factoids = cached.factoids;
            this.hasError = false;
            return;
        }
        
        this.isLoading = true;
        
        try {
            const response = await fetch(`/api/factoids/ai/${this.council}/`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            // Handle AI service unavailable (503) as a special case
            if (response.status === 503 && data.factoids) {
                this.factoids = data.factoids;
                this.hasError = true;
                
                console.log(`❌ AI UNAVAILABLE for ${this.council} - showing retry option`);
                console.log(`📊 Error factoid:`, this.factoids);
                return; // Don't throw error, just use the error factoid
            }
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            if (data.success) {
                // Check if no factoids are available
                if (data.no_factoids) {
                    console.log(`⏳ No AI factoids available for ${this.council} - ${data.message}`);
                    this.showNoFactoidsMessage(data.message);
                    return;
                }
                
                // Check if we have factoids
                if (data.factoids && data.factoids.length > 0) {
                    this.factoids = data.factoids;
                    this.hasError = false;
                    
                    // Cache successful response in browser for 10 minutes
                    this.saveToBrowserCache(cacheKey, { factoids: this.factoids });
                } else {
                    // Empty factoids array
                    console.log(`📭 Empty factoids response for ${this.council}`);
                    this.showNoFactoidsMessage('AI insights are being generated. Please check back soon.');
                    return;
                }
                
                // Determine if these are AI or fallback factoids
                const hasAiFactoids = this.factoids.some(f => 
                    f.insight_type !== 'basic' && 
                    f.insight_type !== 'system' && 
                    f.insight_type !== 'error'
                );
                const hasErrorFactoids = this.factoids.some(f => f.insight_type === 'error');
                const isRateLimited = data.rate_limited || false;
                const isFallback = data.fallback || false;
                
                let factoidType;
                if (hasAiFactoids) {
                    factoidType = '🤖 LIVE AI';
                } else if (isRateLimited) {
                    factoidType = '⏱️ RATE LIMITED';
                } else if (isFallback || hasErrorFactoids) {
                    factoidType = '🔄 FALLBACK';
                } else {
                    factoidType = '📋 BASIC';
                }
                
                console.log(`✅ Loaded ${this.factoids.length} ${factoidType} factoids for ${this.council}`);
                console.log(`📊 ${factoidType} Factoids:`, this.factoids);
                
                // Log individual factoids with type indicators
                this.factoids.forEach((factoid, i) => {
                    let typeIndicator = '🤖';
                    if (factoid.insight_type === 'basic' || factoid.insight_type === 'system') {
                        typeIndicator = '📋';
                    } else if (factoid.insight_type === 'error') {
                        typeIndicator = '❌';
                    }
                    console.log(`  ${typeIndicator} Factoid ${i+1} (${factoid.insight_type}): ${factoid.text}`);
                });
                
                // Log cache status for debugging
                if (data.cache_status) {
                    console.log(`🗂️ Cache status: ${data.cache_status}`);
                }
                
            } else {
                console.warn('⚠️ Invalid API response format:', data);
                this.factoids = this.generateFallbackFactoids(data);
            }
            
        } catch (error) {
            console.error('❌ Failed to load AI factoids:', error);
            this.hasError = true;
            this.factoids = this.generateFallbackFactoids();
            
            // Retry after delay
            setTimeout(() => {
                console.log('🔄 Retrying AI factoid load...');
                this.loadFactoids();
            }, this.retryDelay);
            
        } finally {
            this.isLoading = false;
        }
    }
    
    generateFallbackFactoids(apiResponse = null) {
        // Show AI unavailable message instead of fallback factoids
        return [{
            text: `AI analysis temporarily unavailable for ${this.council}`,
            insight_type: 'error',
            confidence: 1.0,
            show_retry: true
        }];
    }
    
    startPlaylist() {
        // Start the factoid rotation playlist
        if (this.factoids.length === 0) {
            console.warn('⚠️ No factoids to display');
            return;
        }
        
        // Show first factoid immediately
        this.showFactoid(0);
        
        // If only one factoid, don't rotate
        if (this.factoids.length === 1) {
            console.log('📋 Single factoid - no rotation needed');
            return;
        }
        
        // Start rotation timer
        this.interval = setInterval(() => {
            this.currentIndex = (this.currentIndex + 1) % this.factoids.length;
            this.showFactoid(this.currentIndex);
        }, this.rotationInterval);
        
        console.log(`▶️ Started factoid playlist with ${this.factoids.length} insights`);
    }
    
    showFactoid(index) {
        // Display a specific factoid with smooth transition
        if (!this.factoids[index]) {
            console.error(`❌ Invalid factoid index: ${index}`);
            return;
        }
        
        const factoid = this.factoids[index];
        
        // Smooth fade out
        this.container.style.opacity = '0';
        this.container.style.transition = `opacity ${this.fadeTransitionTime}ms ease-in-out`;
        
        setTimeout(() => {
            // Update content
            this.container.innerHTML = this.buildFactoidHTML(factoid, index);
            
            // Fade back in
            this.container.style.opacity = '1';
            
            // Log for debugging
            console.log(`📊 Showing factoid ${index + 1}/${this.factoids.length}: ${factoid.text}`);
            
        }, this.fadeTransitionTime);
    }
    
    buildFactoidHTML(factoid, index = 0) {
        // Build HTML for a factoid display - GOV.UK styled
        const icon = this.getInsightIcon(factoid.insight_type);
        const isSystem = factoid.insight_type === 'system';
        const isError = factoid.insight_type === 'error';
        const showRetry = factoid.show_retry || false;
        
        if (isError) {
            return `
                <div class="gov-uk-notification-banner__header">
                    <h2 class="gov-uk-notification-banner__title">
                        <svg class="w-5 h-5 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
                        </svg>
                        AI Analysis Unavailable
                    </h2>
                </div>
                <div class="gov-uk-notification-banner__content">
                    <p class="gov-uk-body-s mb-3">${this.escapeHTML(factoid.text)}</p>
                    ${showRetry ? `
                        <button class="gov-uk-button gov-uk-button--secondary text-xs px-3 py-2" 
                                onclick="window.aiFactoidManager?.retryAIGeneration('${this.council}')">
                            Try again
                        </button>
                    ` : ''}
                </div>
            `;
        }
        
        return `
            <div class="gov-uk-notification-banner__header">
                <h2 class="gov-uk-notification-banner__title">
                    ${icon}
                    AI Financial Insights
                </h2>
            </div>
            <div class="gov-uk-notification-banner__content">
                <div class="flex items-start justify-between">
                    <div class="flex-1">
                        <p class="gov-uk-body-s font-medium text-gray-900 mb-1">
                            ${this.escapeHTML(factoid.text)}
                        </p>
                        <p class="text-xs text-gray-600">
                            ${this.getInsightTypeLabel(factoid.insight_type)} • 
                            Generated by AI analysis
                        </p>
                    </div>
                    ${this.factoids.length > 1 ? `
                        <div class="flex space-x-1 ml-4 flex-shrink-0">
                            ${this.buildProgressDots(index)}
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }
    
    getInsightTypeLabel(insightType) {
        const labels = {
            'trend': 'Trend Analysis',
            'comparison': 'Comparison',
            'peak': 'Peak Value',
            'change': 'Change Analysis',
            'ranking': 'Ranking',
            'efficiency': 'Efficiency',
            'volatility': 'Volatility',
            'context': 'Context',
            'basic': 'Basic Info',
            'system': 'System',
            'general': 'General Insight'
        };
        return labels[insightType] || 'Financial Insight';
    }
    
    buildProgressDots(currentIndex) {
        // Build progress indicator dots for multi-factoid playlists
        return this.factoids.map((_, i) => {
            const isActive = i === currentIndex;
            const dotClass = isActive 
                ? 'w-2 h-2 bg-blue-600 rounded-full' 
                : 'w-1.5 h-1.5 bg-blue-300 rounded-full';
            return `<div class="${dotClass}"></div>`;
        }).join('');
    }
    
    getInsightIcon(insightType) {
        // Get emoji icon for insight type
        const icons = {
            'trend': '📈',
            'comparison': '⚖️', 
            'peak': '🏔️',
            'change': '🔄',
            'ranking': '🏆',
            'efficiency': '⚡',
            'volatility': '📊',
            'context': '🌍',
            'basic': '📋',
            'system': '⏳',
            'error': '⚠️',
            'general': '💡'
        };
        
        return icons[insightType] || icons.general;
    }
    
    getInsightColorClasses(insightType) {
        // Get Tailwind color classes for insight type
        const colorSchemes = {
            'trend': {
                background: 'bg-green-50',
                border: 'border-green-400',
                text: 'text-green-900',
                accent: 'text-green-600'
            },
            'comparison': {
                background: 'bg-blue-50',
                border: 'border-blue-400',
                text: 'text-blue-900',
                accent: 'text-blue-600'
            },
            'peak': {
                background: 'bg-purple-50',
                border: 'border-purple-400',
                text: 'text-purple-900',
                accent: 'text-purple-600'
            },
            'change': {
                background: 'bg-orange-50',
                border: 'border-orange-400',
                text: 'text-orange-900',
                accent: 'text-orange-600'
            },
            'system': {
                background: 'bg-gray-50',
                border: 'border-gray-300',
                text: 'text-gray-700',
                accent: 'text-gray-500'
            },
            'error': {
                background: 'bg-red-50',
                border: 'border-red-400',
                text: 'text-red-900',
                accent: 'text-red-600'
            }
        };
        
        // Default to blue theme
        return colorSchemes[insightType] || colorSchemes.comparison;
    }
    
    showLoadingState() {
        // Display loading indicator
        this.container.innerHTML = `
            <div class="flex items-center space-x-3 py-3 px-4 bg-gray-50 border-l-4 border-gray-300 rounded-r-lg">
                <div class="animate-spin text-lg">⏳</div>
                <div class="text-sm text-gray-600">Loading AI insights...</div>
            </div>
        `;
    }
    
    showEmptyState() {
        // Display empty state when no factoids available
        this.container.innerHTML = `
            <div class="flex items-center space-x-3 py-3 px-4 bg-yellow-50 border-l-4 border-yellow-300 rounded-r-lg">
                <div class="text-lg">📊</div>
                <div class="text-sm text-yellow-800">AI insights are being generated for this council</div>
            </div>
        `;
    }
    
    showNoFactoidsMessage(message) {
        // Display message when no factoids are available
        this.container.innerHTML = `
            <div class="gov-uk-notification-banner__header">
                <h2 class="gov-uk-notification-banner__title">
                    <svg class="w-5 h-5 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                    AI Financial Insights
                </h2>
            </div>
            <div class="gov-uk-notification-banner__content">
                <p class="gov-uk-body-s mb-0">${this.escapeHTML(message)}</p>
            </div>
        `;
    }
    
    showErrorState() {
        // Display error state when factoid loading fails
        this.container.innerHTML = `
            <div class="flex items-center space-x-3 py-3 px-4 bg-red-50 border-l-4 border-red-300 rounded-r-lg">
                <div class="text-lg">⚠️</div>
                <div class="text-sm text-red-800">Unable to load insights - retrying...</div>
            </div>
        `;
    }
    
    escapeHTML(text) {
        // Escape HTML characters in factoid text
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    getFromBrowserCache(key, maxAge) {
        // Get data from browser localStorage with expiry
        try {
            const stored = localStorage.getItem(key);
            if (!stored) return null;
            
            const data = JSON.parse(stored);
            const now = Date.now();
            
            if (now - data.timestamp > maxAge) {
                localStorage.removeItem(key);
                return null;
            }
            
            return data.value;
        } catch (e) {
            console.warn('Error reading from browser cache:', e);
            return null;
        }
    }
    
    saveToBrowserCache(key, value) {
        // Save data to browser localStorage with timestamp
        try {
            const data = {
                value: value,
                timestamp: Date.now()
            };
            localStorage.setItem(key, JSON.stringify(data));
        } catch (e) {
            console.warn('Error saving to browser cache:', e);
        }
    }
    
    destroy() {
        // Clean up the playlist (remove timers, event listeners)
        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
        }
        
        console.log(`🗑️ AI factoid playlist destroyed for ${this.council}`);
    }
    
    pause() {
        // Pause the factoid rotation
        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
            console.log(`⏸️ AI factoid playlist paused for ${this.council}`);
        }
    }
    
    resume() {
        // Resume the factoid rotation
        if (!this.interval && this.factoids.length > 1) {
            this.startPlaylist();
            console.log(`▶️ AI factoid playlist resumed for ${this.council}`);
        }
    }
}


/**
 * AI Factoid Manager
 * 
 * Manages multiple AI factoid playlists on a page and provides
 * global controls for the AI factoid system.
 */
class AIFactoidManager {
    constructor() {
        this.playlists = new Map();
        this.isVisible = true;
        
        console.log('🎮 AI Factoid Manager initialized');
        this.initializePagePlaylists();
        this.setupVisibilityHandling();
    }
    
    initializePagePlaylists() {
        // Find and initialize all AI factoid containers on the page
        const containers = document.querySelectorAll('.ai-factoid-playlist');
        
        containers.forEach(container => {
            const council = container.dataset.council;
            if (council && !this.playlists.has(council)) {
                const playlist = new AIFactoidPlaylist(container);
                this.playlists.set(council, playlist);
                console.log(`➕ Added AI factoid playlist for ${council}`);
            }
        });
        
        console.log(`🎯 Initialized ${this.playlists.size} AI factoid playlists`);
    }
    
    setupVisibilityHandling() {
        // Pause/resume playlists based on page visibility
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pauseAll();
            } else {
                this.resumeAll();
            }
        });
    }
    
    pauseAll() {
        // Pause all active playlists
        this.playlists.forEach((playlist, council) => {
            playlist.pause();
        });
        console.log('⏸️ All AI factoid playlists paused');
    }
    
    resumeAll() {
        // Resume all paused playlists
        this.playlists.forEach((playlist, council) => {
            playlist.resume();
        });
        console.log('▶️ All AI factoid playlists resumed');
    }
    
    async refreshPlaylist(council) {
        // Refresh a specific council's playlist and clear cache
        console.log(`🔄 Refreshing AI factoid playlist for ${council}`);
        
        const playlist = this.playlists.get(council);
        if (playlist) {
            // Clear AI factoid cache first
            try {
                const response = await fetch(`/api/factoids/ai/${council}/cache/`, {
                    method: 'DELETE',
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json',
                    }
                });
                
                if (response.ok) {
                    console.log(`✅ Cache cleared for ${council}`);
                } else {
                    console.warn(`⚠️ Failed to clear cache for ${council}: ${response.status}`);
                }
            } catch (error) {
                console.warn(`⚠️ Cache clear request failed for ${council}:`, error);
            }
            
            // Destroy current playlist
            playlist.destroy();
            
            // Re-initialize after short delay
            setTimeout(() => {
                const container = document.querySelector(`[data-council="${council}"]`);
                if (container) {
                    const newPlaylist = new AIFactoidPlaylist(container);
                    this.playlists.set(council, newPlaylist);
                    console.log(`🆕 Re-initialized AI factoid playlist for ${council}`);
                }
            }, 100);
        }
    }
    
    retryAIGeneration(council) {
        // Retry AI generation with simple playlist refresh
        console.log(`🤖 Retrying AI generation for ${council}`);
        
        const playlist = this.playlists.get(council);
        if (playlist) {
            // Set hasError to false and retry loading
            playlist.hasError = false;
            playlist.factoids = [];
            playlist.currentIndex = 0;
            
            // Show loading state and reload
            playlist.showLoadingState();
            playlist.loadFactoids();
            
            console.log(`🔄 Initiated AI retry for ${council}`);
        }
    }
    
    getPlaylistStatus() {
        // Get status information for all playlists
        const status = {
            total_playlists: this.playlists.size,
            councils: Array.from(this.playlists.keys()),
            is_visible: this.isVisible
        };
        
        console.log('📊 AI Factoid Manager Status:', status);
        return status;
    }
}


// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Check if we have any AI factoid containers
    const containers = document.querySelectorAll('.ai-factoid-playlist');
    
    if (containers.length > 0) {
        // Initialize global manager
        window.aiFactoidManager = new AIFactoidManager();
        
        console.log(`🚀 AI Factoids system ready with ${containers.length} playlists`);
    } else {
        console.log('ℹ️ No AI factoid containers found on this page');
    }
});


// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AIFactoidPlaylist, AIFactoidManager };
}