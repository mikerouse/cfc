import { useState, useEffect } from 'react';
import FactoidBuilder from './components/FactoidBuilder';
import './App.css';

function App() {
  // Check if we're in integrated mode (embedded in Django template)
  const isIntegratedMode = window?.FACTOID_BUILDER_CONFIG?.isIntegratedMode || false;
  
  useEffect(() => {
    console.log('🎯 Enhanced Factoid Builder App initialized');
    console.log('📊 Integrated Mode:', isIntegratedMode);
    console.log('🔧 Config:', window.FACTOID_BUILDER_CONFIG);
    
    // Dispatch event to let parent know we're ready
    window.dispatchEvent(new CustomEvent('factoidBuilderReady', {
      detail: { isIntegratedMode, config: window.FACTOID_BUILDER_CONFIG }
    }));
  }, [isIntegratedMode]);

  // For integrated mode, only show the component without extra wrapper styling
  if (isIntegratedMode) {
    return (
      <div className="factoid-builder-integrated">
        <FactoidBuilder />
      </div>
    );
  }

  // Standalone mode with full styling
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">
          🎯 Enhanced Factoid Builder
        </h1>
        
        <div className="bg-white rounded-lg shadow-lg overflow-hidden">
          <FactoidBuilder />
        </div>
      </div>
    </div>
  );
}

export default App;
