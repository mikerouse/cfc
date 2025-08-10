import React, { useState, useCallback, useEffect } from 'react';

/**
 * Simple Field Editor for New UI
 * 
 * Auto-save field editor designed for the new GOV.UK-style council edit interface:
 * - Always in editing mode (no separate edit/display states)
 * - Auto-save functionality with debouncing
 * - Clear labels and helper text
 * - Population field special handling
 */
const SimpleFieldEditor = ({ 
  field, 
  value = '', 
  onSave, 
  onValidate,
  error,
  disabled = false,
  showHelp = true,
  showPopulationContext = false,
  yearContext = null,
  allFieldValues = {}, // For cross-field validation
  className = ""
}) => {
  const [currentValue, setCurrentValue] = useState(value || '');
  const [saving, setSaving] = useState(false);
  const [validationMessage, setValidationMessage] = useState('');
  const [saveTimeout, setSaveTimeout] = useState(null);
  const [lastSavedValue, setLastSavedValue] = useState(value || '');
  const [showRevertDialog, setShowRevertDialog] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [retryCount, setRetryCount] = useState(0);

  // Update current value when prop value changes
  useEffect(() => {
    setCurrentValue(value || '');
    setLastSavedValue(value || '');
  }, [value]);

  /**
   * Server-side validation with debouncing
   */
  const debouncedValidation = useCallback(async (newValue) => {
    // Only validate if we have a validation function and the value has changed
    if (!onValidate || newValue === value || !newValue.trim()) {
      return;
    }

    try {
      const validationResult = await onValidate(field.slug, newValue);
      if (validationResult) {
        const serverMessage = validationResult.message || '';
        const serverType = validationResult.type || 'info';
        
        // Combine with client-side validation if both exist
        const clientValidation = validateMonetaryField(newValue, field.slug);
        if (clientValidation && clientValidation.type === 'error') {
          // Client error takes precedence
          setValidationMessage(clientValidation.message);
        } else if (serverMessage) {
          // Use server validation message
          setValidationMessage(`🌐 ${serverMessage}`);
        }
      }
    } catch (error) {
      console.warn('Server validation failed:', error);
      // Continue with client-side validation only
    }
  }, [value, onValidate, field.slug]);

  /**
   * Auto-save with debouncing and error recovery
   */
  const debouncedSave = useCallback(async (newValue, isRetry = false) => {
    if (saveTimeout) {
      clearTimeout(saveTimeout);
    }

    const timeout = setTimeout(async () => {
      if (newValue !== lastSavedValue && newValue.trim() !== '') {
        setSaving(true);
        setValidationMessage('');
        setSaveError(null);
        
        try {
          // Run server-side validation before save
          await debouncedValidation(newValue);
          
          const result = await onSave(newValue);
          if (result?.success) {
            setValidationMessage('✓ Saved automatically');
            setLastSavedValue(newValue);
            setRetryCount(0);
            setTimeout(() => setValidationMessage(''), 2000);
          } else if (result?.error) {
            throw new Error(result.error);
          }
        } catch (error) {
          console.error('Save error:', error);
          setSaveError(error.message || 'Failed to save');
          
          // Implement retry logic for network errors
          if (!isRetry && retryCount < 3 && error.message?.includes('network')) {
            setRetryCount(prev => prev + 1);
            setValidationMessage(`⚠️ Network error - retrying (${retryCount + 1}/3)...`);
            setTimeout(() => debouncedSave(newValue, true), 2000);
          } else {
            setValidationMessage(
              error.message?.includes('network') 
                ? '❌ Network error - please check your connection'
                : `❌ ${error.message || 'Failed to save - please try again'}`
            );
          }
        } finally {
          setSaving(false);
        }
      }
    }, isRetry ? 500 : 1000); // Shorter delay for retries

    setSaveTimeout(timeout);
  }, [saveTimeout, lastSavedValue, onSave, debouncedValidation, retryCount]);

  /**
   * Handle reverting to last saved value
   */
  const handleRevert = useCallback(() => {
    setCurrentValue(lastSavedValue);
    setValidationMessage('↩ Reverted to last saved value');
    setSaveError(null);
    setShowRevertDialog(false);
    setTimeout(() => setValidationMessage(''), 2000);
  }, [lastSavedValue]);

  /**
   * Handle clearing field value with confirmation
   */
  const handleClear = useCallback(() => {
    if (currentValue && currentValue.trim()) {
      if (window.confirm(`Are you sure you want to clear the ${field.name || field.slug} field?`)) {
        setCurrentValue('');
        debouncedSave('');
        setValidationMessage('🗑 Field cleared');
        setTimeout(() => setValidationMessage(''), 2000);
      }
    }
  }, [currentValue, field, debouncedSave]);

  /**
   * Format currency value for preview
   */
  const formatCurrencyPreview = useCallback((value) => {
    if (!value || value === '') return null;
    
    const numValue = parseFloat(value);
    if (isNaN(numValue)) return null;
    
    // Convert millions to actual value
    const actualValue = numValue * 1000000;
    
    // Format with commas
    const formatted = new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(actualValue);
    
    // Also show millions format
    const millionsFormat = `£${numValue}m`;
    
    return {
      full: formatted,
      millions: millionsFormat,
      actualValue: actualValue
    };
  }, []);

  /**
   * Cross-field validation for financial consistency
   */
  const validateCrossField = useCallback((value, fieldSlug, allFieldValues = {}) => {
    if (!value || value === '') return null;
    
    const numValue = parseFloat(value);
    if (isNaN(numValue)) return null;

    // Enhanced cross-field validation rules with helpful guidance
    const crossFieldRules = {
      'total-expenditure': {
        'total-income': {
          check: (expenditure, income) => Math.abs(expenditure - income) / Math.max(expenditure, income) > 0.5,
          message: 'Large difference between income and expenditure may indicate data entry error',
          guidance: 'Check: Are both values from the same statement year? Include all income/expenditure categories?'
        }
      },
      'current-liabilities': {
        'usable-reserves': {
          check: (liabilities, reserves) => liabilities > reserves * 2,
          message: 'Current liabilities significantly exceed usable reserves',
          guidance: 'This ratio suggests potential liquidity concerns. Verify both figures are from the Balance Sheet.'
        }
      },
      'interest-paid': {
        'long-term-liabilities': {
          check: (interest, debt) => debt > 0 && (interest / debt) > 0.1,
          message: 'Interest rate appears unusually high (>10%)',
          guidance: 'Double-check: Is interest from annual I&E statement? Is debt the total outstanding balance?'
        }
      },
      'interest-payments': {
        'long-term-liabilities': {
          check: (interest, debt) => debt > 0 && (interest / debt) > 0.1,
          message: 'Interest payments seem high relative to debt',
          guidance: 'Ensure interest is annual amount and debt is total outstanding (not just annual repayment).'
        }
      },
      'business-rates-income': {
        'total-income': {
          check: (rates, total) => rates > total * 0.8,
          message: 'Business rates seem unusually high compared to total income',
          guidance: 'Check if total income includes all sources (grants, fees, charges, etc.).'
        }
      },
      'council-tax-income': {
        'total-income': {
          check: (tax, total) => tax > total * 0.9,
          message: 'Council tax seems unusually high compared to total income',
          guidance: 'Verify total income includes government grants and other revenue sources.'
        }
      },
      'long-term-liabilities': {
        'current-liabilities': {
          check: (longTerm, current) => current > longTerm * 2,
          message: 'Current liabilities exceed long-term liabilities significantly',
          guidance: 'This is unusual but possible. Verify classification of liabilities by maturity date.'
        }
      },
      'usable-reserves': {
        'unusable-reserves': {
          check: (usable, unusable) => usable > unusable,
          message: 'Usable reserves exceed unusable reserves',
          guidance: 'This is uncommon. Check if reserves are correctly classified (revaluation reserves are unusable).'
        }
      }
    };

    const rules = crossFieldRules[fieldSlug];
    if (!rules) return null;

    // Check each related field with enhanced guidance
    for (const [relatedField, rule] of Object.entries(rules)) {
      const relatedValue = parseFloat(allFieldValues[relatedField]);
      if (!isNaN(relatedValue) && rule.check(numValue, relatedValue)) {
        return {
          type: 'warning',
          message: `⚖️ ${rule.message}`,
          guidance: rule.guidance
        };
      }
    }

    return null;
  }, []);

  /**
   * Smart validation for monetary fields based on field type and value ranges
   */
  const validateMonetaryField = useCallback((value, fieldSlug, allFieldValues = {}) => {
    if (!value || value === '') return null;
    
    const numValue = parseFloat(value);
    if (isNaN(numValue)) {
      return { type: 'error', message: '⚠ Please enter a valid number' };
    }

    // First check cross-field validation
    const crossFieldValidation = validateCrossField(value, fieldSlug, allFieldValues);
    if (crossFieldValidation && crossFieldValidation.type === 'warning') {
      return crossFieldValidation;
    }

    // Enhanced field ranges with council-size awareness
    const fieldRanges = {
      'current-liabilities': { min: 1, max: 5000, typical: [10, 500], unit: 'millions' },
      'long-term-liabilities': { min: 0, max: 10000, typical: [20, 1000], unit: 'millions' },
      'total-income': { min: 5, max: 20000, typical: [50, 2000], unit: 'millions' },
      'total-expenditure': { min: 5, max: 20000, typical: [50, 2000], unit: 'millions' },
      'business-rates-income': { min: 0.1, max: 5000, typical: [10, 500], unit: 'millions' },
      'council-tax-income': { min: 1, max: 10000, typical: [20, 800], unit: 'millions' },
      'interest-paid': { min: 0, max: 500, typical: [1, 50], unit: 'millions' },
      'interest-payments': { min: 0, max: 500, typical: [1, 50], unit: 'millions' },
      'usable-reserves': { min: -500, max: 2000, typical: [5, 200], unit: 'millions', canBeNegative: true },
      'unusable-reserves': { min: -5000, max: 10000, typical: [50, 1000], unit: 'millions', canBeNegative: true },
      'total-reserves': { min: -1000, max: 12000, typical: [50, 1200], unit: 'millions', canBeNegative: true },
      'finance-leases-pfi-liabilities': { min: 0, max: 2000, typical: [0, 100], unit: 'millions' },
      'finance-leases': { min: 0, max: 2000, typical: [0, 100], unit: 'millions' },
      'current-assets': { min: 1, max: 5000, typical: [20, 500], unit: 'millions' },
      'capital-expenditure': { min: 0, max: 2000, typical: [5, 200], unit: 'millions' },
      'pension-liability': { min: 0, max: 10000, typical: [50, 2000], unit: 'millions' },
      'total-debt': { min: 0, max: 15000, typical: [20, 1500], unit: 'millions' }
    };

    const range = fieldRanges[fieldSlug];
    if (!range) return null; // No validation for unknown fields

    // Check for negative values where not allowed
    if (numValue < 0 && !range.canBeNegative) {
      return { 
        type: 'error', 
        message: `❌ ${field.name} cannot be negative. Use positive values only.`,
        guidance: 'If the statement shows brackets (negative), enter as positive for liabilities.'
      };
    }

    // Check for extremely low values
    if (numValue < range.min) {
      return { 
        type: 'warning', 
        message: `⚠ This seems quite low for ${field.name}. Are you sure this is in millions?`,
        guidance: 'Common error: Entering thousands instead of millions. £247,300k should be entered as 247.3'
      };
    }

    // Check for extremely high values
    if (numValue > range.max) {
      return { 
        type: 'warning', 
        message: `⚠ This seems unusually high for ${field.name}. Please double-check the figure.`,
        guidance: 'Verify: Is this the Group total (not just Entity)? Is it definitely in millions?'
      };
    }

    // Check if outside typical range (gentle warning with better guidance)
    if (numValue < range.typical[0] || numValue > range.typical[1]) {
      const isLow = numValue < range.typical[0];
      const suggestion = isLow ? 
        'This is lower than typical for most councils.' :
        'This is higher than typical for most councils.';
      const guidance = isLow ?
        'Double-check: Are you using Group figures? Is the value in millions (not thousands)?' :
        'Large councils or those with significant PFI/housing stock may have higher values. Verify the figure.';
      
      return { 
        type: 'info', 
        message: `ℹ️ ${suggestion}`,
        guidance: guidance
      };
    }

    // Value is in acceptable range
    return { type: 'success', message: '✓ Value looks reasonable' };
  }, [field]);

  /**
   * Handle input change with enhanced validation
   */
  const handleInputChange = useCallback((newValue) => {
    setCurrentValue(newValue);
    setValidationMessage('');
    
    const contentType = field.contentType || field.content_type;
    
    // Enhanced validation based on field type
    if (contentType === 'url' && newValue) {
      try {
        new URL(newValue);
        setValidationMessage('✓ Valid URL format');
      } catch {
        setValidationMessage('⚠ Invalid URL format');
      }
    } else if (contentType === 'integer' && newValue) {
      if (!/^\d+$/.test(newValue)) {
        setValidationMessage('⚠ Please enter numbers only');
      } else {
        setValidationMessage('✓ Valid number');
        // Trigger server validation for additional checks
        if (onValidate && !disabled) {
          setTimeout(() => debouncedValidation(newValue), 500);
        }
      }
    } else if (contentType === 'monetary' && newValue) {
      // Basic monetary validation (avoid circular dependency)
      const numValue = parseFloat(newValue);
      if (isNaN(numValue)) {
        setValidationMessage('⚠ Please enter a valid number');
      } else if (numValue < 0) {
        setValidationMessage('⚠ Please enter a positive value');
      } else {
        setValidationMessage('✓ Valid monetary amount');
        // Trigger server validation for additional checks
        if (onValidate && !disabled) {
          setTimeout(() => debouncedValidation(newValue), 500);
        }
      }
    } else if (contentType === 'postcode' && newValue) {
      // UK postcode validation
      const postcodeRegex = /^[A-Z]{1,2}[0-9][A-Z0-9]?\s?[0-9][A-Z]{2}$/i;
      if (postcodeRegex.test(newValue)) {
        setValidationMessage('✓ Valid UK postcode');
      } else {
        setValidationMessage('⚠ Please enter a valid UK postcode (e.g., SW1A 1AA)');
      }
    } else if (newValue && onValidate && !disabled) {
      // For other field types, trigger server validation after a delay
      setTimeout(() => debouncedValidation(newValue), 500);
    }

    // Trigger auto-save with slight delay to avoid excessive calls
    if (!disabled) {
      debouncedSave(newValue);
    }
  }, [field, debouncedSave, debouncedValidation, onValidate, disabled, allFieldValues]);

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

    // Default descriptions for available fields
    const descriptions = {
      'population': showPopulationContext 
        ? `Population data ${yearContext ? `for ${yearContext}` : 'for display purposes'}`
        : 'Current population of the council area',
      'households': 'Number of households in the council area',
      'council_hq_post_code': 'Postcode for the main council headquarters',
      
      // Financial field descriptions with statement reading guidance
      'current-liabilities': 'Short-term financial obligations due within one year (from Balance Sheet)',
      'long-term-liabilities': 'Financial obligations due after one year (from Balance Sheet)', 
      'usable-reserves': 'Funds available for council use (from Balance Sheet)',
      'unusable-reserves': 'Restricted funds not available for general use (from Balance Sheet)',
      'finance-leases-pfi-liabilities': 'PFI and lease obligations (from Balance Sheet)',
      'total-income': 'All revenue received during the financial year (from Income & Expenditure)',
      'total-expenditure': 'All spending during the financial year (from Income & Expenditure)',
      'business-rates-income': 'Revenue from business rates (from Income & Expenditure)',
      'council-tax-income': 'Revenue from council tax (from Income & Expenditure)',
      'non-ring-fenced-government-grants-income': 'Government grants without spending restrictions (from Income & Expenditure)',
      'interest-paid': 'Interest payments on borrowing (from Income & Expenditure)',
      
      // Legacy descriptions for fields that might be added later  
      'website': 'Official council website URL',
      'council-type': 'Type of local authority',
      'nation': 'Country within the UK',
      'chief-executive': 'Name of the Chief Executive',
      'leader': 'Name of the Council Leader',
      'political-control': 'Current political party in control',
      'contact-url': 'Contact page URL',
      'email': 'Main contact email address'
    };

    return descriptions[field.slug] || `Enter ${field.name?.toLowerCase() || 'value'}`;
  };

  /**
   * Get special context help for population field
   */
  const getPopulationContextHelp = () => {
    if (!showPopulationContext) return null;

    if (yearContext) {
      return (
        <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-sm text-blue-800">
            💡 <strong>Historical Population ({yearContext})</strong>
          </p>
          <p className="text-xs text-blue-700 mt-1">
            This population figure is used to calculate accurate per capita figures for this financial year.
            It may differ from the current population due to annual changes.
          </p>
        </div>
      );
    } else {
      return (
        <div className="mt-2 p-3 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-sm text-green-800">
            ℹ️ <strong>Current Population</strong>
          </p>
          <p className="text-xs text-green-700 mt-1">
            This is the latest population figure displayed on the council page.
            Historical population data for financial calculations is entered separately.
          </p>
        </div>
      );
    }
  };

  /**
   * Get financial statement guidance for monetary fields
   */
  const getFinancialStatementGuidance = () => {
    const contentType = field.contentType || field.content_type;
    if (contentType !== 'monetary') return null;

    return (
      <div className="mt-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
        <p className="text-sm text-amber-800">
          📋 <strong>Reading Financial Statements</strong>
        </p>
        <div className="text-xs text-amber-700 mt-1 space-y-1">
          <p>
            <strong>Important:</strong> Enter values in millions. The system will automatically 
            convert to the full amount.
          </p>
          <p>
            <strong>Balance Sheet Format:</strong> If the statement shows "£247,300" (in thousands), 
            enter "247.3" here.
          </p>
          <p>
            <strong>Group vs Entity:</strong> For councils with subsidiaries, use the 
            <em>Group</em> figures rather than Entity-only figures.
          </p>
          <p>
            <strong>Example:</strong> Statement shows "(268,900)" → Enter "268.9" → Saves as £268,900,000
          </p>
        </div>
      </div>
    );
  };

  /**
   * Render input based on field type
   */
  const renderInput = () => {
    const contentType = field.contentType || field.content_type;
    
    const baseClasses = `
      block w-full border border-gray-300 px-3 py-2
      text-base min-h-[44px] font-normal bg-white
      focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:outline-none
      transition-colors duration-200
      ${disabled ? 
        'border-gray-300 bg-gray-100 text-gray-600 cursor-not-allowed' : 
        'hover:border-gray-400'}
      ${validationMessage.startsWith('✓') ? '!border-green-500' : 
        validationMessage.startsWith('⚠') ? '!border-yellow-500' : ''}
      ${error ? '!border-red-500' : ''}
    `;

    switch (contentType) {
      case 'url':
        return (
          <input
            id={`field-${field.slug}`}
            type="url"
            value={currentValue}
            onChange={(e) => handleInputChange(e.target.value)}
            className={baseClasses}
            placeholder="https://example.com"
            disabled={saving || disabled}
            autoComplete="url"
            inputMode="url"
          />
        );
        
      case 'integer':
        return (
          <input
            id={`field-${field.slug}`}
            type="number"
            value={currentValue}
            onChange={(e) => handleInputChange(e.target.value)}
            className={baseClasses}
            placeholder="Enter number..."
            min="0"
            step="1"
            disabled={saving || disabled}
            inputMode="numeric"
            pattern="[0-9]*"
          />
        );

      case 'monetary':
        return (
          <div className="relative">
            <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500 pointer-events-none">
              £
            </span>
            <input
              id={`field-${field.slug}`}
              type="number"
              value={currentValue}
              onChange={(e) => handleInputChange(e.target.value)}
              className={`${baseClasses} pl-7 pr-20`}
              placeholder="0.00"
              min="0"
              step="0.01"
              disabled={saving || disabled}
              inputMode="decimal"
            />
            <span className="absolute right-3 top-1/2 transform -translate-y-1/2 text-sm text-gray-500 pointer-events-none">
              millions
            </span>
          </div>
        );

      case 'postcode':
        return (
          <input
            id={`field-${field.slug}`}
            type="text"
            value={currentValue}
            onChange={(e) => handleInputChange(e.target.value.toUpperCase())}
            className={baseClasses}
            placeholder="SW1A 1AA"
            disabled={saving || disabled}
            autoComplete="postal-code"
            pattern="[A-Z]{1,2}[0-9][A-Z0-9]? ?[0-9][A-Z]{2}"
            maxLength="8"
          />
        );
        
      case 'list':
        const options = field.choices || [];
        return (
          <select
            id={`field-${field.slug}`}
            value={currentValue}
            onChange={(e) => handleInputChange(e.target.value)}
            className={baseClasses}
            disabled={saving || disabled}
          >
            <option value="">Please select...</option>
            {options.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        );
        
      default:
        return (
          <input
            id={`field-${field.slug}`}
            type="text"
            value={currentValue}
            onChange={(e) => handleInputChange(e.target.value)}
            className={baseClasses}
            placeholder={`Enter ${field.name?.toLowerCase() || 'value'}...`}
            disabled={saving || disabled}
            autoComplete="off"
          />
        );
    }
  };

  return (
    <div className={`space-y-2 ${className}`}>
      {/* Field Label */}
      <label className="block text-sm font-medium text-gray-900" htmlFor={`field-${field.slug}`}>
        {getFieldLabel()}
        {field.required && <span className="text-red-500 ml-1">*</span>}
        {saving && <span className="text-xs text-gray-500 ml-2">(saving...)</span>}
      </label>
      
      {/* Field Description */}
      {showHelp && (
        <p className="text-sm text-gray-600">
          {getFieldDescription()}
        </p>
      )}
      
      {/* Input */}
      <div>
        {renderInput()}
      </div>
      
      {/* Currency Preview for Monetary Fields */}
      {(field.contentType === 'monetary' || field.content_type === 'monetary') && currentValue && (() => {
        const preview = formatCurrencyPreview(currentValue);
        if (preview) {
          return (
            <div className="mt-2 p-2 bg-gray-50 border border-gray-200 rounded-md">
              <p className="text-xs text-gray-700">
                <span className="font-medium">Preview:</span> {preview.full} or {preview.millions}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                If this doesn't look right, adjust the figure above.
              </p>
            </div>
          );
        }
        return null;
      })()}
      
      {/* Status Messages */}
      {validationMessage && (
        <div className={`text-xs space-y-1 ${
          validationMessage.startsWith('✓') ? 'text-green-600' : 
          validationMessage.startsWith('⚠') ? 'text-yellow-600' :
          validationMessage.startsWith('ℹ️') ? 'text-blue-600' :
          validationMessage.startsWith('🌐') ? 'text-purple-600' :
          validationMessage.startsWith('↩') ? 'text-gray-600' :
          validationMessage.startsWith('🗑') ? 'text-gray-600' :
          'text-red-600'
        }`}>
          {validationMessage.split('\n').map((line, idx) => (
            <p key={idx}>{line}</p>
          ))}
        </div>
      )}
      
      {/* Error Recovery Options */}
      {saveError && (
        <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded-md">
          <p className="text-xs text-red-700 mb-2">🚨 Unable to save changes</p>
          <div className="flex space-x-2">
            <button
              onClick={() => debouncedSave(currentValue, true)}
              className="text-xs px-2 py-1 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
              disabled={saving}
            >
              Retry Save
            </button>
            <button
              onClick={handleRevert}
              className="text-xs px-2 py-1 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors"
            >
              Revert Changes
            </button>
          </div>
        </div>
      )}
      
      {/* Error Message */}
      {error && (
        <p className="text-sm text-red-600 mt-1">
          {error}
        </p>
      )}
      
      {/* Clear Field Option (for non-empty fields) */}
      {currentValue && currentValue.trim() && !disabled && (
        <div className="mt-2">
          <button
            onClick={handleClear}
            className="text-xs text-gray-500 hover:text-gray-700 underline"
            type="button"
          >
            Clear this field
          </button>
        </div>
      )}
      
      {/* Population Context Help */}
      {showPopulationContext && getPopulationContextHelp()}
      
      {/* Financial Statement Guidance */}
      {getFinancialStatementGuidance()}
    </div>
  );
};

export default SimpleFieldEditor;