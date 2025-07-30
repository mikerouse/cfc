import React, { useState } from 'react';

/**
 * Mobile-First Year Selector for Temporal Data
 * 
 * Features:
 * - Swipe gestures on mobile
 * - 44px touch targets
 * - Clear current year indication
 * - Responsive design
 */
const YearSelector = ({ years, selectedYear, onChange, isMobile, className = '' }) => {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  if (!years || years.length === 0) {
    return (
      <div className={`text-center py-4 text-gray-500 ${className}`}>
        <p className="text-sm">No financial years available</p>
      </div>
    );
  }

  if (isMobile) {
    // Mobile: Horizontal scrolling year selector
    return (
      <div id="year-selector-mobile" className={`bg-white rounded-lg border border-gray-200 p-4 ${className}`}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-gray-900">Financial Year</h3>
          <span className="text-xs text-gray-500">{years.length} available</span>
        </div>
        
        {/* Horizontal scrolling years */}
        <div className="overflow-x-auto">
          <div className="flex space-x-2 pb-2">
            {years.map((year) => {
              const isSelected = selectedYear?.id === year.id;
              
              return (
                <button
                  key={year.id}
                  onClick={() => onChange(year)}
                  className={`
                    flex-shrink-0 px-4 py-2 rounded-lg font-medium text-sm
                    min-h-[44px] min-w-[80px] flex items-center justify-center
                    transition-all duration-200 border
                    ${isSelected 
                      ? 'bg-blue-600 text-white border-blue-600 shadow-sm' 
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                    }
                  `}
                >
                  <div className="text-center">
                    <div className="font-medium">{year.label}</div>
                    {year.isCurrent && (
                      <div className="text-xs opacity-80">Current</div>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
        
        {/* Swipe hint */}
        <div className="flex items-center justify-center mt-2 text-xs text-gray-400">
          <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16l-4-4m0 0l4-4m-4 4h18"/>
          </svg>
          Swipe to see more years
          <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 8l4 4m0 0l-4 4m4-4H3"/>
          </svg>
        </div>
      </div>
    );
  }

  // Desktop: Dropdown selector with year navigation
  return (
    <div id="year-selector-desktop" className={`bg-white rounded-lg border border-gray-200 p-4 ${className}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h3 className="text-sm font-medium text-gray-900">Financial Year</h3>
          
          {/* Current selection */}
          <div className="relative">
            <button
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              className="flex items-center space-x-2 px-4 py-2 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors"
            >
              <span className="font-medium text-blue-900">
                {selectedYear?.display || selectedYear?.label || 'Select year'}
              </span>
              {selectedYear?.isCurrent && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                  Current
                </span>
              )}
              <svg 
                className={`w-4 h-4 text-blue-600 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`}
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"/>
              </svg>
            </button>
            
            {/* Dropdown */}
            {isDropdownOpen && (
              <div className="absolute top-full left-0 mt-1 w-64 bg-white border border-gray-200 rounded-lg shadow-lg z-10">
                <div className="p-2 max-h-64 overflow-y-auto">
                  {years.map((year) => {
                    const isSelected = selectedYear?.id === year.id;
                    
                    return (
                      <button
                        key={year.id}
                        onClick={() => {
                          onChange(year);
                          setIsDropdownOpen(false);
                        }}
                        className={`
                          w-full text-left px-3 py-2 rounded-md transition-colors flex items-center justify-between
                          ${isSelected 
                            ? 'bg-blue-100 text-blue-900' 
                            : 'text-gray-700 hover:bg-gray-100'
                          }
                        `}
                      >
                        <div>
                          <div className="font-medium">{year.display || year.label}</div>
                          {year.description && (
                            <div className="text-xs text-gray-500">{year.description}</div>
                          )}
                        </div>
                        
                        <div className="flex items-center space-x-2">
                          {year.isCurrent && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                              Current
                            </span>
                          )}
                          {isSelected && (
                            <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"/>
                            </svg>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
        
        {/* Year navigation arrows */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => {
              const currentIndex = years.findIndex(y => y.id === selectedYear?.id);
              if (currentIndex > 0) {
                onChange(years[currentIndex - 1]);
              }
            }}
            disabled={!selectedYear || years.findIndex(y => y.id === selectedYear.id) === 0}
            className="p-2 text-gray-600 hover:text-gray-900 disabled:text-gray-300 disabled:cursor-not-allowed"
            title="Previous year"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7"/>
            </svg>
          </button>
          
          <button
            onClick={() => {
              const currentIndex = years.findIndex(y => y.id === selectedYear?.id);
              if (currentIndex < years.length - 1) {
                onChange(years[currentIndex + 1]);
              }
            }}
            disabled={!selectedYear || years.findIndex(y => y.id === selectedYear.id) === years.length - 1}
            className="p-2 text-gray-600 hover:text-gray-900 disabled:text-gray-300 disabled:cursor-not-allowed"
            title="Next year"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7"/>
            </svg>
          </button>
        </div>
      </div>
      
      {/* Year info */}
      {selectedYear && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          <div className="flex items-center justify-between text-sm">
            <div className="text-gray-600">
              Editing data for <span className="font-medium text-gray-900">{selectedYear.display || selectedYear.label}</span>
            </div>
            {selectedYear.isCurrent && (
              <span className="text-green-600 font-medium">Current financial year</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default YearSelector;