import React from 'react';

/**
 * Mobile-First Edit Header Component
 * 
 * Features:
 * - Council info and navigation
 * - Progress tracking
 * - Save indicator
 * - Responsive design
 */
const EditHeader = ({ council, progress, saving, className = '' }) => {
  return (
    <header id="council-edit-header" className={`bg-white border-b border-gray-200 shadow-sm ${className}`}>
      <div className="mx-auto px-3 sm:px-4 xl:px-6 py-3 max-w-none xl:max-w-desktop">
        
        {/* Mobile Layout */}
        <div className="lg:hidden">
          <div className="flex items-center justify-between mb-2">
            {/* Back button */}
            <button 
              onClick={() => window.history.back()}
              className="p-2 -ml-2 text-gray-600 hover:text-gray-900 min-h-[44px] min-w-[44px] flex items-center justify-center"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
              </svg>
            </button>
            
            {/* Save indicator */}
            {saving && (
              <div className="flex items-center space-x-2 text-sm text-blue-600">
                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
                <span>Saving...</span>
              </div>
            )}
          </div>
          
          {/* Council info */}
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
              <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
              </svg>
            </div>
            <div className="min-w-0 flex-1">
              <h1 className="text-base font-semibold text-gray-900 truncate">
                Edit {council?.name || 'Council'}
              </h1>
              <p className="text-xs text-gray-600">
                {progress.completed}/{progress.total} fields • {progress.points} points earned
              </p>
            </div>
          </div>
        </div>

        {/* Desktop Layout */}
        <div className="hidden lg:flex lg:items-center lg:justify-between">
          <div className="flex items-center space-x-4">
            {/* Back button */}
            <button 
              onClick={() => window.history.back()}
              className="p-2 text-gray-600 hover:text-gray-900 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
              </svg>
            </button>
            
            {/* Council info */}
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                </svg>
              </div>
              <div>
                <h1 className="text-lg font-semibold text-gray-900">
                  Edit {council?.name || 'Council'}
                </h1>
                <p className="text-sm text-gray-600">
                  {council?.councilType || 'Local Authority'} • {council?.nation || 'UK'}
                </p>
              </div>
            </div>
          </div>
          
          {/* Progress and status */}
          <div className="flex items-center space-x-6">
            {/* Progress */}
            <div className="text-right">
              <div className="text-sm font-medium text-gray-900">
                {progress.completed}/{progress.total} fields completed
              </div>
              <div className="text-xs text-gray-600">
                {progress.points} points earned
              </div>
            </div>
            
            {/* Progress bar */}
            <div className="w-32">
              <div className="bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${Math.round((progress.completed / progress.total) * 100)}%` }}
                />
              </div>
              <div className="text-xs text-gray-500 mt-1 text-center">
                {Math.round((progress.completed / progress.total) * 100)}% complete
              </div>
            </div>
            
            {/* Save indicator */}
            {saving && (
              <div className="flex items-center space-x-2 text-sm text-blue-600 bg-blue-50 px-3 py-2 rounded-lg">
                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
                <span>Saving changes...</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

export default EditHeader;