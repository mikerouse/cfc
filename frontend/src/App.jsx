import { useState, useEffect } from 'react';
import FactoidBuilder from './components/FactoidBuilder';
// New error boundary and logger utilities
import ErrorBoundary from './components/ErrorBoundary';
import { logActivity } from './utils/logger';
import './App.css';

function App() {
  // Check if we're in integrated mode (embedded in Django template)
  const isIntegratedMode = window?.FACTOID_BUILDER_CONFIG?.isIntegratedMode || false;
  
  useEffect(() => {
    console.log('🎯 Enhanced Factoid Builder App initialized');
    console.log('📊 Integrated Mode:', isIntegratedMode);
    console.log('🔧 Config:', window.FACTOID_BUILDER_CONFIG);
    
    // Add global debugging utilities
    window.factoidBuilderDebug = {
      getLogs: () => {
        try {
          return JSON.parse(sessionStorage.getItem('factoid_api_logs') || '[]');
        } catch (error) {
          console.warn('Failed to retrieve logs:', error);
          return [];
        }
      },
      clearLogs: () => {
        try {
          sessionStorage.removeItem('factoid_api_logs');
          console.log('🗑️ Factoid API logs cleared');
        } catch (error) {
          console.warn('Failed to clear logs:', error);
        }
      },
      exportLogs: () => {
        const logs = window.factoidBuilderDebug.getLogs();
        const dataStr = JSON.stringify(logs, null, 2);
        const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
        
        const exportFileDefaultName = `factoid-api-logs-${new Date().toISOString().split('T')[0]}.json`;
        
        const linkElement = document.createElement('a');
        linkElement.setAttribute('href', dataUri);
        linkElement.setAttribute('download', exportFileDefaultName);
        linkElement.click();
        
        console.log(`📤 Exported ${logs.length} log entries to ${exportFileDefaultName}`);
      },
      getLogStats: () => {
        const logs = window.factoidBuilderDebug.getLogs();
        const actions = {};
        const errors = [];
        
        logs.forEach(log => {
          actions[log.action] = (actions[log.action] || 0) + 1;
          if (log.error) {
            errors.push(log);
          }
        });
        
        return {
          total_logs: logs.length,
          error_logs: errors.length,
          actions_summary: actions,
          recent_errors: errors.slice(-5),
        };
      }
    };
    
    console.log('🛠️ Debug utilities available at window.factoidBuilderDebug');

    // Global error listeners capture unexpected issues and log them
    const handleGlobalError = (event) => {
      const error = event.error || new Error(event.message);
      logActivity('global_error', {
        message: event.message,
        source: event.filename,
        lineno: event.lineno,
        colno: event.colno,
      }, error);
    };

    const handleUnhandledRejection = (event) => {
      const reason = event.reason instanceof Error ? event.reason : new Error(String(event.reason));
      logActivity('unhandled_rejection', { reason: reason.message }, reason);
    };

    window.addEventListener('error', handleGlobalError);
    window.addEventListener('unhandledrejection', handleUnhandledRejection);

    // Dispatch event to let parent know we're ready
    window.dispatchEvent(new CustomEvent('factoidBuilderReady', {
      detail: { isIntegratedMode, config: window.FACTOID_BUILDER_CONFIG }
    }));

    // Cleanup listeners on unmount
    return () => {
      window.removeEventListener('error', handleGlobalError);
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
    };
  }, [isIntegratedMode]);

  // For integrated mode, only show the component without extra wrapper styling
  if (isIntegratedMode) {
    return (
      <div className="factoid-builder-integrated">
        {/* Wrap the builder with an error boundary for resilience */}
        <ErrorBoundary>
          <FactoidBuilder />
        </ErrorBoundary>
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
          {/* Error boundary also used in standalone mode */}
          <ErrorBoundary>
            <FactoidBuilder />
          </ErrorBoundary>
        </div>
      </div>
    </div>
  );
}

export default App;
