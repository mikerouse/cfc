/**
 * Simple client-side logger used across the factoid builder.
 * Writes structured log entries to sessionStorage and console.
 */
export const logActivity = (action, data = {}, error = null) => {
  const entry = {
    timestamp: new Date().toISOString(),
    action,
    ...data,
    error: error ? {
      name: error.name,
      message: error.message,
      stack: error.stack,
    } : null,
  };

  // Output to console for immediate visibility
  if (error) {
    console.error(`\uD83D\uDD34 ${action}`, data, error);
  } else {
    console.log(`\uD83D\uDFE2 ${action}`, data);
  }

  // Persist in sessionStorage for later inspection
  try {
    const existing = JSON.parse(sessionStorage.getItem('factoid_api_logs') || '[]');
    existing.push(entry);
    if (existing.length > 100) {
      existing.splice(0, existing.length - 100);
    }
    sessionStorage.setItem('factoid_api_logs', JSON.stringify(existing));
  } catch (storageErr) {
    console.warn('Logger storage failed:', storageErr);
  }
};
