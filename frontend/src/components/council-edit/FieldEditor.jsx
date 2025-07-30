import React, { useState, useCallback, useEffect } from 'react';

/**
 * Universal Field Editor Component
 * 
 * Handles editing for all field types with mobile-first design:
 * - URL fields with validation
 * - Text fields with formatting
 * - Integer fields with numeric input
 * - List fields with dropdowns
 * - 44px minimum touch targets
 * - Real-time validation feedback
 */
const FieldEditor = ({ 
  field, 
  value, 
  isEditing, 
  onEdit, 
  onSave, 
  onCancel, 
  error, 
  isMobile, 
  disabled 
}) => {
  const [editValue, setEditValue] = useState(value || '');
  const [validating, setValidating] = useState(false);
  const [validationMessage, setValidationMessage] = useState('');
  const [saving, setSaving] = useState(false);

  // Update edit value when prop value changes
  useEffect(() => {
    setEditValue(value || '');
  }, [value]);

  /**
   * Handle save with validation
   */
  const handleSave = useCallback(async () => {
    if (saving || disabled) return;
    
    setSaving(true);
    setValidationMessage('');
    
    try {
      await onSave(field.slug, editValue);
    } catch (error) {
      setValidationMessage(error.message || 'Failed to save field');
    } finally {
      setSaving(false);
    }
  }, [field.slug, editValue, onSave, saving, disabled]);

  /**
   * Handle cancel
   */
  const handleCancel = useCallback(() => {
    setEditValue(value || '');
    setValidationMessage('');
    onCancel();
  }, [value, onCancel]);

  /**
   * Handle input change with real-time validation
   */
  const handleInputChange = useCallback((newValue) => {
    setEditValue(newValue);
    setValidationMessage('');
    
    // Basic client-side validation
    if (field.contentType === 'url' && newValue) {
      try {
        new URL(newValue);
        setValidationMessage('✓ Valid URL format');
      } catch {
        setValidationMessage('⚠ Invalid URL format');
      }
    }
    
    if (field.contentType === 'integer' && newValue) {
      if (!/^\d+$/.test(newValue)) {
        setValidationMessage('⚠ Please enter numbers only');
      } else {
        setValidationMessage('✓ Valid number');
      }
    }
  }, [field.contentType]);

  /**
   * Render input based on field type
   */
  const renderInput = () => {
    const baseClasses = `
      block w-full border border-gray-300 rounded-lg px-3 py-2
      focus:ring-2 focus:ring-blue-500 focus:border-blue-500
      transition-all duration-200
      ${isMobile ? 'min-h-[44px] text-base' : 'min-h-[40px] text-sm'}
      ${validationMessage.startsWith('✓') ? 'border-green-500' : 
        validationMessage.startsWith('⚠') ? 'border-yellow-500' : ''}
    `;

    switch (field.contentType) {
      case 'url':
        return (
          <input
            type="url"
            value={editValue}
            onChange={(e) => handleInputChange(e.target.value)}
            className={baseClasses}
            placeholder="https://example.com"
            pattern="https://.*"
            disabled={saving || disabled}
            autoComplete="url"
            inputMode="url"
          />
        );
        
      case 'integer':
        return (
          <input
            type="number"
            value={editValue}
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
        
      case 'list':
        return (
          <select
            value={editValue}
            onChange={(e) => handleInputChange(e.target.value)}
            className={baseClasses}
            disabled={saving || disabled}
          >
            <option value="">Please select...</option>
            {/* These would be populated from API */}
            <option value="district">District Council</option>
            <option value="county">County Council</option>
            <option value="unitary">Unitary Authority</option>
            <option value="metropolitan">Metropolitan Borough</option>
            <option value="london">London Borough</option>
          </select>
        );
        
      default:
        return (
          <input
            type="text"
            value={editValue}
            onChange={(e) => handleInputChange(e.target.value)}
            className={baseClasses}
            placeholder="Enter value..."
            disabled={saving || disabled}
            autoComplete="off"
          />
        );
    }
  };

  /**
   * Render display value when not editing
   */
  const renderDisplayValue = () => {
    if (!value) {
      return (
        <div className={`
          text-gray-400 italic cursor-pointer rounded px-2 py-2
          hover:bg-gray-50 transition-colors
          ${isMobile ? 'min-h-[44px]' : 'min-h-[40px]'}
          flex items-center
        `} onClick={onEdit}>
          Click to add {field.name.toLowerCase()}...
        </div>
      );
    }

    if (field.contentType === 'url') {
      return (
        <div className="space-y-2">
          <a 
            href={value} 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-blue-600 hover:text-blue-800 hover:underline text-sm break-all"
          >
            {value.length > 50 ? `${value.substring(0, 50)}...` : value}
          </a>
          <button 
            onClick={onEdit}
            className={`
              block w-full text-left text-gray-600 hover:text-gray-800
              hover:bg-gray-50 rounded px-2 py-1 transition-colors text-xs
              ${isMobile ? 'min-h-[44px]' : 'min-h-[36px]'}
              flex items-center
            `}
          >
            Click to edit URL
          </button>
        </div>
      );
    }

    return (
      <div 
        className={`
          text-gray-900 cursor-pointer rounded px-2 py-2
          hover:bg-gray-50 transition-colors
          ${isMobile ? 'min-h-[44px]' : 'min-h-[40px]'}
          flex items-center
        `}
        onClick={onEdit}
      >
        {field.contentType === 'integer' ? Number(value).toLocaleString() : value}
      </div>
    );
  };

  if (!isEditing) {
    return renderDisplayValue();
  }

  return (
    <div className="space-y-3">
      {/* Input */}
      {renderInput()}
      
      {/* Validation/Help Message */}
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
      
      {/* Action Buttons */}
      <div className={`flex ${isMobile ? 'flex-col space-y-2' : 'flex-row space-x-2'}`}>
        <button
          onClick={handleSave}
          disabled={saving || disabled || !editValue.trim()}
          className={`
            flex items-center justify-center px-4 py-2 rounded-lg font-medium
            text-sm transition-all duration-200 flex-1
            ${isMobile ? 'min-h-[44px]' : 'min-h-[36px]'}
            ${saving || disabled || !editValue.trim()
              ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2'
            }
          `}
        >
          {saving ? (
            <>
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
              </svg>
              Saving...
            </>
          ) : (
            <>
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"/>
              </svg>
              Save & Earn {field.points} Points
            </>
          )}
        </button>
        
        <button
          onClick={handleCancel}
          disabled={saving}
          className={`
            flex items-center justify-center px-4 py-2 rounded-lg font-medium
            text-sm border border-gray-300 bg-white text-gray-700
            hover:bg-gray-50 transition-all duration-200
            ${isMobile ? 'min-h-[44px] flex-1' : 'min-h-[36px]'}
            ${saving ? 'opacity-50 cursor-not-allowed' : ''}
          `}
        >
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
          Cancel
        </button>
      </div>
    </div>
  );
};

export default FieldEditor;