import React, { useState, useEffect, useCallback } from 'react';
import { useDrop } from 'react-dnd';
import CouncilCard from './CouncilCard';
import LoadingSpinner from './LoadingSpinner';

/**
 * Individual list card component with drag-drop zone and statistics
 */
const ListCard = ({ 
  list, 
  expanded = false, 
  onToggleExpand, 
  onMoveCouncil, 
  onAddToList,
  years = [], 
  metricChoices = [], 
  apiUrls 
}) => {
  const [selectedYear, setSelectedYear] = useState(years[0]?.id || '');
  const [selectedMetric, setSelectedMetric] = useState(metricChoices[0]?.value || 'total-debt');
  const [metricData, setMetricData] = useState({ values: {}, total: 0 });
  const [loadingMetrics, setLoadingMetrics] = useState(false);
  const [councils, setCouncils] = useState(list.councils || []);
  
  // Update local state when list prop changes
  useEffect(() => {
    setCouncils(list.councils || []);
  }, [list.councils, list.name]);

  // Drag and drop setup
  const [{ isOver }, drop] = useDrop({
    accept: 'council',
    drop: (item) => {
      if (item.fromListId !== list.id) {
        onMoveCouncil(item.slug, item.fromListId, list.id);
        // Note: State updates are handled by parent MyListsApp component
      }
    },
    collect: (monitor) => ({
      isOver: monitor.isOver(),
    }),
  });

  // Load metric data when year or metric changes
  const loadMetricData = useCallback(async () => {
    if (!selectedYear || !selectedMetric || !apiUrls?.listMetric) return;

    try {
      setLoadingMetrics(true);
      const response = await fetch(
        `${apiUrls.listMetric(list.id)}?field=${selectedMetric}&year=${selectedYear}`
      );
      
      if (!response.ok) throw new Error('Failed to load metrics');
      
      const data = await response.json();
      setMetricData(data);
    } catch (error) {
      console.error('Error loading metrics:', error);
      setMetricData({ values: {}, total: 0 });
    } finally {
      setLoadingMetrics(false);
    }
  }, [selectedYear, selectedMetric, list.id, apiUrls]);

  useEffect(() => {
    if (expanded) {
      loadMetricData();
    }
  }, [expanded, loadMetricData]);

  // Handle council removal from list
  const handleRemoveCouncil = useCallback((councilSlug) => {
    setCouncils(prev => prev.filter(council => council.slug !== councilSlug));
  }, []);

  // Calculate totals
  const councilCount = councils.length;
  const totalPopulation = councils.reduce((sum, council) => {
    const pop = parseInt(council.population) || 0;
    return sum + pop;
  }, 0);

  // Get color classes for this list
  const colorClasses = {
    blue: 'border-blue-200 bg-blue-50',
    green: 'border-green-200 bg-green-50',
    purple: 'border-purple-200 bg-purple-50',
    red: 'border-red-200 bg-red-50',
    yellow: 'border-yellow-200 bg-yellow-50',
    indigo: 'border-indigo-200 bg-indigo-50',
    pink: 'border-pink-200 bg-pink-50',
    gray: 'border-gray-200 bg-gray-50',
  }[list.color] || 'border-blue-200 bg-blue-50';

  const textColorClasses = {
    blue: 'text-blue-800',
    green: 'text-green-800',
    purple: 'text-purple-800',
    red: 'text-red-800',
    yellow: 'text-yellow-800',
    indigo: 'text-indigo-800',
    pink: 'text-pink-800',
    gray: 'text-gray-800',
  }[list.color] || 'text-blue-800';

  return (
    <div
      ref={drop}
      className={`
        bg-white border-2 rounded-lg shadow-sm overflow-hidden transition-all duration-200
        ${isOver ? `${colorClasses} border-dashed` : 'border-gray-200 hover:border-gray-300'}
      `}
    >
      {/* List Header */}
      <div 
        className="p-4 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={onToggleExpand}
      >
        <div className="flex items-start justify-between">
          <div className="flex items-start min-w-0 flex-1">
            {/* Color Indicator */}
            <div className={`
              w-4 h-4 rounded-full flex-shrink-0 mt-1 mr-3 border-2 border-white shadow-sm
              ${colorClasses.replace('bg-', 'bg-').replace('-50', '-400')}
            `} />

            <div className="min-w-0 flex-1">
              <h3 className="font-semibold text-gray-900 text-base leading-tight mb-1">
                {list.name}
              </h3>
              
              {list.description && (
                <p className="text-sm text-gray-600 mb-2 line-clamp-2">
                  {list.description}
                </p>
              )}

              {/* Quick Stats */}
              <div className="flex items-center gap-4 text-sm text-gray-600">
                <div className="flex items-center">
                  <svg className="w-4 h-4 mr-1 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-2m-2 0H5m14 0a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2h2m0 0V9a2 2 0 012-2h2a2 2 0 012 2v10" />
                  </svg>
                  {councilCount} council{councilCount !== 1 ? 's' : ''}
                </div>

                {totalPopulation > 0 && (
                  <div className="flex items-center">
                    <svg className="w-4 h-4 mr-1 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                    </svg>
                    {totalPopulation.toLocaleString()} population
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Expand/Collapse Icon */}
          <div className="flex-shrink-0 ml-2">
            <svg 
              className={`w-5 h-5 text-gray-400 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`} 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>

        {/* Drop Zone Indicator */}
        {isOver && (
          <div className={`mt-3 p-3 border-2 border-dashed rounded-lg ${textColorClasses} ${colorClasses}`}>
            <div className="text-center">
              <svg className="w-8 h-8 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              <p className="font-medium">Drop council here to add to "{list.name}"</p>
            </div>
          </div>
        )}
      </div>

      {/* Expanded Content */}
      {expanded && (
        <div className="border-t border-gray-200">
          {/* Controls Row */}
          <div className="p-4 bg-gray-50 border-b border-gray-200">
            <div className="flex flex-col sm:flex-row gap-3">
              {/* Year Selector */}
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium text-gray-700 whitespace-nowrap">
                  Year:
                </label>
                <select
                  value={selectedYear}
                  onChange={(e) => setSelectedYear(e.target.value)}
                  className="text-sm border border-gray-300 rounded-md px-2 py-1"
                >
                  {years.map(year => (
                    <option key={year.id} value={year.id}>
                      {year.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Metric Selector */}
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium text-gray-700 whitespace-nowrap">
                  Financial Data:
                </label>
                <select
                  value={selectedMetric}
                  onChange={(e) => setSelectedMetric(e.target.value)}
                  className="text-sm border border-gray-300 rounded-md px-2 py-1 flex-1 sm:flex-none"
                >
                  {metricChoices.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Loading Indicator */}
              {loadingMetrics && (
                <div className="flex items-center">
                  <LoadingSpinner size="small" overlay={false} />
                </div>
              )}
            </div>

            {/* Financial Total */}
            {metricData.total > 0 && (
              <div className="mt-3 p-3 bg-white border border-gray-200 rounded-lg">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700">
                    Total {metricChoices.find(([value]) => value === selectedMetric)?.[1]}:
                  </span>
                  <span className="text-lg font-bold text-gray-900">
                    £{metricData.total.toLocaleString()}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Councils List */}
          {councilCount > 0 ? (
            <div className="divide-y divide-gray-200">
              {councils.map((council) => (
                <CouncilCard
                  key={council.slug}
                  council={council}
                  onRemove={() => handleRemoveCouncil(council.slug)}
                  listId={list.id}
                  showRemoveButton={true}
                  isDraggable={true}
                />
              ))}
            </div>
          ) : (
            <div className="p-8 text-center text-gray-500">
              <svg className="w-12 h-12 mx-auto mb-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              <p className="font-medium text-gray-900 mb-1">No councils in this list yet</p>
              <p className="text-sm">
                Drag councils from your favourites or other lists, or use the search above to add councils.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ListCard;