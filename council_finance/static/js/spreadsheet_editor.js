/**
 * Modern Spreadsheet-like Council Edit Interface
 * Provides Excel/Google Sheets-like editing experience with automatic saving and points awarding
 */

class SpreadsheetEditor {
    constructor() {
        this.currentField = null;
        this.currentYear = null;
        this.unsavedChanges = false;
        this.autoSaveTimeout = null;
        this.financialData = [];
        this.pendingSlugs = [];
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadFinancialData();
        this.updateProgress();
        this.setupAutoSave();
    }

    setupEventListeners() {
        // Editable cell clicks
        document.addEventListener('click', (e) => {
            if (e.target.closest('.editable-cell')) {
                this.handleCellClick(e.target.closest('.editable-cell'));
            }
        });

        // Delete button clicks
        document.addEventListener('click', (e) => {
            if (e.target.closest('.delete-field-btn')) {
                e.preventDefault();
                this.handleDeleteField(e.target.closest('.delete-field-btn'));
            }
        });

        // Year selector change
        const yearSelector = document.getElementById('year-selector');
        if (yearSelector) {
            yearSelector.addEventListener('change', (e) => {
                this.changeFinancialYear(e.target.value);
            });
        }


        // Modal controls (legacy - kept for compatibility)
        const closeModal = document.getElementById('close-edit-modal');
        if (closeModal) {
            closeModal.addEventListener('click', () => {
                this.closeEditModal();
            });
        }

        const cancelEdit = document.getElementById('cancel-edit');
        if (cancelEdit) {
            cancelEdit.addEventListener('click', () => {
                this.closeEditModal();
            });
        }

        // Form submission (legacy - kept for compatibility)
        const editForm = document.getElementById('inline-edit-form');
        if (editForm) {
            editForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveFieldData();
            });
        }

        // Bulk actions
        document.getElementById('bulk-add-btn')?.addEventListener('click', () => {
            this.showBulkAddModal();
        });

        document.getElementById('export-data-btn')?.addEventListener('click', () => {
            this.exportToCSV();
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            this.handleKeyboardShortcuts(e);
        });

        // Close modal on outside click (legacy - kept for compatibility)
        const inlineModal = document.getElementById('inline-edit-modal');
        if (inlineModal) {
            inlineModal.addEventListener('click', (e) => {
                if (e.target.id === 'inline-edit-modal') {
                    this.closeEditModal();
                }
            });
        }
    }

    handleCellClick(cell) {
        const fieldSlug = cell.dataset.field;
        const row = cell.closest('tr');
        const category = row.dataset.category;
        
        // Check if this is a characteristic field (non-temporal) or financial field (temporal)
        const isCharacteristic = category === 'characteristics';
        
        this.currentField = fieldSlug;
        // Only set year for financial data, characteristics don't use years
        this.currentYear = isCharacteristic ? null : this.getCurrentYearId();
        
        // Show year context for financial fields only
        if (!isCharacteristic) {
            const yearDisplay = this.getCurrentYear();
            console.log(`Editing financial field: ${fieldSlug} for year: ${yearDisplay}`);
        } else {
            console.log(`Editing characteristic field: ${fieldSlug} (year-independent)`);
        }
        
        // Start inline editing instead of opening modal
        this.startInlineEdit(cell, fieldSlug, category);
    }

    startInlineEdit(cell, fieldSlug, category) {
        // Prevent multiple inline edits
        if (document.querySelector('.inline-input-active')) {
            return;
        }

        const currentValue = this.getCurrentCellValue(cell);
        const row = cell.closest('tr');
        const fieldType = this.getFieldType(fieldSlug, row);
        
        // Create inline input
        const input = document.createElement('input');
        input.type = 'text';
        input.value = currentValue;
        input.className = 'inline-input-active w-full px-2 py-1 border border-blue-500 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500';
        input.dataset.fieldSlug = fieldSlug;
        input.dataset.originalValue = currentValue;
        
        // Set placeholder based on field type
        input.placeholder = this.getFieldPlaceholder(fieldSlug, fieldType);
        
        // Replace cell content with input
        const originalContent = cell.innerHTML;
        cell.innerHTML = '';
        cell.appendChild(input);
        cell.classList.add('inline-editing');
        
        // Focus and select all text
        input.focus();
        input.select();
        
        // Handle input events
        input.addEventListener('blur', () => this.handleInlineEditComplete(cell, input, originalContent));
        input.addEventListener('keydown', (e) => this.handleInlineEditKeydown(e, cell, input, originalContent));
        input.addEventListener('input', () => this.handleInlineInputChange(input, fieldSlug));
    }

    getCurrentCellValue(cell) {
        const textSpan = cell.querySelector('span:not(.text-gray-400)');
        if (textSpan) {
            // Extract raw value from formatted display
            let value = textSpan.textContent.trim();
            // Remove currency symbols, commas, etc.
            value = value.replace(/[£$,]/g, '').replace(/%$/, '');
            return value === 'Click to add...' ? '' : value;
        }
        return '';
    }

    getFieldType(fieldSlug, row = null) {
        // Council characteristics (don't need year)
        if (fieldSlug === 'council_type' || fieldSlug === 'council_nation') return 'select';
        if (fieldSlug.includes('website') || fieldSlug.includes('url')) return 'url';
        
        // Try to determine from row data category if available
        if (row) {
            const category = row.dataset.category;
            if (category === 'characteristics') {
                return fieldSlug.includes('website') ? 'url' : 'text';
            } else if (category === 'financial' || category !== 'characteristics') {
                // All non-characteristic fields are financial and need year
                return 'monetary';
            }
        }
        
        // Fallback to name-based detection for financial fields (need year)
        if (fieldSlug.includes('reserves') || fieldSlug.includes('debt') || fieldSlug.includes('income') || 
            fieldSlug.includes('expenditure') || fieldSlug.includes('cash') || fieldSlug.includes('revenue') ||
            fieldSlug.includes('balance') || fieldSlug.includes('financial') || fieldSlug.includes('funding') ||
            fieldSlug.includes('asset') || fieldSlug.includes('liability') || fieldSlug.includes('budget') ||
            fieldSlug.includes('tax') || fieldSlug.includes('grant') || fieldSlug.includes('surplus') ||
            fieldSlug.includes('deficit') || fieldSlug.includes('cost') || fieldSlug.includes('spending')) {
            return 'monetary';
        }
        
        if (fieldSlug.includes('percentage') || fieldSlug.includes('rate')) return 'percentage';
        return 'text';
    }

    getFieldPlaceholder(fieldSlug, fieldType) {
        switch (fieldType) {
            case 'monetary':
                return 'Enter amount (e.g., 1000000 for £1M)';
            case 'percentage':
                return 'Enter percentage (e.g., 15.5)';
            case 'url':
                return 'Enter full URL (e.g., https://example.com)';
            default:
                return `Enter ${fieldSlug.replace(/_/g, ' ')}...`;
        }
    }

    handleInlineEditKeydown(e, cell, input, originalContent) {
        if (e.key === 'Enter') {
            e.preventDefault();
            input.blur(); // Trigger completion
        } else if (e.key === 'Escape') {
            e.preventDefault();
            this.cancelInlineEdit(cell, input, originalContent);
        } else if (e.key === 'Tab') {
            e.preventDefault();
            // Save current field and move to next
            this.handleTabNavigation(cell, input, originalContent, e.shiftKey);
        }
    }

    async handleTabNavigation(cell, input, originalContent, isShiftTab) {
        // First save the current field if it has changes
        const newValue = input.value.trim();
        const originalValue = input.dataset.originalValue;
        const fieldSlug = input.dataset.fieldSlug;
        
        if (newValue !== originalValue && newValue) {
            // Save the current field
            try {
                await this.saveInlineEdit(cell, input, originalContent, newValue, fieldSlug);
            } catch (error) {
                // If save fails, stay in current field
                return;
            }
        } else {
            // No changes, just cancel editing
            this.cancelInlineEdit(cell, input, originalContent);
        }
        
        // Find the next editable field
        const nextCell = this.findNextEditableCell(cell, isShiftTab);
        if (nextCell) {
            // Small delay to ensure current edit is completed
            setTimeout(() => {
                nextCell.click();
            }, 100);
        }
    }

    findNextEditableCell(currentCell, reverse = false) {
        const allCells = Array.from(document.querySelectorAll('.editable-cell'));
        const currentIndex = allCells.indexOf(currentCell);
        
        if (currentIndex === -1) return null;
        
        let nextIndex;
        if (reverse) {
            // Shift+Tab: go to previous cell
            nextIndex = currentIndex - 1;
            if (nextIndex < 0) nextIndex = allCells.length - 1; // Wrap to last
        } else {
            // Tab: go to next cell
            nextIndex = currentIndex + 1;
            if (nextIndex >= allCells.length) nextIndex = 0; // Wrap to first
        }
        
        return allCells[nextIndex];
    }

    handleInlineInputChange(input, fieldSlug) {
        const value = input.value.trim();
        const row = input.closest('tr');
        const fieldType = this.getFieldType(fieldSlug, row);
        
        // Real-time validation feedback
        input.classList.remove('border-red-500', 'border-yellow-500', 'border-green-500');
        
        if (fieldType === 'monetary' && value) {
            const numericValue = parseFloat(value.replace(/[^\d.]/g, ''));
            if (!isNaN(numericValue)) {
                if (this.shouldWarnAboutFinancialAmount(numericValue)) {
                    input.classList.add('border-yellow-500');
                } else {
                    input.classList.add('border-green-500');
                }
            } else {
                input.classList.add('border-red-500');
            }
        } else if (value) {
            input.classList.add('border-green-500');
        }
    }

    shouldWarnAboutFinancialAmount(amount) {
        // Warn for amounts that might be missing zeros (too small for council finances)
        // or have too many digits (might have extra zeros)
        const digitCount = Math.floor(Math.log10(Math.abs(amount))) + 1;
        
        // Warn if amount seems too small (3-6 digits) or too large (>10 digits)
        return (digitCount >= 3 && digitCount <= 6) || digitCount > 10;
    }

    async handleInlineEditComplete(cell, input, originalContent) {
        const newValue = input.value.trim();
        const fieldSlug = input.dataset.fieldSlug;
        const originalValue = input.dataset.originalValue;
        
        // If no change, just restore
        if (newValue === originalValue) {
            this.cancelInlineEdit(cell, input, originalContent);
            return;
        }
        
        // Allow empty values to clear fields
        const isClearing = newValue === '' && originalValue !== '';
        if (!isClearing && !newValue && !originalValue) {
            // Both empty, no change
            this.cancelInlineEdit(cell, input, originalContent);
            return;
        }
        
        const row = cell.closest('tr');
        const fieldType = this.getFieldType(fieldSlug, row);
        
        // Check if we need validation modal for financial amounts
        if (fieldType === 'monetary' && newValue) {
            const numericValue = parseFloat(newValue.replace(/[^\d.]/g, ''));
            if (!isNaN(numericValue) && this.shouldWarnAboutFinancialAmount(numericValue)) {
                this.showFinancialValidationModal(cell, input, originalContent, newValue, numericValue, fieldSlug);
                return;
            }
        }
        
        // Proceed with save
        await this.saveInlineEdit(cell, input, originalContent, newValue, fieldSlug);
    }

    showFinancialValidationModal(cell, input, originalContent, enteredValue, numericValue, fieldSlug) {
        const digitCount = Math.floor(Math.log10(Math.abs(numericValue))) + 1;
        let suggestedValue, warningMessage;
        
        if (digitCount >= 3 && digitCount <= 6) {
            // Suggest adding zeros
            suggestedValue = numericValue * 1000;
            warningMessage = `You entered ${this.formatCurrency(numericValue)}. Did you mean ${this.formatCurrency(suggestedValue)}? This might be missing three zeros.`;
        } else if (digitCount > 10) {
            // Suggest removing zeros
            suggestedValue = numericValue / 1000;
            warningMessage = `You entered ${this.formatCurrency(numericValue)}. Did you mean ${this.formatCurrency(suggestedValue)}? This might have extra zeros.`;
        }
        
        // Create validation modal
        this.createValidationModal(cell, input, originalContent, enteredValue, suggestedValue, warningMessage, fieldSlug);
    }

    createValidationModal(cell, input, originalContent, enteredValue, suggestedValue, warningMessage, fieldSlug) {
        // Remove existing validation modal if any
        const existingModal = document.getElementById('validation-modal');
        if (existingModal) existingModal.remove();
        
        const modal = document.createElement('div');
        modal.id = 'validation-modal';
        modal.className = 'fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50';
        
        modal.innerHTML = `
            <div class="relative top-20 mx-auto p-6 border w-11/12 max-w-md shadow-lg rounded-md bg-white">
                <div class="mt-3">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-lg font-medium text-gray-900">Verify Amount</h3>
                        <button type="button" class="text-gray-400 hover:text-gray-600" id="close-validation-modal">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                            </svg>
                        </button>
                    </div>
                    
                    <div class="mb-6">
                        <div class="flex items-start">
                            <div class="flex-shrink-0">
                                <svg class="w-6 h-6 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>
                                </svg>
                            </div>
                            <div class="ml-3">
                                <p class="text-sm text-gray-700">${warningMessage}</p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="flex flex-col space-y-3">
                        <button type="button" 
                                id="use-entered-value" 
                                class="w-full px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50">
                            Keep as entered: ${this.formatCurrency(parseFloat(enteredValue.replace(/[^\d.]/g, '')))}
                        </button>
                        <button type="button" 
                                id="use-suggested-value" 
                                class="w-full px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700">
                            Use suggested: ${this.formatCurrency(suggestedValue)}
                        </button>
                        <button type="button" 
                                id="cancel-validation" 
                                class="w-full px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50">
                            Cancel and edit again
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Add event listeners
        document.getElementById('close-validation-modal').addEventListener('click', () => {
            modal.remove();
            this.cancelInlineEdit(cell, input, originalContent);
        });
        
        document.getElementById('use-entered-value').addEventListener('click', async () => {
            modal.remove();
            await this.saveInlineEdit(cell, input, originalContent, enteredValue, fieldSlug);
        });
        
        document.getElementById('use-suggested-value').addEventListener('click', async () => {
            modal.remove();
            await this.saveInlineEdit(cell, input, originalContent, suggestedValue.toString(), fieldSlug);
        });
        
        document.getElementById('cancel-validation').addEventListener('click', () => {
            modal.remove();
            // Return to editing mode
            input.focus();
            input.select();
        });
        
        // Close on outside click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
                this.cancelInlineEdit(cell, input, originalContent);
            }
        });
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('en-GB', {
            style: 'currency',
            currency: 'GBP'
        }).format(amount);
    }

    async saveInlineEdit(cell, input, originalContent, newValue, fieldSlug) {
        // Show loading state
        input.disabled = true;
        input.classList.add('opacity-50');
        
        try {
            // Prepare form data
            const formData = new FormData();
            formData.append('field', fieldSlug);
            formData.append('value', newValue);
            
            // Only add year for financial fields
            const row = cell.closest('tr');
            const fieldType = this.getFieldType(fieldSlug, row);
            console.log(`Saving field: ${fieldSlug}, type: ${fieldType}, currentYear: ${this.currentYear}`);
            
            if (fieldType === 'monetary' && this.currentYear) {
                formData.append('year', this.currentYear);
                console.log(`Added year parameter: ${this.currentYear}`);
            }
            
            // Debug: Log all form data
            console.log('Form data being sent:');
            for (let [key, value] of formData.entries()) {
                console.log(`  ${key}: ${value}`);
            }
            
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
            const response = await fetch('/api/council/contribute/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken ? csrfToken.value : ''
                }
            });

            const result = await response.json();

            if (response.ok) {
                // Success - update cell with new value
                this.completeInlineEdit(cell, input, newValue, fieldSlug);
                this.updateRowStatus(fieldSlug, 'complete');
                this.updateProgress();
                this.showToast('success', `Data saved successfully! ${result.points_awarded || 0} points awarded.`);
                this.markLastSaved();
            } else {
                console.error('API Error Response:', result);
                throw new Error(result.error || result.message || `Server error: ${response.status}`);
            }
        } catch (error) {
            console.error('Error saving data:', error);
            this.showToast('error', error.message || 'An error occurred while saving. Please try again.');
            // Restore original content on error
            this.cancelInlineEdit(cell, input, originalContent);
        }
    }

    completeInlineEdit(cell, input, newValue, fieldSlug) {
        // Update cell with formatted value
        cell.classList.remove('inline-editing');
        cell.innerHTML = '';
        this.updateCellValue(fieldSlug, newValue);
    }

    cancelInlineEdit(cell, input, originalContent) {
        cell.classList.remove('inline-editing');
        cell.innerHTML = originalContent;
    }

    openEditModal(fieldSlug, category) {
        const modal = document.getElementById('inline-edit-modal');
        const titleElement = document.getElementById('edit-modal-title');
        const fieldInput = document.getElementById('edit-field-slug');
        const yearInput = document.getElementById('edit-year-id');
        const valueInput = document.getElementById('edit-value-input');
        const valueSelect = document.getElementById('edit-value-select');
        const sourceInput = document.getElementById('edit-source-input');
        
        if (!modal) return;

        // Set field information with null checks
        if (fieldInput) fieldInput.value = fieldSlug;
        if (yearInput) yearInput.value = this.currentYear || '';
        
        // Clear previous values
        if (valueInput) valueInput.value = '';
        if (valueSelect) valueSelect.value = '';
        if (sourceInput) sourceInput.value = '';
        
        // Get field display name
        const fieldName = this.getFieldDisplayName(fieldSlug);
        if (titleElement) titleElement.textContent = `Edit ${fieldName}`;

        // Load field options if it's a select field
        this.loadFieldOptions(fieldSlug, valueInput, valueSelect);

        // Show modal
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        
        // Focus on input with null checks
        setTimeout(() => {
            if (valueInput && valueSelect) {
                const visibleInput = valueInput.classList.contains('hidden') ? valueSelect : valueInput;
                if (visibleInput) visibleInput.focus();
            }
        }, 100);
    }

    closeEditModal() {
        const modal = document.getElementById('inline-edit-modal');
        if (modal) {
            modal.classList.add('hidden');
            document.body.style.overflow = 'auto';
            
            // Reset form with null checks
            const form = document.getElementById('inline-edit-form');
            const valueInput = document.getElementById('edit-value-input');
            const valueSelect = document.getElementById('edit-value-select');
            
            if (form) form.reset();
            if (valueInput) valueInput.classList.remove('hidden');
            if (valueSelect) valueSelect.classList.add('hidden');
        }
    }

    async saveFieldData() {
        const form = document.getElementById('inline-edit-form');
        const saveButton = document.getElementById('save-edit');
        
        if (!form) {
            console.error('Form not found');
            return;
        }
        
        const formData = new FormData(form);
        
        // Show loading state with null check
        if (saveButton) {
            saveButton.disabled = true;
            saveButton.innerHTML = `
            <span class="flex items-center">
                <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Saving...
            </span>
            `;
        }
        
        try {
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
            const response = await fetch('/api/council/contribute/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken ? csrfToken.value : ''
                }
            });

            const result = await response.json();

            if (response.ok) {
                this.handleSuccessfulSave(result);
                this.closeEditModal();
                this.updateCellValue(this.currentField, formData.get('value'));
                this.updateProgress();
                this.showToast('success', `Data saved successfully! ${result.points_awarded || 0} points awarded.`);
                this.markLastSaved();
            } else {
                throw new Error(result.message || 'Failed to save data');
            }
        } catch (error) {
            console.error('Error saving data:', error);
            this.showToast('error', error.message || 'An error occurred while saving. Please try again.');
        } finally {
            // Reset button state with null check
            if (saveButton) {
                saveButton.disabled = false;
                saveButton.innerHTML = `
                    <span class="flex items-center">
                        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                        </svg>
                        Save & Award Points
                    </span>
                `;
            }
        }
    }

    handleSuccessfulSave(result) {
        // Update UI with new data
        this.updateRowStatus(this.currentField, 'complete');
        
        // Update points display if user info is available
        if (result.user_points) {
            this.updateUserPoints(result.user_points);
        }

        // Trigger any necessary UI updates
        this.triggerProgressUpdate();
    }

    updateCellValue(fieldSlug, newValue) {
        const cell = document.querySelector(`[data-field="${fieldSlug}"] .editable-cell`);
        if (cell) {
            if (newValue && newValue.trim()) {
                if (fieldSlug === 'council_website') {
                    cell.innerHTML = `<a href="${newValue}" target="_blank" class="text-blue-600 hover:text-blue-800 hover:underline">${this.truncateText(newValue, 40)}</a>`;
                } else {
                    cell.innerHTML = `<span class="text-gray-900">${newValue}</span>`;
                }
            } else {
                cell.innerHTML = '<span class="text-gray-400 italic">Click to add...</span>';
            }
        }
    }

    updateRowStatus(fieldSlug, status) {
        const row = document.querySelector(`[data-field="${fieldSlug}"]`);
        if (!row) return;

        const statusCell = row.querySelector('td:nth-child(3)');
        if (!statusCell) return;

        const statusConfig = {
            complete: {
                class: 'bg-green-100 text-green-800',
                icon: 'M5 13l4 4L19 7',
                text: 'Complete'
            },
            pending: {
                class: 'bg-yellow-100 text-yellow-800', 
                icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z',
                text: 'Pending'
            },
            missing: {
                class: 'bg-red-100 text-red-800',
                icon: 'M6 18L18 6M6 6l12 12',
                text: 'Missing'
            }
        };

        const config = statusConfig[status];
        if (config) {
            statusCell.innerHTML = `
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.class}">
                    <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${config.icon}"/>
                    </svg>
                    ${config.text}
                </span>
            `;
        }

        // Update last updated column
        const lastUpdatedCell = row.querySelector('td:nth-child(4)');
        if (lastUpdatedCell) {
            const now = new Date();
            lastUpdatedCell.textContent = now.toLocaleDateString('en-US', { 
                month: 'short', 
                day: 'numeric', 
                year: 'numeric' 
            });
        }
    }

    async loadFinancialData() {
        const currentYear = this.getCurrentYear();
        if (!currentYear) return;

        try {
            const response = await fetch(`${window.location.pathname}financial-data/?year=${encodeURIComponent(currentYear)}`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.renderFinancialData(data.fields_by_category || {}, data.categories || []);
                this.financialData = data.fields_by_category || {};
            } else {
                console.error('Failed to load financial data');
                this.showFinancialDataError();
            }
        } catch (error) {
            console.error('Error loading financial data:', error);
            this.showFinancialDataError();
        }
    }

    renderFinancialData(fieldsByCategory, categories) {
        const container = document.getElementById('financial-data-rows');
        if (!container) return;

        // Remove loading indicator
        const loadingRow = document.getElementById('financial-loading-row');
        if (loadingRow) {
            loadingRow.remove();
        }

        container.innerHTML = '';

        // Category display names and colors
        const categoryConfig = {
            'balance_sheet': {
                name: 'Balance Sheet',
                icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
                color: 'blue'
            },
            'cash_flow': {
                name: 'Cash Flow',
                icon: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1',
                color: 'green'
            },
            'income': {
                name: 'Income',
                icon: 'M7 11l5-5m0 0l5 5m-5-5v12',
                color: 'emerald'
            },
            'spending': {
                name: 'Spending',
                icon: 'M17 13l-5 5m0 0l-5-5m5 5V6',
                color: 'red'
            }
        };

        categories.forEach(category => {
            const fields = fieldsByCategory[category];
            if (!fields || fields.length === 0) return;

            const config = categoryConfig[category] || {
                name: category.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
                icon: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1',
                color: 'gray'
            };

            // Add category header
            const headerRow = document.createElement('tr');
            headerRow.className = `bg-${config.color}-50 border-t border-${config.color}-200`;
            headerRow.innerHTML = `
                <td colspan="6" class="px-6 py-2 text-left text-xs font-medium text-${config.color}-800 uppercase tracking-wider">
                    <div class="flex items-center space-x-2">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${config.icon}"/>
                        </svg>
                        <span>${config.name}</span>
                        <span class="text-xs normal-case text-${config.color}-600">(${fields.length} fields)</span>
                    </div>
                </td>
            `;
            container.appendChild(headerRow);

            // Add fields for this category
            fields.forEach(field => {
                const row = this.createFinancialDataRow(field, config.color);
                container.appendChild(row);
            });
        });

        // Update progress after rendering
        this.updateProgress();
    }

    showFinancialDataError() {
        const container = document.getElementById('financial-data-rows');
        if (!container) return;

        container.innerHTML = `
            <tr>
                <td colspan="6" class="px-6 py-8 text-center">
                    <div class="text-red-600">
                        <svg class="w-8 h-8 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                        <p class="text-sm">Failed to load financial data. Please refresh the page to try again.</p>
                    </div>
                </td>
            </tr>
        `;
    }

    createFinancialDataRow(field, categoryColor = 'green') {
        const row = document.createElement('tr');
        row.className = 'hover:bg-gray-50 transition-colors editable-row';
        row.dataset.field = field.slug;
        row.dataset.category = 'financial';

        const statusInfo = this.getStatusInfo(field);

        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 sticky left-0 bg-white border-r border-gray-200">
                <div class="flex items-center space-x-3">
                    <div class="flex-shrink-0">
                        <div class="w-8 h-8 bg-${categoryColor}-100 rounded-full flex items-center justify-center">
                            <svg class="w-4 h-4 text-${categoryColor}-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1"/>
                            </svg>
                        </div>
                    </div>
                    <div>
                        <div class="text-sm font-medium text-gray-900">${field.name}</div>
                        <div class="text-xs text-gray-500">${field.description || 'Financial metric'}</div>
                    </div>
                </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                <div class="editable-cell cursor-pointer hover:bg-blue-50 rounded px-2 py-1 transition-colors" data-field="${field.slug}">
                    ${field.value 
                        ? `<span class="text-gray-900">${this.formatValue(field.value, field.data_type)}</span>`
                        : '<span class="text-gray-400 italic">Click to add...</span>'
                    }
                </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">${statusInfo.badge}</td>
            <td class="px-6 py-4 whitespace-nowrap text-xs text-gray-500">
                ${field.last_updated ? new Date(field.last_updated).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '-'}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-center">
                ${field.value ? `
                    <button type="button" 
                            class="delete-field-btn inline-flex items-center px-2 py-1 text-xs font-medium text-red-600 bg-red-50 border border-red-200 rounded hover:bg-red-100 transition-colors"
                            data-field="${field.slug}" 
                            title="Clear this field">
                        <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1-1H8a1 1 0 00-1 1v3M4 7h16"/>
                        </svg>
                        Clear
                    </button>
                ` : '<span class="text-gray-400 text-xs">No data</span>'}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-center">
                <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    +2 pts
                </span>
            </td>
        `;

        return row;
    }

    getStatusInfo(field) {
        if (field.value) {
            return {
                status: 'complete',
                badge: `
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                        </svg>
                        Complete
                    </span>
                `
            };
        } else if (this.pendingSlugs.includes(field.slug)) {
            return {
                status: 'pending',
                badge: `
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                        <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                        Pending
                    </span>
                `
            };
        } else {
            return {
                status: 'missing',
                badge: `
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                        <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                        Missing
                    </span>
                `
            };
        }
    }

    formatValue(value, dataType) {
        if (!value) return '';
        
        switch (dataType) {
            case 'monetary':
                return new Intl.NumberFormat('en-GB', {
                    style: 'currency',
                    currency: 'GBP'
                }).format(value);
            case 'integer':
                return new Intl.NumberFormat('en-GB').format(value);
            case 'url':
                return `<a href="${value}" target="_blank" class="text-blue-600 hover:text-blue-800 hover:underline">${this.truncateText(value, 40)}</a>`;
            case 'percentage':
                return `${value}%`;
            case 'currency':  // Legacy support
                return new Intl.NumberFormat('en-GB', {
                    style: 'currency',
                    currency: 'GBP'
                }).format(value);
            case 'number':   // Legacy support
                return new Intl.NumberFormat('en-GB').format(value);
            default:
                return value;
        }
    }

    async loadFieldOptions(fieldSlug, textInput, selectInput) {
        try {
            const response = await fetch(`/api/fields/${fieldSlug}/options/`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (response.ok) {
                const data = await response.json();
                
                if (data.field_type === 'select' && data.options && data.options.length > 0) {
                    // Show select dropdown
                    textInput.classList.add('hidden');
                    selectInput.classList.remove('hidden');
                    
                    selectInput.innerHTML = '<option value="">Select an option...</option>';
                    data.options.forEach(option => {
                        const optionElement = document.createElement('option');
                        optionElement.value = option.value;
                        optionElement.textContent = option.label;
                        selectInput.appendChild(optionElement);
                    });
                } else {
                    // Show text input
                    selectInput.classList.add('hidden');
                    textInput.classList.remove('hidden');
                    
                    if (data.placeholder) {
                        textInput.placeholder = data.placeholder;
                    }
                }
            } else if (response.status === 404) {
                console.warn(`Field ${fieldSlug} not found in database. Using default text input.`);
                // Field not found, use default text input
                selectInput.classList.add('hidden');
                textInput.classList.remove('hidden');
                textInput.placeholder = `Enter ${fieldSlug.replace(/_/g, ' ')}...`;
            } else {
                console.error(`Server error (${response.status}) loading field options for ${fieldSlug}`);
                // Server error, use default text input
                selectInput.classList.add('hidden');
                textInput.classList.remove('hidden');
                textInput.placeholder = `Enter ${fieldSlug.replace(/_/g, ' ')}...`;
            }
        } catch (error) {
            console.error('Error loading field options:', error);
            // Default to text input on error
            selectInput.classList.add('hidden');
            textInput.classList.remove('hidden');
            textInput.placeholder = `Enter ${fieldSlug.replace(/_/g, ' ')}...`;
        }
    }

    // DISABLED: Legacy updateProgress method - React system now handles all progress
    async updateProgress() {
        console.log('🚫 Legacy spreadsheet_editor.js updateProgress() disabled - React system now active');
        // This method is disabled to prevent competing with React progress calculation
        // The React-based CouncilEditApp.jsx handles all progress updates via API calls
        return;
    }

    // DISABLED: Legacy fallback method - React system now handles progress calculation
    updateProgressFallback() {
        console.log('🚫 Legacy progress calculation disabled - React system active');
        // This method is disabled to prevent competing progress calculations
        // The new React-based system handles progress via API calls
        return;
    }

    triggerProgressUpdate() {
        // Debounce progress updates
        clearTimeout(this.progressUpdateTimeout);
        this.progressUpdateTimeout = setTimeout(() => {
            this.updateProgress();
        }, 100);
    }    changeFinancialYear(year) {
        // Update display
        const currentYearDisplay = document.getElementById('current-year-display');
        if (currentYearDisplay) {
            const yearOption = document.querySelector(`#year-selector option[value="${year}"]`);
            currentYearDisplay.textContent = yearOption ? yearOption.textContent : year;
        }

        // Show loading state for financial data only
        const financialDataRows = document.getElementById('financial-data-rows');
        if (financialDataRows) {
            // Add loading row back if it doesn't exist
            let loadingRow = document.getElementById('financial-loading-row');
            if (!loadingRow) {
                loadingRow = document.createElement('tr');
                loadingRow.id = 'financial-loading-row';
                loadingRow.innerHTML = `
                    <td colspan="6" class="px-6 py-8 text-center">
                        <div class="flex items-center justify-center">
                            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            <span class="text-gray-600">Loading financial data for ${year}...</span>
                        </div>
                    </td>
                `;
                financialDataRows.appendChild(loadingRow);
            }
        }

        // Reload financial data for new year (characteristics remain unchanged)
        this.loadFinancialData();
        
        // Update progress after year change
        setTimeout(() => {
            this.updateProgress();
        }, 500);
    }

    getCurrentYear() {
        const yearSelector = document.getElementById('year-selector');
        return yearSelector ? yearSelector.value : null;
    }

    getCurrentYearId() {
        // This should return the year ID for financial data
        const yearSelector = document.getElementById('year-selector');
        if (yearSelector) {
            const selectedOption = yearSelector.selectedOptions[0];
            console.log('Year selector debug:', {
                selectedOption: selectedOption,
                yearId: selectedOption?.dataset?.yearId,
                value: selectedOption?.value,
                text: selectedOption?.textContent
            });
            // Try to get year ID from data attribute, fallback to value
            return selectedOption ? (selectedOption.dataset.yearId || selectedOption.value) : null;
        }
        return null;
    }

    getFieldDisplayName(fieldSlug) {
        const fieldNames = {
            'council_type': 'Council Type',
            'council_website': 'Council Website',
            'council_nation': 'Council Nation'
        };
        
        return fieldNames[fieldSlug] || fieldSlug.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }


    showBulkAddModal() {
        // Implementation for bulk data addition
        console.log('Bulk add functionality - to be implemented');
    }

    exportToCSV() {
        const rows = [];
        const table = document.getElementById('council-data-table');
        
        // Get headers
        const headers = Array.from(table.querySelectorAll('thead th')).map(th => 
            th.textContent.trim()
        );
        rows.push(headers);

        // Get data rows (skip section headers)
        const dataRows = table.querySelectorAll('tbody tr:not([colspan])');
        dataRows.forEach(row => {
            const cells = Array.from(row.querySelectorAll('td')).map(td => {
                // Get text content, clean up
                let text = td.textContent.trim();
                // Remove extra whitespace
                text = text.replace(/\s+/g, ' ');
                return text;
            });
            rows.push(cells);
        });

        // Create CSV content
        const csvContent = rows.map(row => 
            row.map(cell => `"${cell.replace(/"/g, '""')}"`).join(',')
        ).join('\n');

        // Download file
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `${window.councilData?.slug || 'council'}_data.csv`;
        link.click();
    }

    handleKeyboardShortcuts(e) {
        // Ctrl/Cmd + S to save
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            if (!document.getElementById('inline-edit-modal').classList.contains('hidden')) {
                this.saveFieldData();
            }
        }

        // Escape to close modal
        if (e.key === 'Escape') {
            if (!document.getElementById('inline-edit-modal').classList.contains('hidden')) {
                this.closeEditModal();
            }
        }
    }

    setupAutoSave() {
        // Auto-save functionality could be implemented here
        // For now, we'll just track unsaved changes
        setInterval(() => {
            if (this.unsavedChanges) {
                console.log('Checking for unsaved changes...');
            }
        }, 30000); // Check every 30 seconds
    }

    showToast(type, message, duration = 5000) {
        const toast = document.getElementById(`${type}-toast`);
        const messageElement = document.getElementById(`${type}-message`);
        
        if (toast && messageElement) {
            messageElement.textContent = message;
            toast.classList.remove('hidden');
            
            setTimeout(() => {
                toast.classList.add('hidden');
            }, duration);
        }
    }

    markLastSaved() {
        const lastSavedElement = document.getElementById('last-saved');
        if (lastSavedElement) {
            const now = new Date();
            lastSavedElement.textContent = now.toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit'
            });
        }
    }

    truncateText(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    updateUserPoints(points) {
        // Update user points display in UI if available
        const pointsElements = document.querySelectorAll('.user-points');
        pointsElements.forEach(element => {
            element.textContent = points;
        });
    }

    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    async handleDeleteField(button) {
        const fieldSlug = button.dataset.field;
        const row = button.closest('tr');
        const fieldName = row.querySelector('td:first-child .text-sm.font-medium')?.textContent || fieldSlug;
        
        // Show confirmation dialog
        if (!confirm(`Are you sure you want to clear the value for "${fieldName}"? This action cannot be undone.`)) {
            return;
        }

        // Show loading state
        button.disabled = true;
        button.innerHTML = `
            <svg class="animate-spin w-3 h-3 mr-1" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Clearing...
        `;

        try {
            // Get form data
            const formData = new FormData();
            formData.append('field', fieldSlug);
            formData.append('value', ''); // Empty value to clear the field
            formData.append('source', '');
            
            // For financial fields, include year
            const category = row.dataset.category;
            if (category === 'financial') {
                const yearId = this.getCurrentYearId();
                if (yearId) {
                    formData.append('year', yearId);
                }
            }

            // Submit the clear request
            const response = await fetch('/api/council/contribute/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const result = await response.json();

            if (response.ok && result.success) {
                // Update the cell to show empty state
                const editableCell = row.querySelector('.editable-cell');
                if (editableCell) {
                    editableCell.innerHTML = '<span class="text-gray-400 italic">Click to add...</span>';
                }

                // Update status to missing
                this.updateRowStatus(fieldSlug, 'missing');

                // Remove the delete button and replace with "No data"
                const actionsCell = button.closest('td');
                if (actionsCell) {
                    actionsCell.innerHTML = '<span class="text-gray-400 text-xs">No data</span>';
                }

                // Show success message
                this.showToast('success', `${fieldName} cleared successfully! ${result.points_awarded || 0} points awarded.`);

                // Update user points if provided
                if (result.user_points) {
                    this.updateUserPoints(result.user_points);
                }

                // Update progress
                this.triggerProgressUpdate();

            } else {
                // Show error message
                const errorMsg = result.message || result.error || 'Failed to clear field';
                this.showToast('error', `Error clearing ${fieldName}: ${errorMsg}`);
                
                // Restore button
                button.disabled = false;
                button.innerHTML = `
                    <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1-1H8a1 1 0 00-1 1v3M4 7h16"/>
                    </svg>
                    Clear
                `;
            }

        } catch (error) {
            console.error('Error clearing field:', error);
            this.showToast('error', `Error clearing ${fieldName}: ${error.message}`);
            
            // Restore button
            button.disabled = false;
            button.innerHTML = `
                <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1-1H8a1 1 0 00-1 1v3M4 7h16"/>
                </svg>
                Clear
            `;
        }
    }
}

// Initialize the spreadsheet editor when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('council-spreadsheet-editor')) {
        window.spreadsheetEditor = new SpreadsheetEditor();
    }
});

// Make it available globally for debugging
window.SpreadsheetEditor = SpreadsheetEditor;
