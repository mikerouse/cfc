import React from 'react';

/**
 * Save Success Modal - Shows after successful save with navigation options
 */
const SaveSuccessModal = ({
  isVisible = false,
  changeCount = 0,
  councilName = '',
  councilSlug = '',
  onReturnToCouncil,
  onContinueEditing,
  onClose,
  className = ""
}) => {

  if (!isVisible) {
    return null;
  }

  return (
    <div className={`fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50 ${className}`}>
      <div className="bg-white max-w-md w-full border-0 shadow-xl">
        
        {/* Success Header */}
        <div className="p-6 text-center">
          <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
            <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            Changes Saved Successfully!
          </h3>
          
          <p className="text-gray-600">
            You've updated {changeCount} field{changeCount !== 1 ? 's' : ''} for {councilName}.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="px-6 pb-6 space-y-3">
          <button
            onClick={() => {
              if (councilSlug) {
                window.location.href = `/councils/${councilSlug}/`;
              }
              onReturnToCouncil();
            }}
            className="w-full px-4 py-3 bg-blue-600 text-white hover:bg-blue-700 font-medium transition-colors flex items-center justify-center"
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Return to Council Page
          </button>
          
          <button
            onClick={onContinueEditing}
            className="w-full px-4 py-3 bg-gray-100 text-gray-700 hover:bg-gray-200 font-medium transition-colors flex items-center justify-center"
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            Add More Data
          </button>
        </div>

        {/* Additional Options */}
        <div className="px-6 pb-4 border-t border-gray-200 pt-4">
          <div className="text-center space-y-2">
            <button
              onClick={() => {
                // View changes on council page
                if (councilSlug) {
                  window.location.href = `/councils/${councilSlug}/#financial-data`;
                }
              }}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              View Updated Data on Council Page
            </button>
            
            <p className="text-xs text-gray-500">
              Your changes are live and visible to all users
            </p>
          </div>
        </div>

        {/* Close button */}
        <button
          onClick={onClose}
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

export default SaveSuccessModal;