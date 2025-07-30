import React from 'react';

/**
 * Loading spinner component for My Lists operations
 */
const LoadingSpinner = ({ size = 'default', overlay = true }) => {
  const sizeClasses = {
    small: 'w-4 h-4',
    default: 'w-8 h-8',
    large: 'w-12 h-12'
  };

  const spinner = (
    <div className={`inline-block ${sizeClasses[size]} animate-spin rounded-full border-4 border-solid border-current border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]`}>
      <span className="!absolute !-m-px !h-px !w-px !overflow-hidden !whitespace-nowrap !border-0 !p-0 ![clip:rect(0,0,0,0)]">
        Loading...
      </span>
    </div>
  );

  if (overlay) {
    return (
      <div id="my-lists-loading-overlay" className="fixed inset-0 bg-black bg-opacity-25 flex items-center justify-center z-50">
        <div id="my-lists-loading-modal" className="bg-white rounded-lg p-6 shadow-xl">
          <div className="flex items-center space-x-3">
            <div className="text-blue-600">
              {spinner}
            </div>
            <span className="text-gray-700 font-medium">Loading...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="text-blue-600">
      {spinner}
    </div>
  );
};

export default LoadingSpinner;