import React, { useState, useEffect, useCallback } from 'react';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { TouchBackend } from 'react-dnd-touch-backend';
import { isMobile } from 'react-device-detect';
import SearchAndAdd from './SearchAndAdd';
import FavouritesList from './FavouritesList';
import ListsManager from './ListsManager';
import ListCreator from './ListCreator';
import LoadingSpinner from './LoadingSpinner';
import ErrorBoundary from './ErrorBoundary';

/**
 * Main container component for the enhanced My Lists feature
 * Provides drag-and-drop functionality and manages overall state
 */
const MyListsApp = ({ initialData = {} }) => {
  // State management
  const [lists, setLists] = useState(initialData.lists || []);
  const [favouritesList, setFavouritesList] = useState(initialData.favourites || []);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showListCreator, setShowListCreator] = useState(false);
  const [notification, setNotification] = useState(null);

  // Configuration from Django context
  const [config] = useState({
    apiUrls: {
      searchCouncils: '/api/councils/search/',
      createList: '/lists/create/',
      addFavourite: '/lists/favourites/add/',
      removeFavourite: '/lists/favourites/remove/',
      addToList: (listId) => `/lists/${listId}/add/`,
      removeFromList: (listId) => `/lists/${listId}/remove/`,
      moveCouncil: '/lists/move/',
      listMetric: (listId) => `/lists/${listId}/metric/`,
    },
    csrfToken: document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                getCsrfTokenFromCookie(),
    user: initialData.user || {},
    years: initialData.years || [],
    metricChoices: initialData.metricChoices || [],
  });

  /**
   * Get CSRF token from cookie as fallback
   */
  function getCsrfTokenFromCookie() {
    const name = 'csrftoken';
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
      const [cookieName, value] = cookie.trim().split('=');
      if (cookieName === name) {
        return decodeURIComponent(value);
      }
    }
    return '';
  }

  /**
   * Show notification message to user
   */
  const showNotification = useCallback((message, type = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 3000);
  }, []);

  /**
   * Generic API call handler with error handling
   */
  const apiCall = useCallback(async (url, options = {}) => {
    try {
      setError(null);
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-CSRFToken': config.csrfToken,
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (err) {
      console.error('API call failed:', err);
      setError(err.message);
      showNotification(`Error: ${err.message}`, 'error');
      throw err;
    }
  }, [config.csrfToken, showNotification]);

  /**
   * Add council to favourites list
   */
  const addToFavourites = useCallback(async (councilSlug) => {
    try {
      setLoading(true);
      const data = await apiCall(config.apiUrls.addFavourite, {
        method: 'POST',
        body: `council=${encodeURIComponent(councilSlug)}`,
      });

      if (data.success) {
        // Refresh favourites list - in a real app we'd optimistically update
        showNotification(`Added to favourites`, 'success');
        // Note: We'd normally update state here, but for now just show success
      }
    } catch (err) {
      // Error already handled in apiCall
    } finally {
      setLoading(false);
    }
  }, [apiCall, config.apiUrls.addFavourite, showNotification]);

  /**
   * Remove council from favourites list
   */
  const removeFromFavourites = useCallback(async (councilSlug) => {
    try {
      setLoading(true);
      const data = await apiCall(config.apiUrls.removeFavourite, {
        method: 'POST',
        body: `council=${encodeURIComponent(councilSlug)}`,
      });

      if (data.success) {
        // Update local state
        setFavouritesList(prev => prev.filter(council => council.slug !== councilSlug));
        showNotification(`Removed from favourites`, 'success');
      }
    } catch (err) {
      // Error already handled in apiCall
    } finally {
      setLoading(false);
    }
  }, [apiCall, config.apiUrls.removeFavourite, showNotification]);

  /**
   * Add council to a specific list
   */
  const addToList = useCallback(async (listId, councilSlug) => {
    try {
      setLoading(true);
      const data = await apiCall(config.apiUrls.addToList(listId), {
        method: 'POST',
        body: `council=${encodeURIComponent(councilSlug)}`,
      });

      if (data.success) {
        showNotification(data.message, 'success');
        // Update local state - find the list and add council
        // This would be more sophisticated in a real app with proper state management
      }
    } catch (err) {
      // Error already handled in apiCall
    } finally {
      setLoading(false);
    }
  }, [apiCall, config.apiUrls.addToList, showNotification]);

  /**
   * Move council between lists (drag & drop handler)
   */
  const moveCouncilBetweenLists = useCallback(async (councilSlug, fromListId, toListId) => {
    if (fromListId === toListId) return;

    try {
      setLoading(true);
      const data = await apiCall(config.apiUrls.moveCouncil, {
        method: 'POST',
        body: `council=${encodeURIComponent(councilSlug)}&from=${fromListId}&to=${toListId}`,
      });

      if (data.success) {
        showNotification(data.message, 'success');
        // Update local state for both lists
        // This would trigger a re-render with updated counts
      }
    } catch (err) {
      // Error already handled in apiCall
    } finally {
      setLoading(false);
    }
  }, [apiCall, config.apiUrls.moveCouncil, showNotification]);

  /**
   * Create a new list
   */
  const createList = useCallback(async (listData) => {
    try {
      setLoading(true);
      const data = await apiCall(config.apiUrls.createList, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(listData),
      });

      if (data.success) {
        showNotification(data.message, 'success');
        setShowListCreator(false);
        
        // Add the new list to our local state
        setLists(prevLists => [...prevLists, data.list]);
      }
    } catch (err) {
      showNotification(`Failed to create list: ${err.message}`, 'error');
      throw err; // Re-throw so ListCreator can show the error
    } finally {
      setLoading(false);
    }
  }, [apiCall, config.apiUrls.createList, showNotification]);

  // Choose appropriate drag & drop backend based on device
  const dndBackend = isMobile ? TouchBackend : HTML5Backend;
  const dndOptions = isMobile ? { enableMouseEvents: true } : {};

  return (
    <ErrorBoundary>
      <DndProvider backend={dndBackend} options={dndOptions}>
        <div className="my-lists-app">
          {/* Notification Display */}
          {notification && (
            <div className={`fixed top-4 right-4 z-50 max-w-sm p-4 rounded-lg shadow-lg ${
              notification.type === 'success' 
                ? 'bg-green-50 border border-green-200 text-green-800'
                : 'bg-red-50 border border-red-200 text-red-800'
            }`}>
              <div className="flex items-start">
                <div className="flex-1">
                  {notification.message}
                </div>
                <button 
                  onClick={() => setNotification(null)}
                  className="ml-3 text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
          )}

          {/* Loading Overlay */}
          {loading && <LoadingSpinner />}

          {/* Error Display */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
              <div className="flex items-start">
                <svg className="w-5 h-5 text-red-500 mt-0.5 mr-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd"/>
                </svg>
                <div className="text-sm text-red-800">
                  <strong>Error:</strong> {error}
                </div>
              </div>
            </div>
          )}

          {/* Main Content */}
          <div className="space-y-6">
            {/* Search and Add Component */}
            <SearchAndAdd 
              onAddToFavourites={addToFavourites}
              onAddToList={addToList}
              lists={lists}
              apiUrls={config.apiUrls}
              csrfToken={config.csrfToken}
            />

            {/* Favourites List */}
            <FavouritesList 
              councils={favouritesList}
              onRemoveFromFavourites={removeFromFavourites}
              onAddToList={addToList}
              lists={lists}
            />

            {/* Custom Lists Manager */}
            <ListsManager 
              lists={lists}
              onMoveCouncil={moveCouncilBetweenLists}
              onAddToList={addToList}
              years={config.years}
              metricChoices={config.metricChoices}
              apiUrls={config.apiUrls}
            />

            {/* Create List Button */}
            <div className="text-center">
              <button
                onClick={() => setShowListCreator(true)}
                className="inline-flex items-center px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
                Create New List
              </button>
            </div>
          </div>

          {/* List Creator Modal */}
          {showListCreator && (
            <ListCreator 
              onClose={() => setShowListCreator(false)}
              onCreate={createList}
              loading={loading}
            />
          )}
        </div>
      </DndProvider>
    </ErrorBoundary>
  );
};

export default MyListsApp;