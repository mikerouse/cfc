import React from 'react';
import { createRoot } from 'react-dom/client';
import MyListsApp from './MyListsApp';
import ErrorBoundary from './ErrorBoundary';

/**
 * Integration component that initializes the My Lists React app
 * This bridges the Django template with React components
 */
const MyListsIntegration = () => {
  // Wait for DOM to be ready and look for React container
  const initializeReactApp = () => {
    const container = document.getElementById('my-lists-react-root');
    
    if (!container) {
      // Container not found - this is expected on other pages, so no warning needed
      return;
    }

    console.log('✅ MyListsIntegration: Found React container, initializing app...');

    try {
      // Get initial data from Django template
      const initialDataElement = document.getElementById('my-lists-initial-data');
      let initialData = {};

      if (initialDataElement) {
        try {
          initialData = JSON.parse(initialDataElement.textContent);
          console.log('📊 MyListsIntegration: Loaded initial data:', initialData);
        } catch (e) {
          console.error('❌ MyListsIntegration: Failed to parse initial data:', e);
        }
      } else {
        console.warn('⚠️ MyListsIntegration: No initial data found in template');
      }

      // Create React root and render app
      const root = createRoot(container);
      root.render(
        <ErrorBoundary>
          <MyListsApp initialData={initialData} />
        </ErrorBoundary>
      );

      // Mark container as having React mounted successfully
      container.setAttribute('data-react-mounted', 'true');
      
      console.log('🎉 MyListsIntegration: React app successfully mounted!');
    } catch (error) {
      console.error('💥 MyListsIntegration: Failed to mount React app:', error);
      
      // Show fallback error UI
      container.innerHTML = `
        <div class="bg-red-50 border border-red-200 rounded-lg p-6 m-4">
          <div class="flex items-start">
            <svg class="w-6 h-6 text-red-500 mt-1 mr-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
            </svg>
            <div>
              <h3 class="text-lg font-medium text-red-800 mb-2">React App Failed to Load</h3>
              <p class="text-red-700 mb-3">
                The enhanced My Lists interface encountered an error. The page will fall back to the basic version.
              </p>
              <details class="text-sm text-red-600">
                <summary class="cursor-pointer font-medium">Technical Details</summary>
                <pre class="mt-2 p-3 bg-red-100 rounded border overflow-auto">${error.message}\n\n${error.stack}</pre>
              </details>
              <button onclick="window.location.reload()" class="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors">
                Reload Page
              </button>
            </div>
          </div>
        </div>
      `;
    }
  };

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeReactApp);
  } else {
    initializeReactApp();
  }
};

export default MyListsIntegration;