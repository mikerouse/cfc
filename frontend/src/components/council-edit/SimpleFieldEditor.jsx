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
  className = ""
}) => {
  const [currentValue, setCurrentValue] = useState(value || '');
  const [saving, setSaving] = useState(false);
  const [validationMessage, setValidationMessage] = useState('');
  const [saveTimeout, setSaveTimeout] = useState(null);

  // Update current value when prop value changes
  useEffect(() => {
    setCurrentValue(value || '');
  }, [value]);

  /**
   * Auto-save with debouncing
   */
  const debouncedSave = useCallback(async (newValue) => {
    if (saveTimeout) {
      clearTimeout(saveTimeout);
    }

    const timeout = setTimeout(async () => {
      if (newValue !== value && newValue.trim() !== '') {
        setSaving(true);
        setValidationMessage('');
        
        try {
          const result = await onSave(newValue);
          if (result?.success) {
            setValidationMessage('✓ Saved automatically');
            setTimeout(() => setValidationMessage(''), 2000);
          }
        } catch (error) {
          setValidationMessage(error.message || 'Failed to save');
        } finally {
          setSaving(false);
        }
      }
    }, 1000); // 1 second debounce

    setSaveTimeout(timeout);
  }, [saveTimeout, value, onSave]);

  /**
   * Handle input change
   */
  const handleInputChange = useCallback((newValue) => {
    setCurrentValue(newValue);
    setValidationMessage('');
    
    // Basic client-side validation
    if (field.contentType === 'url' && newValue) {
      try {
        new URL(newValue);
        setValidationMessage('');
      } catch {
        setValidationMessage('⚠ Invalid URL format');
      }
    }
    
    if (field.contentType === 'integer' && newValue) {
      if (!/^\d+$/.test(newValue)) {
        setValidationMessage('⚠ Please enter numbers only');
      }
    }

    // Trigger auto-save
    if (!disabled) {
      debouncedSave(newValue);
    }
  }, [field.contentType, debouncedSave, disabled]);

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
   * Render input based on field type
   */
  const renderInput = () => {
    const baseClasses = `
      block w-full border rounded-lg px-3 py-2
      transition-all duration-200 min-h-[44px] text-base
      ${disabled ? 
        'border-gray-200 bg-gray-50 text-gray-500 cursor-not-allowed' : 
        'border-gray-300 bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500'}
      ${validationMessage.startsWith('✓') ? '!border-green-500' : 
        validationMessage.startsWith('⚠') ? '!border-yellow-500' : ''}
      ${error ? '!border-red-500' : ''}
    `;

    switch (field.contentType) {
      case 'url':
        return (
          <input
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

      case 'postcode':
        return (
          <input
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
      <label className="block">
        <span className="text-sm font-medium text-gray-900">
          {getFieldLabel()}
          {field.required && <span className="text-red-500 ml-1">*</span>}
          {saving && <span className="text-xs text-gray-500 ml-2">(saving...)</span>}
        </span>
        
        {/* Field Description */}
        {showHelp && (
          <p className="text-xs text-gray-600 mt-1 mb-2">
            {getFieldDescription()}
          </p>
        )}
        
        {/* Input */}
        <div className="mt-1">
          {renderInput()}
        </div>
      </label>
      
      {/* Status Messages */}
      {validationMessage && (
        <p className={`text-xs ${
          validationMessage.startsWith('✓') ? 'text-green-600' : 
          validationMessage.startsWith('⚠') ? 'text-yellow-600' : 
          'text-red-600'
        }`}>
          {validationMessage}
        </p>
      )}
      
      {/* Error Message */}
      {error && (
        <p className="text-xs text-red-600 flex items-center">
          <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          {error}
        </p>
      )}
      
      {/* Population Context Help */}
      {showPopulationContext && getPopulationContextHelp()}
    </div>
  );
};

export default SimpleFieldEditor;