import React from 'react';

/**
 * Category Selection Step - Choose which financial data category to work on
 * Part of the redesigned wizard flow: Year → Category → Fields
 */
const CategorySelection = ({
  availableCategories = [],
  selectedCategory,
  onCategorySelect,
  onBack,
  className = ""
}) => {

  // Define category information with completion status
  const categoryInfo = {
    basic: {
      title: 'Basic Information',
      description: 'Council details, population, and document links',
      icon: '📋',
      estimatedTime: '2-3 minutes',
      priority: 'Required'
    },
    income: {
      title: 'Income & Expenditure',
      description: 'Revenue, spending, and operational finances',
      icon: '💷',
      estimatedTime: '5-7 minutes',
      priority: 'Required'
    },
    balance: {
      title: 'Balance Sheet',
      description: 'Assets, liabilities, and reserves',
      icon: '⚖️',
      estimatedTime: '4-6 minutes',
      priority: 'Required'
    },
    debt: {
      title: 'Debt & Obligations',
      description: 'Borrowing, pensions, and long-term commitments',
      icon: '📊',
      estimatedTime: '3-4 minutes',
      priority: 'Optional'
    },
    other: {
      title: 'Additional Fields',
      description: 'Other council information and financial data',
      icon: '📁',
      estimatedTime: '2-3 minutes',
      priority: 'Optional'
    }
  };

  return (
    <div className={`max-w-4xl mx-auto px-4 py-6 ${className}`}>
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center mb-4">
          <button
            onClick={onBack}
            className="mr-4 p-2 text-gray-500 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-label="Go back"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Choose Data Category</h2>
            <p className="text-gray-600 mt-1">
              Select which financial information you'd like to work on. You can complete categories in any order.
            </p>
          </div>
        </div>
      </div>

      {/* Progress Indicator */}
      <div className="mb-8 p-4 bg-blue-50 border-l-4 border-blue-500">
        <h3 className="font-semibold text-blue-900 mb-2">📈 Smart Approach</h3>
        <p className="text-sm text-blue-800">
          Work on one category at a time to stay focused. Required categories help calculate key metrics like per-capita figures.
          You can always come back to add more data later.
        </p>
      </div>

      {/* Category Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {availableCategories.map(category => {
          const info = categoryInfo[category.key] || {};
          const isSelected = selectedCategory === category.key;
          const completionPercentage = category.completionPercentage || 0;
          const isComplete = completionPercentage >= 100;
          
          return (
            <button
              key={category.key}
              onClick={() => onCategorySelect(category.key)}
              className={`
                p-6 border-2 text-left transition-all duration-200 hover:shadow-md
                ${isSelected 
                  ? 'border-blue-600 bg-blue-50' 
                  : 'border-gray-200 bg-white hover:border-gray-300'
                }
                ${isComplete ? 'ring-2 ring-green-500' : ''}
              `}
            >
              {/* Category Header */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center">
                  <span className="text-3xl mr-3">{info.icon}</span>
                  <div>
                    <h3 className="font-semibold text-gray-900 text-lg">
                      {info.title}
                    </h3>
                    <span className={`text-xs px-2 py-1 border inline-block mt-1 ${
                      info.priority === 'Required' 
                        ? 'border-orange-500 bg-orange-50 text-orange-700'
                        : 'border-gray-400 bg-gray-50 text-gray-600'
                    }`}>
                      {info.priority}
                    </span>
                  </div>
                </div>
                
                {/* Completion Status */}
                {isComplete && (
                  <div className="text-green-600">
                    <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  </div>
                )}
              </div>

              {/* Description */}
              <p className="text-sm text-gray-600 mb-4">
                {info.description}
              </p>

              {/* Progress Bar */}
              <div className="mb-3">
                <div className="flex justify-between text-xs text-gray-500 mb-1">
                  <span>{category.completed || 0} of {category.total || 0} fields</span>
                  <span>{completionPercentage}%</span>
                </div>
                <div className="w-full bg-gray-200 h-2">
                  <div 
                    className={`h-2 transition-all duration-300 ${
                      isComplete ? 'bg-green-600' : 'bg-blue-600'
                    }`}
                    style={{ width: `${completionPercentage}%` }}
                  />
                </div>
              </div>

              {/* Estimated Time */}
              <div className="text-xs text-gray-500 flex items-center">
                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Est. {info.estimatedTime}
              </div>
            </button>
          );
        })}
      </div>

      {/* Continue Button */}
      {selectedCategory && (
        <div className="mt-8 flex justify-center">
          <button
            onClick={() => onCategorySelect(selectedCategory)}
            className="px-8 py-3 bg-blue-600 text-white font-semibold hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors duration-200"
          >
            Continue with {categoryInfo[selectedCategory]?.title}
          </button>
        </div>
      )}

      {/* Help Text */}
      <div className="mt-8 text-center">
        <p className="text-sm text-gray-500">
          💡 <strong>Tip:</strong> Start with required categories (Basic Information, Income & Expenditure, Balance Sheet) 
          for the most accurate calculations.
        </p>
      </div>
    </div>
  );
};

export default CategorySelection;