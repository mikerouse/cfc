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

  // API helper function
  const apiCall = useCallback(async (endpoint, options = {}) => {
    const url = `${API_BASE_URL}${endpoint}`;
    const defaultOptions = {
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
      },
      credentials: 'same-origin',
    };

    try {
      const response = await fetch(url, { ...defaultOptions, ...options });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      return data;
    } catch (error) {
      console.error(`API call failed for ${url}:`, error);
      throw error;
    }
  }, []);

  // Field discovery
  const discoverFields = useCallback(async () => {
    const cacheKey = 'field_discovery';
    
    // Check cache first (5 minute TTL)
    if (cache.current[cacheKey] && 
        Date.now() - cache.current[cacheKey].timestamp < 300000) {
      const cached = cache.current[cacheKey];
      setFields(cached.fields);
      setFieldGroups(cached.fieldGroups);
      return cached;
    }

    setIsLoading(true);
    try {
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
        
        console.log(`✅ Discovered ${response.total_fields} fields in ${Object.keys(response.field_groups).length} categories`);
        return response;
      } else {
        throw new Error(response.error || 'Failed to discover fields');
      }
    } catch (error) {
      console.error('Field discovery failed:', error);
      setValidationErrors(prev => [...prev, `Field discovery failed: ${error.message}`]);
      return { success: false, error: error.message };
    } finally {
      setIsLoading(false);
    }
  }, [apiCall]);

  // Template validation with debouncing
  const validateTemplate = useCallback((templateText) => {
    // Clear existing timer
    if (debounceTimers.current.validation) {
      clearTimeout(debounceTimers.current.validation);
    }

    // Debounce validation calls
    debounceTimers.current.validation = setTimeout(async () => {
      if (!templateText || !templateText.trim()) {
        setValidationErrors([]);
        return;
      }

      try {
        const response = await apiCall('/templates/validate/', {
          method: 'POST',
          body: JSON.stringify({ template_text: templateText }),
        });

        if (response.success) {
          setValidationErrors(response.validation_errors || []);
          console.log(`✅ Template validation: ${response.is_valid ? 'Valid' : 'Invalid'}`);
        } else {
          setValidationErrors([response.error || 'Validation failed']);
        }
      } catch (error) {
        console.error('Template validation failed:', error);
        setValidationErrors([`Validation error: ${error.message}`]);
      }
    }, 500); // 500ms debounce
  }, [apiCall]);

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
        const payload = {
          template_text: templateText,
          council_slug: options.councilSlug || null,
          year_slug: options.yearSlug || '2023-24',
          counter_slug: options.counterSlug || null,
        };

        const response = await apiCall('/templates/1/preview/', {
          method: 'POST',
          body: JSON.stringify(payload),
        });

        if (response.success) {
          setPreviewData(response.preview);
          console.log('✅ Generated live preview');
        } else {
          console.warn('Preview generation failed:', response.error);
          setPreviewData({
            rendered_text: 'Preview error',
            validation_errors: [response.error],
          });
        }
      } catch (error) {
        console.error('Preview generation failed:', error);
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

  // Cleanup function
  const cleanup = useCallback(() => {
    // Clear all debounce timers
    Object.values(debounceTimers.current).forEach(timer => {
      if (timer) clearTimeout(timer);
    });
    debounceTimers.current = {};
  }, []);

  return {
    // State
    fields,
    fieldGroups,
    previewData,
    validationErrors,
    isLoading,
    
    // Actions
    discoverFields,
    validateTemplate,
    generatePreview,
    saveTemplate,
    searchFields,
    getSampleCouncils,
    cleanup,
    
    // Direct API access
    apiCall,
  };
};
