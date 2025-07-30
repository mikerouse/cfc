import React from 'react';

/**
 * Mobile-First Progress Tracker
 * 
 * Features:
 * - Gamification with points
 * - Visual progress bars
 * - Motivational messaging
 * - Responsive design
 */
const ProgressTracker = ({ progress, isMobile, className = '' }) => {
  const { completed, total, points } = progress;
  const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;

  // Calculate progress levels for motivation
  const getProgressLevel = () => {
    if (percentage >= 90) return { level: 'excellent', color: 'green', message: 'Outstanding! You\'re almost done!' };
    if (percentage >= 70) return { level: 'good', color: 'blue', message: 'Great progress! Keep going!' };
    if (percentage >= 40) return { level: 'fair', color: 'yellow', message: 'Good start! More data helps everyone.' };
    if (percentage >= 20) return { level: 'started', color: 'purple', message: 'Nice! Every contribution matters.' };
    return { level: 'beginning', color: 'gray', message: 'Let\'s get started! Your contributions make a difference.' };
  };

  const progressLevel = getProgressLevel();

  if (isMobile) {
    // Mobile: Compact horizontal progress bar
    return (
      <div id="progress-tracker-mobile" className={`bg-white rounded-lg border border-gray-200 p-4 ${className}`}>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center
              ${progressLevel.color === 'green' ? 'bg-green-100' :
                progressLevel.color === 'blue' ? 'bg-blue-100' :
                progressLevel.color === 'yellow' ? 'bg-yellow-100' :
                progressLevel.color === 'purple' ? 'bg-purple-100' :
                'bg-gray-100'}
            `}>
              <svg className={`w-4 h-4
                ${progressLevel.color === 'green' ? 'text-green-600' :
                  progressLevel.color === 'blue' ? 'text-blue-600' :
                  progressLevel.color === 'yellow' ? 'text-yellow-600' :
                  progressLevel.color === 'purple' ? 'text-purple-600' :
                  'text-gray-600'}
              `} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
              </svg>
            </div>
            <span className="text-sm font-medium text-gray-900">{completed}/{total} completed</span>
          </div>
          
          <div className="flex items-center space-x-2">
            <svg className="w-4 h-4 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
            </svg>
            <span className="text-sm font-medium text-gray-900">{points} pts</span>
          </div>
        </div>
        
        {/* Progress bar */}
        <div className="mb-2">
          <div className="bg-gray-200 rounded-full h-2">
            <div 
              className={`h-2 rounded-full transition-all duration-500
                ${progressLevel.color === 'green' ? 'bg-green-500' :
                  progressLevel.color === 'blue' ? 'bg-blue-500' :
                  progressLevel.color === 'yellow' ? 'bg-yellow-500' :
                  progressLevel.color === 'purple' ? 'bg-purple-500' :
                  'bg-gray-400'}
              `}
              style={{ width: `${percentage}%` }}
            />
          </div>
        </div>
        
        {/* Motivational message */}
        <p className="text-xs text-gray-600 text-center">{progressLevel.message}</p>
      </div>
    );
  }

  // Desktop: Full progress dashboard
  return (
    <div id="progress-tracker-desktop" className={`bg-white rounded-lg border border-gray-200 p-6 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className={`w-10 h-10 rounded-full flex items-center justify-center
            ${progressLevel.color === 'green' ? 'bg-green-100' :
              progressLevel.color === 'blue' ? 'bg-blue-100' :
              progressLevel.color === 'yellow' ? 'bg-yellow-100' :
              progressLevel.color === 'purple' ? 'bg-purple-100' :
              'bg-gray-100'}
          `}>
            <svg className={`w-6 h-6
              ${progressLevel.color === 'green' ? 'text-green-600' :
                progressLevel.color === 'blue' ? 'text-blue-600' :
                progressLevel.color === 'yellow' ? 'text-yellow-600' :
                progressLevel.color === 'purple' ? 'text-purple-600' :
                'text-gray-600'}
            `} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
            </svg>
          </div>
          
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Data Completion Progress</h3>
            <p className="text-sm text-gray-600">{progressLevel.message}</p>
          </div>
        </div>
        
        {/* Stats */}
        <div className="flex items-center space-x-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">{completed}</div>
            <div className="text-xs text-gray-500">Completed</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-400">{total - completed}</div>
            <div className="text-xs text-gray-500">Remaining</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-yellow-600 flex items-center">
              {points}
              <svg className="w-5 h-5 ml-1" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
              </svg>
            </div>
            <div className="text-xs text-gray-500">Points</div>
          </div>
        </div>
      </div>
      
      {/* Progress bar with percentage */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Completion</span>
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
      
      {/* Achievement milestones */}
      <div className="flex items-center justify-between text-xs text-gray-500">
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