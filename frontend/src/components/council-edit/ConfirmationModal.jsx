import React from 'react';

/**
 * Confirmation Modal - Replaces alert() with proper modal UI
 * Used for edit confirmations and other user decisions
 */
const ConfirmationModal = ({
  isVisible = false,
  title = "Confirm Action",
  message = "Are you sure you want to proceed?",
  confirmText = "Confirm",
  cancelText = "Cancel",
  onConfirm,
  onCancel,
  type = "default", // default, warning, danger
  className = ""
}) => {

  if (!isVisible) {
    return null;
  }

  const getTypeStyles = () => {
    switch (type) {
      case 'warning':
        return {
          iconColor: 'text-yellow-600',
          confirmButton: 'bg-yellow-600 hover:bg-yellow-700 text-white',
          icon: (
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" 
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          )
        };
      case 'danger':
        return {
          iconColor: 'text-red-600',
          confirmButton: 'bg-red-600 hover:bg-red-700 text-white',
          icon: (
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" 
                    d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          )
        };
      default:
        return {
          iconColor: 'text-blue-600',
          confirmButton: 'bg-blue-600 hover:bg-blue-700 text-white',
          icon: (
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" 
                    d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          )
        };
    }
  };

  const typeStyles = getTypeStyles();

  return (
    <div className={`fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50 ${className}`}>
      <div className="bg-white max-w-md w-full border-0 shadow-xl">
        
        {/* Header with Icon */}
        <div className="p-6 pb-4">
          <div className="flex items-start space-x-4">
            <div className={`flex-shrink-0 ${typeStyles.iconColor}`}>
              {typeStyles.icon}
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                {title}
              </h3>
              <div className="text-sm text-gray-600 space-y-2">
                {typeof message === 'string' ? (
                  <p>{message}</p>
                ) : (
                  message
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 font-medium transition-colors"
          >
            {cancelText}
          </button>
          <button
            onClick={onConfirm}
            className={`px-4 py-2 font-medium transition-colors ${typeStyles.confirmButton}`}
          >
            {confirmText}
          </button>
        </div>

      </div>
    </div>
  );
};

export default ConfirmationModal;