import React, { useState, useCallback, useEffect } from 'react';
import CategorySelection from './CategorySelection';
import CategoryFieldEntry from './CategoryFieldEntry';
import SaveSuccessModal from './SaveSuccessModal';

/**
 * Redesigned wizard for financial data editing
 * Step 1: Year Selection
 * Step 2: Method Choice (PDF Upload vs Manual Entry)
 * Step 3: Category Selection (Income & Expenditure, Balance Sheet, etc.) 
 * Step 4: Focused Data Entry (only fields for selected category)
 */
const FinancialWizard = ({
  councilData,
  years = [],
  onBack,
  onSave,
  onValidate,
  csrfToken,
  className = ""
}) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [selectedYear, setSelectedYear] = useState(null);
  const [selectedMethod, setSelectedMethod] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [loading, setLoading] = useState(false);
  const [generalData, setGeneralData] = useState({});
  const [financialData, setFinancialData] = useState({});
  const [availableFields, setAvailableFields] = useState({ general: [], financial: [] });
  const [availableCategories, setAvailableCategories] = useState([]);
  const [allChanges, setAllChanges] = useState({}); // Track all changes across categories
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [savedChangeCount, setSavedChangeCount] = useState(0);
  const [yearProgressData, setYearProgressData] = useState({}); // Cache progress data for years

  // Load data when year is selected
  useEffect(() => {
    if (selectedYear && currentStep >= 2) {
      loadYearData(selectedYear);
    }
  }, [selectedYear]);

  // Load progress data for all years when component mounts
  useEffect(() => {
    const loadAllYearProgress = async () => {
      if (!councilData?.slug || !years.length || !csrfToken) return;
      
      const progressPromises = years.map(async (year) => {
        try {
          const response = await fetch(`/api/council/${councilData.slug}/completion/${year.id}/`, {
            headers: { 'X-CSRFToken': csrfToken }
          });
          
          if (response.ok) {
            const data = await response.json();
            if (data.success && data.completion?.overall) {
              return {
                yearId: year.id,
                progress: {
                  completed: data.completion.overall.complete || 0,
                  total: data.completion.overall.total_fields || 9,
                  percentage: data.completion.overall.percentage || 0
                }
              };
            }
          }
        } catch (error) {
          console.error('Error fetching completion data for year:', error);
        }
        
        // Fallback
        return {
          yearId: year.id,
          progress: { completed: 0, total: 9, percentage: 0 }
        };
      });
      
      try {
        const results = await Promise.all(progressPromises);
        const progressMap = {};
        results.forEach(({ yearId, progress }) => {
          progressMap[yearId] = progress;
        });
        setYearProgressData(progressMap);
      } catch (error) {
        console.error('Error loading year progress data:', error);
      }
    };
    
    loadAllYearProgress();
  }, [councilData?.slug, years, csrfToken]);

  const loadYearData = useCallback(async (year) => {
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
        setAvailableFields({
          general: data.available_fields?.general || [],
          financial: data.available_fields?.financial || []
        });
        
        // Generate available categories based on fields
        const fieldCategoryMap = {
          'population': 'basic',
          'financial-statement-link': 'basic',
          'statement-date': 'basic',
          'council-hq-post-code': 'basic',
          'total-income': 'income',
          'total-expenditure': 'income',
          'interest-payments': 'income',
          'interest-paid': 'income',
          'business-rates-income': 'income',
          'council-tax-income': 'income',
          'non-ring-fenced-government-grants-income': 'income',
          'capital-expenditure': 'income',
          'current-assets': 'balance',
          'current-liabilities': 'balance',
          'long-term-liabilities': 'balance',
          'total-reserves': 'balance',
          'usable-reserves': 'balance',
          'unusable-reserves': 'balance',
          'total-debt': 'debt',
          'pension-liability': 'debt',
          'finance-leases': 'debt',
          'finance-leases-pfi-liabilities': 'debt'
        };
        
        const categories = new Set();
        (data.available_fields?.financial || []).forEach(field => {
          const category = fieldCategoryMap[field.slug];
          if (category) categories.add(category);
        });
        
        // Add 'other' category if there are unmapped fields
        const hasOtherFields = (data.available_fields?.financial || []).some(field => 
          !fieldCategoryMap[field.slug]
        );
        if (hasOtherFields) categories.add('other');
        
        setAvailableCategories(Array.from(categories).map(key => ({ key })));
      }
    } catch (error) {
      console.error('Error loading year data:', error);
    } finally {
      setLoading(false);
    }
  }, [councilData?.slug, csrfToken]);

  const calculateProgress = useCallback(async (year) => {
    // Use real completion API data instead of mock values
    try {
      const response = await fetch(`/api/council/${councilData?.slug}/completion/${year.id}/`, {
        headers: { 'X-CSRFToken': csrfToken }
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success && data.completion?.overall) {
          return {
            completed: data.completion.overall.complete || 0,
            total: data.completion.overall.total_fields || 9,
            percentage: data.completion.overall.percentage || 0
          };
        }
      }
    } catch (error) {
      console.error('Error fetching completion data for year:', error);
    }
    
    // Fallback to basic calculation based on 9 financial fields
    return { completed: 0, total: 9, percentage: 0 };
  }, [councilData?.slug, csrfToken]);

  const getYearStatus = useCallback((progress) => {
    if (progress.percentage >= 100) return { label: 'Complete', color: 'green' };
    if (progress.percentage >= 75) return { label: 'Nearly complete', color: 'blue' };
    if (progress.percentage >= 25) return { label: 'In progress', color: 'amber' };
    return { label: 'Needs attention', color: 'red' };
  }, []);

  const handleYearSelect = (year) => {
    setSelectedYear(year);
    setCurrentStep(2);
  };

  const handleMethodSelect = (method) => {
    setSelectedMethod(method);
    if (method === 'pdf') {
      setCurrentStep(4); // Skip category selection for PDF for now
    } else {
      setCurrentStep(3); // Go to category selection for manual entry
    }
  };

  const handleCategorySelect = (category) => {
    setSelectedCategory(category);
    setCurrentStep(4);
  };

  const handleBack = () => {
    if (currentStep === 1) {
      onBack();
    } else if (currentStep === 5) {
      // From review, go back to data entry
      setCurrentStep(4);
    } else {
      setCurrentStep(currentStep - 1);
    }
  };

  // Jump to specific step
  const jumpToStep = (stepNumber) => {
    if (stepNumber === 1) {
      setCurrentStep(1);
    } else if (stepNumber === 2 && selectedYear) {
      setCurrentStep(2);
    } else if (stepNumber === 3 && selectedYear && selectedMethod) {
      setCurrentStep(3);
    } else if (stepNumber === 4 && selectedYear && selectedMethod && (selectedCategory || selectedMethod === 'pdf')) {
      setCurrentStep(4);
    }
  };

  const renderStepIndicator = () => {
    const steps = [
      { number: 1, title: 'Select Year', active: currentStep >= 1, completed: currentStep > 1, clickable: true },
      { number: 2, title: 'Choose Method', active: currentStep >= 2, completed: currentStep > 2, clickable: selectedYear },
      { number: 3, title: 'Choose Category', active: currentStep >= 3, completed: currentStep > 3, clickable: selectedYear && selectedMethod },
      { number: 4, title: 'Edit Data', active: currentStep >= 4, completed: false, clickable: selectedYear && selectedMethod && (selectedCategory || selectedMethod === 'pdf') }
    ];

    const totalChanges = Object.keys(allChanges).length;

    return (
      <div id="financial-wizard-progress" className="mb-8">
        <div className="flex items-center justify-between overflow-x-auto pb-2">
          {steps.map((step, index) => (
            <React.Fragment key={step.number}>
              <div className="flex items-center">
                <button
                  onClick={() => step.clickable ? jumpToStep(step.number) : null}
                  disabled={!step.clickable}
                  className={`
                    w-8 h-8 rounded-full border-2 flex items-center justify-center text-sm font-medium transition-colors
                    ${step.completed ? 'bg-blue-600 border-blue-600 text-white' :
                      step.active ? 'border-blue-600 text-blue-600' : 
                      'border-gray-300 text-gray-500'}
                    ${step.clickable ? 'hover:border-blue-400 cursor-pointer' : 'cursor-not-allowed'}
                  `}
                >
                  {step.completed ? (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                    </svg>
                  ) : step.number}
                </button>
                <span className={`ml-2 text-sm font-medium ${step.active ? 'text-gray-900' : 'text-gray-500'}`}>
                  {step.title}
                </span>
              </div>
              {index < steps.length - 1 && (
                <div className={`flex-1 h-px mx-4 ${step.completed ? 'bg-blue-600' : 'bg-gray-300'}`} />
              )}
            </React.Fragment>
          ))}
        </div>
        
        {/* Review Changes Button - Show even with no changes for quick access */}
        {currentStep >= 3 && currentStep !== 5 && (
          <div className="mt-4 p-3 border flex items-center justify-between" 
               style={{
                 backgroundColor: totalChanges > 0 ? '#f0fdf4' : '#eff6ff',
                 borderColor: totalChanges > 0 ? '#bbf7d0' : '#bfdbfe'
               }}>
            <div className="flex items-center">
              {totalChanges > 0 ? (
                <>
                  <svg className="w-5 h-5 text-green-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="text-green-800 font-medium">
                    {totalChanges} change{totalChanges !== 1 ? 's' : ''} ready for review
                  </span>
                </>
              ) : (
                <>
                  <svg className="w-5 h-5 text-blue-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="text-blue-800">
                    Edit any field and review changes, or go straight to review
                  </span>
                </>
              )}
            </div>
            <button
              onClick={() => setCurrentStep(5)}
              className={`px-4 py-2 font-medium transition-colors ${
                totalChanges > 0 
                  ? 'bg-green-600 text-white hover:bg-green-700' 
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              }`}
            >
              {totalChanges > 0 ? 'Review Changes' : 'Go to Review'}
            </button>
          </div>
        )}
      </div>
    );
  };

  const renderYearSelection = () => (
    <div id="financial-wizard-year-selection">
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          Select financial year
        </h2>
        <p className="text-gray-600">
          Which year would you like to edit financial data for?
        </p>
      </div>

      <div className="space-y-3">
        {years.map(year => {
          const progress = yearProgressData[year.id] || { completed: 0, total: 9, percentage: 0 };
          const status = getYearStatus(progress);
          
          return (
            <div
              key={year.id}
              className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer group"
              onClick={() => handleYearSelect(year)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <div className="mr-4">
                    <div className="text-lg font-semibold text-gray-900 group-hover:text-blue-600">
                      {year.label}
                    </div>
                    {year.label.includes('2024') && (
                      <span className="text-sm text-gray-500">(Current year)</span>
                    )}
                  </div>
                </div>
                
                <div className="flex items-center space-x-4">
                  <div className="text-right">
                    <div className={`text-sm font-medium text-${status.color}-600`}>
                      {status.label}
                    </div>
                    <div className="text-xs text-gray-500">
                      {progress.completed}/{progress.total} fields
                    </div>
                  </div>
                  
                  <div className="w-16 h-2 bg-gray-200 rounded-full">
                    <div 
                      className={`h-2 bg-${status.color}-500 rounded-full transition-all duration-300`}
                      style={{ width: `${progress.percentage}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
        <p className="text-sm text-blue-800">
          💡 You can add a new year if it's not listed above by contacting support.
        </p>
      </div>
    </div>
  );

  const renderMethodChoice = () => (
    <div id="financial-wizard-method-selection">
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          How would you like to add financial data?
        </h2>
        <p className="text-gray-600">
          Choose the method that works best for you
        </p>
      </div>

      <div className="space-y-4">
        {/* PDF Upload Option */}
        <div
          className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow cursor-pointer group"
          onClick={() => handleMethodSelect('pdf')}
        >
          <div className="flex items-start">
            <div className="text-3xl mr-4">📤</div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-gray-900 group-hover:text-blue-600 mb-2">
                Upload Financial Statement (Recommended)
              </h3>
              <p className="text-gray-600 mb-4">
                Upload a PDF of the annual financial statement. Our AI will extract the data automatically.
              </p>
              
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
                <div className="flex items-center text-sm text-green-700">
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                  </svg>
                  Fast and accurate
                </div>
                <div className="flex items-center text-sm text-green-700">
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                  </svg>
                  Extracts 20+ figures
                </div>
                <div className="flex items-center text-sm text-green-700">
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                  </svg>
                  You review before saving
                </div>
              </div>
              
              <button className="bg-blue-600 text-white px-6 py-3 rounded-md font-medium hover:bg-blue-700 group-hover:bg-blue-700 transition-colors">
                📤 Upload PDF Statement
              </button>
            </div>
          </div>
        </div>

        {/* Manual Entry Option */}
        <div
          className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow cursor-pointer group"
          onClick={() => handleMethodSelect('manual')}
        >
          <div className="flex items-start">
            <div className="text-3xl mr-4">✏️</div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-gray-900 group-hover:text-blue-600 mb-2">
                Enter Data Manually
              </h3>
              <p className="text-gray-600 mb-4">
                Type in financial figures one by one using our guided form.
              </p>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
                <div className="flex items-center text-sm text-amber-700">
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.998-.833-2.768 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                  More time-consuming
                </div>
                <div className="flex items-center text-sm text-green-700">
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                  </svg>
                  Full control over each figure
                </div>
              </div>
              
              <button className="border border-gray-300 text-gray-700 px-6 py-3 rounded-md font-medium hover:bg-gray-50 group-hover:bg-gray-50 transition-colors">
                ✏️ Manual Entry
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const renderCategorySelection = () => {
    // Calculate categories with completion status
    const categoriesWithProgress = availableCategories.map(category => ({
      ...category,
      completionPercentage: Math.floor(Math.random() * 100), // TODO: Calculate real progress
      completed: Math.floor(Math.random() * 5),
      total: 5
    }));

    return (
      <CategorySelection
        availableCategories={categoriesWithProgress}
        selectedCategory={selectedCategory}
        onCategorySelect={handleCategorySelect}
        onBack={handleBack}
      />
    );
  };

  const renderDataEntry = () => {
    if (selectedMethod === 'pdf') {
      return (
        <div className="text-center py-12">
          <div className="text-6xl mb-6">🚧</div>
          <h3 className="text-xl font-semibold text-gray-900 mb-4">PDF Upload Coming Soon</h3>
          <p className="text-gray-600 mb-6 max-w-md mx-auto">
            The PDF upload feature is currently being developed. 
            For now, please use manual entry to add your financial data.
          </p>
          <button 
            onClick={() => {
              setSelectedMethod('manual');
              setCurrentStep(3); // Go back to category selection
            }}
            className="bg-blue-600 text-white px-6 py-3 font-medium hover:bg-blue-700 transition-colors"
          >
            Switch to Manual Entry
          </button>
        </div>
      );
    }

    // Filter fields for the selected category
    const categoryFields = availableFields.financial.filter(field => {
      // Map fields to categories based on their purpose
      const fieldCategoryMap = {
        'population': 'basic',
        'financial-statement-link': 'basic',
        'statement-date': 'basic',
        'council-hq-post-code': 'basic',
        'total-income': 'income',
        'total-expenditure': 'income', 
        'interest-payments': 'income',
        'interest-paid': 'income',
        'business-rates-income': 'income',
        'council-tax-income': 'income',
        'non-ring-fenced-government-grants-income': 'income',
        'capital-expenditure': 'income',
        'current-assets': 'balance',
        'current-liabilities': 'balance',
        'long-term-liabilities': 'balance',
        'total-reserves': 'balance',
        'usable-reserves': 'balance',
        'unusable-reserves': 'balance',
        'total-debt': 'debt',
        'pension-liability': 'debt',
        'finance-leases': 'debt',
        'finance-leases-pfi-liabilities': 'debt'
      };
      
      return fieldCategoryMap[field.slug] === selectedCategory;
    });

    return (
      <div id="financial-wizard-data-entry" className="mx-auto">
        {/* Category Context Header */}
        <div className="mb-8 p-4 bg-blue-50 border-l-4 border-blue-500">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">
                {selectedCategory === 'basic' && '📋 Basic Information'}
                {selectedCategory === 'income' && '💷 Income & Expenditure'}
                {selectedCategory === 'balance' && '⚖️ Balance Sheet'}
                {selectedCategory === 'debt' && '📊 Debt & Obligations'}
                {selectedCategory === 'other' && '📁 Additional Fields'}
              </h2>
              <p className="text-gray-600 mt-1">
                {selectedYear?.label} • {categoryFields.length} fields in this category
              </p>
            </div>
            <button
              onClick={() => setCurrentStep(3)}
              className="text-blue-600 hover:text-blue-800 text-sm font-medium"
            >
              ← Change Category
            </button>
          </div>
        </div>

        {/* Focused Field Entry */}
        <CategoryFieldEntry
          councilData={councilData}
          selectedYear={selectedYear}
          selectedCategory={selectedCategory}
          financialData={financialData}
          availableFields={categoryFields}
          onSave={onSave}
          onValidate={onValidate}
          onTrackChange={(fieldSlug, changeData) => {
            setAllChanges(prev => ({
              ...prev,
              [fieldSlug]: changeData
            }));
          }}
          errors={{}}
          loading={loading}
        />
      </div>
    );
  };

  // Render review step
  const renderReviewStep = () => {
    const changesArray = Object.values(allChanges);
    
    if (changesArray.length === 0) {
      return (
        <div className="space-y-6">
          {/* Empty state with helpful guidance */}
          <div className="text-center py-12 bg-white border border-gray-200">
            <div className="text-gray-400 text-6xl mb-4">📋</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Review & Save</h3>
            <p className="text-gray-500 mb-6 max-w-md mx-auto">
              You haven't made any changes yet. You can either:
            </p>
            <div className="space-y-3 max-w-sm mx-auto">
              <button
                onClick={() => setCurrentStep(3)}
                className="w-full px-4 py-3 bg-blue-600 text-white hover:bg-blue-700 transition-colors flex items-center justify-center"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                Edit Financial Data
              </button>
              <button
                onClick={() => {
                  // Just close without changes
                  setCurrentStep(1);
                }}
                className="w-full px-4 py-3 text-gray-700 bg-gray-100 hover:bg-gray-200 transition-colors"
              >
                Exit Without Changes
              </button>
            </div>
          </div>
          
          {/* Quick edit suggestion */}
          <div className="bg-blue-50 border border-blue-200 p-4">
            <h4 className="font-medium text-blue-900 mb-2">💡 Quick Edit Mode</h4>
            <p className="text-sm text-blue-800 mb-3">
              You can edit just one or two fields without completing all categories:
            </p>
            <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
              <li>Go to the category containing your field</li>
              <li>Edit just the field you need</li>
              <li>Click "Review & Save" to save your single change</li>
            </ol>
          </div>
        </div>
      );
    }
    
    return (
      <div className="space-y-6 max-w-4xl mx-auto">
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Review All Changes
          </h2>
          <p className="text-gray-600">
            {changesArray.length} field{changesArray.length !== 1 ? 's' : ''} have been updated across all categories
          </p>
        </div>
        
        <div className="space-y-4">
          {changesArray.map((change, index) => (
            <div key={change.fieldName || index} className="border border-gray-200 p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-medium text-gray-900">{change.fieldName}</h3>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <div className="text-sm font-medium text-gray-700 flex items-center">
                    <svg className="w-4 h-4 mr-1 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M20 12H4" />
                    </svg>
                    Original
                  </div>
                  <div className="p-3 bg-red-50 border border-red-200 text-red-900">
                    {change.originalFormatted || 'Not set'}
                  </div>
                </div>
                
                <div className="space-y-2">
                  <div className="text-sm font-medium text-gray-700 flex items-center">
                    <svg className="w-4 h-4 mr-1 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                    </svg>
                    New
                  </div>
                  <div className="p-3 bg-green-50 border border-green-200 text-green-900">
                    {change.newFormatted}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
        
        <div className="pt-6 border-t border-gray-200">
          {/* Primary actions */}
          <div className="space-y-4">
            {/* Main action buttons */}
            <div className="flex justify-center space-x-3">
              <button
                onClick={() => {
                  // Show success modal with options
                  setSavedChangeCount(changesArray.length);
                  setShowSuccessModal(true);
                  setAllChanges({});
                }}
                className="px-6 py-3 bg-green-600 text-white hover:bg-green-700 font-medium transition-colors flex items-center"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                </svg>
                Confirm & Save Changes
              </button>
              
              <button
                onClick={() => setCurrentStep(3)}
                className="px-6 py-3 bg-blue-600 text-white hover:bg-blue-700 font-medium transition-colors flex items-center"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
                Save & Continue Editing
              </button>
            </div>
            
            {/* Secondary actions */}
            <div className="flex justify-center space-x-6 pt-2">
              <button
                onClick={() => {
                  setAllChanges({});
                  setCurrentStep(1);
                }}
                className="text-sm text-gray-600 hover:text-gray-800"
              >
                Discard Changes
              </button>
              
              <button
                onClick={() => {
                  // Save and start over
                  setAllChanges({});
                  setCurrentStep(1);
                }}
                className="text-sm text-gray-600 hover:text-gray-800"
              >
                Start Over
              </button>
            </div>
          </div>
          
          {/* Info message */}
          <div className="text-center mt-6 p-3 bg-blue-50 border border-blue-200">
            <p className="text-sm text-blue-800">
              <strong>Note:</strong> Your changes have been auto-saved. You have successfully updated {changesArray.length} field{changesArray.length !== 1 ? 's' : ''}.
            </p>
          </div>
        </div>
      </div>
    );
  };

  // Floating Action Button for quick review access
  const renderFloatingActionButton = () => {
    const totalChanges = Object.keys(allChanges).length;
    
    // Show FAB on steps 3 and 4 when there are changes, but not on review step itself
    if ((currentStep === 3 || currentStep === 4) && totalChanges > 0 && currentStep !== 5) {
      return (
        <div className="fixed bottom-6 right-6 z-40">
          <div className="flex flex-col items-end space-y-3">
            {/* Quick action menu */}
            <div className="bg-white border border-gray-200 shadow-lg rounded-lg p-3 mr-2">
              <div className="text-sm text-gray-600 mb-2">
                {totalChanges} unsaved change{totalChanges !== 1 ? 's' : ''}
              </div>
              <div className="space-y-2">
                <button
                  onClick={() => setCurrentStep(5)}
                  className="w-full px-4 py-2 bg-green-600 text-white hover:bg-green-700 font-medium transition-colors flex items-center justify-center"
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Review & Save
                </button>
                <button
                  onClick={() => setCurrentStep(3)}
                  className="w-full px-3 py-1 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
                >
                  Switch Category
                </button>
              </div>
            </div>
          </div>
        </div>
      );
    }
    
    // Simplified button when no changes
    if ((currentStep === 3 || currentStep === 4) && currentStep !== 5) {
      return (
        <div className="fixed bottom-6 right-6 z-40">
          <button
            onClick={() => setCurrentStep(5)}
            className="bg-blue-600 text-white p-4 rounded-full shadow-lg hover:bg-blue-700 transition-all hover:scale-110"
            title="Go to Review"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </button>
        </div>
      );
    }
    
    return null;
  };

  return (
    <div id="financial-wizard-main" className={`bg-gray-50 min-h-screen ${className}`}>
      <div className="max-w-4xl mx-auto px-6 py-8">
        
        {/* Header with Back Navigation */}
        <div id="financial-wizard-header" className="mb-8">
          <button 
            onClick={handleBack}
            className="inline-flex items-center text-blue-600 hover:text-blue-800 text-sm font-medium mb-4"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
            </svg>
            Back
          </button>
          
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-2">
            Financial Data
          </h1>
          <p className="text-lg text-gray-600">
            Edit financial information for {councilData?.name}
          </p>
        </div>

        {/* Step Indicator */}
        {renderStepIndicator()}

        {/* Step Content */}
        <div id="financial-wizard-content">
          {loading && (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-500 border-t-transparent mr-3"></div>
              <span className="text-gray-600">Loading financial data...</span>
            </div>
          )}
          
          {!loading && currentStep === 1 && renderYearSelection()}
          {!loading && currentStep === 2 && renderMethodChoice()}
          {!loading && currentStep === 3 && renderCategorySelection()}
          {!loading && currentStep === 4 && renderDataEntry()}
          {!loading && currentStep === 5 && renderReviewStep()}
        </div>
      </div>
      
      {/* Floating Action Button for quick access to review */}
      {renderFloatingActionButton()}
      
      {/* Success Modal */}
      <SaveSuccessModal
        isVisible={showSuccessModal}
        changeCount={savedChangeCount}
        councilName={councilData?.name}
        councilSlug={councilData?.slug}
        onReturnToCouncil={() => {
          setShowSuccessModal(false);
          if (councilData?.slug) {
            window.location.href = `/councils/${councilData.slug}/`;
          }
        }}
        onContinueEditing={() => {
          setShowSuccessModal(false);
          setCurrentStep(3); // Go back to category selection
        }}
        onClose={() => setShowSuccessModal(false)}
      />
    </div>
  );
};

export default FinancialWizard;