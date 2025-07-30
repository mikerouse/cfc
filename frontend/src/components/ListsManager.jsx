import React, { useState } from 'react';
import ListCard from './ListCard';

/**
 * Manager component for custom council lists with drag-and-drop support
 */
const ListsManager = ({ 
  lists = [], 
  onMoveCouncil, 
  onAddToList, 
  years = [], 
  metricChoices = [], 
  apiUrls 
}) => {
  const [expandedLists, setExpandedLists] = useState(new Set());

  // Filter out the default favourites list
  const customLists = lists.filter(list => !list.is_default);

  const toggleListExpansion = (listId) => {
    const newExpanded = new Set(expandedLists);
    if (newExpanded.has(listId)) {
      newExpanded.delete(listId);
    } else {
      newExpanded.add(listId);
    }
    setExpandedLists(newExpanded);
  };

  // Calculate totals across all lists
  const totalLists = customLists.length;
  const totalCouncils = customLists.reduce((sum, list) => sum + (list.council_count || 0), 0);

  if (customLists.length === 0) {
    return (
      <div id="my-lists-custom-section" className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
        <div id="my-lists-custom-header" className="flex items-start mb-4">
          <svg className="w-6 h-6 text-purple-500 mr-3 mt-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          <div>
            <h2 className="text-lg font-semibold text-gray-900 mb-2">My Custom Lists</h2>
            <p className="text-gray-600">Create custom lists to organize councils by region, type, or any criteria you choose</p>
          </div>
        </div>

        <div id="my-lists-custom-empty-state" className="text-center py-8">
          <svg className="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No custom lists yet</h3>
          <p className="text-gray-600 mb-4">
            Create your first custom list to start organizing councils by themes like:
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-6 text-sm">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="font-medium text-blue-900 mb-1">By Region</div>
              <div className="text-blue-700">North London Boroughs, Yorkshire Districts, Welsh Councils</div>
            </div>
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="font-medium text-green-900 mb-1">By Type</div>
              <div className="text-green-700">Metropolitan Boroughs, County Councils, Unitary Authorities</div>
            </div>
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
              <div className="font-medium text-purple-900 mb-1">By Interest</div>
              <div className="text-purple-700">High Debt Councils, Growing Populations, Budget Comparisons</div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with Summary Stats */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-4 sm:p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-start">
            <svg className="w-6 h-6 text-purple-500 mr-3 mt-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">My Custom Lists</h2>
              <p className="text-sm text-gray-600 mt-1">
                {totalLists} list{totalLists !== 1 ? 's' : ''} • 
                {totalCouncils} council{totalCouncils !== 1 ? 's' : ''} total
              </p>
            </div>
          </div>

          {/* Bulk Actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                if (expandedLists.size === customLists.length) {
                  setExpandedLists(new Set());
                } else {
                  setExpandedLists(new Set(customLists.map(list => list.id)));
                }
              }}
              className="text-sm text-gray-600 hover:text-gray-800 transition-colors"
            >
              {expandedLists.size === customLists.length ? 'Collapse All' : 'Expand All'}
            </button>
          </div>
        </div>
      </div>

      {/* Lists Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {customLists.map((list) => (
          <ListCard
            key={list.id}
            list={list}
            expanded={expandedLists.has(list.id)}
            onToggleExpand={() => toggleListExpansion(list.id)}
            onMoveCouncil={onMoveCouncil}
            onAddToList={onAddToList}
            years={years}
            metricChoices={metricChoices}
            apiUrls={apiUrls}
          />
        ))}
      </div>

      {/* Drag & Drop Instructions */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start">
          <svg className="w-5 h-5 text-blue-500 mt-0.5 mr-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd"/>
          </svg>
          <div className="text-sm text-blue-800">
            <strong>💡 Pro Tip:</strong> You can drag councils between lists to reorganize them. 
            On mobile, tap and hold to drag. Use the grip icon (⋮⋮) to easily grab councils. 
            Changes are saved automatically!
          </div>
        </div>
      </div>
    </div>
  );
};

export default ListsManager;