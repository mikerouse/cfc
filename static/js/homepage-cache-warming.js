/**
 * Homepage Cache Warming UI
 * 
 * Provides real-time updates for counter cache warming progress.
 * Shows "Calculating..." states and progress indicators while cache warming.
 */

class HomepageCacheWarmingUI {
    constructor() {
        this.updateInterval = 5000; // Check every 5 seconds
        this.maxRetries = 12; // Stop after 1 minute of errors
        this.retryCount = 0;
        this.isRunning = false;
        this.intervalId = null;
        
        this.init();
    }
    
    init() {
        // Start monitoring if there are calculating counters on page load
        const calculatingCounters = document.querySelectorAll('.calculating-state');
        if (calculatingCounters.length > 0) {
            console.log('Found calculating counters, starting real-time updates');
            this.startMonitoring();
        }
        
        // Add trigger button for staff (if present)
        this.setupTriggerButton();
    }
    
    startMonitoring() {
        if (this.isRunning) return;
        
        this.isRunning = true;
        this.retryCount = 0;
        this.checkProgress();
        
        // Set up regular polling
        this.intervalId = setInterval(() => {
            this.checkProgress();
        }, this.updateInterval);
    }
    
    stopMonitoring() {
        this.isRunning = false;
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }
    
    async checkProgress() {
        try {
            const response = await fetch('/api/cache-warming/progress/');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            this.updateUI(data);
            this.retryCount = 0; // Reset on success
            
        } catch (error) {
            console.error('Error checking cache warming progress:', error);
            this.retryCount++;
            
            if (this.retryCount >= this.maxRetries) {
                console.warn('Too many errors, stopping cache warming monitoring');
                this.stopMonitoring();
                this.showError('Connection lost. Please refresh the page.');
            }
        }
    }
    
    updateUI(data) {
        const counterStates = data.counter_states || [];
        let allReady = true;
        
        counterStates.forEach(counter => {
            const counterElement = document.getElementById(`counter-${counter.slug}`);
            if (!counterElement) return;
            
            const calculatingState = counterElement.querySelector('.calculating-state');
            const counterValue = counterElement.querySelector('.counter-value');
            
            if (counter.state === 'calculating') {
                allReady = false;
                // Ensure calculating state is shown
                if (calculatingState) {
                    calculatingState.style.display = 'block';
                }
                if (counterValue) {
                    counterValue.style.display = 'none';
                }
                
                // Update progress text if available
                this.updateCalculatingProgress(calculatingState, data.warming_progress);
                
            } else if (counter.state === 'ready') {
                // Counter is now ready - transition to showing value
                this.transitionToReady(counterElement, counter);
                
            } else if (counter.state === 'error') {
                this.showCounterError(counterElement, 'Unable to load counter value');
            }
        });
        
        // Stop monitoring if all counters are ready
        if (allReady && this.isRunning) {
            console.log('All counters ready, stopping monitoring');
            setTimeout(() => {
                this.stopMonitoring();
            }, 2000); // Give a bit of time for animations to complete
        }
    }
    
    updateCalculatingProgress(calculatingState, progressInfo) {
        if (!calculatingState || !progressInfo) return;
        
        const progressText = calculatingState.querySelector('.text-xs');
        if (progressText && progressInfo.current_step) {
            const statusText = progressText.querySelector('span:last-child');
            if (statusText) {
                statusText.textContent = progressInfo.current_step;
            }
        }
        
        // Update progress bar if available
        const progressBar = calculatingState.querySelector('.bg-gradient-to-r');
        if (progressBar && progressInfo.counters_total > 0) {
            const progressPercent = (progressInfo.counters_completed / progressInfo.counters_total) * 100;
            progressBar.style.width = `${Math.min(progressPercent, 100)}%`;
            
            // Update progress text
            const progressLabel = calculatingState.querySelector('.text-xs.text-gray-400');
            if (progressLabel) {
                progressLabel.textContent = `${progressInfo.counters_completed}/${progressInfo.counters_total} counters warmed`;
            }
        }
    }
    
