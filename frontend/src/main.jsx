import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './index.css';

console.log('🚀 Main.jsx loading - React app initialization');

// Add error boundary for better debugging
function ErrorBoundary({ children }) {
  const [hasError, setHasError] = React.useState(false);
  
  React.useEffect(() => {
    const handleError = (error) => {
      console.error('React Error Boundary caught:', error);
      setHasError(true);
    };
    
    window.addEventListener('error', handleError);
    return () => window.removeEventListener('error', handleError);
  }, []);
  
  if (hasError) {
    return (
      <div className="p-8 text-center">
        <h2 className="text-xl font-bold text-red-600 mb-4">Application Error</h2>
        <p className="text-gray-600">The React application encountered an error. Check the console for details.</p>
      </div>
    );
  }
  
  return children;
}

try {
  const container = document.getElementById('root');
  console.log('📍 Root container found:', container);
  
  if (!container) {
    console.error('❌ Root container not found! Expected element with id="root"');
    // Create fallback message
    document.body.innerHTML += `
      <div style="padding: 20px; text-align: center; background: #fee; border: 1px solid #fcc; margin: 20px; border-radius: 8px;">
        <h3 style="color: #c33;">React Mount Error</h3>
        <p>Could not find root container element. Expected &lt;div id="root"&gt;&lt;/div&gt;</p>
      </div>
    `;
  } else {
    console.log('✅ Creating React root...');
    const root = createRoot(container);
    
    console.log('🎯 Mounting React app...');
    root.render(
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    );
    
    console.log('🎉 React app mounted successfully!');
  }
} catch (error) {
  console.error('💥 Critical error in main.jsx:', error);
  // Add fallback error display
  const errorDiv = document.createElement('div');
  errorDiv.innerHTML = `
    <div style="padding: 20px; text-align: center; background: #fee; border: 1px solid #fcc; margin: 20px; border-radius: 8px;">
      <h3 style="color: #c33;">React Initialization Failed</h3>
      <p>Error: ${error.message}</p>
      <pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; text-align: left; font-size: 12px;">${error.stack}</pre>
    </div>
  `;
  document.body.appendChild(errorDiv);
}
