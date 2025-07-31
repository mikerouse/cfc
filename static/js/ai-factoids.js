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
        // Load AI factoids from the API
        if (this.isLoading) {
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
            
            if (data.success && data.factoids) {
                this.factoids = data.factoids;
                this.hasError = false;
                
                // Determine if these are AI or fallback factoids
                const hasAiFactoids = this.factoids.some(f => 
                    f.insight_type !== 'basic' && 
                    f.insight_type !== 'system' && 
                    f.insight_type !== 'error'
                );
                const hasErrorFactoids = this.factoids.some(f => f.insight_type === 'error');
                const factoidType = hasAiFactoids ? '🤖 LIVE AI' : hasErrorFactoids ? '❌ AI UNAVAILABLE' : '🔄 FALLBACK';
                
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
        // Build HTML for a factoid display
        const icon = this.getInsightIcon(factoid.insight_type);
        const colorClasses = this.getInsightColorClasses(factoid.insight_type);
        const isSystem = factoid.insight_type === 'system';
        const isError = factoid.insight_type === 'error';
        const showRetry = factoid.show_retry || false;
        
        return `
            <div class="flex items-center space-x-3 py-3 px-4 ${colorClasses.background} border-l-4 ${colorClasses.border} rounded-r-lg">
                <div class="flex-shrink-0 text-lg">
                    ${icon}
                </div>
                <div class="flex-grow min-w-0">
                    <div class="text-sm ${colorClasses.text} font-medium leading-relaxed">
                        ${this.escapeHTML(factoid.text)}
                    </div>
                    ${showRetry ? `
                        <button class="mt-2 text-xs px-2 py-1 bg-red-600 text-white rounded hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500" 
                                onclick="window.aiFactoidManager?.retryAIGeneration('${this.council}')">
                            Retry AI Analysis
                        </button>
                    ` : ''}
                </div>
                <div class="flex-shrink-0 flex flex-col items-end space-y-1">
                    <div class="text-xs ${colorClasses.accent} font-medium">
                        ${isError ? 'Error' : isSystem ? 'System' : 'AI Insight'}
                    </div>
                    ${this.factoids.length > 1 && !isError ? `
                        <div class="flex space-x-1">
                            ${this.buildProgressDots(index)}
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
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