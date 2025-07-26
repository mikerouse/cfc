import React from 'react';
import { logActivity } from '../utils/logger';

/**
 * React Error Boundary component used to catch runtime errors in the
 * factoid builder and display a friendly fallback UI while logging
 * the details for debugging purposes.
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    // Update state so the fallback UI is rendered
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Log the error using the shared logger
    logActivity('error_boundary', { componentStack: errorInfo.componentStack }, error);
  }

  render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      return this.props.fallback || (
        <div className="p-4 bg-red-50 border border-red-200 rounded">
          <h2 className="font-bold text-red-800 mb-2">Something went wrong.</h2>
          <pre className="text-xs text-red-700 whitespace-pre-wrap">
            {this.state.error?.message}
          </pre>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
