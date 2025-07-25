import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

console.log('🚀 Main.jsx loading - React app initialization');

function waitForRoot() {
  const container = document.getElementById('root');
  if (container) {
    console.log('✅ Root container found, mounting React app...');
    
    try {
      const root = createRoot(container);
      root.render(<App />);
      console.log('🎉 React app mounted successfully!');
    } catch (error) {
      console.error('💥 React mount failed:', error);
    }
  } else {
    console.log('⏳ Waiting for root container...');
    setTimeout(waitForRoot, 100); // Check every 100ms
  }
}

try {
  console.log('📍 Starting root container check...');
  
  // Start checking for root container immediately
  waitForRoot();
  
  console.log('✅ Main.jsx execution completed');
} catch (error) {
  console.error('💥 Critical error in main.jsx:', error);
  // Add fallback error display
  const errorDiv = document.createElement('div');
  errorDiv.innerHTML = `
    <div style="padding: 20px; text-align: center; background: #fee; border: 1px solid #fcc; margin: 20px; border-radius: 8px;">
      <h3 style="color: #c33;">JavaScript Module Failed</h3>
      <p>Error: ${error.message}</p>
      <pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; text-align: left; font-size: 12px;">${error.stack}</pre>
    </div>
  `;
  document.body.appendChild(errorDiv);
}
