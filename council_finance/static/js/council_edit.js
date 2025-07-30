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
     * Validate URL for security and accessibility
     */
    async function validateURL(url) {
        // Basic URL format validation
        try {Be careful 
            const urlObj = new URL(url);
            
            // Check for allowed protocols
            const allowedProtocols = ['http:', 'https:'];
            if (!allowedProtocols.includes(urlObj.protocol)) {
                return {
                    valid: false,
                    message: 'Only HTTP and HTTPS URLs are allowed'
                };
            }
            
            // Check for suspicious domains or patterns
            const suspiciousDomains = [
                'bit.ly', 'tinyurl.com', 'goo.gl', 't.co', 'ow.ly',
                'localhost', '127.0.0.1', '0.0.0.0'
            ];
            
            const domain = urlObj.hostname.toLowerCase();
            if (suspiciousDomains.some(suspicious => domain.includes(suspicious))) {
                return {
                    valid: false,
                    message: 'URL shorteners and local addresses are not allowed for security reasons'
                };
            }
            
            // Check if URL is accessible (basic connectivity test)
            try {
                const testResponse = await fetch('/api/validate-url/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    },
                    body: JSON.stringify({ 
                        url: url,
                        field_slug: currentFieldSlug 
                    })
                });
                
                const validationResult = await testResponse.json();
                return validationResult;
                
            } catch (fetchError) {
                // If validation service is unavailable, allow URL but warn
                console.warn('URL validation service unavailable:', fetchError);
                return {
                    valid: true,
                    message: 'URL format appears valid (validation service unavailable)'
                };
            }
            
        } catch (urlError) {
            return {
                valid: false,
                message: 'Invalid URL format'
            };
        }
    }

    /**
     * Show a toast notification
     */
    function showToast(type, message) {
        const toast = type === 'success' ? successToast : errorToast;
        const messageEl = type === 'success' ? successMessage : errorMessage;
        
        if (messageEl && toast) {
            messageEl.textContent = message;
            toast.classList.remove('hidden');
            
            setTimeout(() => {
                toast.classList.add('hidden');
            }, 5000);
        } else {
            console.log(`${type.toUpperCase()}: ${message}`);
        }
    }

    /**
     * Close the modal
     */
    function closeModal() {
        if (modal) {
            modal.classList.add('hidden');
        }
        document.body.style.overflow = '';
        if (editForm) {
            editForm.reset();
        }
    }

    /**
     * Open the edit modal for a specific field
     */
    function openEditModal(fieldSlug, fieldName, yearId = null, currentVal = null, source = null) {
        if (fieldInput) fieldInput.value = fieldSlug;
        if (yearInput) yearInput.value = yearId || '';
        if (modalFieldName) modalFieldName.textContent = fieldName;
        if (modalCouncilName) modalCouncilName.textContent = councilName;
        
        loadFieldInfo(fieldSlug, currentVal, source);
        
        if (modal) {
            modal.classList.remove('hidden');
        }
        document.body.style.overflow = 'hidden';
    }

    /**
     * Load field information from the server
     */
    async function loadFieldInfo(fieldSlug, currentVal = null, source = null) {
        currentFieldSlug = fieldSlug;
        
        try {
            const response = await fetch(`/api/field/${fieldSlug}/info/`);
            if (!response.ok) throw new Error('Failed to load field info');
            
            const fieldData = await response.json();
            
            if (fieldInfoTitle) fieldInfoTitle.textContent = fieldData.name;
            if (fieldInfoDescription) fieldInfoDescription.textContent = fieldData.description || 'No description available';
            if (inputLabel) inputLabel.textContent = fieldData.name;
            
            if (yearSelection) {
                if (fieldData.category === 'financial') {
                    yearSelection.classList.remove('hidden');
                } else {
                    yearSelection.classList.add('hidden');
                }
            }
            
            updateHelperText(fieldData.content_type);
            createInput(fieldData.content_type, currentVal);
            
            if (currentValue) currentValue.textContent = currentVal || 'No data';
            if (currentSource) currentSource.textContent = source || 'No source information';
            
            loadRecentActivity(fieldSlug);
            
        } catch (error) {
            console.error('Error loading field info:', error);
            showToast('error', 'Failed to load field information');
        }
    }

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
        
        if (helperText) {
            helperText.textContent = helpers[contentType] || 'Please enter a valid value';
        }
    }

    function createInput(contentType, currentVal = null) {
        let inputHTML = '';
        
        switch (contentType) {
            case 'monetary':
                inputHTML = `<div class="relative"><div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><span class="text-gray-500 text-sm">£</span></div><input type="text" id="contribution-value" name="value" class="block w-full pl-8 pr-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500" placeholder="0.00" pattern="[0-9,.]+" value="${currentVal || ''}" required></div>`;
                break;
            case 'integer':
                inputHTML = `<input type="number" id="contribution-value" name="value" class="block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500" placeholder="Enter number..." step="1" value="${currentVal || ''}" required>`;
                break;
            case 'url':
                inputHTML = `<input type="url" id="contribution-value" name="value" class="block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500" placeholder="https://example.com" pattern="https://.*" value="${currentVal || ''}" required>`;
                break;
            case 'percentage':
                inputHTML = `<div class="relative"><input type="number" id="contribution-value" name="value" class="block w-full pr-8 pl-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500" placeholder="0.0" step="0.1" min="0" max="100" value="${currentVal || ''}" required><div class="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none"><span class="text-gray-500 text-sm">%</span></div></div>`;
                break;
            case 'list':
                inputHTML = `<div class="text-center py-4"><svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-blue-600 inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 714 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg><span class="text-sm text-gray-600">Loading options...</span></div>`;
                break;
            default:
                inputHTML = `<input type="text" id="contribution-value" name="value" class="block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500" placeholder="Enter value..." value="${currentVal || ''}" required>`;
        }
        
        if (inputContainer) {
            inputContainer.innerHTML = inputHTML;
        }
        
        if (contentType === 'list') {
            loadListOptions(currentFieldSlug, currentVal);
        }
    }

    async function loadListOptions(fieldSlug, currentValue = null) {
        try {
            const response = await fetch(`/api/field/${fieldSlug}/options/`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            const container = document.getElementById('input-container');
            
            if (!container) {
                console.warn('Input container not found');
                return;
            }
            
            if (!data.options || data.options.length === 0) {
                container.innerHTML = `<div class="text-center py-4 text-red-600"><svg class="w-5 h-5 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg><p class="text-sm">No options available for this field</p></div>`;
                return;
            }
            
            let optionsHTML = '<option value="">Please select...</option>';
            data.options.forEach(option => {
                const selected = currentValue && currentValue == option.id ? 'selected' : '';
                optionsHTML += `<option value="${option.id}" ${selected}>${option.name}</option>`;
            });
            
            container.innerHTML = `<select id="contribution-value" name="value" class="block w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500" required>${optionsHTML}</select>`;
            
        } catch (error) {
            console.error('Error loading list options:', error);
            const container = document.getElementById('input-container');
            if (container) {
                container.innerHTML = `<div class="text-center py-4 text-red-600"><svg class="w-5 h-5 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg><p class="text-sm">Error loading options: ${error.message}</p></div>`;
            }
        }
    }

    async function loadRecentActivity(fieldSlug) {
        try {
            const response = await fetch(`/api/council/${councilSlug}/recent-activity/${fieldSlug}/`);
            if (!response.ok) throw new Error('Failed to load recent activity');
            
            const activities = await response.json();
            const recentList = document.getElementById('recent-list');
            
            if (!recentList) {
                console.warn('Recent list element not found');
                return;
            }
            
            if (activities.length === 0) {
                recentList.innerHTML = '<div class="text-center text-gray-400 py-2">No recent activity</div>';
                return;
            }
            
            const activityHTML = activities.map(activity => `<div class="flex items-center justify-between py-1"><div class="text-xs"><div class="font-medium">${activity.field_name}</div><div class="text-gray-500">${activity.time_ago}</div></div><div class="text-xs font-mono text-gray-600">${activity.value || 'N/A'}</div></div>`).join('');
            
            recentList.innerHTML = activityHTML;
            
        } catch (error) {
            console.error('Error loading recent activity:', error);
            const recentList = document.getElementById('recent-list');
            if (recentList) {
                recentList.innerHTML = '<div class="text-center text-gray-400 py-2">Unable to load activity</div>';
            }
        }
    }

    // Form submission handler
    if (editForm) {
        editForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const submitBtn = document.getElementById('submit-edit');
            const originalText = submitBtn ? submitBtn.innerHTML : '';
            
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="inline-flex items-center"><svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 818-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>Submitting...</span>';
            }
            
            try {
                // Get field information to check content type
                const fieldResponse = await fetch(`/api/field/${currentFieldSlug}/info/`);
                if (!fieldResponse.ok) throw new Error('Failed to get field information');
                const fieldData = await fieldResponse.json();
                
                // Validate URL fields
                if (fieldData.content_type === 'url') {
                    const urlValue = valueInput.value.trim();
                    if (urlValue) {
                        const validationResult = await validateURL(urlValue);
                        if (!validationResult.valid) {
                            throw new Error(validationResult.message);
                        }
                    }
                }
                
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
                    setTimeout(() => window.location.reload(), 1000);
                } else {
                    throw new Error(result.message || 'Submission failed');
                }
            } catch (error) {
                console.error('Error submitting contribution:', error);
                showToast('error', error.message || 'Failed to submit contribution');
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalText;
                }
            }
        });
    }

    // Event listeners
    if (closeModalBtn) closeModalBtn.addEventListener('click', closeModal);
    if (cancelEditBtn) cancelEditBtn.addEventListener('click', closeModal);

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal && !modal.classList.contains('hidden')) {
            closeModal();
        }
    });
    
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeModal();
            }
        });
    }

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
        
        if (e.target.matches('a[href*="tab=edit&focus="]')) {
            e.preventDefault();
            
            const url = new URL(e.target.href);
            const focus = url.searchParams.get('focus');
            
            if (focus) {
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

    window.openEditModal = openEditModal;    // Handle year selection changes for financial data table
    const editYearSelect = document.getElementById('edit-year-select');
    if (editYearSelect) {
        editYearSelect.addEventListener('change', function() {
            const selectedYear = this.value;
            const tableContainer = document.getElementById('edit-table-container');
            
            if (!tableContainer) return;
            
            tableContainer.innerHTML = '<div class="flex items-center justify-center py-8"><svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 818-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 714 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>Loading financial data...</div>';
              fetch(`${window.location.pathname}edit-table/?year=${encodeURIComponent(selectedYear)}`, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => {
                // Check for JSON response which might contain error info
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.indexOf('application/json') !== -1) {
                    return response.json().then(data => {
                        // If it's JSON, it's probably an error
                        if (!response.ok) {
                            throw new Error(data.message || 'Failed to load data');
                        }
                        return data;
                    });
                }
                
                if (!response.ok) throw new Error('Failed to load data');
                return response.text();
            })
            .then(result => {
                // Handle both text and JSON responses
                if (typeof result === 'string') {
                    tableContainer.innerHTML = result;
                } else {
                    // Should not normally reach here with successful JSON
                    tableContainer.innerHTML = '<div class="text-center py-8"><p class="text-lg font-medium">Data loaded successfully</p></div>';
                }
            })
            .catch(error => {
                console.error('Error loading financial data:', error);
                tableContainer.innerHTML = '<div class="text-center py-8 text-red-600"><svg class="w-12 h-12 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg><p class="text-lg font-medium">Error</p><p class="text-sm">' + error.message + '</p></div>';
            });
        });
    }
});
