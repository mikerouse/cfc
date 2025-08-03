import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import MyListsIntegration from './components/MyListsIntegration';
import CouncilEditApp from './components/CouncilEditApp';
import ComparisonBasketApp from './components/ComparisonBasketApp';
import AddToBasketButton from './components/comparison/AddToBasketButton';
import GlobalComparison from './components/comparison/GlobalComparison';
import LegacyFactoidBuilder from './components/legacy/LegacyFactoidBuilder';

console.log('🚀 Main.jsx loading - React apps initialization');

/**
 * Initialize the main Factoid Builder React app
 */
function initializeMainApp() {
  const container = document.getElementById('factoid-builder-root');
  if (container) {
    try {
      const root = createRoot(container);
      root.render(<App />);
      console.log('🎉 Factoid Builder app mounted successfully!');
    } catch (error) {
      console.error('💥 Factoid Builder app mount failed:', error);
    }
  }
}

function initializeLegacyApp() {
  const container = document.getElementById('legacy-factoid-builder-root');
  if (container) {
    try {
      const root = createRoot(container);
      root.render(
        <LegacyFactoidBuilder config={window.FACTOID_BUILDER_CONFIG || {}} />
      );
      console.log('🎨 Legacy Factoid Builder mounted successfully');
    } catch (error) {
      console.error('💥 Legacy Factoid Builder mount failed:', error);
    }
  }
}

/**
 * Initialize all React apps based on available containers
 */
