import React from 'react';

/**
 * Change Summary - Shows diff of all changes before final confirmation
 * Displays original vs new values for user review
 */
const ChangeSummary = ({
  changes = [],
  onConfirm,
  onCancel,
  onEditField,
  isVisible = false,
  className = ""
}) => {

  if (!isVisible || !changes.length) {
    return null;
  }

  const totalChanges = changes.length;

  return (
    <div className={`fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50 ${className}`}>
      <div className="bg-white max-w-4xl w-full max-h-[80vh] overflow-hidden flex flex-col">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Review Your Changes</h2>
              <p className="text-gray-600 mt-1">
                {totalChanges} field{totalChanges !== 1 ? 's' : ''} will be updated
              </p>
            </div>
            <button
              onClick={onCancel}
              className="text-gray-400 hover:text-gray-600"
              aria-label="Close"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Changes List */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          <div className="space-y-4">
            {changes.map((change, index) => (
              <div key={change.fieldSlug} className="border border-gray-200 p-4">
                
                {/* Field Name */}
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-medium text-gray-900">{change.fieldName}</h3>
                  <button
                    onClick={() => onEditField(change.fieldSlug)}
                    className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                  >
                    Edit Again
                  </button>
                </div>

                {/* Before/After Comparison */}
                <div className="grid grid-cols-2 gap-4">
                  
                  {/* Original Value */}
                  <div className="space-y-2">
                    <div className="text-sm font-medium text-gray-700 flex items-center">
                      <svg className="w-4 h-4 mr-1 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M20 12H4" />
                      </svg>
                      Original
                    </div>
                    <div className="p-3 bg-red-50 border border-red-200 text-red-900">
                      {change.originalFormatted || 'Not set'}
                    </div>
                  </div>

                  {/* New Value */}
                  <div className="space-y-2">
                    <div className="text-sm font-medium text-gray-700 flex items-center">
                      <svg className="w-4 h-4 mr-1 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                      </svg>
                      New
                    </div>
                    <div className="p-3 bg-green-50 border border-green-200 text-green-900">
                      {change.newFormatted}
                    </div>
                  </div>
                </div>

                {/* Change Impact */}
                {change.originalValue && change.newValue && (
                  <div className="mt-3 p-2 bg-blue-50 border border-blue-200">
                    <p className="text-xs text-blue-800">
                      <strong>Impact:</strong> This change will affect per-capita calculations and may update related metrics.
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
          <div className="text-sm text-gray-600">
            These changes will be saved immediately and update the council's financial data.
          </div>
          <div className="flex space-x-3">
            <button
              onClick={onCancel}
              className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 font-medium transition-colors"
            >
              Cancel Changes
            </button>
            <button
              onClick={onConfirm}
              className="px-6 py-2 bg-blue-600 text-white hover:bg-blue-700 font-medium transition-colors"
            >
              Confirm {totalChanges} Change{totalChanges !== 1 ? 's' : ''}
            </button>
          </div>
        </div>

        {/* Additional Info */}
        <div className="px-6 py-3 bg-gray-50 border-t border-gray-200">
          <div className="flex items-start space-x-2 text-xs text-gray-600">
            <svg className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="space-y-1">
              <p><strong>Data Security:</strong> All changes are logged and can be reviewed in the council's edit history.</p>
              <p><strong>Calculations:</strong> Updated figures will automatically recalculate per-capita metrics and comparisons.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChangeSummary;