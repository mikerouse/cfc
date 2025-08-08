import React from 'react';

/**
 * GOV.UK-style landing page for council editing
 * Replaces confusing tabs with clear choice cards
 */
const CouncilEditLanding = ({ 
  councilData, 
  progress = {}, 
  onChoiceSelect,
  className = ""
}) => {
  
  const formatProgress = (completed, total) => {
    if (!total || total === 0) return '0%';
    return `${Math.round((completed / total) * 100)}%`;
  };

  const getLastUpdated = () => {
    // This would come from the backend in real implementation
    return "2 weeks ago by Mike Rouse";
  };

  return (
    <div id="council-edit-landing-main" className={`bg-white ${className}`}>
      <div className="max-w-4xl mx-auto px-4 py-6 sm:px-6 sm:py-8">
        {/* Back Navigation */}
        <div id="council-edit-back-nav" className="mb-6">
          <a 
            href={`/councils/${councilData?.slug}/`}
            className="inline-flex items-center text-blue-600 hover:text-blue-800 text-sm font-medium"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
            </svg>
            Back to {councilData?.name}
          </a>
        </div>

        {/* Header */}
        <div id="council-edit-header" className="mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-2">
            {councilData?.name}
          </h1>
          <p className="text-lg text-gray-600">
            Choose what you'd like to edit:
          </p>
        </div>

        {/* Choice Cards */}
        <div id="council-edit-choice-cards" className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          
          {/* Council Details Card */}
          <div id="council-edit-characteristics-card" 
               className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow cursor-pointer group"
               onClick={() => onChoiceSelect('characteristics')}>
            <div className="flex items-start justify-between mb-4">
              <div className="text-4xl">📋</div>
              <div className="text-right">
                <span className="text-sm text-gray-500">Status</span>
                <div className="text-sm font-medium text-green-600">
                  {formatProgress(progress.characteristics || 0, 8)} complete
                </div>
              </div>
            </div>
            
            <h3 className="text-xl font-semibold text-gray-900 mb-3 group-hover:text-blue-600">
              Council Details
            </h3>
            
            <p className="text-gray-600 mb-4">
              Basic information that doesn't change by year
            </p>
            
            <ul className="text-sm text-gray-500 space-y-1 mb-6">
              <li>• Population and demographics</li>
              <li>• Council type and nation</li>
              <li>• Website and contact details</li>
              <li>• Leadership information</li>
            </ul>
            
            <div className="flex items-center justify-between">
              <button className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700 group-hover:bg-blue-700 transition-colors">
                Edit Details →
              </button>
              <span className="text-xs text-gray-400">
                Usually takes 5 minutes
              </span>
            </div>
          </div>

          {/* Financial Data Card */}
          <div id="council-edit-financial-card"
               className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow cursor-pointer group"
               onClick={() => onChoiceSelect('financial')}>
            <div className="flex items-start justify-between mb-4">
              <div className="text-4xl">💰</div>
              <div className="text-right">
                <span className="text-sm text-gray-500">Status</span>
                <div className="text-sm font-medium text-amber-600">
                  {formatProgress(progress.financial || 0, 20)} complete
                </div>
              </div>
            </div>
            
            <h3 className="text-xl font-semibold text-gray-900 mb-3 group-hover:text-blue-600">
              Financial Data
            </h3>
            
            <p className="text-gray-600 mb-4">
              Upload statements or edit financial figures for a specific year
            </p>
            
            <ul className="text-sm text-gray-500 space-y-1 mb-6">
              <li>• Balance sheet items</li>
              <li>• Income & expenditure</li>
              <li>• PDF upload & AI extraction</li>
              <li>• Year-specific population data</li>
            </ul>
            
            <div className="flex items-center justify-between">
              <button className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700 group-hover:bg-blue-700 transition-colors">
                Edit Financial Data →
              </button>
              <span className="text-xs text-gray-400">
                Usually takes 10-15 minutes
              </span>
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div id="council-edit-recent-activity" className="bg-gray-50 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 mb-2">Recent activity</h4>
          <ul className="text-sm text-gray-600 space-y-1">
            <li>• Financial data for 2024/25 - {formatProgress(progress.financial || 0, 20)} complete</li>
            <li>• Council details - {formatProgress(progress.characteristics || 0, 8)} complete</li>
            <li>• Last updated {getLastUpdated()}</li>
          </ul>
        </div>

        {/* Help Text */}
        <div id="council-edit-help" className="mt-6 text-center">
          <p className="text-sm text-gray-500">
            Need help? Check our{' '}
            <a href="/help/council-editing" className="text-blue-600 hover:text-blue-800 underline">
              council editing guide
            </a>
            {' '}or{' '}
            <a href="/contact" className="text-blue-600 hover:text-blue-800 underline">
              contact us
            </a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default CouncilEditLanding;