function initializeReactApps() {
  console.log('🔍 Checking for React app containers...');
  
  let initializedApps = [];
  
  // Initialize main app (Factoid Builder)
  const mainContainer = document.getElementById('factoid-builder-root');
  if (mainContainer) {
    console.log('📊 Factoid Builder container found, initializing...');
    initializeMainApp();
    initializedApps.push('Factoid Builder');
  }

  // Initialize legacy app if container exists
  const legacyContainer = document.getElementById('legacy-factoid-builder-root');
  if (legacyContainer) {
    console.log('🕹️ Legacy Factoid Builder container found, initializing...');
    initializeLegacyApp();
    initializedApps.push('Legacy Factoid Builder');
  }
  
  // Initialize My Lists app if container exists
  const myListsContainer = document.getElementById('my-lists-react-root');
  if (myListsContainer) {
    console.log('📋 My Lists container found, initializing...');
    MyListsIntegration();
    initializedApps.push('My Lists');
  }
  
  // Initialize Council Edit app if container exists
  const councilEditContainer = document.getElementById('council-edit-react-root');
  if (councilEditContainer) {
    console.log('🏛️ Council Edit container found, initializing...');
    try {
      // Parse data from template
      let councilData, yearsData, csrfToken;
      try {
        councilData = JSON.parse(councilEditContainer.dataset.council || '{}');
        yearsData = JSON.parse(councilEditContainer.dataset.years || '[]');
        csrfToken = councilEditContainer.dataset.csrfToken || '';
        
        console.log('📊 Council Edit: Data parsed successfully', {
          council: councilData.name,
          years: yearsData.length,
          hasCSRF: !!csrfToken
        });
      } catch (error) {
        console.error('❌ Council Edit: Failed to parse data', error);
        throw error;
      }

      // Mount React app directly
      console.log('🚀 Council Edit: Mounting React app directly...');
      const root = createRoot(councilEditContainer);
      root.render(<CouncilEditApp 
        councilData={councilData}
        initialYears={yearsData} 
        csrfToken={csrfToken}
      />);
      
      // Mark as mounted
      councilEditContainer.dataset.reactMounted = 'true';
      
      // Hide loading fallback
      const loadingFallback = document.getElementById('council-edit-loading-fallback');
      if (loadingFallback) {
        loadingFallback.style.display = 'none';
        console.log('🔍 Council Edit: Loading fallback hidden');
      }
      
      initializedApps.push('Council Edit');
      console.log('🎉 Council Edit: React app mounted successfully');
      
    } catch (error) {
      console.error('💥 Council Edit app initialization failed:', error);
      
      // Show fallback interface
      const fallbackInterface = document.getElementById('council-edit-fallback-interface');
      if (fallbackInterface) {
        const loadingFallback = document.getElementById('council-edit-loading-fallback');
        if (loadingFallback) loadingFallback.style.display = 'none';
        fallbackInterface.classList.remove('hidden');
        fallbackInterface.classList.add('block');
      }
    }
  }

  // Initialize Comparison Basket app if container exists
  const comparisonBasketContainer = document.getElementById('comparison-basket-react-root');
  if (comparisonBasketContainer) {
    console.log('🛒 Comparison Basket container found, initializing...');
    try {
      // Parse data from template
      let initialData, csrfToken;
      try {
        // Try to get data from script tag first (safer for JSON embedding)
        const dataScript = document.getElementById('comparison-basket-initial-data');
        if (dataScript) {
          initialData = JSON.parse(dataScript.textContent);
        } else {
          // Fallback to data attribute if script tag not found
          initialData = JSON.parse(comparisonBasketContainer.dataset.initialData || '{}');
        }
        csrfToken = comparisonBasketContainer.dataset.csrfToken || '';
        
        console.log('📊 Comparison Basket: Data parsed successfully', {
          councils: initialData.councils?.length || 0,
          fields: initialData.availableFields?.length || 0,
          years: initialData.availableYears?.length || 0,
          hasCSRF: !!csrfToken
        });
      } catch (error) {
        console.error('❌ Comparison Basket: Failed to parse data', error);
        // Still try to mount with empty data
        initialData = {};
        csrfToken = '';
      }

      // Mount React app directly
      console.log('🚀 Comparison Basket: Mounting React app directly...');
      const root = createRoot(comparisonBasketContainer);
      root.render(<ComparisonBasketApp 
        initialData={initialData}
        csrfToken={csrfToken}
        onComparisonToggle={true}
      />);
      
      // Mark as mounted
      comparisonBasketContainer.dataset.reactMounted = 'true';
      
      // Hide loading fallback
      const loadingFallback = document.getElementById('comparison-basket-loading-fallback');
      if (loadingFallback) {
        loadingFallback.style.display = 'none';
        console.log('🔍 Comparison Basket: Loading fallback hidden');
      }
      
      initializedApps.push('Comparison Basket');
      console.log('🎉 Comparison Basket: React app mounted successfully');
      
    } catch (error) {
      console.error('💥 Comparison Basket app initialization failed:', error);
      
      // Show fallback interface
      const fallbackInterface = document.getElementById('comparison-basket-fallback-interface');
      if (fallbackInterface) {
        const loadingFallback = document.getElementById('comparison-basket-loading-fallback');
        if (loadingFallback) loadingFallback.style.display = 'none';
        fallbackInterface.classList.remove('hidden');
        fallbackInterface.classList.add('block');
      }
    }
  }

  // Initialize Add to Basket buttons if they exist
  const basketButtons = document.querySelectorAll('[data-add-to-basket]');
  if (basketButtons.length > 0) {
    console.log(`🛒 Found ${basketButtons.length} Add to Basket button(s), initializing...`);
    basketButtons.forEach((button, index) => {
      try {
        const councilSlug = button.dataset.councilSlug;
        const councilName = button.dataset.councilName;
        
        if (councilSlug && councilName) {
          const root = createRoot(button);
          root.render(<AddToBasketButton 
            councilSlug={councilSlug}
            councilName={councilName}
          />);
          console.log(`🎯 Add to Basket button ${index + 1} mounted for: ${councilName}`);
        } else {
          console.warn(`⚠️ Add to Basket button ${index + 1} missing data attributes`);
        }
      } catch (error) {
        console.error(`💥 Add to Basket button ${index + 1} initialization failed:`, error);
      }
    });
    initializedApps.push(`${basketButtons.length} Add to Basket Button(s)`);
  }

  // Initialize Global Comparison (skip if already on compare page)
  const isComparePage = window.location.pathname === '/compare/' || window.location.pathname.startsWith('/compare/');
  if (!isComparePage || !comparisonBasketContainer) {
    console.log('🌐 Initializing Global Comparison overlay...');
    try {
      // Create a container for the global comparison
      const globalComparisonContainer = document.createElement('div');
      globalComparisonContainer.id = 'global-comparison-root';
      document.body.appendChild(globalComparisonContainer);
      
      const root = createRoot(globalComparisonContainer);
      root.render(<GlobalComparison />);
      
      initializedApps.push('Global Comparison Overlay');
      console.log('✅ Global Comparison overlay mounted successfully');
    } catch (error) {
      console.error('💥 Global Comparison initialization failed:', error);
    }
  } else {
    console.log('ℹ️ Skipping Global Comparison on compare page (using dedicated app instead)');
  }
  
  if (initializedApps.length > 0) {
    console.log(`✅ Initialized ${initializedApps.length} React app(s): ${initializedApps.join(', ')}`);
  } else {
    console.log('ℹ️ No React app containers found on this page');
  }
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
