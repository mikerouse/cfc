import React, { useEffect } from 'react';

/**
 * Validation System Component
 * 
 * Displays validation errors and success messages
 * Auto-dismisses after timeout
 * Mobile-first toast notifications
 */
const ValidationSystem = ({ errors, onClearError }) => {
  
  // Auto-clear errors after 5 seconds
  useEffect(() => {
    Object.keys(errors).forEach(field => {
      if (errors[field]) {
        const timer = setTimeout(() => {
          onClearError(field);
        }, 5000);
        
        return () => clearTimeout(timer);
      }
    });
  }, [errors, onClearError]);

  if (!errors || Object.keys(errors).length === 0) {
    return null;
  }

  return (
    <div id="validation-system" className="fixed top-4 right-4 z-50 space-y-2">
      {Object.entries(errors).map(([field, error]) => (
        <div
          key={field}
          className="bg-red-50 border border-red-200 rounded-lg p-4 shadow-lg max-w-sm animate-slide-in"
        >
          <div className="flex items-start justify-between">
            <div className="flex items-start space-x-3">
              <svg className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              <div className="flex-1">
                <h4 className="text-sm font-medium text-red-800 capitalize">
                  {field.replace(/-/g, ' ')} Error
                </h4>
                <p className="text-sm text-red-700 mt-1">{error}</p>
              </div>
            </div>
            <button
              onClick={() => onClearError(field)}
              className="ml-4 text-red-400 hover:text-red-600 flex-shrink-0"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};

export default ValidationSystem;