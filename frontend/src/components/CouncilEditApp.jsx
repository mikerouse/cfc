import React, { useState, useEffect, useCallback } from 'react';
import { useDeviceType } from './hooks/useDeviceType';
import EditHeader from './council-edit/EditHeader';
import TabNavigation from './council-edit/TabNavigation';
import CharacteristicsTab from './council-edit/CharacteristicsTab';
import GeneralDataTab from './council-edit/GeneralDataTab';
import FinancialDataTab from './council-edit/FinancialDataTab';
import YearSelector from './council-edit/YearSelector';
import ValidationSystem from './council-edit/ValidationSystem';
import ProgressTracker from './council-edit/ProgressTracker';
import LoadingSpinner from './LoadingSpinner';

/**
 * Mobile-First Council Edit Interface
 * 
 * Separates editing into three clear categories:
 * 1. Characteristics (non-temporal): Website, Nation, Type, etc.
 * 2. General Data (temporal): Link to Financial Statement, Political Control
 * 3. Financial Data (temporal): Debt, Expenditure, Revenue, etc.
 */
const CouncilEditApp = ({ councilData, initialYears, csrfToken }) => {
  const { isMobile, isTablet } = useDeviceType();
  
  // State management
  const [activeTab, setActiveTab] = useState('characteristics');
  const [selectedYear, setSelectedYear] = useState(initialYears?.[0] || null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState({});
  const [progress, setProgress] = useState({ completed: 0, total: 0, points: 0 });
  
  // Data state
  const [characteristics, setCharacteristics] = useState({});
  const [generalData, setGeneralData] = useState({});
  const [financialData, setFinancialData] = useState({});
  
  // Available years for temporal data
  const [years, setYears] = useState(initialYears || []);

  /**
   * Load initial data for the council
   */
  useEffect(() => {
    if (councilData?.slug) {
      loadCouncilData();
    }
  }, [councilData?.slug]);

  /**
   * Load year-specific data when year changes
   */
  useEffect(() => {
    if (selectedYear && (activeTab === 'general' || activeTab === 'financial')) {
      loadTemporalData(selectedYear);
    }
  }, [selectedYear, activeTab]);

  /**
   * Fetch all council data from the backend
   */
  const loadCouncilData = useCallback(async () => {
    setLoading(true);
    try {
      // Load characteristics (non-temporal)
      const charResponse = await fetch(`/api/council/${councilData.slug}/characteristics/`, {
        headers: { 'X-CSRFToken': csrfToken }
      });
      
      if (charResponse.ok) {
        const charData = await charResponse.json();
        setCharacteristics(charData.characteristics || {});
      }

      // Load available years
      const yearsResponse = await fetch(`/api/council/${councilData.slug}/years/`, {
        headers: { 'X-CSRFToken': csrfToken }
      });
      
      if (yearsResponse.ok) {
        const yearsData = await yearsResponse.json();
        setYears(yearsData.years || []);
        if (yearsData.years?.length > 0 && !selectedYear) {
          setSelectedYear(yearsData.years[0]);
        }
      }

      // Update progress
      updateProgress();
      
    } catch (error) {
      console.error('Error loading council data:', error);
      setErrors({ general: 'Failed to load council data. Please refresh the page.' });
    } finally {
      setLoading(false);
    }
  }, [councilData?.slug, csrfToken]);

  /**
   * Load temporal data for a specific year
   */
  const loadTemporalData = useCallback(async (year) => {
    if (!year?.id) return;
    
    setLoading(true);
    try {
      const response = await fetch(`/api/council/${councilData.slug}/temporal/${year.id}/`, {
        headers: { 'X-CSRFToken': csrfToken }
      });
      
      if (response.ok) {
        const data = await response.json();
        setGeneralData(data.general || {});
        setFinancialData(data.financial || {});
      }
    } catch (error) {
      console.error('Error loading temporal data:', error);
      setErrors({ temporal: 'Failed to load year-specific data.' });
    } finally {
      setLoading(false);
    }
  }, [councilData?.slug, csrfToken]);

  /**
   * Save field data with optimistic updates
   */
  const saveField = useCallback(async (category, fieldSlug, value, yearId = null) => {
    setSaving(true);
    
    // Optimistic update
    if (category === 'characteristics') {
      setCharacteristics(prev => ({ ...prev, [fieldSlug]: value }));
    } else if (category === 'general') {
      setGeneralData(prev => ({ ...prev, [fieldSlug]: value }));
    } else if (category === 'financial') {
      setFinancialData(prev => ({ ...prev, [fieldSlug]: value }));
    }

    try {
      const endpoint = category === 'characteristics' 
        ? `/api/council/${councilData.slug}/characteristics/`
        : `/api/council/${councilData.slug}/temporal/${yearId}/`;

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
          field: fieldSlug,
          value: value,
          category: category
        })
      });

      const result = await response.json();
      
      if (response.ok && result.success) {
        // Clear any previous errors for this field
        setErrors(prev => {
          const newErrors = { ...prev };
          delete newErrors[fieldSlug];
          return newErrors;
        });
        
        // Update progress
        updateProgress();
        
        // Show success feedback
        showSuccessMessage(`${result.field_name || 'Field'} updated successfully! +${result.points || 3} points`);
        
        return { success: true, points: result.points };
      } else {
        throw new Error(result.message || 'Failed to save field');
      }
    } catch (error) {
      console.error('Error saving field:', error);
      
      // Revert optimistic update
      loadCouncilData();
      
      setErrors(prev => ({
        ...prev,
        [fieldSlug]: error.message || 'Failed to save field'
      }));
      
      return { success: false, error: error.message };
    } finally {
      setSaving(false);
    }
  }, [councilData?.slug, csrfToken, loadCouncilData]);

  /**
   * Validate URL fields with backend security checks
   */
  const validateField = useCallback(async (fieldSlug, value) => {
    try {
      const response = await fetch('/api/validate-url/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
          url: value,
          field_slug: fieldSlug
        })
      });
      
      const result = await response.json();
      return result;
    } catch (error) {
      console.error('Error validating field:', error);
      return { valid: false, message: 'Validation service unavailable' };
    }
  }, [csrfToken]);

  /**
   * Update progress tracking
   */
  const updateProgress = useCallback(() => {
    const charCount = Object.keys(characteristics).length;
    const generalCount = Object.keys(generalData).length;
    const financialCount = Object.keys(financialData).length;
    
    const totalCompleted = charCount + generalCount + financialCount;
    const estimatedTotal = 20; // Rough estimate, could be dynamic
    const pointsEarned = totalCompleted * 3; // 3 points per field
    
    setProgress({
      completed: totalCompleted,
      total: estimatedTotal,
      points: pointsEarned
    });
  }, [characteristics, generalData, financialData]);

  /**
   * Show success message with auto-hide
   */
  const showSuccessMessage = useCallback((message) => {
    // Could integrate with a toast system
    console.log('Success:', message);
  }, []);

  /**
   * Handle tab change with validation
   */
  const handleTabChange = useCallback((newTab) => {
    // Clear any tab-specific errors
    setErrors(prev => {
      const newErrors = { ...prev };
      delete newErrors.temporal;
      delete newErrors.general;
      return newErrors;
    });
    
    setActiveTab(newTab);
  }, []);

  /**
   * Handle year change for temporal data
   */
  const handleYearChange = useCallback((newYear) => {
    setSelectedYear(newYear);
  }, []);

  // Show loading spinner during initial load
  if (loading && !characteristics && !generalData && !financialData) {
    return (
      <div id="council-edit-loading" className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="large" message="Loading council data..." />
      </div>
    );
  }

  return (
    <div id="council-edit-main-container" className="min-h-screen bg-gray-50">
      {/* Fixed Header */}
      <EditHeader 
        council={councilData}
        progress={progress}
        saving={saving}
        className="sticky top-0 z-40"
      />

      {/* Main Content Container */}
      <div id="council-edit-content" className="mx-auto px-3 sm:px-4 xl:px-6 py-4 xl:py-8 max-w-none xl:max-w-desktop">
        
        {/* Progress Tracker - Mobile optimized */}
        <ProgressTracker 
          progress={progress}
          isMobile={isMobile}
          className="mb-6"
        />

        {/* Year Selector - Only for temporal tabs */}
        {(activeTab === 'general' || activeTab === 'financial') && (
          <YearSelector
            years={years}
            selectedYear={selectedYear}
            onChange={handleYearChange}
            isMobile={isMobile}
            className="mb-6"
          />
        )}

        {/* Tab Content */}
        <div id="council-edit-tab-content" className="bg-white rounded-lg shadow-sm border border-gray-200">
          {activeTab === 'characteristics' && (
            <CharacteristicsTab
              characteristics={characteristics}
              onSave={(fieldSlug, value) => saveField('characteristics', fieldSlug, value)}
              onValidate={validateField}
              errors={errors}
              loading={loading}
              isMobile={isMobile}
            />
          )}
          
          {activeTab === 'general' && selectedYear && (
            <GeneralDataTab
              generalData={generalData}
              selectedYear={selectedYear}
              onSave={(fieldSlug, value) => saveField('general', fieldSlug, value, selectedYear.id)}
              onValidate={validateField}
              errors={errors}
              loading={loading}
              isMobile={isMobile}
            />
          )}
          
          {activeTab === 'financial' && selectedYear && (
            <FinancialDataTab
              financialData={financialData}
              selectedYear={selectedYear}
              onSave={(fieldSlug, value) => saveField('financial', fieldSlug, value, selectedYear.id)}
              onValidate={validateField}
              errors={errors}
              loading={loading}
              isMobile={isMobile}
            />
          )}
        </div>

        {/* Global Error Display */}
        {errors.general && (
          <div id="council-edit-error" className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-center">
              <svg className="w-5 h-5 text-red-400 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-red-800">{errors.general}</p>
            </div>
          </div>
        )}
      </div>

      {/* Bottom Navigation - Mobile First */}
      <TabNavigation
        activeTab={activeTab}
        onChange={handleTabChange}
        isMobile={isMobile}
        progress={progress}
        className="sticky bottom-0 z-40"
      />

      {/* Validation System */}
      <ValidationSystem 
        errors={errors}
        onClearError={(field) => setErrors(prev => {
          const newErrors = { ...prev };
          delete newErrors[field];
          return newErrors;
        })}
      />
    </div>
  );
};

export default CouncilEditApp;