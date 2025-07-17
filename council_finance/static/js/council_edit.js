/* Enhanced Council Edit JavaScript */
document.addEventListener('DOMContentLoaded', function() {
    // Modal elements
    const modal = document.getElementById('edit-modal');
    const closeModalBtn = document.getElementById('close-modal');
    const cancelEditBtn = document.getElementById('cancel-edit');
    const editForm = document.getElementById('edit-form');
    
    // Form elements
    const fieldInput = document.getElementById('edit-field');
    const yearInput = document.getElementById('edit-year');
    const valueInput = document.getElementById('contribution-value');
    const yearSelect = document.getElementById('year-select');
    const yearSelection = document.getElementById('year-selection');
    
    // Display elements
    const modalFieldName = document.getElementById('modal-field-name');
    const modalCouncilName = document.getElementById('modal-council-name');
    const fieldInfoTitle = document.getElementById('field-info-title');
    const fieldInfoDescription = document.getElementById('field-info-description');
    const inputLabel = document.getElementById('input-label');
    const helperText = document.getElementById('helper-text');
    const inputContainer = document.getElementById('input-container');
    const currentValue = document.getElementById('current-value');
    const currentSource = document.getElementById('current-source');
    
    // Toast elements
    const successToast = document.getElementById('success-toast');
    const errorToast = document.getElementById('error-toast');
    const successMessage = document.getElementById('success-message');
    const errorMessage = document.getElementById('error-message');

    // Council data
    const councilSlug = window.councilData?.slug || 'unknown';
    
    // Store current field information
    let currentFieldSlug = null;
    const councilName = window.councilData?.name || 'Council';

    /**
     * Show a toast notification
     */
    function showToast(type, message) {
        const toast = type === 'success' ? successToast : errorToast;
        const messageEl = type === 'success' ? successMessage : errorMessage;
        
        messageEl.textContent = message;
        toast.classList.remove('hidden');
        
        setTimeout(() => {
            toast.classList.add('hidden');
        }, 5000);
    }

    /**
     * Close the modal
     */
    function closeModal() {
        modal.classList.add('hidden');
        document.body.style.overflow = '';
        editForm.reset();
    }

    /**
     * Open the edit modal for a specific field
     */
    function openEditModal(fieldSlug, fieldName, yearId = null, currentVal = null, source = null) {
        // Set form data
        fieldInput.value = fieldSlug;
        if (yearId) {
            yearInput.value = yearId;
            yearSelect.value = yearId;
        }
        
        // Update display
        modalFieldName.textContent = fieldName;
        modalCouncilName.textContent = councilName;
        
        // Show modal
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        
        // Load field information
        loadFieldInfo(fieldSlug, currentVal, source);
        
        // Focus on value input
        setTimeout(() => {
            valueInput.focus();
        }, 100);
    }

    /**
     * Load field information from the server
     */
    async function loadFieldInfo(fieldSlug, currentVal = null, source = null) {
        // Store the current field slug for list field loading
        currentFieldSlug = fieldSlug;
        
        try {
            const response = await fetch(`/api/field/${fieldSlug}/info/`);
            if (!response.ok) throw new Error('Failed to load field info');
            
            const fieldData = await response.json();
            
            // Update field info
            fieldInfoTitle.textContent = fieldData.name;
            fieldInfoDescription.textContent = fieldData.description || 'No description available';
            inputLabel.textContent = fieldData.name;
            
            // Show/hide year selection for financial fields
            if (fieldData.category === 'financial') {
                yearSelection.classList.remove('hidden');
            } else {
                yearSelection.classList.add('hidden');
            }
            
            // Update helper text based on content type
            updateHelperText(fieldData.content_type);
            
            // Create appropriate input based on content type
            createInput(fieldData.content_type, currentVal);
            
            // Update current value display
            currentValue.textContent = currentVal || 'No data';
            currentSource.textContent = source || 'No source information';
            
            // Load recent activity
            loadRecentActivity(fieldSlug);
            
        } catch (error) {
            console.error('Error loading field info:', error);
            showToast('error', 'Failed to load field information');
        }
    }

    /**
     * Update helper text based on content type
     */
    function updateHelperText(contentType) {
        const helpers = {
            'monetary': 'Enter amount in pounds (£). You can include commas or decimal places.',
            'integer': 'Enter a whole number only. No decimal places or commas.',
            'text': 'Enter text information. Keep it concise and accurate.',
            'url': 'Enter a valid URL starting with https://',
            'percentage': 'Enter percentage as a number (e.g., 15.5 for 15.5%)',
            'list': 'Select an option from the dropdown list below.',
            'date': 'Enter date in format YYYY-MM-DD'
        };
        
        helperText.textContent = helpers[contentType] || 'Please enter a valid value';
    }

    /**
     * Create appropriate input element based on content type
     */
    function createInput(contentType, currentVal = null) {
        let inputHTML = '';
        
        switch (contentType) {
            case 'monetary':
                inputHTML = `
                    <div class="relative">
                        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <span class="text-gray-500 text-sm">£</span>
                        </div>
                        <input type="text" 
                               id="contribution-value" 
                               name="value" 
                               class="block w-full pl-8 pr-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                               placeholder="0.00" 
                               pattern="[0-9,.]+"
                               value="${currentVal || ''}"
                               required>
                    </div>
                `;
                break;
                
            case 'integer':
                inputHTML = `
                    <input type="number" 
                           id="contribution-value" 
                           name="value" 
                           class="block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                           placeholder="Enter number..." 
                           step="1"
                           value="${currentVal || ''}"
                           required>
                `;
                break;
                
            case 'url':
                inputHTML = `
                    <input type="url" 
                           id="contribution-value" 
                           name="value" 
                           class="block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                           placeholder="https://example.com" 
                           pattern="https://.*"
                           value="${currentVal || ''}"
                           required>
                `;
                break;
                
            case 'percentage':
                inputHTML = `
                    <div class="relative">
                        <input type="number" 
                               id="contribution-value" 
                               name="value" 
                               class="block w-full pr-8 pl-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                               placeholder="0.0" 
                               step="0.1"
                               min="0"
                               max="100"
                               value="${currentVal || ''}"
                               required>
                        <div class="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                            <span class="text-gray-500 text-sm">%</span>
                        </div>
                    </div>
                `;
                break;
                
            case 'list':
                // For list fields, show loading state - options will be loaded by loadListOptions
                inputHTML = `
                    <div class="text-center py-4">
                        <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-blue-600 inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        <span class="text-sm text-gray-600">Loading options...</span>
                    </div>
                `;
                break;
                
            default:
                inputHTML = `
                    <input type="text" 
                           id="contribution-value" 
                           name="value" 
                           class="block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                           placeholder="Enter value..." 
                           value="${currentVal || ''}"
                           required>
                `;
        }
        
        inputContainer.innerHTML = inputHTML;
        
        // If this is a list field, load the options
        if (contentType === 'list') {
            loadListOptions(currentFieldSlug, currentVal);
        }
    }

    /**
     * Load options for list type fields
     */
    async function loadListOptions(fieldSlug, currentValue = null) {
        try {
            const response = await fetch(`/api/field/${fieldSlug}/options/`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            const container = document.getElementById('input-container');  // Use input-container instead
            
            if (!data.options || data.options.length === 0) {
                container.innerHTML = `
                    <div class="text-center py-4 text-red-600">
                        <svg class="w-5 h-5 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                        <p class="text-sm">No options available for this field</p>
                    </div>
                `;
                return;
            }
            
            // Build the select dropdown
            let optionsHTML = '<option value="">Please select...</option>';
            data.options.forEach(option => {
                const selected = currentValue && currentValue == option.id ? 'selected' : '';
                optionsHTML += `<option value="${option.id}" ${selected}>${option.name}</option>`;
            });
            
            container.innerHTML = `
                <select id="contribution-value" 
                        name="value" 
                        class="block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        required>
                    ${optionsHTML}
                </select>
            `;
            
        } catch (error) {
            console.error('Error loading list options:', error);
            const container = document.getElementById('input-container');  // Use input-container instead
            container.innerHTML = `
                <div class="text-center py-4 text-red-600">
                    <svg class="w-5 h-5 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                    <p class="text-sm">Error loading options: ${error.message}</p>
                    <p class="text-xs text-gray-500 mt-1">Please try again or contact support</p>
                </div>
            `;
        }
    }

    /**
     * Load recent activity for this field/council
     */
    async function loadRecentActivity(fieldSlug) {
        try {
            const response = await fetch(`/api/council/${councilSlug}/recent-activity/${fieldSlug}/`);
            if (!response.ok) throw new Error('Failed to load recent activity');
            
            const activities = await response.json();
            const recentList = document.getElementById('recent-list');
            
            if (activities.length === 0) {
                recentList.innerHTML = '<div class="text-center text-gray-400 py-2">No recent activity</div>';
                return;
            }
            
            const activityHTML = activities.map(activity => `
                <div class="flex items-center justify-between py-1">
                    <div class="text-xs">
                        <div class="font-medium">${activity.field_name}</div>
                        <div class="text-gray-500">${activity.time_ago}</div>
                    </div>
                    <div class="text-xs font-mono text-gray-600">${activity.value || 'N/A'}</div>
                </div>
            `).join('');
            
            recentList.innerHTML = activityHTML;
            
        } catch (error) {
            console.error('Error loading recent activity:', error);
            document.getElementById('recent-list').innerHTML = '<div class="text-center text-gray-400 py-2">Unable to load activity</div>';
        }
    }

    /**
     * Handle form submission
     */
    editForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const submitBtn = document.getElementById('submit-edit');
        const originalText = submitBtn.innerHTML;
        
        // Show loading state
        submitBtn.disabled = true;
        submitBtn.innerHTML = `
            <span class="inline-flex items-center">
                <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Submitting...
            </span>
        `;
        
        try {
            const formData = new FormData(editForm);
            const response = await fetch(editForm.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                showToast('success', result.message || 'Contribution submitted successfully!');
                closeModal();
                
                // Refresh the page to show updated data
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                throw new Error(result.message || 'Submission failed');
            }
            
        } catch (error) {
            console.error('Error submitting contribution:', error);
            showToast('error', error.message || 'Failed to submit contribution');
        } finally {
            // Restore button
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    });

    // Event listeners
    closeModalBtn.addEventListener('click', closeModal);
    cancelEditBtn.addEventListener('click', closeModal);
    
    // Close modal on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
            closeModal();
        }
    });
    
    // Close modal on backdrop click
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeModal();
        }
    });

    // Attach to edit buttons
    document.body.addEventListener('click', function(e) {
        if (e.target.classList.contains('edit-missing') || e.target.closest('.edit-missing')) {
            e.preventDefault();
            
            const btn = e.target.classList.contains('edit-missing') ? e.target : e.target.closest('.edit-missing');
            const fieldSlug = btn.dataset.field;
            const fieldName = btn.dataset.fieldName;
            const yearId = btn.dataset.year || null;
            const currentVal = btn.dataset.currentValue || null;
            
            openEditModal(fieldSlug, fieldName, yearId, currentVal);
        }
        
        // Handle direct edit links (from header)
        if (e.target.matches('a[href*="tab=edit&focus="]')) {
            e.preventDefault();
            
            const url = new URL(e.target.href);
            const focus = url.searchParams.get('focus');
            
            if (focus) {
                // Convert focus parameter to field data
                const fieldMappings = {
                    'council_type': 'Council Type',
                    'council_website': 'Council Website', 
                    'council_nation': 'Council Nation'
                };
                
                const fieldName = fieldMappings[focus] || focus.replace('_', ' ');
                openEditModal(focus, fieldName);
            }
        }
    });

    // Make the function globally available
    window.openEditModal = openEditModal;
    
    // Handle year selection changes for financial data table
    const editYearSelect = document.getElementById('edit-year-select');
    if (editYearSelect) {
        editYearSelect.addEventListener('change', function() {
            const selectedYear = this.value;
            const tableContainer = document.getElementById('edit-table-container');
            
            if (!tableContainer) return;
            
            // Show loading state
            tableContainer.innerHTML = `
                <div class="flex items-center justify-center py-8">
                    <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Loading financial data...
                </div>
            `;
            
            // Load new data via AJAX
            fetch(`/councils/${councilSlug}/edit-table/?year=${selectedYear}`, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => {
                if (!response.ok) throw new Error('Failed to load data');
                return response.text();
            })
            .then(html => {
                tableContainer.innerHTML = html;
            })
            .catch(error => {
                console.error('Error loading financial data:', error);
                tableContainer.innerHTML = `
                    <div class="text-center py-8 text-red-600">
                        <svg class="w-12 h-12 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                        <p class="text-lg font-medium">Failed to load data</p>
                        <p class="text-sm">Please try refreshing the page</p>
                    </div>
                `;
            });
        });
    }
});
