/**
 * Improved Factoid Builder - GOV.UK Inspired Design
 * 
 * A completely redesigned factoid builder that emphasizes:
 * - Clear step-by-step process
 * - Plain English guidance  
 * - Progressive disclosure
 * - GOV.UK design patterns
 * - Better error handling
 */
import { useState, useEffect, useCallback } from 'react';
import { logActivity } from '../utils/logger';
import { useFactoidAPI } from '../hooks/useFactoidAPI';

const ImprovedFactoidBuilder = () => {
  console.log('🎨 Improved FactoidBuilder mounting...');

  // Check if we're in integrated mode
  const isIntegratedMode = window?.FACTOID_BUILDER_CONFIG?.isIntegratedMode || false;

  // Current step in the process
  const [currentStep, setCurrentStep] = useState(1);
  
  // Core state
  const [template, setTemplate] = useState({
    name: '',
    template_text: '',
    factoid_type: 'context',
    emoji: '📊',
    color_scheme: 'blue',
    priority: 50,
    is_active: true,
  });
  const [templateId, setTemplateId] = useState(null);
  const [isDirty, setIsDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  
  // User guidance state
  const [showHelp, setShowHelp] = useState(false);
  const [selectedField, setSelectedField] = useState(null);
  const [previewCouncil, setPreviewCouncil] = useState(null);
  
  // API hook for real-time features
  const {
    fields,
    fieldGroups,
    previewData,
    setPreviewData,
    validationErrors,
    isLoading,
    discoverFields,
    validateTemplate,
    generatePreview,
    generatePreviewWithFallback,
    generateMockPreview,
    saveTemplate,
    getSampleCouncils,
    getAvailableYears,
  } = useFactoidAPI();

  // Preview-specific state
  const [availableCouncils, setAvailableCouncils] = useState([]);
  const [availableYears, setAvailableYears] = useState([]);
  const [selectedCouncil, setSelectedCouncil] = useState('');
  const [selectedYear, setSelectedYear] = useState('2024-25');
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(null);

  // Steps configuration
  const steps = [
    {
      number: 1,
      title: "What do you want to create?",
      description: "Choose what type of factoid you're building"
    },
    {
      number: 2,
      title: "Give your factoid a name",
      description: "Choose a clear, descriptive name"
    },
    {
      number: 3,
      title: "Write your factoid text",
      description: "Create the message using available data fields"
    },
    {
      number: 4,
      title: "Check your factoid works",
      description: "Preview with real council data"
    },
    {
      number: 5,
      title: "Save your factoid",
      description: "Review and save your completed factoid"
    }
  ];

  // Initialize field discovery on mount
  useEffect(() => {
    console.log('🔍 ImprovedFactoidBuilder: Discovering available fields...');
    
    // Make sure we have the API functions before calling them
    if (typeof discoverFields === 'function') {
      discoverFields().catch(error => {
        console.error('Field discovery failed:', error);
        logActivity('field_discovery_error', {}, error);
      });
    } else {
      console.error('discoverFields function not available');
    }
    
    // Emit ready event for integration
    if (isIntegratedMode) {
      const readyEvent = new CustomEvent('factoidBuilderReady', {
        detail: { component: 'ImprovedFactoidBuilder' }
      });
      window.dispatchEvent(readyEvent);
    }
  }, []); // Remove dependencies to prevent re-mounting

  // Template change handler
  const handleTemplateChange = useCallback((field, value) => {
    setTemplate(prev => ({
      ...prev,
      [field]: value
    }));
    setIsDirty(true);

    // Auto-validate on template text changes
    if (field === 'template_text' && value.trim()) {
      try {
        console.log('🔄 Template text changed, validating and generating preview...');
        if (typeof validateTemplate === 'function') {
          validateTemplate(value, templateId);
        }
        if (typeof generatePreview === 'function') {
          generatePreview(value, { templateId });
        }
      } catch (err) {
        console.error('Template change processing failed:', err);
        logActivity('template_change_error', { field }, err);
      }
    }
  }, [validateTemplate, generatePreview, templateId]);

  // Insert field into template text
  const insertField = useCallback((fieldVariable, formatType = 'default') => {
    try {
      const currentText = template.template_text;
      const formatSuffix = formatType !== 'default' ? `:${formatType}` : '';
      const fieldPlaceholder = `{${fieldVariable}${formatSuffix}}`;
      
      // Just append to the end for simplicity
      const newText = currentText + fieldPlaceholder;
      handleTemplateChange('template_text', newText);
      
      // Show preview
      generatePreview(newText, { templateId });
    } catch (err) {
      console.error('Field insert failed:', err);
      logActivity('field_insert_error', { fieldVariable }, err);
    }
  }, [template.template_text, handleTemplateChange, generatePreview, templateId]);

  // Save handler
  const handleSave = async () => {
    setSaving(true);
    try {
      const result = await saveTemplate(template);
      if (result.success) {
        setTemplateId(result.data.id);
        setIsDirty(false);
        logActivity('template_saved', { id: result.data.id });
        // Move to success step
        setCurrentStep(6);
      } else {
        logActivity('template_save_failed', { error: result.error });
        alert(`Save failed: ${result.error}`);
      }
    } catch (error) {
      console.error('Save error:', error);
      logActivity('template_save_error', {}, error);
      alert(`Save failed: ${error.message}`);
    } finally {
      setSaving(false);
    }
  };

  // Load preview data when needed
  const loadPreviewData = useCallback(async () => {
    try {
      const [councilsResult, yearsResult] = await Promise.all([
        getSampleCouncils(),
        getAvailableYears()
      ]);

      if (councilsResult.success && councilsResult.councils) {
        setAvailableCouncils(councilsResult.councils);
        if (councilsResult.councils.length > 0 && !selectedCouncil) {
          setSelectedCouncil(councilsResult.councils[0].slug);
        }
      }

      if (yearsResult.success && yearsResult.years) {
        setAvailableYears(yearsResult.years);
      }
    } catch (error) {
      console.error('Failed to load preview data:', error);
      setPreviewError('Failed to load preview options');
    }
  }, [getSampleCouncils, getAvailableYears, selectedCouncil]);

  // Generate preview with user selections
  const generateUserPreview = useCallback(async () => {
    if (!template.template_text.trim()) return;

    setPreviewLoading(true);
    setPreviewError(null);

    try {
      console.log('🔄 Generating preview with selections:', { selectedCouncil, selectedYear });
      
      // First try with real data using user selections
      const previewResult = await generatePreview(template.template_text, {
        councilSlug: selectedCouncil,
        yearSlug: selectedYear,
      });

      // If preview was successful, we're done
      if (previewResult && previewResult.success) {
        setPreviewLoading(false);
        return;
      }

      // If no preview data or preview failed, generate mock preview
      console.log('🔄 Real data preview failed, generating mock preview...');
      const mockResult = generateMockPreview(template.template_text, {
        yearSlug: selectedYear,
      });
      
      if (mockResult && mockResult.preview) {
        setPreviewData(mockResult.preview);
      }
      setPreviewLoading(false);

    } catch (error) {
      console.error('Preview generation failed:', error);
      setPreviewError(error.message);
      
      // Generate mock preview as fallback
      const mockResult = generateMockPreview(template.template_text, {
        yearSlug: selectedYear,
      });
      
      if (mockResult && mockResult.preview) {
        setPreviewData(mockResult.preview);
      }
      setPreviewLoading(false);
    }
  }, [template.template_text, selectedCouncil, selectedYear, generatePreview, generateMockPreview, setPreviewData]);

  // Navigation handlers
  const goToNextStep = () => {
    if (currentStep < steps.length) {
      const nextStep = currentStep + 1;
      setCurrentStep(nextStep);
      
      // Load preview data when entering step 4
      if (nextStep === 4) {
        loadPreviewData();
        generateUserPreview();
      }
    }
  };

  const goToPreviousStep = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  // Check if current step can proceed
  const canProceed = () => {
    switch (currentStep) {
      case 1:
        return template.factoid_type;
      case 2:
        return template.name.trim().length > 0;
      case 3:
        return template.template_text.trim().length > 0;
      case 4:
        // Allow proceeding if we have some preview data (even with mock data)
        return previewData !== null;
      case 5:
        return true;
      default:
        return false;
    }
  };

  // Render step 1: Choose factoid type
  const renderStep1 = () => (
    <div className="space-y-6">
      <div className="bg-blue-50 border-l-4 border-blue-400 p-4">
        <div className="flex">
          <div className="ml-3">
            <p className="text-sm text-blue-700">
              <strong>What are factoids?</strong><br />
              Factoids are small pieces of text that display council data in an engaging way. 
              For example: "Worcestershire County Council spent £2.5 million on highways in 2023-24"
            </p>
          </div>
        </div>
      </div>

      <fieldset className="space-y-4">
        <legend className="text-lg font-medium">What type of factoid do you want to create?</legend>
        
        <div className="space-y-3">
          <label className="flex items-start space-x-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer">
            <input
              type="radio"
              name="factoid_type"
              value="context"
              checked={template.factoid_type === 'context'}
              onChange={(e) => handleTemplateChange('factoid_type', e.target.value)}
              className="mt-1"
            />
            <div>
              <div className="font-medium">📊 Context factoid</div>
              <div className="text-sm text-gray-600">
                Provides background information about a council or financial figure
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Example: "This council serves 592,000 residents across West Yorkshire"
              </div>
            </div>
          </label>

          <label className="flex items-start space-x-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer">
            <input
              type="radio"
              name="factoid_type"
              value="comparison"
              checked={template.factoid_type === 'comparison'}
              onChange={(e) => handleTemplateChange('factoid_type', e.target.value)}
              className="mt-1"
            />
            <div>
              <div className="font-medium">⚖️ Comparison factoid</div>
              <div className="text-sm text-gray-600">
                Compares this council's data with others or previous years
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Example: "This is 15% higher than the national average"
              </div>
            </div>
          </label>

          <label className="flex items-start space-x-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer">
            <input
              type="radio"
              name="factoid_type"
              value="insight"
              checked={template.factoid_type === 'insight'}
              onChange={(e) => handleTemplateChange('factoid_type', e.target.value)}
              className="mt-1"
            />
            <div>
              <div className="font-medium">💡 Insight factoid</div>
              <div className="text-sm text-gray-600">
                Highlights interesting patterns or notable facts
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Example: "Debt has increased by 23% over the past 3 years"
              </div>
            </div>
          </label>
        </div>
      </fieldset>
    </div>
  );

  // Render step 2: Name the factoid
  const renderStep2 = () => (
    <div className="space-y-6">
      <div className="bg-green-50 border-l-4 border-green-400 p-4">
        <div className="flex">
          <div className="ml-3">
            <p className="text-sm text-green-700">
              <strong>Choose a good name</strong><br />
              Pick something descriptive that helps you find this factoid later. 
              You can always change it later.
            </p>
          </div>
        </div>
      </div>

      <div>
        <label htmlFor="factoid-name" className="block text-sm font-medium text-gray-700 mb-2">
          Factoid name
        </label>
        <input
          id="factoid-name"
          type="text"
          value={template.name}
          onChange={(e) => handleTemplateChange('name', e.target.value)}
          placeholder="e.g. Council spending overview, Debt comparison, Population facts"
          className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
        />
        <p className="mt-1 text-sm text-gray-500">
          Give your factoid a clear, descriptive name
        </p>
      </div>

      <div>
        <label htmlFor="factoid-emoji" className="block text-sm font-medium text-gray-700 mb-2">
          Choose an emoji (optional)
        </label>
        <select
          id="factoid-emoji"
          value={template.emoji}
          onChange={(e) => handleTemplateChange('emoji', e.target.value)}
          className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="📊">📊 Chart</option>
          <option value="💰">💰 Money</option>
          <option value="🏛️">🏛️ Government</option>
          <option value="📈">📈 Growth</option>
          <option value="📉">📉 Decline</option>
          <option value="⚖️">⚖️ Balance</option>
          <option value="🌟">🌟 Star</option>
          <option value="💡">💡 Insight</option>
          <option value="🔍">🔍 Analysis</option>
        </select>
      </div>
    </div>
  );

  // Render step 3: Write the factoid text
  const renderStep3 = () => (
    <div className="space-y-6">
      <div className="bg-amber-50 border-l-4 border-amber-400 p-4">
        <div className="flex">
          <div className="ml-3">
            <p className="text-sm text-amber-700">
              <strong>How to write factoids</strong><br />
              Write your factoid like a sentence, then insert data fields using the buttons below. 
              Fields appear as {`{field_name}`} and will be replaced with real data.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Template editor */}
        <div>
          <label htmlFor="template-text" className="block text-sm font-medium text-gray-700 mb-2">
            Your factoid text
          </label>
          <textarea
            id="template-text"
            value={template.template_text}
            onChange={(e) => handleTemplateChange('template_text', e.target.value)}
            placeholder="Start typing your factoid... e.g. 'This council spent'"
            rows={6}
            className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          />
          <p className="mt-1 text-sm text-gray-500">
            Write naturally, then add data fields using the buttons below
          </p>
          
          {validationErrors.length > 0 && (
            <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded-md">
              <div className="text-sm text-red-700">
                <strong>Issues to fix:</strong>
                <ul className="mt-1 list-disc list-inside">
                  {validationErrors.map((error, index) => (
                    <li key={index}>{error}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>

        {/* Available fields */}
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-3">Available data fields</h3>
          <div className="space-y-3 max-h-64 overflow-y-auto">
            {isLoading ? (
              <div className="text-center py-4">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto mb-2"></div>
                <p className="text-sm text-gray-500">Loading fields...</p>
              </div>
            ) : Object.keys(fieldGroups).length === 0 ? (
              <div className="text-center py-4">
                <p className="text-sm text-gray-500">No fields available</p>
                <button
                  onClick={() => discoverFields()}
                  className="mt-2 text-xs text-blue-600 hover:text-blue-800"
                >
                  Try to reload fields
                </button>
              </div>
            ) : (
              Object.entries(fieldGroups).map(([category, fields]) => (
                <div key={category}>
                  <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                    {category.replace('_', ' ')}
                  </h4>
                  <div className="space-y-1">
                    {fields.slice(0, 5).map((field) => (
                      <button
                        key={field.id}
                        onClick={() => insertField(field.variable_name)}
                        className="w-full text-left p-2 text-sm border border-gray-200 rounded hover:bg-blue-50 hover:border-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <div className="font-medium">{field.name}</div>
                        {field.description && (
                          <div className="text-xs text-gray-500 truncate">
                            {field.description}
                          </div>
                        )}
                      </button>
                    ))}
                    {fields.length > 5 && (
                      <p className="text-xs text-gray-500 p-2">
                        And {fields.length - 5} more...
                      </p>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Example section */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-700 mb-2">Example factoids</h3>
        <div className="space-y-2 text-sm text-gray-600">
          <div>• "This council spent {`{total_expenditure}`} in {`{year_label}`}"</div>
          <div>• "{`{council_name}`} serves {`{population}`} residents"</div>
          <div>• "Debt per resident is {`{debt_per_resident}`}"</div>
        </div>
      </div>
    </div>
  );

  // Render step 4: Preview
  const renderStep4 = () => (
    <div className="space-y-6">
      <div className="bg-purple-50 border-l-4 border-purple-400 p-4">
        <div className="flex">
          <div className="ml-3">
            <p className="text-sm text-purple-700">
              <strong>Check it works</strong><br />
              See how your factoid looks with council data. 
              Choose a council and year below, or use sample data if real data isn't available.
            </p>
          </div>
        </div>
      </div>

      {/* Preview Controls */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-700 mb-3">Preview settings</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="council-select" className="block text-sm font-medium text-gray-700 mb-1">
              Council
            </label>
            <select
              id="council-select"
              value={selectedCouncil}
              onChange={(e) => {
                setSelectedCouncil(e.target.value);
                generateUserPreview();
              }}
              className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
            >
              <option value="">Use sample data</option>
              {availableCouncils.map((council) => (
                <option key={council.slug} value={council.slug}>
                  {council.name}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              Choose a council to use real data, or leave as "sample data" for demo values
            </p>
          </div>

          <div>
            <label htmlFor="year-select" className="block text-sm font-medium text-gray-700 mb-1">
              Financial year
            </label>
            <select
              id="year-select"
              value={selectedYear}
              onChange={(e) => {
                setSelectedYear(e.target.value);
                generateUserPreview();
              }}
              className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
            >
              {availableYears.map((year) => (
                <option key={year.value} value={year.value}>
                  {year.label}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              Financial year for the data
            </p>
          </div>
        </div>

        <div className="mt-3">
          <button
            onClick={generateUserPreview}
            disabled={previewLoading}
            className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {previewLoading ? 'Updating...' : 'Update preview'}
          </button>
        </div>
      </div>

      {/* Preview Display */}
      {previewLoading ? (
        <div className="text-center py-8 text-gray-500">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
          Generating preview...
        </div>
      ) : previewError ? (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h3 className="text-sm font-medium text-red-800 mb-2">Preview Error</h3>
          <p className="text-sm text-red-700">{previewError}</p>
          <button
            onClick={generateUserPreview}
            className="mt-2 px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
          >
            Try again
          </button>
        </div>
      ) : previewData ? (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900">
              {template.emoji} Preview
            </h3>
            {previewData.is_mock_data && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                Sample data
              </span>
            )}
          </div>
          
          <div className="text-lg text-gray-700 leading-relaxed mb-4">
            {previewData.rendered_text}
          </div>
          
          <div className="text-sm text-gray-500 border-t pt-3">
            {previewData.is_mock_data ? (
              <div>
                <p>
                  <strong>Using sample data</strong> - This preview shows how your factoid will look. 
                  {selectedCouncil ? ' Real data not available for this council/year.' : ' Choose a council above to try with real data.'}
                </p>
                <p className="mt-1">
                  You can save this factoid and add real data later.
                </p>
              </div>
            ) : (
              <p>
                Preview using real data from <strong>{previewData.council_name}</strong> ({previewData.year_label})
              </p>
            )}
          </div>
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500">
          <p>No preview available</p>
          <button
            onClick={generateUserPreview}
            className="mt-2 px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Generate preview
          </button>
        </div>
      )}

      {/* Validation Errors */}
      {previewData?.validation_errors?.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h3 className="text-sm font-medium text-red-800 mb-2">Issues found:</h3>
          <ul className="text-sm text-red-700 list-disc list-inside">
            {previewData.validation_errors.map((error, index) => (
              <li key={index}>{error}</li>
            ))}
          </ul>
          <p className="text-xs text-gray-600 mt-2">
            These issues may prevent the factoid from working correctly. 
            Go back to step 3 to fix them or save anyway using sample data.
          </p>
        </div>
      )}
    </div>
  );

  // Render step 5: Save
  const renderStep5 = () => (
    <div className="space-y-6">
      <div className="bg-green-50 border-l-4 border-green-400 p-4">
        <div className="flex">
          <div className="ml-3">
            <p className="text-sm text-green-700">
              <strong>Ready to save</strong><br />
              Your factoid is ready! Review the details below and save when you're happy.
            </p>
          </div>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Review your factoid</h3>
        
        <dl className="space-y-3">
          <div>
            <dt className="text-sm font-medium text-gray-500">Name</dt>
            <dd className="text-sm text-gray-900">{template.name}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Type</dt>
            <dd className="text-sm text-gray-900 capitalize">{template.factoid_type}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Template text</dt>
            <dd className="text-sm text-gray-900 font-mono bg-gray-50 p-2 rounded">
              {template.template_text}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Preview</dt>
            <dd className="text-sm text-gray-900">
              {previewData?.rendered_text || 'No preview available'}
            </dd>
          </div>
        </dl>

        <div className="mt-6">
          <button
            onClick={handleSave}
            disabled={saving}
            className="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
          >
            {saving ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Saving...
              </>
            ) : (
              'Save factoid'
            )}
          </button>
        </div>
      </div>
    </div>
  );

  // Render success message
  const renderSuccess = () => (
    <div className="space-y-6">
      <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
        <div className="text-4xl mb-4">✅</div>
        <h3 className="text-lg font-medium text-green-900 mb-2">Factoid saved successfully!</h3>
        <p className="text-green-700">
          Your factoid "{template.name}" has been saved and is now available for use.
        </p>
      </div>
      
      <div className="flex justify-center space-x-4">
        <button
          onClick={() => {
            setCurrentStep(1);
            setTemplate({
              name: '',
              template_text: '',
              factoid_type: 'context',
              emoji: '📊',
              color_scheme: 'blue',
              priority: 50,
              is_active: true,
            });
            setIsDirty(false);
          }}
          className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          Create another factoid
        </button>
      </div>
    </div>
  );

  // Render current step content
  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return renderStep1();
      case 2:
        return renderStep2();
      case 3:
        return renderStep3();
      case 4:
        return renderStep4();
      case 5:
        return renderStep5();
      case 6:
        return renderSuccess();
      default:
        return null;
    }
  };

  return (
    <div className={`improved-factoid-builder ${isIntegratedMode ? 'integrated-mode' : 'standalone-mode'} ${isIntegratedMode ? 'p-6' : 'h-full'} max-w-4xl mx-auto`}>
      {/* Progress indicator */}
      {currentStep <= 5 && (
        <div className="mb-8">
          <div className="flex items-center justify-between">
            {steps.map((step, index) => (
              <div key={step.number} className="flex items-center">
                <div
                  className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium ${
                    currentStep >= step.number
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 text-gray-500'
                  }`}
                >
                  {currentStep > step.number ? '✓' : step.number}
                </div>
                {index < steps.length - 1 && (
                  <div
                    className={`w-12 h-0.5 ml-2 ${
                      currentStep > step.number ? 'bg-blue-600' : 'bg-gray-200'
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
          <div className="mt-2 text-center">
            <p className="text-sm text-gray-500">
              Step {currentStep} of {steps.length}
            </p>
          </div>
        </div>
      )}

      {/* Main content */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        {currentStep <= 5 && (
          <div className="mb-6">
            <h2 className="text-xl font-bold text-gray-900 mb-2">
              {steps[currentStep - 1]?.title}
            </h2>
            <p className="text-gray-600">
              {steps[currentStep - 1]?.description}
            </p>
          </div>
        )}

        {renderStepContent()}
      </div>

      {/* Navigation */}
      {currentStep <= 5 && (
        <div className="flex justify-between">
          <button
            onClick={goToPreviousStep}
            disabled={currentStep === 1}
            className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>

          <button
            onClick={goToNextStep}
            disabled={!canProceed()}
            className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {currentStep === 5 ? 'Review' : 'Continue'}
          </button>
        </div>
      )}
    </div>
  );
};

export default ImprovedFactoidBuilder;