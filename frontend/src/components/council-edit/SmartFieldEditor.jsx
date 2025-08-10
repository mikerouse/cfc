import React, { useState, useCallback, useEffect } from 'react';
import ConfirmationModal from './ConfirmationModal';
import DataValidationModal from './DataValidationModal';
import { validateFieldValue } from '../../utils/dataValidation';
import '../../styles/input-groups.css';

/**
 * Smart Field Editor with View/Edit modes
 * - View mode for existing data (with Edit button)
 * - Edit mode for new/changed data  
 * - Contextual help (shows on focus)
 * - Change tracking for diff summaries
 */
const SmartFieldEditor = ({ 
  field, 
  value = '', 
  onSave, 
  onValidate,
  onTrackChange, // New: track changes for diff summary
  error,
  disabled = false,
  showPopulationContext = false,
  yearContext = null,
  allFieldValues = {},
  className = ""
}) => {
  const [currentValue, setCurrentValue] = useState(value || '');
  const [originalValue, setOriginalValue] = useState(value || ''); // Track original for diffs
  const [isEditing, setIsEditing] = useState(!value || value === ''); // Edit mode if empty
  const [showHelp, setShowHelp] = useState(false);
  const [saving, setSaving] = useState(false);
  const [validationMessage, setValidationMessage] = useState('');
  const [saveTimeout, setSaveTimeout] = useState(null);
  const [showEditConfirmation, setShowEditConfirmation] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [showValidationModal, setShowValidationModal] = useState(false);
  const [validationIssue, setValidationIssue] = useState(null);
  const [pendingValue, setPendingValue] = useState(null);

  // Update current value when prop value changes
  useEffect(() => {
    // Only update if we're not currently editing or if the value is significantly different
    // This prevents the field from resetting after a successful save
    if (!isEditing || !currentValue) {
      setCurrentValue(value || '');
      // Only auto-enable editing if field is truly empty
      if (!value || value === '') {
        setIsEditing(true);
      }
    }
  }, [value]);

  /**
   * Format value for display based on field type
   */
  const formatDisplayValue = useCallback((val) => {
    if (!val || val === '') return 'Not set';
    
    const contentType = field.contentType || field.content_type;
    
    if (contentType === 'monetary') {
      const numValue = parseFloat(val);
      if (!isNaN(numValue)) {
        // ALL FINANCIAL DATA IS NOW STORED IN POUNDS (post-migration)
        // Format consistently for display
        const actualValue = numValue;
        const displaySuffix = numValue >= 1_000_000 
          ? `£${(numValue / 1_000_000).toFixed(1)}m`
          : `£${numValue.toLocaleString()}`;
        
        const formatted = new Intl.NumberFormat('en-GB', {
          style: 'currency',
          currency: 'GBP',
          minimumFractionDigits: 0,
          maximumFractionDigits: 0
        }).format(actualValue);
        
        return `${formatted} (${displaySuffix})`;
      }
    }
    
    return val;
  }, [field]);

  /**
   * Get field label with proper formatting
   */
  const getFieldLabel = () => {
    if (!field.name) return field.slug || 'Unknown Field';
    return field.name;
  };

  /**
   * Get field description/help text
   */
  const getFieldDescription = () => {
    if (field.description) {
      return field.description;
    }

    // Contextual descriptions
    const descriptions = {
      'population': showPopulationContext 
        ? `Population data ${yearContext ? `for ${yearContext}` : 'for display purposes'}`
        : 'Current population of the council area',
      'households': 'Number of households in the council area',
      'council-hq-post-code': 'Postcode for the main council headquarters',
      
      // Financial field descriptions
      'current-liabilities': 'Short-term financial obligations due within one year',
      'long-term-liabilities': 'Financial obligations due after one year', 
      'usable-reserves': 'Funds available for council use',
      'unusable-reserves': 'Restricted funds not available for general use',
      'finance-leases-pfi-liabilities': 'PFI and lease obligations',
      'total-income': 'All revenue received during the financial year',
      'total-expenditure': 'All spending during the financial year',
      'business-rates-income': 'Revenue from business rates',
      'council-tax-income': 'Revenue from council tax',
      'non-ring-fenced-government-grants-income': 'Government grants without spending restrictions',
      'interest-paid': 'Interest payments on borrowing',
    };

    return descriptions[field.slug] || `Enter ${field.name?.toLowerCase() || 'value'}`;
  };

  /**
   * Get statement reading guidance based on field type
   */
  const getStatementGuidance = () => {
    const contentType = field.contentType || field.content_type;
    if (contentType !== 'monetary') return null;

    const guidanceByField = {
      'current-liabilities': 'Find in Balance Sheet → Current Liabilities section',
      'long-term-liabilities': 'Find in Balance Sheet → Long-term Liabilities section',
      'total-income': 'Find in Income & Expenditure Statement → Total Income',
      'total-expenditure': 'Find in Income & Expenditure Statement → Total Expenditure',
      'usable-reserves': 'Find in Balance Sheet → Reserves section',
      'unusable-reserves': 'Find in Balance Sheet → Reserves section',
    };

    return guidanceByField[field.slug];
  };

  /**
   * Handle enabling edit mode
   */
  const handleEnableEdit = () => {
    if (originalValue && originalValue !== '') {
      // Show confirmation modal for existing data
      setShowEditConfirmation(true);
    } else {
      setIsEditing(true);
      setShowHelp(true);
    }
  };

  /**
   * Confirm edit mode activation
   */
  const handleConfirmEdit = () => {
    setIsEditing(true);
    setShowHelp(true);
    setShowEditConfirmation(false);
  };

  /**
   * Cancel edit mode activation
   */
  const handleCancelEditConfirmation = () => {
    setShowEditConfirmation(false);
  };

  /**
   * Handle canceling edit mode
   */
  const handleCancelEdit = () => {
    setCurrentValue(originalValue); // Reset to original
    setIsEditing(false);
    setShowHelp(false);
    setValidationMessage('');
  };

  /**
   * Validate and save value
   */
  const validateAndSave = useCallback(async (newValue) => {
    // Validate the value first
    const validation = validateFieldValue(field, newValue);
    
    if (!validation.isValid && validation.severity === 'error') {
      // Show validation modal for errors
      setValidationIssue(validation);
      setPendingValue(newValue);
      setShowValidationModal(true);
      return;
    }
    
    if (!validation.isValid && validation.severity === 'warning') {
      // Show warning but allow save
      setValidationMessage(`⚠️ ${validation.message}`);
    }
    
    // Proceed with save
    await performSave(newValue);
  }, [field]);
  
  /**
   * Perform the actual save operation
   */
  const performSave = useCallback(async (newValue) => {
    setSaving(true);
    setValidationMessage('');
    
    try {
      const result = await onSave(newValue);
      if (result?.success) {
        setValidationMessage('✓ Saved successfully');
        
        // Update tracking with saved status
        if (onTrackChange) {
          onTrackChange(field.slug, {
            fieldName: getFieldLabel(),
            fieldSlug: field.slug,
            originalValue: originalValue,
            newValue: newValue,
            originalFormatted: formatDisplayValue(originalValue),
            newFormatted: formatDisplayValue(newValue),
            saved: true
          });
        }
        
        setHasUnsavedChanges(false);
        
        // Update the original value to the new saved value
        setOriginalValue(newValue);
        
        // Keep in edit mode for continued editing
        // Only show success message briefly
        setTimeout(() => {
          setValidationMessage('');
        }, 2000);
      }
    } catch (error) {
      setValidationMessage(`❌ ${error.message || 'Failed to save'}`);
    } finally {
      setSaving(false);
    }
  }, [originalValue, onSave, onTrackChange, field, getFieldLabel, formatDisplayValue]);

  /**
   * Auto-save with debouncing and validation
   */
  const debouncedSave = useCallback(async (newValue) => {
    if (saveTimeout) {
      clearTimeout(saveTimeout);
    }

    const timeout = setTimeout(async () => {
      if (newValue !== originalValue) {
        await validateAndSave(newValue);
      }
    }, 1000);

    setSaveTimeout(timeout);
  }, [saveTimeout, originalValue, validateAndSave]);

  /**
   * Handle input change
   */
  const handleInputChange = (newValue) => {
    setCurrentValue(newValue);
    setValidationMessage('');
    setHasUnsavedChanges(newValue !== originalValue);
    
    // Track change immediately for review (even before save)
    if (newValue !== originalValue && onTrackChange) {
      onTrackChange(field.slug, {
        fieldName: getFieldLabel(),
        fieldSlug: field.slug,
        originalValue: originalValue,
        newValue: newValue,
        originalFormatted: formatDisplayValue(originalValue),
        newFormatted: formatDisplayValue(newValue)
      });
    }
    
    if (!disabled) {
      debouncedSave(newValue);
    }
  };

  /**
   * Render input field
   */
  const renderInput = () => {
    const contentType = field.contentType || field.content_type;
    
    const baseClasses = `
      block w-full border-2 border-gray-300 px-3 py-3
      text-base min-h-[48px] font-normal bg-white
      focus:ring-0 focus:border-blue-600 focus:outline-none
      transition-colors duration-200
      ${disabled || saving ? 
        'border-gray-300 bg-gray-50 text-gray-600 cursor-not-allowed' : 
        'hover:border-gray-400'}
      ${validationMessage.startsWith('✓') ? '!border-green-500' : 
        validationMessage.startsWith('⚠') ? '!border-yellow-500' : ''}
      ${error ? '!border-red-500' : ''}
    `;

    const handleFocus = () => {
      setShowHelp(true);
    };

    const handleBlur = () => {
      // Keep help visible while editing
      if (!isEditing) {
        setShowHelp(false);
      }
    };

    switch (contentType) {
      case 'monetary':
        const getMonetaryClasses = () => {
          let classes = 'monetary-input-group input-group--both';
          if (error) classes += ' monetary-input-group--error';
          if (validationMessage.startsWith('✓')) classes += ' monetary-input-group--success';
          if (saving || disabled) classes += ' monetary-input-group--disabled';
          return classes;
        };
        
        return (
          <div className={getMonetaryClasses()}>
            <span className="input-group__leading">
              £
            </span>
            <input
              id={`field-${field.slug}`}
              type="number"
              value={currentValue}
              onChange={(e) => handleInputChange(e.target.value)}
              onFocus={handleFocus}
              onBlur={handleBlur}
              className={`input-group__input ${
                error ? 'error' : 
                validationMessage.startsWith('✓') ? 'success' :
                validationMessage.startsWith('⚠') ? 'warning' : ''
              }`}
              placeholder="0.00"
              min="0"
              step="0.01"
              disabled={saving || disabled}
              inputMode="decimal"
            />
            <span className="input-group__trailing">
              pounds
            </span>
          </div>
        );
        
      case 'integer':
        return (
          <input
            id={`field-${field.slug}`}
            type="number"
            value={currentValue}
            onChange={(e) => handleInputChange(e.target.value)}
            onFocus={handleFocus}
            onBlur={handleBlur}
            className={baseClasses}
            placeholder="Enter number..."
            min="0"
            step="1"
            disabled={saving || disabled}
            inputMode="numeric"
          />
        );
        
      default:
        return (
          <input
            id={`field-${field.slug}`}
            type="text"
            value={currentValue}
            onChange={(e) => handleInputChange(e.target.value)}
            onFocus={handleFocus}
            onBlur={handleBlur}
            className={baseClasses}
            placeholder={`Enter ${field.name?.toLowerCase() || 'value'}...`}
            disabled={saving || disabled}
          />
        );
    }
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Field Label */}
      <div className="flex items-center justify-between">
        <label className="block text-sm font-medium text-gray-900" htmlFor={`field-${field.slug}`}>
          {getFieldLabel()}
          {field.required && <span className="text-red-500 ml-1">*</span>}
        </label>
        
        {/* Edit/Cancel Buttons */}
        {!isEditing && originalValue && (
          <button
            onClick={handleEnableEdit}
            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            Edit
          </button>
        )}
        {isEditing && originalValue && (
          <button
            onClick={handleCancelEdit}
            className="text-sm text-gray-600 hover:text-gray-800"
          >
            Cancel
          </button>
        )}
      </div>

      {/* Basic Description (always visible) */}
      <p className="text-sm text-gray-600">
        {getFieldDescription()}
      </p>

      {/* View Mode - Display existing value */}
      {!isEditing && originalValue && (
        <div className="p-4 bg-green-50 border border-green-200 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-green-800">Current value:</span>
            <div className="text-green-600">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            </div>
          </div>
          <div className="text-lg font-semibold text-green-900">
            {formatDisplayValue(originalValue)}
          </div>
        </div>
      )}

      {/* Edit Mode - Input field */}
      {isEditing && (
        <div className="space-y-2">
          {renderInput()}
          
          {saving && (
            <p className="text-xs text-gray-500 flex items-center">
              <div className="animate-spin rounded-full h-3 w-3 border border-gray-400 border-t-transparent mr-2"></div>
              Saving...
            </p>
          )}
        </div>
      )}

      {/* Contextual Help (shows when focused/editing) */}
      {showHelp && (
        <div className="p-3 bg-blue-50 border border-blue-200">
          <div className="space-y-2">
            {/* Statement guidance */}
            {getStatementGuidance() && (
              <p className="text-sm text-blue-800">
                <strong>📋 Where to find:</strong> {getStatementGuidance()}
              </p>
            )}
            
            {/* Monetary field guidance */}
            {(field.contentType === 'monetary' || field.content_type === 'monetary') && (
              <div className="text-sm text-blue-800 space-y-1">
                <p><strong>💡 Entry tips:</strong></p>
                <ul className="list-disc list-inside ml-2 space-y-1">
                  <li>Enter full amount in pounds (e.g., "4200000" for £4.2m)</li>
                  <li>You can use decimals for precision (e.g., "4200000.50")</li>
                  <li>Use Group figures if council has subsidiaries</li>
                  <li>Brackets "(268900)" means negative - enter "-268900"</li>
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Validation Messages */}
      {validationMessage && (
        <p className={`text-sm ${
          validationMessage.startsWith('✓') ? 'text-green-600' : 
          validationMessage.startsWith('⚠') ? 'text-yellow-600' :
          'text-red-600'
        }`}>
          {validationMessage}
        </p>
      )}

      {/* Error Message */}
      {error && (
        <p className="text-sm text-red-600">
          {error}
        </p>
      )}

      {/* Edit Confirmation Modal */}
      <ConfirmationModal
        isVisible={showEditConfirmation}
        title={`Edit ${getFieldLabel()}?`}
        message={
          <div className="space-y-3">
            <p>You're about to edit existing data:</p>
            <div className="p-3 bg-gray-100 border border-gray-200">
              <span className="text-sm text-gray-600">Current value:</span>
              <div className="font-medium text-gray-900">
                {formatDisplayValue(originalValue)}
              </div>
            </div>
            <p className="text-sm text-gray-600">
              Any changes will be tracked and shown for your review before being saved permanently.
            </p>
          </div>
        }
        confirmText="Edit Field"
        cancelText="Keep Current Value"
        type="default"
        onConfirm={handleConfirmEdit}
        onCancel={handleCancelEditConfirmation}
      />

      {/* Data Validation Modal */}
      <DataValidationModal
        isVisible={showValidationModal}
        fieldName={getFieldLabel()}
        enteredValue={pendingValue}
        validationIssue={validationIssue}
        onAcceptValue={async (value) => {
          setShowValidationModal(false);
          await performSave(value);
        }}
        onUseCorrection={async (correctedValue) => {
          setShowValidationModal(false);
          setCurrentValue(correctedValue);
          await performSave(correctedValue);
        }}
        onEditValue={() => {
          setShowValidationModal(false);
          // Keep current input focused for editing
          setTimeout(() => {
            const inputElement = document.getElementById(`field-${field.slug}`);
            if (inputElement) {
              inputElement.focus();
              inputElement.select();
            }
          }, 100);
        }}
        onCancel={() => {
          setShowValidationModal(false);
          setCurrentValue(originalValue);
          setPendingValue(null);
        }}
      />
    </div>
  );
};

export default SmartFieldEditor;