    transitionToReady(counterElement, counter) {
        const calculatingState = counterElement.querySelector('.calculating-state');
        const counterValue = counterElement.querySelector('.counter-value');
        
        if (!calculatingState || !counterValue) {
            // Fallback: refresh the page to show updated values
            setTimeout(() => {
                window.location.reload();
            }, 1000);
            return;
        }
        
        // Fade out calculating state
        calculatingState.style.transition = 'opacity 0.5s ease-out';
        calculatingState.style.opacity = '0';
        
        setTimeout(() => {
            // Hide calculating state and show counter
            calculatingState.style.display = 'none';
            counterValue.style.display = 'block';
            counterValue.style.opacity = '0';
            counterValue.style.transition = 'opacity 0.5s ease-in';
            
            // Update counter value and trigger animation
            if (counter.display_value) {
                counterValue.textContent = counter.display_value;
            }
            
            // Fade in counter value
            setTimeout(() => {
                counterValue.style.opacity = '1';
                
                // Trigger CountUp animation if available
                this.triggerCounterAnimation(counterValue);
            }, 50);
            
        }, 500);
    }
    
    triggerCounterAnimation(counterElement) {
        // Re-initialize CountUp animation for the updated counter
        if (typeof countUp !== 'undefined' && countUp.CountUp) {
            const val = parseFloat(counterElement.dataset.value || '0');
            const dur = parseInt(counterElement.dataset.duration || '2000') / 1000;
            const showCurrency = (counterElement.dataset.showCurrency || 'false').toLowerCase() === 'true';
            const precision = parseInt(counterElement.dataset.precision || '0');
            
            const cu = new countUp.CountUp(counterElement, val, {
                duration: dur,
                decimalPlaces: precision,
                separator: showCurrency ? ',' : '',
                prefix: showCurrency ? '£' : '',
            });
            
            if (!cu.error) {
                cu.start();
            }
        }
    }
    
    showCounterError(counterElement, message) {
        const calculatingState = counterElement.querySelector('.calculating-state');
        const counterValue = counterElement.querySelector('.counter-value');
        
        if (calculatingState) {
            calculatingState.innerHTML = `
                <div class="text-4xl font-bold text-red-600 mb-2">
                    <div class="inline-flex items-center space-x-2">
                        <svg class="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                        </svg>
                        <span>Error</span>
                    </div>
                </div>
                <div class="text-sm text-red-500">${message}</div>
            `;
        }
        
        if (counterValue) {
            counterValue.style.display = 'none';
        }
    }
    
    showError(message) {
        // Show a subtle error notification
        const errorDiv = document.createElement('div');
        errorDiv.className = 'fixed top-4 right-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded z-50';
        errorDiv.innerHTML = `
            <div class="flex items-center">
                <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                </svg>
                <span>${message}</span>
            </div>
        `;
        
        document.body.appendChild(errorDiv);
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.parentNode.removeChild(errorDiv);
            }
        }, 10000);
    }
    
    setupTriggerButton() {
        // Add a trigger button for staff members (if they have permission)
        const existingButton = document.getElementById('trigger-cache-warming');
        if (existingButton) {
            existingButton.addEventListener('click', () => {
                this.triggerCacheWarming();
            });
        }
    }
    
    async triggerCacheWarming() {
        try {
            const response = await fetch('/api/cache-warming/trigger/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            const data = await response.json();
            
            if (data.status === 'started') {
                alert('Cache warming started in background');
                // Start monitoring
                this.startMonitoring();
            } else if (data.status === 'already_running') {
                alert('Cache warming is already in progress');
                this.startMonitoring();
            } else {
                alert('Failed to start cache warming');
            }
            
        } catch (error) {
            console.error('Error triggering cache warming:', error);
            alert('Error starting cache warming');
        }
    }
    
    getCSRFToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        return '';
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        new HomepageCacheWarmingUI();
    });
} else {
    new HomepageCacheWarmingUI();
}