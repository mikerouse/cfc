import React, { useState, useEffect, useCallback } from 'react';
import { useDeviceType } from './hooks/useDeviceType';
import CouncilEditLanding from './council-edit/CouncilEditLanding';
import CharacteristicsEditor from './council-edit/CharacteristicsEditor';
import FinancialWizard from './council-edit/FinancialWizard';
import FieldEditor from './council-edit/FieldEditor';
import LoadingSpinner from './LoadingSpinner';

/**
 * GOV.UK-Style Council Edit Interface
 * 
 * Uses landing page with choice cards instead of confusing tabs:
 * 1. Landing Page: Choose between Council Details or Financial Data
 * 2. Council Details: Simple form for characteristics (non-temporal)
 * 3. Financial Data: Wizard flow (Year → Method → Entry)
 */
const CouncilEditApp = ({ councilData, initialYears, csrfToken, focusYear = '2024/25' }) => {
  // Extract the year pattern from the focus year (e.g., '2024' from '2024/25')
  const FOCUS_YEAR_PATTERN = focusYear.split('/')[0];
  const { isMobile, isTablet } = useDeviceType();
  
  // Navigation state - replaces old tab system
  const [currentView, setCurrentView] = useState('landing'); // landing, characteristics, financial
  const [selectedYear, setSelectedYear] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState({});
  const [progress, setProgress] = useState({ 
    characteristics: 0, 
    financial: 0, 
    total: 0, 
    points: 0 
  });
  
  // Data state - simplified for new architecture
  const [characteristics, setCharacteristics] = useState({});
  const [financialData, setFinancialData] = useState({});
  
  // Available fields from the API
  const [availableFields, setAvailableFields] = useState({
    characteristics: [],
    financial: []
  });
  
  // Available years for temporal data
  const [years, setYears] = useState(initialYears || []);
  
  // Progress tracking with AJAX API
  const [progressData, setProgressData] = useState(null);

  /**
   * Update completion progress using the new AJAX API
   */
  const updateCompletionProgress = useCallback(async () => {
    if (!councilData?.slug) return;
    
    try {
      // Build API URL - include year if available
      let apiUrl = `/api/council/${councilData.slug}/completion/`;
      if (selectedYear?.id) {
        apiUrl += `${selectedYear.id}/`;
      }
      
      const response = await fetch(apiUrl, {
        headers: { 
          'X-CSRFToken': csrfToken,
          'X-Requested-With': 'XMLHttpRequest'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setProgressData(data.completion);
          
          // Update legacy progress state for compatibility (now focused on financial data)
          setProgress({
            characteristics: data.completion.by_category.characteristics.complete,
            financial: data.completion.by_category.financial.complete,
            total: data.completion.overall.complete, // Now focuses on financial fields only
            points: Math.round(data.completion.overall.complete * 2.5) // Estimate points
          });
          
          console.log(`📊 Progress updated via API: ${data.completion.focus.year_label} (Financial: ${data.completion.focus.financial_progress}%)`);
        }
      }
    } catch (error) {
      console.error('Failed to update completion progress:', error);
    }
  }, [councilData?.slug, selectedYear?.id, csrfToken]);

  /**
   * Load initial data for the council
   */
  useEffect(() => {
    if (councilData?.slug) {
      loadCouncilData();
    }
  }, [councilData?.slug]);

  /**
   * Load year-specific data when year changes and we're in financial view
   */
  useEffect(() => {
    if (selectedYear && currentView === 'financial') {
      loadFinancialData(selectedYear);
    }
    // Update progress when year changes
    if (selectedYear) {
      updateCompletionProgress();
    }
  }, [selectedYear, currentView, updateCompletionProgress]);

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
        setAvailableFields(prev => ({
          ...prev,
          characteristics: charData.available_fields || []
        }));
        
        // Calculate progress using our new API
        await updateCompletionProgress();
      }

      // Load available years
      const yearsResponse = await fetch(`/api/council/${councilData.slug}/years/`, {
        headers: { 'X-CSRFToken': csrfToken }
      });
      
      if (yearsResponse.ok) {
        const yearsData = await yearsResponse.json();
        setYears(yearsData.years || []);
        if (yearsData.years?.length > 0 && !selectedYear) {
          // Select the current focus year (2024/25) if available, otherwise don't auto-select
          const focusYear = yearsData.years.find(year => 
            year.label && year.label.includes(FOCUS_YEAR_PATTERN)
          );
          if (focusYear) {
            setSelectedYear(focusYear);
          }
          // Don't auto-select future years - let user explicitly choose
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
   * Load financial data for a specific year
   */
  const loadFinancialData = useCallback(async (year) => {
    if (!year?.id) return;
    
    setLoading(true);
    try {
      const response = await fetch(`/api/council/${councilData.slug}/temporal/${year.id}/`, {
        headers: { 'X-CSRFToken': csrfToken }
      });
      
      if (response.ok) {
        const data = await response.json();
        setFinancialData(data.financial || {});
        
        // Update available fields for financial data
        if (data.available_fields?.financial) {
          setAvailableFields(prev => ({
            ...prev,
            financial: data.available_fields.financial || []
          }));
          
          // Update progress for financial data
          const completedCount = Object.keys(data.financial || {}).length;
          const totalCount = data.available_fields.financial.length;
          setProgress(prev => ({
            ...prev,
            financial: completedCount
          }));
        }
      }
    } catch (error) {
      console.error('Error loading financial data:', error);
      setErrors({ financial: 'Failed to load financial data.' });
    } finally {
      setLoading(false);
    }
  }, [councilData?.slug, csrfToken]);

  /**
   * Save field data with optimistic updates
   */
  const saveField = useCallback(async (fieldSlug, value, yearId = null) => {
    setSaving(true);
    
    // Determine category from current view
    const category = currentView === 'characteristics' ? 'characteristics' : 'financial';
    
    // Convert financial values from millions to full amounts
    let processedValue = value;
    if (category === 'financial' && value && typeof value === 'string') {
      const numValue = parseFloat(value);
      if (!isNaN(numValue)) {
        // Financial fields entered in millions need conversion to full amounts
        // e.g., user enters "166.897" meaning £166.897 million = £166,897,000
        const financialFieldSlugs = [
          'total-income', 'total-expenditure', 'interest-payments', 'interest-paid',
          'capital-expenditure', 'business-rates-income', 'council-tax-income',
          'non-ring-fenced-government-grants-income', 'current-assets', 'current-liabilities',
          'long-term-liabilities', 'total-reserves', 'usable-reserves', 'unusable-reserves',
          'total-debt', 'pension-liability', 'finance-leases', 'finance-leases-pfi-liabilities'
        ];
        
        if (financialFieldSlugs.includes(fieldSlug)) {
          processedValue = (numValue * 1000000).toString(); // Convert millions to full amount
          console.log(`💰 Converting ${fieldSlug}: ${value} million → ${processedValue} (full amount)`);
        }
      }
    }
    
    // Optimistic update with processed value
    if (category === 'characteristics') {
      setCharacteristics(prev => ({ ...prev, [fieldSlug]: value }));
    } else if (category === 'financial') {
      setFinancialData(prev => ({ ...prev, [fieldSlug]: value }));
    }

    try {
      const endpoint = category === 'characteristics' 
        ? `/api/council/${councilData.slug}/characteristics/save/`
        : `/api/council/${councilData.slug}/temporal/${yearId}/save/`;

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
          field: fieldSlug,
          value: processedValue, // Send the converted value to backend
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
        
        // Update progress using our new API
        await updateCompletionProgress();
        
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
  }, [councilData?.slug, csrfToken, loadCouncilData, currentView]);

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
   * Navigation handlers for new landing page system
   */
  const handleChoiceSelect = useCallback((choice) => {
    if (choice === 'characteristics') {
      setCurrentView('characteristics');
    } else if (choice === 'financial') {
      setCurrentView('financial');
    }
  }, []);

  const handleBackToLanding = useCallback(() => {
    setCurrentView('landing');
    setSelectedYear(null);
    setErrors({});
  }, []);

  /**
   * Update progress tracking (simplified for new system)
   */
  /**
   * Legacy updateProgress function - now delegates to API-based progress calculation
   */
  const updateProgress = useCallback(() => {
    updateCompletionProgress();
  }, [updateCompletionProgress]);

  /**
   * Show success message with auto-hide
   */
  const showSuccessMessage = useCallback((message) => {
    // Could integrate with a toast system
    console.log('Success:', message);
  }, []);

  // Show loading spinner during initial load
  if (loading && Object.keys(characteristics).length === 0 && Object.keys(financialData).length === 0) {
    return (
      <div id="council-edit-loading" className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="large" message="Loading council data..." />
      </div>
    );
  }

  return (
    <div id="council-edit-main-container" className="min-h-screen bg-gray-50">
      {/* Landing Page - Choose between Council Details or Financial Data */}
      {currentView === 'landing' && (
        <CouncilEditLanding
          councilData={councilData}
          progress={progress}
          progressData={progressData}
          focusYear={focusYear}
          onChoiceSelect={handleChoiceSelect}
          className="min-h-screen"
        />
      )}

      {/* Council Details Editor */}
      {currentView === 'characteristics' && (
        <CharacteristicsEditor
          councilData={councilData}
          characteristics={characteristics}
          availableFields={availableFields.characteristics}
          onSave={saveField}
          onValidate={validateField}
          onBack={handleBackToLanding}
          errors={errors}
          loading={loading}
          className="min-h-screen"
        />
      )}

      {/* Financial Data Wizard */}
      {currentView === 'financial' && (
        <FinancialWizard
          councilData={councilData}
          years={years}
          onBack={handleBackToLanding}
          onSave={(fieldSlug, value, yearId) => saveField(fieldSlug, value, yearId)}
          onValidate={validateField}
          csrfToken={csrfToken}
          className="min-h-screen"
        />
      )}

      {/* Global Error Display */}
      {errors.general && (
        <div id="council-edit-error" className="fixed bottom-4 left-4 right-4 z-50 p-4 bg-red-50 border border-red-200 rounded-lg shadow-lg">
          <div className="flex items-center">
            <svg className="w-5 h-5 text-red-400 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-red-800">{errors.general}</p>
            <button 
              onClick={() => setErrors(prev => ({ ...prev, general: null }))}
              className="ml-auto text-red-600 hover:text-red-800"
            >
              ×
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default CouncilEditApp;