import React, { useState, useEffect, useRef, useCallback } from 'react';
import LoadingSpinner from './LoadingSpinner';

/**
 * Search and add councils component with live search and quick actions
 */
const SearchAndAdd = ({ 
  onAddToFavourites, 
  onAddToList, 
  lists = [], 
  apiUrls, 
  csrfToken 
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const searchRef = useRef(null);
  const resultsRef = useRef(null);

  /**
   * Debounced search function
   */
  const performSearch = useCallback(async (query) => {
    if (query.length < 2) {
      setSearchResults([]);
      setShowResults(false);
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(`${apiUrls.searchCouncils}?q=${encodeURIComponent(query)}`, {
        headers: {
          'X-CSRFToken': csrfToken,
        },
      });

      if (!response.ok) {
        throw new Error('Search failed');
      }

      const results = await response.json();
      setSearchResults(results);
      setShowResults(true);
    } catch (error) {
      console.error('Search error:', error);
      setSearchResults([]);
      setShowResults(false);
    } finally {
      setLoading(false);
    }
  }, [apiUrls.searchCouncils, csrfToken]);

  // Debounce search queries
  useEffect(() => {
    const timer = setTimeout(() => {
      performSearch(searchQuery);
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery, performSearch]);

  // Handle click outside to close results
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        resultsRef.current && 
        !resultsRef.current.contains(event.target) &&
        !searchRef.current.contains(event.target)
      ) {
        setShowResults(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  /**
   * Handle adding council to favourites
   */
  const handleAddToFavourites = useCallback(async (councilSlug, councilName) => {
    try {
      await onAddToFavourites(councilSlug);
      setShowResults(false);
      setSearchQuery('');
    } catch (error) {
      // Error handling is done in parent component
    }
  }, [onAddToFavourites]);

  /**
   * Handle adding council to specific list
   */
  const handleAddToList = useCallback(async (listId, councilSlug, councilName) => {
    try {
      await onAddToList(listId, councilSlug);
      setShowResults(false);
      setSearchQuery('');
    } catch (error) {
      // Error handling is done in parent component
    }
  }, [onAddToList]);

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-4 sm:p-6">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Find Councils</h2>
        <p className="text-sm text-gray-600">
          Search for councils to add to your favourites or custom lists
        </p>
      </div>

      {/* Search Input */}
      <div className="relative mb-4">
        <div className="relative">
          <input
            ref={searchRef}
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-4 py-3 pl-12 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 min-h-[44px]"
            placeholder="Search councils by name, type, or location..."
            autoComplete="off"
          />
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            {loading ? (
              <LoadingSpinner size="small" overlay={false} />
            ) : (
              <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            )}
          </div>
        </div>

        {/* Search Results Dropdown */}
        {showResults && searchResults.length > 0 && (
          <div 
            ref={resultsRef}
            className="absolute z-50 w-full bg-white border border-gray-300 rounded-lg shadow-lg mt-1 max-h-96 overflow-y-auto"
          >
            {searchResults.map((council) => (
              <div 
                key={council.slug} 
                className="p-4 border-b border-gray-100 last:border-b-0 hover:bg-gray-50"
              >
                <div className="flex items-start justify-between gap-4">
                  {/* Council Info */}
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-gray-900 truncate">
                      <a 
                        href={`/councils/${council.slug}/`}
                        className="text-blue-600 hover:text-blue-700 hover:underline"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {council.name}
                      </a>
                    </h3>
                    <div className="mt-1 text-sm text-gray-600 space-y-1">
                      {council.type && (
                        <div>{council.type}</div>
                      )}
                      {council.nation && (
                        <div>{council.nation}</div>
                      )}
                      {council.population && (
                        <div>Population: {council.population.toLocaleString()}</div>
                      )}
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex flex-col gap-2 min-w-0">
                    {/* Add to Favourites */}
                    <button
                      onClick={() => handleAddToFavourites(council.slug, council.name)}
                      className="inline-flex items-center px-3 py-2 text-xs font-medium rounded-md text-blue-700 bg-blue-50 border border-blue-300 hover:bg-blue-100 transition-colors min-w-[80px] justify-center"
                      title="Add to favourites"
                    >
                      <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                      </svg>
                      Favourite
                    </button>

                    {/* Add to Custom List */}
                    {lists.length > 0 && (
                      <div className="flex gap-1">
                        <select 
                          className="flex-1 text-xs border border-gray-300 rounded-md px-2 py-1 min-w-[100px]"
                          onChange={(e) => {
                            if (e.target.value) {
                              handleAddToList(e.target.value, council.slug, council.name);
                              e.target.value = ''; // Reset selection
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
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* No Results Message */}
        {showResults && searchResults.length === 0 && searchQuery.length >= 2 && !loading && (
          <div className="absolute z-50 w-full bg-white border border-gray-300 rounded-lg shadow-lg mt-1">
            <div className="p-4 text-center text-gray-500">
              <svg className="w-8 h-8 mx-auto mb-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9.172 16.172a4 4 0 015.656 0M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p>No councils found matching "{searchQuery}"</p>
              <p className="text-sm mt-1">Try a different search term</p>
            </div>
          </div>
        )}
      </div>

      {/* Search Tips */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
        <div className="flex items-start">
          <svg className="w-5 h-5 text-blue-500 mt-0.5 mr-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd"/>
          </svg>
          <div className="text-sm text-blue-800">
            <strong>Search Tips:</strong> Try searching by council name (e.g., "Birmingham"), 
            type (e.g., "District"), or location (e.g., "Yorkshire"). 
            You can add councils to your favourites or custom lists for easy access.
          </div>
        </div>
      </div>
    </div>
  );
};

export default SearchAndAdd;