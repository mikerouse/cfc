/**
 * Homepage Counter Guardian - Defensive System for £0 Counter Detection
 * 
 * This script automatically detects £0 counters on the home page and triggers
 * emergency cache warming to fix them. Also sends email alerts to administrators.
 * 
 * Created: 2025-08-03
 * Purpose: Prevent users from seeing £0 counter values due to cache misses
 */

class HomepageCounterGuardian {
    constructor() {
        this.checkInterval = 2000; // Check every 2 seconds
        this.emergencyTriggered = false;
        this.maxRetries = 3;
        this.retryCount = 0;
        this.debugMode = false; // Set to true for console logging
        this.instanceId = Math.random().toString(36).substr(2, 9); // Unique instance ID
        this.lastEmergencyTime = 0; // Rate limiting
        
        this.init();
    }
    
    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.startMonitoring());
        } else {
            this.startMonitoring();
        }
    }
    
    startMonitoring() {
        this.log('Homepage Counter Guardian initialized');
        
        // Start monitoring after a delay to allow counters to animate
        setTimeout(() => {
            this.checkForZeroCounters();
            
            // Set up periodic checking
            this.monitoringInterval = setInterval(() => {
                if (!this.emergencyTriggered) {
                    this.checkForZeroCounters();
                }
            }, this.checkInterval);
        }, 3000); // Wait 3 seconds for counter animation to complete
    }
    
    checkForZeroCounters() {
        const counterElements = document.querySelectorAll('.counter-value');
        const zeroCounters = [];
        
        counterElements.forEach((element, index) => {
            const dataValue = parseFloat(element.dataset.value || '0');
            const currentText = element.textContent.trim();
            const showCurrency = (element.dataset.showCurrency || 'false').toLowerCase() === 'true';
            
            // Check if counter shows £0 or 0 (when it should show currency)
            const isZeroValue = (
                dataValue === 0 || 
                currentText === '£0' || 
                currentText === '0' ||
                currentText === '£0.00' ||
                (showCurrency && currentText === '0')
            );
            
            // Get counter context for debugging
            const counterContainer = element.closest('[id^="counter-"]');
            const counterName = counterContainer ? 
                counterContainer.querySelector('h3')?.textContent?.trim() || `Counter ${index + 1}` :
                `Counter ${index + 1}`;
            
            if (isZeroValue) {
                zeroCounters.push({
                    index: index,
                    name: counterName,
                    dataValue: dataValue,
                    displayText: currentText,
                    showCurrency: showCurrency,
                    elementId: counterContainer?.id || `counter-${index}`
                });
                
                this.log(`Zero counter detected: ${counterName} (${currentText})`);
            }
        });
        
        // If we found zero counters and haven't triggered emergency yet
        if (zeroCounters.length > 0 && !this.emergencyTriggered) {
            this.log(`Detected ${zeroCounters.length} zero counters - triggering emergency cache warming`);
            this.triggerEmergencyCacheWarming(zeroCounters);
        } else if (zeroCounters.length === 0 && this.retryCount > 0) {
            this.log('No zero counters detected - issue appears to be resolved');
            this.emergencyTriggered = false;
            this.retryCount = 0;
        }
    }
    
    async triggerEmergencyCacheWarming(zeroCounters) {
        // Security: Rate limiting - max 1 emergency per 30 seconds
        const now = Date.now();
        if (now - this.lastEmergencyTime < 30000) {
            this.log('Emergency rate limited - too soon since last attempt');
            return;
        }
        
        if (this.emergencyTriggered && this.retryCount >= this.maxRetries) {
            this.log('Maximum retries reached - stopping emergency attempts');
            return;
        }
        
        this.emergencyTriggered = true;
        this.retryCount++;
        this.lastEmergencyTime = now;
        
        // Security: Validate and sanitize zero counter data
        const sanitizedCounters = zeroCounters.slice(0, 10).map(counter => ({
            name: String(counter.name || 'Unknown').substring(0, 100),
            index: Math.max(0, Math.min(50, parseInt(counter.index) || 0)),
            displayText: String(counter.displayText || '').substring(0, 50)
        }));
        
        // Show user notification
        this.showUserNotification('Detected data loading issue - fixing automatically...');
        
        try {
            // Security: Get CSRF token for the request
            const csrfToken = this.getCSRFToken();
            
            const headers = {
                'Content-Type': 'application/json',
            };
            
            // Add CSRF token if available
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }
            
            const response = await fetch('/api/emergency-cache-warming/', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({
                    zero_counters: sanitizedCounters,
                    timestamp: new Date().toISOString(),
                    retry_count: this.retryCount,
                    instance_id: this.instanceId
                })
            });
            
            const result = await response.json();
            
            // Handle rate limiting
            if (response.status === 429) {
                this.log('Emergency cache warming rate limited');
                this.showUserNotification('Too many requests - please wait before trying again', 'error');
                return;
            }
            
            // Handle concurrent operations
            if (response.status === 409) {
                this.log('Cache warming already in progress');
                this.showUserNotification('System is already fixing the issue - please wait', 'info');
                return;
            }
            
            if (result.success) {
                this.log('Emergency cache warming successful:', result);
                
                // Show success notification
                this.showUserNotification(
                    `Fixed ${result.fixed_counters} counters in ${result.warming_duration}`,
                    'success'
                );
                
                // Reload the page after a short delay to show fresh data
                setTimeout(() => {
                    this.log('Reloading page to show updated counter values');
                    window.location.reload();
                }, 2000);
                
            } else {
                this.log('Emergency cache warming failed:', result.error);
                this.showUserNotification('Data fix attempt failed - please refresh the page', 'error');
                
                // Reset emergency flag to allow retry
                setTimeout(() => {
                    if (this.retryCount < this.maxRetries) {
                        this.emergencyTriggered = false;
                    }
                }, 10000);
            }
            
        } catch (error) {
            this.log('Network error during emergency cache warming:', error);
            this.showUserNotification('Network error during data fix - please refresh the page', 'error');
            
            // Reset emergency flag to allow retry
            setTimeout(() => {
                if (this.retryCount < this.maxRetries) {
                    this.emergencyTriggered = false;
                }
            }, 10000);
        }
    }
    
    showUserNotification(message, type = 'info') {
        // Create notification element if it doesn't exist
        let notification = document.getElementById('counter-guardian-notification');
        if (!notification) {
            notification = document.createElement('div');
            notification.id = 'counter-guardian-notification';
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: #1f2937;
                color: white;
                padding: 12px 16px;
                border-radius: 6px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                z-index: 10000;
                font-size: 14px;
                max-width: 350px;
                transition: all 0.3s ease;
            `;
            document.body.appendChild(notification);
        }
        
        // Update notification style based on type
        const colors = {
            info: '#1f2937',
            success: '#059669',
            error: '#dc2626'
        };
        
        notification.style.background = colors[type] || colors.info;
        notification.textContent = message;
        notification.style.opacity = '1';
        notification.style.transform = 'translateY(0)';
        
        // Auto-hide after 5 seconds for success/info, 10 seconds for error
        const hideDelay = type === 'error' ? 10000 : 5000;
        setTimeout(() => {
            if (notification.parentNode) {
                notification.style.opacity = '0';
                notification.style.transform = 'translateY(-10px)';
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                }, 300);
            }
        }, hideDelay);
    }
    
    getCSRFToken() {
        // Try multiple methods to get CSRF token
        
        // Method 1: From meta tag
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        if (csrfMeta) {
            return csrfMeta.getAttribute('content');
        }
        
        // Method 2: From cookie
        const csrfCookie = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='));
        if (csrfCookie) {
            return csrfCookie.split('=')[1];
        }
        
        // Method 3: From Django's default cookie name
        const djangoCSRF = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='));
        if (djangoCSRF) {
            return djangoCSRF.split('=')[1];
        }
        
        this.log('CSRF token not found - request may fail');
        return null;
    }
    
    log(message, ...args) {
        if (this.debugMode) {
            console.log(`[Counter Guardian] ${message}`, ...args);
        }
    }
    
    destroy() {
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
        }
        
        const notification = document.getElementById('counter-guardian-notification');
        if (notification && notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }
}

// Initialize the guardian when the script loads
// Use a slight delay to ensure other page scripts have loaded
setTimeout(() => {
    // Security: Only initialize on the home page and prevent multiple instances
    if (document.querySelector('#homepage-counters') && !window.homepageCounterGuardian) {
        // Security: Verify we're on the intended domain (prevent iframe attacks)
        if (window.location.hostname === window.parent.location.hostname) {
            window.homepageCounterGuardian = new HomepageCounterGuardian();
        }
    }
}, 1000);

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (window.homepageCounterGuardian) {
        window.homepageCounterGuardian.destroy();
    }
});