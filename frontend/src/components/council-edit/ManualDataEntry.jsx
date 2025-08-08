import React, { useState, useCallback } from 'react';
import FieldEditor from './FieldEditor';

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

  // Group fields by category for better organization
  const fieldGroups = {
    basic: {
      title: 'Basic Information',
      description: 'Statement links and population data',
      fields: availableFields.filter(field => 
        ['population', 'financial-statement-link', 'statement-date'].includes(field.slug)
      )
    },
    income: {
      title: 'Income & Expenditure',
      description: 'Revenue and spending figures',
      fields: availableFields.filter(field => 
        ['total-income', 'total-expenditure', 'interest-payments', 'capital-expenditure'].includes(field.slug)
      )
    },
    balance: {
      title: 'Balance Sheet',
      description: 'Assets and liabilities',
      fields: availableFields.filter(field => 
        ['current-assets', 'current-liabilities', 'long-term-liabilities', 'total-reserves'].includes(field.slug)
      )
    },
    debt: {
      title: 'Debt & Pensions',
      description: 'Additional financial metrics',
      fields: availableFields.filter(field => 
        ['total-debt', 'pension-liability', 'finance-leases'].includes(field.slug)
      )
    },
    other: {
      title: 'Other Fields',
      description: 'Additional financial data',
      fields: availableFields.filter(field => 
        !['population', 'financial-statement-link', 'statement-date',
          'total-income', 'total-expenditure', 'interest-payments', 'capital-expenditure',
          'current-assets', 'current-liabilities', 'long-term-liabilities', 'total-reserves',
          'total-debt', 'pension-liability', 'finance-leases'].includes(field.slug)
      )
    }
  };

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

  const calculateProgress = () => {
    const completedFields = availableFields.filter(field => 
      financialData[field.slug] && financialData[field.slug].toString().trim().length > 0
    ).length;
    return {
      completed: completedFields,
      total: availableFields.length,
      percentage: availableFields.length > 0 ? Math.round((completedFields / availableFields.length) * 100) : 0
    };
  };

  const progress = calculateProgress();

  const renderFieldGroup = (group, groupKey) => {
    if (!group.fields.length) return null;

    return (
      <div key={groupKey} id={`manual-entry-group-${groupKey}`} className="mb-8">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-gray-900">{group.title}</h3>
          <p className="text-sm text-gray-600">{group.description}</p>
        </div>
        
        <div className="space-y-4">
          {group.fields.map(field => (
            <div key={field.slug} className="bg-gray-50 rounded-lg p-4">
              <FieldEditor
                field={field}
                value={getFieldValue(field.slug)}
                onSave={(value) => handleSave(field.slug, value)}
                onValidate={onValidate}
                error={errors[field.slug]}
                disabled={saving}
                showHelp={true}
                showPopulationContext={field.slug === 'population'}
                yearContext={field.slug === 'population' ? selectedYear?.label : null}
              />
            </div>
          ))}
        </div>
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

        {/* Progress Bar */}
        <div id="manual-entry-progress" className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">
              Progress: {progress.completed} of {progress.total} fields complete
            </span>
            <span className="text-sm text-gray-500">
              {progress.percentage}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress.percentage}%` }}
            />
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