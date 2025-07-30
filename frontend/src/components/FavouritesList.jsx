import React, { useState } from 'react';
import CouncilCard from './CouncilCard';

/**
 * Favourites list component - displays user's default favourites list
 */
const FavouritesList = ({ 
  councils = [], 
  onRemoveFromFavourites, 
  onAddToList, 
  lists = [] 
}) => {
  const [sortBy, setSortBy] = useState('name');
  const [sortOrder, setSortOrder] = useState('asc');

  // Calculate totals
  const totalPopulation = councils.reduce((sum, council) => {
    const pop = parseInt(council.population) || 0;
    return sum + pop;
  }, 0);

  // Sort councils
  const sortedCouncils = [...councils].sort((a, b) => {
    let aVal, bVal;
    
    switch (sortBy) {
      case 'population':
        aVal = parseInt(a.population) || 0;
        bVal = parseInt(b.population) || 0;
        break;
      case 'name':
      default:
        aVal = a.name.toLowerCase();
        bVal = b.name.toLowerCase();
        break;
    }

    if (typeof aVal === 'string') {
      return sortOrder === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    } else {
      return sortOrder === 'asc' ? aVal - bVal : bVal - aVal;
    }
  });

  const handleSort = (newSortBy) => {
    if (sortBy === newSortBy) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(newSortBy);
      setSortOrder('asc');
    }
  };

  if (councils.length === 0) {
    return (
      <div id="my-lists-favourites-section" className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
        <div id="my-lists-favourites-header-empty" className="flex items-start mb-4">
          <svg className="w-6 h-6 text-blue-500 mr-3 mt-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
          </svg>
          <div>
            <h2 className="text-lg font-semibold text-gray-900 mb-2">My Favourites</h2>
            <p className="text-gray-600">Your default list for quick access to councils you follow</p>
          </div>
        </div>

        <div id="my-lists-favourites-empty-state" className="text-center py-8">
          <svg className="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
          </svg>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No favourite councils yet</h3>
          <p className="text-gray-600 mb-4">
            Use the search above to find councils and add them to your favourites for quick access.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div id="my-lists-favourites-section" className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
      {/* Header */}
      <div id="my-lists-favourites-header" className="px-4 sm:px-6 py-4 border-b border-gray-200">
        <div className="flex items-start justify-between">
          <div className="flex items-start">
            <svg className="w-6 h-6 text-blue-500 mr-3 mt-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
            </svg>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">My Favourites</h2>
              <p id="my-lists-favourites-stats" className="text-sm text-gray-600 mt-1">
                {councils.length} council{councils.length !== 1 ? 's' : ''} • 
                Total population: {totalPopulation.toLocaleString()}
              </p>
            </div>
          </div>

          {/* Sort Controls */}
          <div id="my-lists-favourites-sort-controls" className="flex items-center gap-2">
            <span className="text-sm text-gray-500">Sort by:</span>
            <select 
              id="my-lists-favourites-sort-select"
              value={`${sortBy}-${sortOrder}`}
              onChange={(e) => {
                const [newSortBy, newOrder] = e.target.value.split('-');
                setSortBy(newSortBy);
                setSortOrder(newOrder);
              }}
              className="text-sm border border-gray-300 rounded-md px-2 py-1"
            >
              <option value="name-asc">Name (A-Z)</option>
              <option value="name-desc">Name (Z-A)</option>
              <option value="population-desc">Population (High-Low)</option>
              <option value="population-asc">Population (Low-High)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Desktop Table View */}
      <div id="my-lists-favourites-desktop-view" className="hidden md:block overflow-x-auto">
        <table id="my-lists-favourites-table" className="min-w-full divide-y divide-gray-200">
          <thead id="my-lists-favourites-table-head" className="bg-gray-50">
            <tr>
              <th 
                id="my-lists-favourites-header-name"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('name')}
              >
                <div className="flex items-center">
                  Council Name
                  {sortBy === 'name' && (
                    <svg className={`w-4 h-4 ml-1 ${sortOrder === 'desc' ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l4-4 4 4m0 6l-4 4-4-4" />
                    </svg>
                  )}
                </div>
              </th>
              <th 
                id="my-lists-favourites-header-population"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('population')}
              >
                <div className="flex items-center">
                  Population
                  {sortBy === 'population' && (
                    <svg className={`w-4 h-4 ml-1 ${sortOrder === 'desc' ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l4-4 4 4m0 6l-4 4-4-4" />
                    </svg>
                  )}
                </div>
              </th>
              <th id="my-lists-favourites-header-actions" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody id="my-lists-favourites-table-body" className="bg-white divide-y divide-gray-200">
            {sortedCouncils.map((council) => (
              <tr key={council.slug} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <div className="flex-shrink-0 h-10 w-10">
                      {council.logo_url ? (
                        <img className="h-10 w-10 rounded-lg object-cover" src={council.logo_url} alt={council.name} />
                      ) : (
                        <div className="h-10 w-10 rounded-lg bg-gray-200 flex items-center justify-center">
                          <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-2m-2 0H5m14 0a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2h2m0 0V9a2 2 0 012-2h2a2 2 0 012 2v10" />
                          </svg>
                        </div>
                      )}
                    </div>
                    <div className="ml-4">
                      <div className="text-sm font-medium text-gray-900">
                        <a href={`/councils/${council.slug}/`} className="text-blue-600 hover:text-blue-700 hover:underline">
                          {council.name}
                        </a>
                      </div>
                      <div className="text-sm text-gray-500">
                        {council.type} • {council.nation}
                      </div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {council.population ? council.population.toLocaleString() : 'Not available'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <div className="flex items-center justify-end gap-2">
                    {/* Add to List Dropdown */}
                    {lists.filter(list => !list.is_default).length > 0 && (
                      <select 
                        className="text-xs border border-gray-300 rounded-md px-2 py-1"
                        onChange={(e) => {
                          if (e.target.value) {
                            onAddToList(e.target.value, council.slug);
                            e.target.value = '';
                          }
                        }}
                      >
                        <option value="">Add to list...</option>
                        {lists.filter(list => !list.is_default).map(list => (
                          <option key={list.id} value={list.id}>
                            {list.name}
                          </option>
                        ))}
                      </select>
                    )}
                    
                    {/* Remove Button */}
                    <button
                      onClick={() => onRemoveFromFavourites(council.slug)}
                      className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-md text-red-700 bg-red-50 border border-red-300 hover:bg-red-100 transition-colors"
                      title="Remove from favourites"
                    >
                      <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                      Remove
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile Card View */}
      <div id="my-lists-favourites-mobile-view" className="md:hidden">
        <div id="my-lists-favourites-mobile-container" className="divide-y divide-gray-200">
          {sortedCouncils.map((council) => (
            <CouncilCard
              key={council.slug}
              council={council}
              onRemove={() => onRemoveFromFavourites(council.slug)}
              onAddToList={onAddToList}
              lists={lists.filter(list => !list.is_default)}
              showRemoveButton={true}
              isDraggable={false}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

export default FavouritesList;