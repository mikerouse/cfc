import React, { useState, useCallback, useEffect } from 'react';
import ManualDataEntry from './ManualDataEntry';

/**
 * GOV.UK-style wizard for financial data editing
 * Step 1: Year Selection
 * Step 2: Method Choice (PDF Upload vs Manual Entry)  
 * Step 3a: PDF Upload & Processing
 * Step 3b: Manual Data Entry
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
  const [loading, setLoading] = useState(false);
  const [generalData, setGeneralData] = useState({});
  const [financialData, setFinancialData] = useState({});
  const [availableFields, setAvailableFields] = useState({ general: [], financial: [] });

  // Load data when year is selected
  useEffect(() => {
    if (selectedYear && currentStep >= 2) {
      loadYearData(selectedYear);
    }
  }, [selectedYear]);

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
      }
    } catch (error) {
      console.error('Error loading year data:', error);
    } finally {
      setLoading(false);
    }
  }, [councilData?.slug, csrfToken]);

  const calculateProgress = useCallback((year) => {
    // This would calculate based on actual data for the year
    // For now, return mock progress
    const completed = Math.floor(Math.random() * 15) + 5;
    const total = 20;
    return { completed, total, percentage: Math.round((completed / total) * 100) };
  }, []);

  const getYearStatus = useCallback((year) => {
    const progress = calculateProgress(year);
    if (progress.percentage >= 100) return { label: 'Complete', color: 'green' };
    if (progress.percentage >= 75) return { label: 'Nearly complete', color: 'blue' };
    if (progress.percentage >= 25) return { label: 'In progress', color: 'amber' };
    return { label: 'Needs attention', color: 'red' };
  }, [calculateProgress]);

  const handleYearSelect = (year) => {
    setSelectedYear(year);
    setCurrentStep(2);
  };

  const handleMethodSelect = (method) => {
    setSelectedMethod(method);
    setCurrentStep(3);
  };

  const handleBack = () => {
    if (currentStep === 1) {
      onBack();
    } else {
      setCurrentStep(currentStep - 1);
    }
  };

  const renderStepIndicator = () => {
    const steps = [
      { number: 1, title: 'Select Year', active: currentStep >= 1, completed: currentStep > 1 },
      { number: 2, title: 'Choose Method', active: currentStep >= 2, completed: currentStep > 2 },
      { number: 3, title: 'Edit Data', active: currentStep >= 3, completed: false }
    ];

    return (
      <div id="financial-wizard-progress" className="mb-8">
        <div className="flex items-center justify-between">
          {steps.map((step, index) => (
            <React.Fragment key={step.number}>
              <div className="flex items-center">
                <div className={`
                  w-8 h-8 rounded-full border-2 flex items-center justify-center text-sm font-medium
                  ${step.completed ? 'bg-blue-600 border-blue-600 text-white' :
                    step.active ? 'border-blue-600 text-blue-600' : 
                    'border-gray-300 text-gray-500'}
                `}>
                  {step.completed ? (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                    </svg>
                  ) : step.number}
                </div>
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
          const progress = calculateProgress(year);
          const status = getYearStatus(year);
          
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

  const renderDataEntry = () => (
    <div id="financial-wizard-data-entry">
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          {selectedMethod === 'pdf' ? 'Upload Financial Statement' : 'Manual Data Entry'}
        </h2>
        <p className="text-gray-600">
          {selectedYear?.label} financial data
        </p>
      </div>

      {selectedMethod === 'pdf' ? (
        <div className="text-center py-8">
          <div className="text-6xl mb-4">🚧</div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">PDF Upload Coming Soon</h3>
          <p className="text-gray-600 mb-4">
            The PDF upload feature is currently being developed. 
            For now, please use manual entry.
          </p>
          <button 
            onClick={() => handleMethodSelect('manual')}
            className="bg-blue-600 text-white px-6 py-3 rounded-md font-medium hover:bg-blue-700"
          >
            Switch to Manual Entry
          </button>
        </div>
      ) : (
        <ManualDataEntry
          councilData={councilData}
          selectedYear={selectedYear}
          financialData={financialData}
          availableFields={availableFields.financial}
          onSave={onSave}
          onValidate={onValidate}
          errors={{}}
          loading={loading}
        />
      )}
    </div>
  );

  return (
    <div id="financial-wizard-main" className={`bg-white ${className}`}>
      <div className="max-w-4xl mx-auto px-4 py-6 sm:px-6 sm:py-8">
        
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
          {!loading && currentStep === 3 && renderDataEntry()}
        </div>
      </div>
    </div>
  );
};

export default FinancialWizard;