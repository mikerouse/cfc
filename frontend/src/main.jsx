import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import MyListsIntegration from './components/MyListsIntegration';
import CouncilEditApp from './components/CouncilEditApp';

console.log('🚀 Main.jsx loading - React apps initialization');

/**
 * Initialize the main Factoid Builder React app
 */
function initializeMainApp() {
  const container = document.getElementById('root');
  if (container) {
    console.log('✅ Main app container found, mounting React app...');
    
    try {
      const root = createRoot(container);
      root.render(<App />);
      console.log('🎉 Main React app mounted successfully!');
    } catch (error) {
      console.error('💥 Main React app mount failed:', error);
    }
  } else {
    console.log('⏳ Main app container not found - likely not on factoid builder page');
  }
}

/**
 * Initialize all React apps based on available containers
 */
function initializeReactApps() {
  console.log('📍 Searching for React app containers...');
  
  // Initialize main app (Factoid Builder)
  initializeMainApp();
  
  // Initialize My Lists app if container exists
  const myListsContainer = document.getElementById('my-lists-react-root');
  if (myListsContainer) {
    console.log('🎯 My Lists container found, initializing...');
    MyListsIntegration();
  }
  
  // Initialize Council Edit app if container exists
  const councilEditContainer = document.getElementById('council-edit-react-root');
  if (councilEditContainer) {
    console.log('🏛️ Council Edit container found, initializing...');
    try {
      // Make CouncilEditApp globally available for template integration
      window.CouncilEditApp = {
        mount: (container, props) => {
          console.log('🚀 Mounting Council Edit React app with props:', props);
          const root = createRoot(container);
          root.render(<CouncilEditApp {...props} />);
          return root;
        }
      };
      console.log('✅ Council Edit app registered successfully');
    } catch (error) {
      console.error('💥 Council Edit app registration failed:', error);
    }
  }
  
  console.log('✅ React apps initialization completed');
}

/**
 * Wait for DOM to be ready, then initialize apps
 */
function waitForDOM() {
  if (document.readyState === 'loading') {
    console.log('⏳ Waiting for DOM to be ready...');
    document.addEventListener('DOMContentLoaded', initializeReactApps);
  } else {
    console.log('📋 DOM already ready, initializing immediately...');
    initializeReactApps();
  }
}

try {
  waitForDOM();
} catch (error) {
  console.error('💥 Critical error in main.jsx:', error);
  
  // Add fallback error display
  const errorDiv = document.createElement('div');
  errorDiv.innerHTML = `
    <div style="padding: 20px; text-align: center; background: #fee; border: 1px solid #fcc; margin: 20px; border-radius: 8px;">
      <h3 style="color: #c33;">JavaScript Module Failed</h3>
      <p>Error: ${error.message}</p>
      <pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; text-align: left; font-size: 12px;">${error.stack}</pre>
      <button onclick="window.location.reload()" style="margin-top: 10px; padding: 8px 16px; background: #c33; color: white; border: none; border-radius: 4px; cursor: pointer;">
        Reload Page
      </button>
    </div>
  `;
  document.body.appendChild(errorDiv);
}
