/* Flagging System JavaScript Component */

// Only declare FlaggingSystem if it doesn't already exist
if (typeof FlaggingSystem === 'undefined') {
class FlaggingSystem {
    constructor() {
        console.log('FlaggingSystem constructor called');
        this.isInitialized = false;
        this.init();
    }

    init() {
        console.log('FlaggingSystem init() called, isInitialized:', this.isInitialized);
        if (this.isInitialized) return;
        
        // Add flag modal to body if it doesn't exist
        this.createFlagModal();
        
        // Bind event listeners
        this.bindEvents();
        
        this.isInitialized = true;
        console.log('FlaggingSystem initialization completed');
    }

    createFlagModal() {
        if (document.getElementById('flagModal')) return;
        
        const modalHTML = `
            <div id="flagModal" class="hidden fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" role="dialog" aria-labelledby="flagModalLabel" aria-hidden="true">
                <div class="bg-white rounded-xl shadow-2xl border border-gray-200 w-full max-w-lg mx-4 max-h-screen overflow-y-auto">
                    <div class="p-6">
                        <div class="flex items-center justify-between mb-6">
                            <h5 class="text-lg font-semibold text-gray-900 flex items-center" id="flagModalLabel">
                                <svg class="w-5 h-5 text-yellow-500 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9"/>
                                </svg>
                                Flag Content
                            </h5>
                            <button type="button" class="text-gray-400 hover:text-gray-600 transition-colors" id="closeFlagModal" aria-label="Close">
                                <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                                </svg>
                            </button>
                        </div>
                        
                        <form id="flagForm" class="space-y-4">
                            <input type="hidden" id="flagContentType" name="content_type">
                            <input type="hidden" id="flagObjectId" name="object_id">
                            
                            <div>
                                <label for="flagType" class="block text-sm font-medium text-gray-700 mb-2">Why are you flagging this content?</label>
                                <select class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" id="flagType" name="flag_type" required>
                                    <option value="">-- Select a reason --</option>
                                    <option value="content_incorrect">Data is Incorrect</option>
                                    <option value="content_outdated">Data is Outdated</option>
                                    <option value="content_spam">Spam or Irrelevant</option>
                                    <option value="content_duplicate">Duplicate Entry</option>
                                    <option value="user_abuse">User Abuse/Harassment</option>
                                    <option value="user_spam">User Spamming</option>
                                    <option value="system_error">System/Technical Error</option>
                                    <option value="other">Other (See Description)</option>
                                </select>
                            </div>
                            
                            <!-- Data Field/Counter Selection (shown when data_issue is selected) -->
                            <div id="dataFieldContainer" class="hidden">
                                <label for="dataFieldSelect" class="block text-sm font-medium text-gray-700 mb-2">Which data field or counter has an issue?</label>
                                <select class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" id="dataFieldSelect" name="data_field">
                                    <option value="">-- Select field or counter --</option>
                                    <optgroup label="Data Fields">
                                        <!-- These will be populated dynamically -->
                                    </optgroup>
                                    <optgroup label="Counters">
                                        <!-- These will be populated dynamically -->
                                    </optgroup>
                                </select>
                            </div>
                            
                            <div>
                                <label for="flagDescription" class="block text-sm font-medium text-gray-700 mb-2">Please provide details about the issue:</label>
                                <textarea class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" id="flagDescription" name="description" rows="4" 
                                          placeholder="Explain why this content should be reviewed..." required></textarea>
                                <p class="text-sm text-gray-600 mt-1">
                                    Be specific about the issue to help moderators review it quickly.
                                </p>
                            </div>
                            
                            <div>
                                <label for="flagPriority" class="block text-sm font-medium text-gray-700 mb-2">Priority Level:</label>
                                <select class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" id="flagPriority" name="priority">
                                    <option value="low">Low - Minor issue</option>
                                    <option value="medium" selected>Medium - Moderate concern</option>
                                    <option value="high">High - Serious issue</option>
                                    <option value="critical">Critical - Urgent attention needed</option>
                                </select>
                            </div>
                            
                            <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
                                <div class="flex items-start">
                                    <svg class="w-5 h-5 text-blue-500 mt-0.5 mr-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                        <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
                                    </svg>
                                    <div class="text-sm text-blue-800">
                                        <strong>Community Guidelines:</strong> Flags are reviewed by our moderation team. 
                                        Please only flag content that genuinely violates our guidelines. 
                                        Misuse of the flagging system may result in restrictions on your account.
                                    </div>
                                </div>
                            </div>
                        </form>
                        
                        <div class="flex justify-end space-x-3 mt-6">
                            <button type="button" class="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors" id="cancelFlag">Cancel</button>
                            <button type="button" class="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors flex items-center" id="submitFlag">
                                <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9"/>
                                </svg>
                                Submit Flag
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }

    bindEvents() {
        // Handle flag button clicks
        document.addEventListener('click', (e) => {
            // Check if the clicked element or any of its parents has the flag-content-btn class
            const button = e.target.closest('.flag-content-btn');
            if (button) {
                console.log('Flag button clicked:', button);
                e.preventDefault();
                this.showFlagModal(button);
            }
        });

        // Handle flag form submission
        document.addEventListener('click', (e) => {
            if (e.target.id === 'submitFlag') {
                e.preventDefault();
                this.submitFlag();
            }
        });

        // Handle modal close buttons
        document.addEventListener('click', (e) => {
            if (e.target.id === 'closeFlagModal' || e.target.id === 'cancelFlag') {
                e.preventDefault();
                this.hideFlagModal();
            }
        });

        // Handle clicking outside modal to close
        document.addEventListener('click', (e) => {
            const modal = document.getElementById('flagModal');
            if (e.target === modal) {
                this.hideFlagModal();
            }
        });

        // Handle escape key to close modal
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const modal = document.getElementById('flagModal');
                if (modal && !modal.classList.contains('hidden')) {
                    this.hideFlagModal();
                }
            }
        });

        // Handle flag type change to show/hide data field selector
        document.addEventListener('change', (e) => {
            if (e.target.id === 'flagType') {
                const dataFieldContainer = document.getElementById('dataFieldContainer');
                const dataFieldSelect = document.getElementById('dataFieldSelect');
                
                if (e.target.value === 'content_incorrect') {
                    dataFieldContainer.classList.remove('hidden');
                    dataFieldSelect.required = true;
                } else {
                    dataFieldContainer.classList.add('hidden');
                    dataFieldSelect.required = false;
                    dataFieldSelect.value = '';
                }
            }
        });
    }

    showFlagModal(button) {
        console.log('showFlagModal called with button:', button);
        const contentType = button.dataset.contentType;
        const objectId = button.dataset.objectId;
        const contentDescription = button.dataset.contentDescription || 'this content';
        
        console.log('Content data:', { contentType, objectId, contentDescription });
        
        if (!contentType || !objectId) {
            console.error('Missing content information:', { contentType, objectId });
            this.showNotification('Error: Missing content information', 'error');
            return;
        }

        // Set form values
        document.getElementById('flagContentType').value = contentType;
        document.getElementById('flagObjectId').value = objectId;
        
        // Update modal title
        document.getElementById('flagModalLabel').innerHTML = 
            `<svg class="w-5 h-5 text-yellow-500 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9"/>
            </svg>
            Flag ${contentDescription}`;
        
        // Populate data fields if we're on a council page
        if (this.isCouncilPage()) {
            this.populateDataFields();
        }
        
        // Show modal
        const modal = document.getElementById('flagModal');
        console.log('Modal element:', modal);
        if (modal) {
            modal.classList.remove('hidden');
            modal.setAttribute('aria-hidden', 'false');
            console.log('Modal should now be visible');
        } else {
            console.error('Modal element not found!');
        }
    }

    hideFlagModal() {
        const modal = document.getElementById('flagModal');
        if (modal) {
            modal.classList.add('hidden');
            modal.setAttribute('aria-hidden', 'true');
            this.resetFlagForm();
        }
    }

    async submitFlag() {
        const form = document.getElementById('flagForm');
        const formData = new FormData(form);
        const submitButton = document.getElementById('submitFlag');
        
        // Validate form
        if (!this.validateFlagForm(form)) {
            return;
        }

        // Show loading state
        const originalText = submitButton.innerHTML;
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';

        try {
            const response = await fetch('/ajax/flag-content/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                this.hideFlagModal();
                this.showNotification(data.message, 'success');
                
                // Update button to show it's been flagged
                this.updateFlaggedButton(formData.get('content_type'), formData.get('object_id'));
            } else {
                this.showNotification(data.error || 'Error submitting flag', 'error');
            }
        } catch (error) {
            console.error('Error submitting flag:', error);
            this.showNotification('Network error occurred', 'error');
        } finally {
            submitButton.disabled = false;
            submitButton.innerHTML = originalText;
        }
    }

    validateFlagForm(form) {
        const flagType = form.querySelector('#flagType').value;
        const description = form.querySelector('#flagDescription').value.trim();
        const dataFieldSelect = form.querySelector('#dataFieldSelect');

        if (!flagType) {
            this.showNotification('Please select a reason for flagging', 'error');
            return false;
        }

        // If data issue is selected, ensure a field/counter is selected
        if (flagType === 'content_incorrect' && dataFieldSelect && !dataFieldSelect.value) {
            this.showNotification('Please select which data field or counter has an issue', 'error');
            return false;
        }

        if (!description || description.length < 10) {
            this.showNotification('Please provide at least 10 characters describing the issue', 'error');
            return false;
        }

        return true;
    }

    updateFlaggedButton(contentType, objectId) {
        const buttons = document.querySelectorAll(
            `.flag-content-btn[data-content-type="${contentType}"][data-object-id="${objectId}"]`
        );
        
        buttons.forEach(button => {
            button.classList.remove('border-yellow-300', 'text-yellow-700', 'bg-yellow-50', 'hover:bg-yellow-100');
            button.classList.add('bg-yellow-500', 'text-white', 'border-yellow-500');
            button.innerHTML = `
                <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9"/>
                </svg>
                Flagged
            `;
            button.disabled = true;
            button.title = 'You have flagged this content';
        });
    }

    resetFlagForm() {
        const form = document.getElementById('flagForm');
        if (form) {
            form.reset();
            document.getElementById('flagContentType').value = '';
            document.getElementById('flagObjectId').value = '';
        }
    }

    getCsrfToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return decodeURIComponent(value);
            }
        }
        return '';
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const colorClasses = {
            'success': 'bg-green-50 border-green-200 text-green-800',
            'error': 'bg-red-50 border-red-200 text-red-800',
            'warning': 'bg-yellow-50 border-yellow-200 text-yellow-800',
            'info': 'bg-blue-50 border-blue-200 text-blue-800'
        }[type] || 'bg-blue-50 border-blue-200 text-blue-800';

        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 z-50 max-w-sm p-4 border rounded-lg shadow-lg ${colorClasses}`;
        notification.innerHTML = `
            <div class="flex items-start">
                <div class="flex-1">
                    ${message}
                </div>
                <button type="button" class="ml-3 text-gray-400 hover:text-gray-600 transition-colors" onclick="this.parentElement.parentElement.remove()">
                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                </button>
            </div>
        `;

        document.body.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }

    // Check if we're on a council detail page
    isCouncilPage() {
        return window.location.pathname.match(/^\/councils\/[^\/]+\/?$/);
    }

    // Populate data fields and counters from the page
    populateDataFields() {
        const dataFieldSelect = document.getElementById('dataFieldSelect');
        if (!dataFieldSelect) return;

        // Clear existing options except the first one
        const fieldsOptgroup = dataFieldSelect.querySelector('optgroup[label="Data Fields"]');
        const countersOptgroup = dataFieldSelect.querySelector('optgroup[label="Counters"]');
        
        fieldsOptgroup.innerHTML = '';
        countersOptgroup.innerHTML = '';

        // Extract data fields from meta fields on the page
        const metaFields = document.querySelectorAll('.council-meta-item');
        metaFields.forEach(field => {
            const label = field.querySelector('.council-meta-label')?.textContent.trim();
            if (label) {
                const option = document.createElement('option');
                option.value = `field:${label}`;
                option.textContent = label;
                fieldsOptgroup.appendChild(option);
            }
        });

        // Extract counters from the page
        const counters = document.querySelectorAll('.counter-box');
        counters.forEach(counter => {
            const title = counter.querySelector('.counter-title')?.textContent.trim();
            if (title) {
                const option = document.createElement('option');
                option.value = `counter:${title}`;
                option.textContent = title;
                countersOptgroup.appendChild(option);
            }
        });

        // Add some common fields if not found on page
        if (fieldsOptgroup.children.length === 0) {
            const commonFields = [
                'Population', 'Total Spending', 'Interest Payments', 
                'Total Debt', 'Reserves', 'Council Tax'
            ];
            commonFields.forEach(field => {
                const option = document.createElement('option');
                option.value = `field:${field}`;
                option.textContent = field;
                fieldsOptgroup.appendChild(option);
            });
        }

        // Remove optgroups if they're empty
        if (fieldsOptgroup.children.length === 0) {
            fieldsOptgroup.remove();
        }
        if (countersOptgroup.children.length === 0) {
            countersOptgroup.remove();
        }
    }

    // Static method to create flag button
    static createFlagButton(contentType, objectId, contentDescription = '', options = {}) {
        const {
            size = 'sm',
            text = 'Flag',
            className = 'border-yellow-300 text-yellow-700 bg-yellow-50 hover:bg-yellow-100'
        } = options;

        const sizeClasses = {
            'xs': 'px-2 py-1 text-xs',
            'sm': 'px-3 py-2 text-sm',
            'md': 'px-4 py-2 text-base',
            'lg': 'px-5 py-3 text-lg'
        }[size] || 'px-3 py-2 text-sm';

        return `
            <button type="button" 
                    class="inline-flex items-center border rounded-lg font-medium transition-colors flag-content-btn ${sizeClasses} ${className}"
                    data-content-type="${contentType}"
                    data-object-id="${objectId}"
                    data-content-description="${contentDescription}"
                    title="Flag this content for review">
                <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9"/>
                </svg>
                ${text}
            </button>
        `;
    }
} // End of FlaggingSystem class

// Initialize flagging system when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded event fired for flagging system');
    if (!window.flaggingSystem) {
        console.log('Creating new FlaggingSystem instance');
        window.flaggingSystem = new FlaggingSystem();
    } else {
        console.log('FlaggingSystem already exists');
    }
});

// Also try to initialize immediately if DOM is already loaded
if (document.readyState !== 'loading') {
    console.log('DOM already loaded, initializing flagging system immediately');
    if (!window.flaggingSystem) {
        window.flaggingSystem = new FlaggingSystem();
    }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FlaggingSystem;
}
} // End of if (typeof FlaggingSystem === 'undefined')
