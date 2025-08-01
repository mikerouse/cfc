/**
 * useFactoidAPI Hook
 * 
 * Custom React hook that provides real-time integration with the Django factoid API.
 * Handles field discovery, template validation, live preview, and saving.
 */
import { useState, useCallback, useRef } from 'react';

const API_BASE_URL = '/api/factoid';

export const useFactoidAPI = () => {
  // State management
  const [fields, setFields] = useState([]);
  const [fieldGroups, setFieldGroups] = useState({});
  const [previewData, setPreviewData] = useState(null);
  const [validationErrors, setValidationErrors] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  
  // Cache and debouncing
  const debounceTimers = useRef({});
  const cache = useRef({});

  // Client-side logging helper
  const logClientActivity = useCallback((action, data = {}, error = null) => {
    const logEntry = {
      timestamp: new Date().toISOString(),
      action,
      session_id: window.FACTOID_BUILDER_CONFIG?.sessionId || 'unknown',
      user_agent: navigator.userAgent,
      url: window.location.href,
      error: error ? {
        name: error.name,
        message: error.message,
        stack: error.stack
      } : null,
      ...data
    };
    
    // Log to console with structured format
    if (error) {
      console.error(`🔴 Factoid API Error [${action}]:`, logEntry);
    } else {
      console.log(`🟢 Factoid API Activity [${action}]:`, logEntry);
    }
    
    // Store in session storage for debugging
    try {
      const existingLogs = JSON.parse(sessionStorage.getItem('factoid_api_logs') || '[]');
      existingLogs.push(logEntry);
      
      // Keep only last 100 log entries
      if (existingLogs.length > 100) {
        existingLogs.splice(0, existingLogs.length - 100);
      }
      
      sessionStorage.setItem('factoid_api_logs', JSON.stringify(existingLogs));
    } catch (storageError) {
      console.warn('Failed to store client log:', storageError);
    }
  }, []);

  // API helper function
  const apiCall = useCallback(async (endpoint, options = {}) => {
    const url = `${API_BASE_URL}${endpoint}`;
    const startTime = performance.now();
    
    const defaultOptions = {
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
      },
      credentials: 'same-origin',
    };

    try {
      logClientActivity('api_call_start', {
        endpoint,
        method: options.method || 'GET',
        has_body: !!options.body,
        body_length: options.body ? options.body.length : 0,
      });
      
      const response = await fetch(url, { ...defaultOptions, ...options });
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      if (!response.ok) {
        const error = new Error(`HTTP ${response.status}: ${response.statusText}`);
        
        logClientActivity('api_call_failed', {
          endpoint,
          method: options.method || 'GET',
          status: response.status,
          status_text: response.statusText,
          duration_ms: duration,
        }, error);
        
        throw error;
      }
      
      const data = await response.json();
      
      logClientActivity('api_call_success', {
        endpoint,
        method: options.method || 'GET',
        status: response.status,
        duration_ms: duration,
        response_size: JSON.stringify(data).length,
        success: data.success,
      });
      
      return data;
    } catch (error) {
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      logClientActivity('api_call_error', {
        endpoint,
        method: options.method || 'GET',
        duration_ms: duration,
        error_type: error.name,
        error_message: error.message,
      }, error);
      
      console.error(`API call failed for ${url}:`, error);
      throw error;
    }
  }, [logClientActivity]);

  // Field discovery
  const discoverFields = useCallback(async () => {
    const cacheKey = 'field_discovery';
    
    // Check cache first (5 minute TTL)
    if (cache.current[cacheKey] && 
        Date.now() - cache.current[cacheKey].timestamp < 300000) {
      const cached = cache.current[cacheKey];
      setFields(cached.fields);
      setFieldGroups(cached.fieldGroups);
      
      logClientActivity('field_discovery_cache_hit', {
        cache_age_ms: Date.now() - cached.timestamp,
        total_fields: Object.values(cached.fieldGroups).reduce((sum, group) => sum + group.length, 0),
        categories_count: Object.keys(cached.fieldGroups).length,
      });
      
      return cached;
    }

    setIsLoading(true);
    
    try {
      logClientActivity('field_discovery_start', {
        cache_miss: true,
        cache_expired: !!cache.current[cacheKey],
      });
      
      console.log('🔍 Discovering fields from API...');
      const response = await apiCall('/templates/discover_fields/');
      
      if (response.success) {
        setFields(response.field_groups);
        setFieldGroups(response.field_groups);
        
        // Cache the result
        cache.current[cacheKey] = {
          fields: response.field_groups,
          fieldGroups: response.field_groups,
          timestamp: Date.now(),
        };
        
        logClientActivity('field_discovery_success', {
          total_fields: response.total_fields,
          categories_count: Object.keys(response.field_groups).length,
          field_categories: Object.keys(response.field_groups),
          cached: true,
        });
        
        console.log(`✅ Discovered ${response.total_fields} fields in ${Object.keys(response.field_groups).length} categories`);
        return response;
      } else {
        const error = new Error(response.error || 'Failed to discover fields');
        logClientActivity('field_discovery_failed', {
          api_success: false,
          api_error: response.error,
        }, error);
        throw error;
      }
    } catch (error) {
      logClientActivity('field_discovery_error', {
        error_type: error.name,
        error_message: error.message,
      }, error);
      
      console.error('Field discovery failed:', error);
      setValidationErrors(prev => [...prev, `Field discovery failed: ${error.message}`]);
      return { success: false, error: error.message };
    } finally {
      setIsLoading(false);
    }
  }, [apiCall, logClientActivity]);

  // Template validation with debouncing
  const validateTemplate = useCallback((templateText, templateId = null) => {
    // Clear existing timer
    if (debounceTimers.current.validation) {
      clearTimeout(debounceTimers.current.validation);
    }

    logClientActivity('validation_debounce_start', {
      template_length: templateText ? templateText.length : 0,
      has_existing_timer: !!debounceTimers.current.validation,
    });

    // Debounce validation calls
    debounceTimers.current.validation = setTimeout(async () => {
      if (!templateText || !templateText.trim()) {
        setValidationErrors([]);
        logClientActivity('validation_skipped_empty', {
          template_length: templateText ? templateText.length : 0,
          template_trimmed_length: templateText ? templateText.trim().length : 0,
        });
        return;
      }

      try {
        logClientActivity('validation_start', {
          template_length: templateText.length,
          template_preview: templateText.substring(0, 100),
        });

        // Use new quick-validate endpoint when the template
        // has not yet been persisted. Otherwise fall back to
        // the standard template-specific validation URL.
        const endpoint = templateId
          ? `/templates/${templateId}/validate_template/`
          : '/quick-validate/';
        const response = await apiCall(endpoint, {
          method: 'POST',
          body: JSON.stringify({ template_text: templateText }),
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': window.FACTOID_BUILDER_CONFIG?.csrfToken || '',
          },
        });

        if (response.success) {
          setValidationErrors(response.validation_errors || []);
          
          logClientActivity('validation_success', {
            is_valid: response.is_valid,
            validation_errors_count: response.validation_errors ? response.validation_errors.length : 0,
            validation_errors: response.validation_errors,
            referenced_fields_count: response.referenced_fields ? response.referenced_fields.length : 0,
            referenced_fields: response.referenced_fields,
            template_length: templateText.length,
          });
          
          console.log(`✅ Template validation: ${response.is_valid ? 'Valid' : 'Invalid'}`);
        } else {
          const errorMessage = response.error || 'Validation failed';
          setValidationErrors([errorMessage]);
          alert(errorMessage);
          
          logClientActivity('validation_failed', {
            api_success: false,
            api_error: response.error,
            template_length: templateText.length,
          });
        }
      } catch (error) {
        logClientActivity('validation_error', {
          error_type: error.name,
          error_message: error.message,
          template_length: templateText.length,
        }, error);

        console.error('Template validation failed:', error);
        setValidationErrors([`Validation error: ${error.message}`]);
        alert(`Validation error: ${error.message}`);
      }
    }, 500); // 500ms debounce
  }, [apiCall, logClientActivity]);

  // Live preview generation with debouncing
  const generatePreview = useCallback((templateText, options = {}) => {
    // Clear existing timer
    if (debounceTimers.current.preview) {
      clearTimeout(debounceTimers.current.preview);
    }

    // Debounce preview calls
    debounceTimers.current.preview = setTimeout(async () => {
      if (!templateText || !templateText.trim()) {
        setPreviewData(null);
        return;
      }

      try {
        const {
          templateId = null,
          councilSlug,
          yearSlug = '2023-24',
          counterSlug,
        } = options;

        const payload = {
          template_text: templateText,
          council_slug: councilSlug || null,
          year_slug: yearSlug,
          counter_slug: counterSlug || null,
        };

        // When no template has been saved yet send preview
        // requests to the quick-preview endpoint. Saved templates
        // still use their instance specific preview URL.
        const endpoint = templateId
          ? `/templates/${templateId}/preview/`
          : '/quick-preview/';

        const response = await apiCall(endpoint, {
          method: 'POST',
          body: JSON.stringify(payload),
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': window.FACTOID_BUILDER_CONFIG?.csrfToken || '',
          },
        });

        if (response.success) {
          setPreviewData(response.preview);
          console.log('✅ Generated live preview');
        } else {
          console.warn('Preview generation failed:', response.error);
          alert(response.error || 'Preview generation failed');
          setPreviewData({
            rendered_text: 'Preview error',
            validation_errors: [response.error],
          });
        }
      } catch (error) {
        console.error('Preview generation failed:', error);
        alert(`Preview error: ${error.message}`);
        setPreviewData({
          rendered_text: 'Preview unavailable',
          validation_errors: [`Preview error: ${error.message}`],
        });
      }
    }, 750); // 750ms debounce for preview (longer than validation)
  }, [apiCall]);

  // Save template
  const saveTemplate = useCallback(async (templateData) => {
    try {
      console.log('💾 Saving template...', templateData);
      
      const response = await apiCall('/templates/', {
        method: 'POST',
        body: JSON.stringify(templateData),
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': window.FACTOID_BUILDER_CONFIG?.csrfToken || '',
        },
      });

      if (response.id) {
        console.log(`✅ Template saved with ID: ${response.id}`);
        
        // Clear cache to force refresh on next field discovery
        cache.current = {};
        
        return { success: true, data: response };
      } else {
        throw new Error(response.error || 'Save failed');
      }
    } catch (error) {
      console.error('Template save failed:', error);
      return { success: false, error: error.message };
    }
  }, [apiCall]);

  // Search fields (for autocomplete)
  const searchFields = useCallback(async (query) => {
    if (!query || query.length < 2) {
      return { success: true, fields: [] };
    }

    try {
      const response = await apiCall(`/fields/search/?q=${encodeURIComponent(query)}&limit=20`);
      return response;
    } catch (error) {
      console.error('Field search failed:', error);
      return { success: false, error: error.message };
    }
  }, [apiCall]);

  // Get sample councils for preview
  const getSampleCouncils = useCallback(async () => {
    const cacheKey = 'sample_councils';
    
    // Check cache (10 minute TTL)
    if (cache.current[cacheKey] && 
        Date.now() - cache.current[cacheKey].timestamp < 600000) {
      return cache.current[cacheKey].data;
    }

    try {
      const response = await apiCall('/templates/sample_councils/');
      
      if (response.success) {
        cache.current[cacheKey] = {
          data: response,
          timestamp: Date.now(),
        };
      }
      
      return response;
    } catch (error) {
      console.error('Failed to get sample councils:', error);
      return { success: false, error: error.message };
    }
  }, [apiCall]);

  // Get available financial years for preview
  const getAvailableYears = useCallback(async () => {
    const cacheKey = 'available_years';
    
    // Check cache (10 minute TTL)
    if (cache.current[cacheKey] && 
        Date.now() - cache.current[cacheKey].timestamp < 600000) {
      return cache.current[cacheKey].data;
    }

    try {
      // For now, return common years - could be enhanced with API call
      const currentYear = new Date().getFullYear();
      const years = [];
      for (let i = 0; i < 5; i++) {
        const startYear = currentYear - i;
        const endYear = startYear + 1;
        years.push({
          label: `${startYear}-${String(endYear).slice(-2)}`,
          value: `${startYear}-${String(endYear).slice(-2)}`,
        });
      }
      
      const response = { success: true, years };
      
      cache.current[cacheKey] = {
        data: response,
        timestamp: Date.now(),
      };
      
      return response;
    } catch (error) {
      console.error('Failed to get available years:', error);
      return { success: false, error: error.message };
    }
  }, []);

  // Generate preview with fallback mock data
  const generatePreviewWithFallback = useCallback(async (templateText, options = {}) => {
    try {
      // First try with real data
      const result = await new Promise((resolve) => {
        generatePreview(templateText, options);
        
        // Wait a bit for the preview to be generated
        setTimeout(() => {
          resolve(previewData);
        }, 1000);
      });
      
      return result;
    } catch (error) {
      console.warn('Real data preview failed, generating mock preview:', error);
      
      // Generate mock preview
      return generateMockPreview(templateText, options);
    }
  }, [generatePreview, previewData]);

  // Generate mock preview when real data isn't available
  const generateMockPreview = useCallback((templateText, options = {}) => {
    try {
      const mockData = {
        council_name: 'Sample County Council',
        year_label: options.yearSlug || '2023-24',
        population: '592,000',
        total_expenditure: '£1,250,000,000',
        total_revenue: '£1,180,000,000',
        debt_per_resident: '£1,450',
        council_type: 'County Council',
        website: 'https://sample-council.gov.uk',
        total_debt: '£856,000,000',
        reserves: '£89,000,000',
        precept: '£687',
      };
      
      // Simple template replacement
      let rendered = templateText;
      Object.entries(mockData).forEach(([key, value]) => {
        const regex = new RegExp(`\\{${key}[^}]*\\}`, 'g');
        rendered = rendered.replace(regex, value);
      });
      
      const mockPreview = {
        rendered_text: rendered,
        context_data: mockData,
        referenced_fields: templateText.match(/\{([^}]+)\}/g) || [],
        validation_errors: [],
        council_name: mockData.council_name,
        year_label: mockData.year_label,
        is_mock_data: true,
      };
      
      return { success: true, preview: mockPreview };
    } catch (error) {
      console.error('Mock preview generation failed:', error);
      return {
        rendered_text: 'Preview unavailable',
        validation_errors: [`Preview error: ${error.message}`],
        is_mock_data: true,
      };
    }
  }, []);

  // Get client-side logs for debugging
  const getClientLogs = useCallback(() => {
    try {
      return JSON.parse(sessionStorage.getItem('factoid_api_logs') || '[]');
    } catch (error) {
      console.warn('Failed to retrieve client logs:', error);
      return [];
    }
  }, []);

  // Get existing factoid templates
  const getFactoidTemplates = useCallback(async () => {
    const cacheKey = 'factoid_templates';
    
    // Check cache (5 minute TTL)
    if (cache.current[cacheKey] && 
        Date.now() - cache.current[cacheKey].timestamp < 300000) {
      logClientActivity('factoid_templates_cache_hit', {
        cache_age_ms: Date.now() - cache.current[cacheKey].timestamp,
        templates_count: cache.current[cacheKey].data.templates?.length || 0,
      });
      return cache.current[cacheKey].data;
    }

    try {
      logClientActivity('factoid_templates_fetch_start');
      const response = await apiCall('/templates/');
      
      // Debug: Log the actual response structure
      console.log('🔍 Raw API response for /templates/:', response);
      console.log('🔍 Response type:', typeof response);
      console.log('🔍 Is array:', Array.isArray(response));
      console.log('🔍 Response keys:', response ? Object.keys(response) : 'null/undefined');
      
      // Try to stringify for better debugging
      try {
        console.log('🔍 Response JSON:', JSON.stringify(response, null, 2));
      } catch (e) {
        console.log('🔍 Cannot stringify response:', e.message);
      }
      
      // DRF ViewSet returns an array directly for list action
      if (Array.isArray(response)) {
        const result = { success: true, templates: response };
        
        cache.current[cacheKey] = {
          data: result,
          timestamp: Date.now(),
        };
        
        logClientActivity('factoid_templates_fetch_success', {
          templates_count: response.length,
          cached: true,
        });
        
        return result;
      } else if (response && response.success) {
        // Handle other response formats
        cache.current[cacheKey] = {
          data: response,
          timestamp: Date.now(),
        };
        
        logClientActivity('factoid_templates_fetch_success', {
          templates_count: response.templates?.length || 0,
          cached: true,
        });
        
        return response;
      } else if (response && typeof response === 'object') {
        // Handle case where we get an object that might contain templates
        console.log('🔍 Handling object response, creating success wrapper');
        const result = { 
          success: true, 
          templates: response.results || response.templates || (response.data && Array.isArray(response.data) ? response.data : [])
        };
        
        cache.current[cacheKey] = {
          data: result,
          timestamp: Date.now(),
        };
        
        logClientActivity('factoid_templates_fetch_success', {
          templates_count: result.templates.length,
          cached: true,
        });
        
        return result;
      } else {
        console.log('🔍 Unhandled response format, attempting fallback');
        console.log('🔍 Response value:', response);
        
        // Last resort fallback - treat any truthy response as empty array
        if (response !== null && response !== undefined) {
          console.log('🔍 Using fallback: empty templates array');
          const result = { success: true, templates: [] };
          
          cache.current[cacheKey] = {
            data: result,
            timestamp: Date.now(),
          };
          
          logClientActivity('factoid_templates_fetch_success', {
            templates_count: 0,
            cached: true,
            fallback_used: true,
          });
          
          return result;
        }
        
        console.log('🔍 Complete failure, throwing error');
        throw new Error(response?.error || 'Failed to fetch factoid templates - unexpected response format');
      }
    } catch (error) {
      logClientActivity('factoid_templates_fetch_error', {
        error_type: error.name,
        error_message: error.message,
      }, error);
      
      console.error('Failed to fetch factoid templates:', error);
      return { success: false, error: error.message };
    }
  }, [apiCall, logClientActivity]);

  // Get specific factoid template by ID
  const getFactoidTemplate = useCallback(async (templateId) => {
    try {
      logClientActivity('factoid_template_fetch_start', { template_id: templateId });
      const response = await apiCall(`/templates/${templateId}/`);
      
      // DRF ViewSet returns the object directly for detail action
      if (response.id) {
        logClientActivity('factoid_template_fetch_success', {
          template_id: templateId,
          template_name: response.name,
        });
        
        return { success: true, template: response };
      } else if (response.success) {
        // Handle other response formats
        logClientActivity('factoid_template_fetch_success', {
          template_id: templateId,
          template_name: response.template?.name || response.name,
        });
        
        return response;
      } else {
        throw new Error(response.error || 'Failed to fetch factoid template');
      }
    } catch (error) {
      logClientActivity('factoid_template_fetch_error', {
        template_id: templateId,
        error_type: error.name,
        error_message: error.message,
      }, error);
      
      console.error(`Failed to fetch factoid template ${templateId}:`, error);
      return { success: false, error: error.message };
    }
  }, [apiCall, logClientActivity]);

  // Update existing factoid template
  const updateFactoidTemplate = useCallback(async (templateId, templateData) => {
    try {
      logClientActivity('factoid_template_update_start', {
        template_id: templateId,
        template_name: templateData.name,
      });
      
      const response = await apiCall(`/templates/${templateId}/`, {
        method: 'PUT',
        body: JSON.stringify(templateData),
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': window.FACTOID_BUILDER_CONFIG?.csrfToken || '',
        },
      });

      // DRF ViewSet returns the updated object directly
      if (response.id) {
        logClientActivity('factoid_template_update_success', {
          template_id: templateId,
          template_name: response.name || templateData.name,
        });
        
        // Clear cache to force refresh
        cache.current = {};
        
        return { success: true, data: response };
      } else if (response.success) {
        // Handle other response formats
        logClientActivity('factoid_template_update_success', {
          template_id: templateId,
          template_name: response.data?.name || response.name || templateData.name,
        });
        
        // Clear cache to force refresh
        cache.current = {};
        
        return response;
      } else {
        throw new Error(response.error || 'Update failed');
      }
    } catch (error) {
      logClientActivity('factoid_template_update_error', {
        template_id: templateId,
        error_type: error.name,
        error_message: error.message,
      }, error);
      
      console.error(`Template update failed for ID ${templateId}:`, error);
      return { success: false, error: error.message };
    }
  }, [apiCall, logClientActivity]);

  // Delete factoid template
  const deleteFactoidTemplate = useCallback(async (templateId) => {
    try {
      logClientActivity('factoid_template_delete_start', { template_id: templateId });
      
      const response = await apiCall(`/templates/${templateId}/`, {
        method: 'DELETE',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': window.FACTOID_BUILDER_CONFIG?.csrfToken || '',
        },
      });

      logClientActivity('factoid_template_delete_success', { template_id: templateId });
      
      // Clear cache to force refresh
      cache.current = {};
      
      return { success: true };
    } catch (error) {
      logClientActivity('factoid_template_delete_error', {
        template_id: templateId,
        error_type: error.name,
        error_message: error.message,
      }, error);
      
      console.error(`Template delete failed for ID ${templateId}:`, error);
      return { success: false, error: error.message };
    }
  }, [apiCall, logClientActivity]);

  // Check data availability for a factoid template
  const checkDataAvailability = useCallback(async (templateId) => {
    try {
      logClientActivity('data_availability_check_start', { template_id: templateId });
      const response = await apiCall(`/templates/${templateId}/check_data_availability/`);
      
      if (response.success) {
        logClientActivity('data_availability_check_success', {
          template_id: templateId,
          available_combinations: response.available_data?.length || 0,
          councils_with_data: response.summary?.councils_with_data || 0,
          years_with_data: response.summary?.years_with_data || 0,
        });
        
        return response;
      } else {
        throw new Error(response.error || 'Failed to check data availability');
      }
    } catch (error) {
      logClientActivity('data_availability_check_error', {
        template_id: templateId,
        error_type: error.name,
        error_message: error.message,
      }, error);
      
      console.error(`Failed to check data availability for template ${templateId}:`, error);
      return { success: false, error: error.message };
    }
  }, [apiCall, logClientActivity]);

  // Clear client-side logs
  const clearClientLogs = useCallback(() => {
    try {
      sessionStorage.removeItem('factoid_api_logs');
      console.log('🗑️ Factoid API client logs cleared');
    } catch (error) {
      console.warn('Failed to clear client logs:', error);
    }
  }, []);

  // Export logs for debugging
  const exportLogs = useCallback(() => {
    const logs = getClientLogs();
    const dataStr = JSON.stringify(logs, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `factoid-api-logs-${new Date().toISOString().split('T')[0]}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
    
    logClientActivity('logs_exported', {
      logs_count: logs.length,
      export_filename: exportFileDefaultName,
    });
  }, [getClientLogs, logClientActivity]);

  // Cleanup function
  const cleanup = useCallback(() => {
    // Clear all debounce timers
    Object.values(debounceTimers.current).forEach(timer => {
      if (timer) clearTimeout(timer);
    });
    debounceTimers.current = {};
    
    logClientActivity('hook_cleanup', {
      timers_cleared: Object.keys(debounceTimers.current).length,
    });
  }, [logClientActivity]);

  return {
    // State
    fields,
    fieldGroups,
    previewData,
    setPreviewData,
    validationErrors,
    isLoading,
    
    // Actions
    discoverFields,
    validateTemplate,
    generatePreview,
    generatePreviewWithFallback,
    generateMockPreview,
    saveTemplate,
    searchFields,
    getSampleCouncils,
    getAvailableYears,
    cleanup,
    
    // Template management
    getFactoidTemplates,
    getFactoidTemplate,
    updateFactoidTemplate,
    deleteFactoidTemplate,
    checkDataAvailability,
    
    // Debugging utilities
    getClientLogs,
    clearClientLogs,
    exportLogs,
    
    // Direct API access
    apiCall,
  };
};
