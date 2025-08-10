import React from 'react';

/**
 * Data Validation Modal - Shows warnings for unrealistic values with suggestions
 */
const DataValidationModal = ({
  isVisible = false,
  fieldName = '',
  enteredValue = '',
  validationIssue = {},
  onAcceptValue,
  onUseCorrection,
  onEditValue,
  onCancel,
  className = ""
}) => {

  if (!isVisible) {
    return null;
  }

  const formatCurrency = (value) => {
    const numValue = parseFloat(value);
    if (isNaN(numValue)) return value;
    
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP',
      minimumFractionDigits: 1,
      maximumFractionDigits: 1
    }).format(numValue);
  };

  return (
    <div className={`fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50 ${className}`}>
      <div className="bg-white max-w-lg w-full border-0 shadow-xl">
        
        {/* Warning Header */}
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center">
            <div className="mx-auto w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center mr-4">
              <svg className="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L3.232 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-gray-900">
                Value Seems Unusually High
              </h3>
              <p className="text-sm text-gray-600">
                {fieldName}
              </p>
            </div>
          </div>
        </div>

        {/* Issue Description */}
        <div className="p-6 space-y-4">
          <div className="bg-red-50 border border-red-200 p-4">
            <div className="flex items-center mb-2">
              <span className="text-sm font-medium text-red-800">You entered:</span>
            </div>
            <div className="text-lg font-semibold text-red-900">
              {formatCurrency(enteredValue * 1000000)} ({enteredValue} million)
            </div>
          </div>
          
          <p className="text-sm text-gray-700">
            {validationIssue.message}
          </p>
          
          {validationIssue.suggestedValue && (
            <div className="bg-green-50 border border-green-200 p-4">
              <div className="flex items-center mb-2">
                <span className="text-sm font-medium text-green-800">Did you mean:</span>
              </div>
              <div className="text-lg font-semibold text-green-900">
                {formatCurrency(validationIssue.suggestedValue * 1000000)} ({validationIssue.suggestedValue} million)
              </div>
              <p className="text-xs text-green-700 mt-1">
                {validationIssue.suggestion}
              </p>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="px-6 pb-6 space-y-3">
          {validationIssue.suggestedValue && (
            <button
              onClick={() => onUseCorrection(validationIssue.suggestedValue)}
              className="w-full px-4 py-3 bg-green-600 text-white hover:bg-green-700 font-medium transition-colors flex items-center justify-center"
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Use Suggested Value ({validationIssue.suggestedValue} million)
            </button>
          )}
          
          <button
            onClick={onEditValue}
            className="w-full px-4 py-3 bg-blue-600 text-white hover:bg-blue-700 font-medium transition-colors flex items-center justify-center"
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            Edit Value Again
          </button>
          
          <button
            onClick={() => onAcceptValue(enteredValue)}
            className="w-full px-4 py-3 bg-gray-100 text-gray-700 hover:bg-gray-200 font-medium transition-colors"
          >
            Keep Original Value (I'm Sure)
          </button>
        </div>

        {/* Additional Context */}
        <div className="px-6 pb-4 border-t border-gray-200 pt-4">
          <div className="bg-blue-50 border border-blue-200 p-3">
            <h4 className="text-sm font-medium text-blue-900 mb-1">💡 Common Mistakes</h4>
            <ul className="text-xs text-blue-800 space-y-1">
              <li>• Entering amounts in pounds instead of millions (e.g., 208487000 instead of 208.487)</li>
              <li>• Missing decimal point (e.g., 208487 instead of 208.487)</li>
              <li>• Including thousands instead of millions (e.g., 208487 thousands = 208.487 millions)</li>
            </ul>
          </div>
        </div>

        {/* Close button */}
        <button
          onClick={onCancel}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
          aria-label="Close"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

      </div>
    </div>
  );
};

export default DataValidationModal;