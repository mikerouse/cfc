import React from 'react';

/**
 * Mobile-First Tab Navigation for Council Edit
 * 
 * Features:
 * - Bottom navigation for mobile (thumb-friendly)
 * - 44px minimum touch targets
 * - Progress indicators per tab
 * - Clear visual separation of temporal vs non-temporal
 */
const TabNavigation = ({ activeTab, onChange, isMobile, progress, className = '' }) => {
  const tabs = [
    {
      id: 'characteristics',
      name: 'Characteristics',
      shortName: 'Chars',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
        </svg>
      ),
      description: 'Council type, website, nation',
      category: 'non-temporal',
      color: 'blue'
    },
    {
      id: 'general',
      name: 'General Data',
      shortName: 'General',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
        </svg>
      ),
      description: 'Links, political control (yearly)',
      category: 'temporal',
      color: 'green'
    },
    {
      id: 'financial',
      name: 'Financial Data',
      shortName: 'Financial',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1"/>
        </svg>
      ),
      description: 'Debt, expenditure, revenue (yearly)',
      category: 'temporal',
      color: 'purple'
    }
  ];

  const getTabProgress = (tabId) => {
    // Mock progress calculation - would be real in production
    const baseProgress = Math.floor(Math.random() * 8) + 2;
    return {
      completed: baseProgress,
      total: 10,
      percentage: Math.round((baseProgress / 10) * 100)
    };
  };

  const getColorClasses = (tab, isActive) => {
    const baseClasses = {
      blue: {
        active: 'bg-blue-600 text-white border-blue-600',
        inactive: 'text-blue-600 border-blue-200 hover:bg-blue-50'
      },
      green: {
        active: 'bg-green-600 text-white border-green-600',
        inactive: 'text-green-600 border-green-200 hover:bg-green-50'
      },
      purple: {
        active: 'bg-purple-600 text-white border-purple-600',
        inactive: 'text-purple-600 border-purple-200 hover:bg-purple-50'
      }
    };

    return baseClasses[tab.color][isActive ? 'active' : 'inactive'];
  };

  if (isMobile) {
    // Mobile: Bottom navigation with large touch targets
    return (
      <nav id="council-edit-bottom-nav" className={`bg-white border-t border-gray-200 shadow-lg ${className}`}>
        <div className="grid grid-cols-3 gap-0">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            const tabProgress = getTabProgress(tab.id);
            
            return (
              <button
                key={tab.id}
                onClick={() => onChange(tab.id)}
                className={`
                  min-h-[60px] px-2 py-3 flex flex-col items-center justify-center
                  transition-all duration-200 border-t-2 relative
                  ${getColorClasses(tab, isActive)}
                `}
                aria-label={`${tab.name} - ${tabProgress.completed}/${tabProgress.total} completed`}
              >
                {/* Icon */}
                <div className="flex-shrink-0 mb-1">
                  {tab.icon}
                </div>
                
                {/* Label */}
                <span className="text-xs font-medium leading-tight text-center">
                  {tab.shortName}
                </span>
                
                {/* Progress indicator */}
                <div className="absolute bottom-1 left-1/2 transform -translate-x-1/2">
                  <div className="flex space-x-1">
                    {[...Array(3)].map((_, i) => (
                      <div 
                        key={i}
                        className={`w-1 h-1 rounded-full ${
                          i < Math.ceil(tabProgress.percentage / 34) 
                            ? (isActive ? 'bg-white' : `bg-${tab.color}-400`)
                            : 'bg-gray-300'
                        }`}
                      />
                    ))}
                  </div>
                </div>
                
                {/* Temporal indicator */}
                {tab.category === 'temporal' && (
                  <div className="absolute top-2 right-2">
                    <svg className="w-3 h-3 opacity-60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </nav>
    );
  }

  // Desktop: Horizontal tabs with full information
  return (
    <nav id="council-edit-desktop-nav" className={`bg-white border-b border-gray-200 ${className}`}>
      <div className="mx-auto px-6">
        <div className="flex space-x-8">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            const tabProgress = getTabProgress(tab.id);
            
            return (
              <button
                key={tab.id}
                onClick={() => onChange(tab.id)}
                className={`
                  py-4 px-6 border-b-2 font-medium text-sm transition-all duration-200
                  min-h-[60px] flex items-center space-x-3 hover:text-gray-700
                  ${getColorClasses(tab, isActive)}
                `}
                aria-label={`${tab.name} - ${tabProgress.completed}/${tabProgress.total} completed`}
              >
                {/* Icon */}
                <div className="flex-shrink-0">
                  {tab.icon}
                </div>
                
                {/* Content */}
                <div className="flex flex-col items-start">
                  <div className="flex items-center space-x-2">
                    <span className="font-medium">{tab.name}</span>
                    
                    {/* Temporal indicator */}
                    {tab.category === 'temporal' && (
                      <svg className="w-4 h-4 opacity-60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                      </svg>
                    )}
                  </div>
                  
                  <span className="text-xs opacity-75 mt-1">{tab.description}</span>
                  
                  {/* Progress bar */}
                  <div className="w-full bg-gray-200 rounded-full h-1 mt-2">
                    <div 
                      className={`h-1 rounded-full bg-${tab.color}-400 transition-all duration-300`}
                      style={{ width: `${tabProgress.percentage}%` }}
                    />
                  </div>
                  
                  {/* Progress text */}
                  <span className="text-xs opacity-60 mt-1">
                    {tabProgress.completed}/{tabProgress.total} completed
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </nav>
  );
};

export default TabNavigation;