import React from 'react';

/**
 * Enhanced Mobile-First Progress Tracker
 * 
 * Features:
 * - Detailed field-level progress indicators
 * - Required vs optional field tracking
 * - Section-wise completion percentages
 * - Visual progress bars
 * - Motivational messaging
 * - Responsive design
 */
const ProgressTracker = ({ 
  progress, 
  isMobile, 
  className = '',
  sectionsProgress = {},
  showSectionDetails = false 
}) => {
  const { completed, total, points, required = 0, optional = 0 } = progress;
  const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;
  const requiredPercentage = required > 0 ? Math.round((Math.min(completed, required) / required) * 100) : 100;

  // Calculate progress levels for motivation with enhanced messaging
  const getProgressLevel = () => {
    if (percentage >= 90) return { 
      level: 'excellent', 
      color: 'green', 
      message: 'Outstanding! You\'re almost done!',
      emoji: '🎉'
    };
    if (percentage >= 70) return { 
      level: 'good', 
      color: 'blue', 
      message: 'Great progress! Keep going!',
      emoji: '🚀'
    };
    if (percentage >= 40) return { 
      level: 'fair', 
      color: 'yellow', 
      message: 'Good start! More data helps everyone.',
      emoji: '⭐'
    };
    if (percentage >= 20) return { 
      level: 'started', 
      color: 'purple', 
      message: 'Nice! Every contribution matters.',
      emoji: '💪'
    };
    return { 
      level: 'beginning', 
      color: 'gray', 
      message: 'Let\'s get started! Your contributions make a difference.',
      emoji: '🌱'
    };
  };

  const progressLevel = getProgressLevel();

  // Calculate required field status for priority indication
  const getRequiredFieldsStatus = () => {
    if (required === 0) return null;
    const requiredCompleted = Math.min(completed, required);
    return {
      completed: requiredCompleted,
      total: required,
      percentage: requiredPercentage,
      isComplete: requiredCompleted >= required
    };
  };

  const requiredStatus = getRequiredFieldsStatus();

  if (isMobile) {
    // Mobile: Enhanced compact progress display with required field priority
    return (
      <div id="progress-tracker-mobile" className={`bg-white rounded-lg border border-gray-200 p-4 ${className}`}>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-lg
              ${progressLevel.color === 'green' ? 'bg-green-100' :
                progressLevel.color === 'blue' ? 'bg-blue-100' :
                progressLevel.color === 'yellow' ? 'bg-yellow-100' :
                progressLevel.color === 'purple' ? 'bg-purple-100' :
                'bg-gray-100'}
            `}>
              {progressLevel.emoji}
            </div>
            <div>
              <span className="text-sm font-medium text-gray-900">{completed}/{total} completed</span>
              {requiredStatus && (
                <div className="text-xs text-gray-600">
                  {requiredStatus.isComplete ? (
                    <span className="text-green-600">✓ All required fields complete</span>
                  ) : (
                    <span className="text-orange-600">
                      {requiredStatus.completed}/{requiredStatus.total} required fields
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
          <div className="text-right">
            <span className={`text-sm font-medium
              ${progressLevel.color === 'green' ? 'text-green-600' :
                progressLevel.color === 'blue' ? 'text-blue-600' :
                progressLevel.color === 'yellow' ? 'text-yellow-600' :
                progressLevel.color === 'purple' ? 'text-purple-600' :
                'text-gray-600'}
            `}>
              {percentage}%
            </span>
            {points && (
              <div className="text-xs text-gray-500">{points} pts</div>
            )}
          </div>
        </div>

        {/* Enhanced Progress Bar with Required/Optional Indication */}
        <div className="space-y-2">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className={`h-2 rounded-full transition-all duration-300
                ${progressLevel.color === 'green' ? 'bg-green-500' :
                  progressLevel.color === 'blue' ? 'bg-blue-500' :
                  progressLevel.color === 'yellow' ? 'bg-yellow-500' :
                  progressLevel.color === 'purple' ? 'bg-purple-500' :
                  'bg-gray-500'}
              `}
              style={{ width: `${percentage}%` }}
            />
          </div>
          
          {/* Required Fields Progress Bar */}
          {requiredStatus && !requiredStatus.isComplete && (
            <div className="space-y-1">
              <div className="text-xs text-gray-600 flex items-center justify-between">
                <span>Required fields:</span>
                <span className="text-orange-600">{requiredStatus.percentage}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-1">
                <div 
                  className="h-1 rounded-full bg-orange-500 transition-all duration-300"
                  style={{ width: `${requiredStatus.percentage}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Motivational Message */}
        <div className="mt-3">
          <p className="text-xs text-gray-600">{progressLevel.message}</p>
        </div>

        {/* Section Details (collapsible) */}
        {showSectionDetails && Object.keys(sectionsProgress).length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-100">
            <details className="cursor-pointer">
              <summary className="text-xs font-medium text-gray-700 hover:text-gray-900">
                Section Progress
              </summary>
              <div className="mt-2 space-y-2">
                {Object.entries(sectionsProgress).map(([sectionName, sectionData]) => (
                  <div key={sectionName} className="flex items-center justify-between">
                    <span className="text-xs text-gray-600 capitalize">{sectionName}:</span>
                    <div className="flex items-center space-x-2">
                      <div className="w-16 bg-gray-200 rounded-full h-1">
                        <div 
                          className="h-1 rounded-full bg-blue-500 transition-all duration-300"
                          style={{ width: `${sectionData.percentage || 0}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-500 w-8 text-right">
                        {sectionData.percentage || 0}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </details>
          </div>
        )}
      </div>
    );
  }

  // Desktop: Enhanced full progress dashboard
  return (
    <div id="progress-tracker-desktop" className={`bg-white rounded-lg border border-gray-200 p-6 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className={`w-12 h-12 rounded-full flex items-center justify-center text-2xl
            ${progressLevel.color === 'green' ? 'bg-green-100' :
              progressLevel.color === 'blue' ? 'bg-blue-100' :
              progressLevel.color === 'yellow' ? 'bg-yellow-100' :
              progressLevel.color === 'purple' ? 'bg-purple-100' :
              'bg-gray-100'}
          `}>
            {progressLevel.emoji}
          </div>
          
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Data Completion Progress</h3>
            <p className="text-sm text-gray-600">{progressLevel.message}</p>
          </div>
        </div>
        
        {/* Enhanced Stats */}
        <div className="flex items-center space-x-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">{completed}</div>
            <div className="text-xs text-gray-500">Completed</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-400">{total - completed}</div>
            <div className="text-xs text-gray-500">Remaining</div>
          </div>
          {requiredStatus && (
            <div className="text-center">
              <div className={`text-2xl font-bold ${requiredStatus.isComplete ? 'text-green-600' : 'text-orange-600'}`}>
                {requiredStatus.completed}
              </div>
              <div className="text-xs text-gray-500">Required</div>
            </div>
          )}
          {points && (
            <div className="text-center">
              <div className="text-2xl font-bold text-yellow-600 flex items-center">
                {points}
                <svg className="w-5 h-5 ml-1" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
                </svg>
              </div>
              <div className="text-xs text-gray-500">Points</div>
            </div>
          )}
        </div>
      </div>
      
      {/* Enhanced Progress bar with percentage */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Overall Completion</span>
          <span className="text-sm font-medium text-gray-900">{percentage}%</span>
        </div>
        <div className="bg-gray-200 rounded-full h-3">
          <div 
            className={`h-3 rounded-full transition-all duration-500 relative
              ${progressLevel.color === 'green' ? 'bg-green-500' :
                progressLevel.color === 'blue' ? 'bg-blue-500' :
                progressLevel.color === 'yellow' ? 'bg-yellow-500' :
                progressLevel.color === 'purple' ? 'bg-purple-500' :
                'bg-gray-400'}
            `}
            style={{ width: `${percentage}%` }}
          >
            {/* Animated glow effect for high completion */}
            {percentage > 80 && (
              <div className="absolute inset-0 rounded-full animate-pulse bg-white opacity-30" />
            )}
          </div>
        </div>
      </div>

      {/* Required Fields Progress */}
      {requiredStatus && (
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Required Fields</span>
            <span className={`text-sm font-medium ${requiredStatus.isComplete ? 'text-green-600' : 'text-orange-600'}`}>
              {requiredStatus.percentage}%
            </span>
          </div>
          <div className="bg-gray-200 rounded-full h-2">
            <div 
              className={`h-2 rounded-full transition-all duration-500
                ${requiredStatus.isComplete ? 'bg-green-500' : 'bg-orange-500'}
              `}
              style={{ width: `${requiredStatus.percentage}%` }}
            />
          </div>
        </div>
      )}

      {/* Section Progress */}
      {showSectionDetails && Object.keys(sectionsProgress).length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <h4 className="text-sm font-medium text-gray-700 mb-3">Section Progress</h4>
          <div className="grid grid-cols-2 gap-4">
            {Object.entries(sectionsProgress).map(([sectionName, sectionData]) => (
              <div key={sectionName} className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 capitalize">{sectionName}</span>
                  <span className="text-sm font-medium text-gray-900">
                    {sectionData.percentage || 0}%
                  </span>
                </div>
                <div className="bg-gray-200 rounded-full h-2">
                  <div 
                    className="h-2 rounded-full bg-blue-500 transition-all duration-300"
                    style={{ width: `${sectionData.percentage || 0}%` }}
                  />
                </div>
                <div className="text-xs text-gray-500">
                  {sectionData.completed || 0} of {sectionData.total || 0} fields
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Achievement milestones */}
      <div className="flex items-center justify-between text-xs text-gray-500 mt-4">
        <div className={`flex items-center space-x-1 ${percentage >= 25 ? 'text-green-600' : ''}`}>
          <div className={`w-2 h-2 rounded-full ${percentage >= 25 ? 'bg-green-500' : 'bg-gray-300'}`} />
          <span>25% Basic Info</span>
        </div>
        <div className={`flex items-center space-x-1 ${percentage >= 50 ? 'text-blue-600' : ''}`}>
          <div className={`w-2 h-2 rounded-full ${percentage >= 50 ? 'bg-blue-500' : 'bg-gray-300'}`} />
          <span>50% Good Progress</span>
        </div>
        <div className={`flex items-center space-x-1 ${percentage >= 75 ? 'text-purple-600' : ''}`}>
          <div className={`w-2 h-2 rounded-full ${percentage >= 75 ? 'bg-purple-500' : 'bg-gray-300'}`} />
          <span>75% Nearly Complete</span>
        </div>
        <div className={`flex items-center space-x-1 ${percentage >= 90 ? 'text-yellow-600' : ''}`}>
          <div className={`w-2 h-2 rounded-full ${percentage >= 90 ? 'bg-yellow-500' : 'bg-gray-300'}`} />
          <span>90% Excellent!</span>
        </div>
      </div>
    </div>
  );
};

export default ProgressTracker;