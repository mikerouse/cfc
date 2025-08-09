import React, { useState, useCallback, useMemo } from 'react';
import SimpleFieldEditor from './SimpleFieldEditor';

/**
 * Manual data entry component for financial data
 * Grouped fields with progress tracking and population handling
 */
const ManualDataEntry = ({
  councilData,
  selectedYear,
  financialData = {},
  availableFields = [],
  onSave,
  onValidate,
  errors = {},
  loading = false,
  className = ""
}) => {
  const [saving, setSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [expandedSections, setExpandedSections] = useState({
    basic: true,
    income: true,
    balance: false,
    debt: false,
    other: false
  });

  // Enhanced field grouping with priority and required field identification
  const fieldGroups = useMemo(() => {
    // Define required fields for smart prioritization
    const requiredFieldSlugs = [
      'population',
      'total-income',
      'total-expenditure',
      'current-liabilities',
      'long-term-liabilities'
    ];

    // Mark fields as required if they match our priority list
    const enhancedFields = availableFields.map(field => ({
      ...field,
      required: requiredFieldSlugs.includes(field.slug)
    }));

    return {
      basic: {
        title: '📋 Basic Information',
        description: 'Essential council data and document references',
        priority: 1,
        icon: '📋',
        fields: enhancedFields.filter(field => 
          ['population', 'financial-statement-link', 'statement-date', 'council-hq-post-code'].includes(field.slug)
        )
      },
      income: {
        title: '💷 Income & Expenditure',
        description: 'Revenue, spending, and operational finances from the Income & Expenditure Statement',
        priority: 2,
        icon: '💷',
        fields: enhancedFields.filter(field => 
          ['total-income', 'total-expenditure', 'interest-payments', 'interest-paid', 
           'capital-expenditure', 'business-rates-income', 'council-tax-income',
           'non-ring-fenced-government-grants-income'].includes(field.slug)
        )
      },
      balance: {
        title: '⚖️ Balance Sheet',
        description: 'Assets, liabilities, and reserves from the Balance Sheet',
        priority: 3,
        icon: '⚖️',
        fields: enhancedFields.filter(field => 
          ['current-assets', 'current-liabilities', 'long-term-liabilities', 
           'total-reserves', 'usable-reserves', 'unusable-reserves'].includes(field.slug)
        )
      },
      debt: {
        title: '📊 Debt & Obligations',
        description: 'Borrowing, pensions, and long-term financial obligations',
        priority: 4,
        icon: '📊',
        fields: enhancedFields.filter(field => 
          ['total-debt', 'pension-liability', 'finance-leases', 
           'finance-leases-pfi-liabilities'].includes(field.slug)
        )
      },
      other: {
        title: '📁 Additional Fields',
        description: 'Other financial and council information',
        priority: 5,
        icon: '📁',
        fields: enhancedFields.filter(field => {
          const categorizedSlugs = [
            'population', 'financial-statement-link', 'statement-date', 'council-hq-post-code',
            'total-income', 'total-expenditure', 'interest-payments', 'interest-paid',
            'capital-expenditure', 'business-rates-income', 'council-tax-income',
            'non-ring-fenced-government-grants-income',
            'current-assets', 'current-liabilities', 'long-term-liabilities',
            'total-reserves', 'usable-reserves', 'unusable-reserves',
            'total-debt', 'pension-liability', 'finance-leases', 'finance-leases-pfi-liabilities'
          ];
          return !categorizedSlugs.includes(field.slug);
        })
      }
    };
  }, [availableFields]);

  const handleSave = useCallback(async (fieldSlug, value) => {
    setSaving(true);
    setSuccessMessage('');
    
    try {
      const result = await onSave(fieldSlug, value);
      if (result?.success) {
        setSuccessMessage(`Field updated successfully! +${result.points || 3} points`);
        setTimeout(() => setSuccessMessage(''), 3000);
      }
      return result;
    } catch (error) {
      console.error('Save error:', error);
      return { success: false, error: error.message };
    } finally {
      setSaving(false);
    }
  }, [onSave]);

  const getFieldValue = useCallback((fieldSlug) => {
    return financialData[fieldSlug] || '';
  }, [financialData]);

  // Enhanced progress calculation with section details
  const calculateProgress = useCallback(() => {
    const completedFields = availableFields.filter(field => 
      financialData[field.slug] && financialData[field.slug].toString().trim().length > 0
    );
    
    // Calculate section-wise progress
    const sectionsProgress = {};
    Object.entries(fieldGroups).forEach(([key, group]) => {
      const sectionCompleted = group.fields.filter(field => 
        financialData[field.slug] && financialData[field.slug].toString().trim().length > 0
      ).length;
      sectionsProgress[key] = {
        completed: sectionCompleted,
        total: group.fields.length,
        percentage: group.fields.length > 0 ? Math.round((sectionCompleted / group.fields.length) * 100) : 0
      };
    });

    // Calculate required fields progress
    const requiredFields = availableFields.filter(field => field.required);
    const completedRequired = requiredFields.filter(field => 
      financialData[field.slug] && financialData[field.slug].toString().trim().length > 0
    ).length;

    return {
      completed: completedFields.length,
      total: availableFields.length,
      percentage: availableFields.length > 0 ? Math.round((completedFields.length / availableFields.length) * 100) : 0,
      required: requiredFields.length,
      requiredCompleted: completedRequired,
      sectionsProgress
    };
  }, [availableFields, financialData, fieldGroups]);

  // Toggle section expansion
  const toggleSection = useCallback((sectionKey) => {
    setExpandedSections(prev => ({
      ...prev,
      [sectionKey]: !prev[sectionKey]
    }));
  }, []);

  const progress = calculateProgress();

  const renderFieldGroup = (group, groupKey) => {
    if (!group.fields.length) return null;

    const isExpanded = expandedSections[groupKey];
    const sectionProgress = progress.sectionsProgress?.[groupKey] || {};
    const hasRequiredFields = group.fields.some(field => field.required);
    const allRequiredComplete = group.fields.filter(f => f.required).every(field => 
      financialData[field.slug] && financialData[field.slug].toString().trim().length > 0
    );

    return (
      <div key={groupKey} id={`manual-entry-group-${groupKey}`} className="govuk-form-group mb-8">
        {/* GOV.UK-style Section Header */}
        <div className="govuk-section-break govuk-section-break--l govuk-section-break--visible" />
        
        <details className="govuk-details" data-module="govuk-details" open={isExpanded}>
          <summary className="govuk-details__summary" onClick={(e) => { e.preventDefault(); toggleSection(groupKey); }}>
            <span className="govuk-details__summary-text">
              <h3 className="govuk-heading-m mb-0 flex items-center">
                <span className="text-2xl mr-3">{group.icon}</span>
                {group.title.replace(group.icon, '').trim()}
                {hasRequiredFields && (
                  <span className={`ml-3 text-sm px-2 py-1 border ${
                    allRequiredComplete 
                      ? 'border-green-600 bg-green-50 text-green-800' 
                      : 'border-orange-600 bg-orange-50 text-orange-800'
                  }`}>
                    {allRequiredComplete ? '✓ Required complete' : 'Required fields'}
                  </span>
                )}
              </h3>
            </span>
          </summary>
          
          <div className="govuk-details__text">
            <p className="govuk-hint">{group.description}</p>
            
            {/* Section Progress Indicator */}
            <div className="mb-4 p-4 border-l-4 border-l-blue-500 bg-blue-50">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-gray-900">
                  Progress: {sectionProgress.completed || 0} of {sectionProgress.total || 0} fields
                </span>
                <span className="text-sm text-gray-600">
                  {sectionProgress.percentage || 0}%
                </span>
              </div>
              <div className="w-full bg-gray-300 h-2 border">
                <div 
                  className="bg-blue-600 h-2 transition-all duration-300"
                  style={{ width: `${sectionProgress.percentage || 0}%` }}
                />
              </div>
            </div>
        
            {/* Fields - GOV.UK Form Groups */}
            <div className="space-y-6">
              {group.fields.map(field => (
                <div key={field.slug} className="govuk-form-group">
                  <SimpleFieldEditor
                    field={field}
                    value={getFieldValue(field.slug)}
                    onSave={(value) => handleSave(field.slug, value)}
                    onValidate={onValidate}
                    error={errors[field.slug]}
                    disabled={saving}
                    showHelp={true}
                    showPopulationContext={field.slug === 'population'}
                    yearContext={field.slug === 'population' ? selectedYear?.label : null}
                    allFieldValues={financialData}
                  />
                </div>
              ))}
            </div>
            
            {/* Section-specific help - GOV.UK Inset Text */}
            {groupKey === 'income' && (
              <div className="govuk-inset-text">
                <strong>💡 Reading Financial Statements:</strong> Find these figures in the Comprehensive Income and Expenditure Statement.
                Look for the "Net Cost of Services" section and the financing/investment sections.
              </div>
            )}
            {groupKey === 'balance' && (
              <div className="govuk-inset-text">
                <strong>💡 Reading Financial Statements:</strong> These values come from the Balance Sheet. 
                Use Group figures if available (not Entity-only).
              </div>
            )}
          </div>
        </details>
      </div>
    );
  };

  return (
    <div id="manual-data-entry" className={`bg-white ${className}`}>
      <div className="max-w-4xl mx-auto px-4 py-6 sm:px-6 sm:py-8">
        
        {/* Header */}
        <div id="manual-entry-header" className="mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Manual Data Entry
          </h2>
          <p className="text-gray-600">
            Enter financial data for {selectedYear?.label} manually
          </p>
        </div>

        {/* Enhanced Progress Summary - GOV.UK Style */}
        <div id="manual-entry-progress" className="govuk-form-group mb-8 p-6 border-l-4 border-l-blue-600 bg-gray-50">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="govuk-label govuk-label--s text-lg font-semibold text-gray-900">Overall Progress</h3>
              <p className="govuk-hint text-gray-600">
                {progress.completed} of {progress.total} fields complete
                {progress.required > 0 && (
                  <span className="ml-2">
                    ({progress.requiredCompleted}/{progress.required} required)
                  </span>
                )}
              </p>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold text-gray-900">{progress.percentage}%</div>
              <div className="text-xs text-gray-500">Complete</div>
            </div>
          </div>
          
          {/* Main Progress Bar */}
          <div className="space-y-3">
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-gray-700">Overall</span>
                <span className="text-xs text-gray-500">{progress.percentage}%</span>
              </div>
              <div className="w-full bg-gray-300 h-2 border">
                <div 
                  className="bg-blue-600 h-2 transition-all duration-300"
                  style={{ width: `${progress.percentage}%` }}
                />
              </div>
            </div>
            
            {/* Required Fields Progress */}
            {progress.required > 0 && progress.requiredCompleted < progress.required && (
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-orange-700">Required Fields</span>
                  <span className="text-xs text-orange-600">
                    {Math.round((progress.requiredCompleted / progress.required) * 100)}%
                  </span>
                </div>
                <div className="w-full bg-gray-300 h-1 border">
                  <div 
                    className="bg-orange-600 h-1 transition-all duration-300"
                    style={{ width: `${(progress.requiredCompleted / progress.required) * 100}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Success Message */}
        {successMessage && (
          <div id="manual-entry-success" className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-center">
              <svg className="w-5 h-5 text-green-400 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-green-800">{successMessage}</p>
            </div>
          </div>
        )}

        {/* Field Groups */}
        <div id="manual-entry-field-groups">
          {Object.entries(fieldGroups).map(([groupKey, group]) => 
            renderFieldGroup(group, groupKey)
          )}
        </div>

        {/* Loading State */}
        {loading && (
          <div id="manual-entry-loading" className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-500 border-t-transparent mr-3"></div>
            <span className="text-gray-600">Loading financial data...</span>
          </div>
        )}

        {/* Auto-save Notice */}
        <div id="manual-entry-notice" className="mt-8 p-4 bg-blue-50 rounded-lg border border-blue-200">
          <h4 className="font-medium text-blue-900 mb-2">Tips for entering financial data</h4>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>• <strong>Population ({selectedYear?.label}):</strong> Historical population for accurate per capita calculations</li>
            <li>• <strong>Figures:</strong> Enter amounts in millions (e.g., enter "4.2" for £4.2m)</li>
            <li>• <strong>Balance sheet:</strong> Focus on group figures if council has subsidiaries</li>
            <li>• Changes are saved automatically as you type</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default ManualDataEntry;