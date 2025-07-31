import React, { useState, useCallback } from 'react';
import FieldEditor from './FieldEditor';

/**
 * Financial Data Editor - Temporal Financial Data
 * 
 * Handles year-specific financial information:
 * - Total debt
 * - Current liabilities  
 * - Long-term liabilities
 * - Revenue and expenditure
 * - Interest payments
 * 
 * Mobile-first design with financial field grouping
 */
const FinancialDataTab = ({ 
  financialData, 
  availableFields,
  selectedYear,
  onSave, 
  onValidate, 
  errors, 
  loading, 
  isMobile 
}) => {
  const [editingField, setEditingField] = useState(null);
  const [saving, setSaving] = useState({});

  // Icon mapping for financial field categories
  const getCategoryIcon = (category) => {
    const iconMap = {
      'balance_sheet': (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"/>
        </svg>
      ),
      'income': (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1"/>
        </svg>
      ),
      'spending': (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v2a2 2 0 002 2z"/>
        </svg>
      ),
      'calculated': (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"/>
        </svg>
      )
    };
    return iconMap[category] || iconMap['balance_sheet'];
  };

  // Group available fields by their database category
  let financialFieldGroups = {};
  
  if (availableFields && availableFields.length > 0) {
    availableFields.forEach(field => {
      const category = field.category || 'other';
      const categoryName = {
        'balance_sheet': 'Balance Sheet',
        'income': 'Income',
        'spending': 'Spending',
        'calculated': 'Calculated Fields'
      }[category] || 'Other';
      
      if (!financialFieldGroups[category]) {
        financialFieldGroups[category] = {
          name: categoryName,
          color: {
            'balance_sheet': 'blue',
            'income': 'green', 
            'spending': 'red',
            'calculated': 'purple'
          }[category] || 'gray',
          icon: getCategoryIcon(category),
          fields: []
        };
      }
      
      financialFieldGroups[category].fields.push({
        slug: field.slug,
        name: field.name,
        description: field.category === 'calculated' 
          ? `${field.description || field.name} (Automatically calculated from other fields)`
          : field.description || `${field.name} for ${selectedYear?.label || 'this year'}`,
        contentType: field.content_type,
        required: field.required,
        points: field.required ? 5 : 3,
        isCalculated: field.category === 'calculated',
        readonly: field.category === 'calculated'
      });
    });
  } else {
    // Fallback groups if no API data available
    financialFieldGroups = {
    debt: {
      name: 'Debt & Liabilities',
      color: 'red',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1"/>
        </svg>
      ),
      fields: [
        {
          slug: 'total-debt',
          name: 'Total Debt',
          description: 'Total outstanding debt including all liabilities',
          contentType: 'monetary',
          required: true,
          points: 5
        },
        {
          slug: 'current-liabilities',
          name: 'Current Liabilities',
          description: 'Short-term debts due within one year',
          contentType: 'monetary',
          required: false,
          points: 3
        },
        {
          slug: 'long-term-liabilities',
          name: 'Long-term Liabilities',
          description: 'Debts due after one year',
          contentType: 'monetary',
          required: false,
          points: 3
        }
      ]
    },
    revenue: {
      name: 'Revenue & Income',
      color: 'green',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 11.5V14m0-2.5v-6a1.5 1.5 0 113 0m-3 6a1.5 1.5 0 00-3 0v2a7.5 7.5 0 0015 0v-5a1.5 1.5 0 00-3 0m-6-3V11m0-5.5v-1a1.5 1.5 0 013 0v1m0 0V11m0-5.5a1.5 1.5 0 013 0v3"/>
        </svg>
      ),
      fields: [
        {
          slug: 'total-revenue',
          name: 'Total Revenue',
          description: 'Total income including grants, council tax, fees',
          contentType: 'monetary',
          required: false,
          points: 4
        },
        {
          slug: 'council-tax-income',
          name: 'Council Tax Income',
          description: 'Revenue from council tax collection',
          contentType: 'monetary',
          required: false,
          points: 3
        },
        {
          slug: 'government-grants',
          name: 'Government Grants',
          description: 'Central government funding received',
          contentType: 'monetary',
          required: false,
          points: 3
        }
      ]
    },
    expenditure: {
      name: 'Expenditure & Spending',
      color: 'blue',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"/>
        </svg>
      ),
      fields: [
        {
          slug: 'total-expenditure',
          name: 'Total Expenditure',
          description: 'Total spending across all services',
          contentType: 'monetary',
          required: false,
          points: 4
        },
        {
          slug: 'interest-payments',
          name: 'Interest Payments',
          description: 'Interest paid on loans and debt',
          contentType: 'monetary',
          required: false,
          points: 3
        },
        {
          slug: 'staff-costs',
          name: 'Staff Costs',
          description: 'Employee salaries and benefits',
          contentType: 'monetary',
          required: false,
          points: 2
        }
      ]
    }
  };
  }

  /**
   * Handle field save
   */
  const handleSave = useCallback(async (fieldSlug, value) => {
    setSaving(prev => ({ ...prev, [fieldSlug]: true }));
    
    try {
      const result = await onSave(fieldSlug, value);
      
      if (result.success) {
        setEditingField(null);
        return result;
      } else {
        throw new Error(result.error || 'Failed to save field');
      }
    } catch (error) {
      console.error('Error saving financial data:', error);
      throw error;
    } finally {
      setSaving(prev => ({ ...prev, [fieldSlug]: false }));
    }
  }, [onSave]);

  /**
   * Get field status
   */
  const getFieldStatus = (field) => {
    const hasValue = financialData[field.slug] != null && financialData[field.slug] !== '';
    const hasError = errors[field.slug];
    const isSaving = saving[field.slug];
    
    if (isSaving) {
      return { status: 'saving', color: 'yellow', text: 'Saving...' };
    } else if (hasError) {
      return { status: 'error', color: 'red', text: 'Error' };
    } else if (hasValue) {
      return { status: 'complete', color: 'green', text: 'Complete' };
    } else if (field.required) {
      return { status: 'required', color: 'red', text: 'Required' };
    } else {
      return { status: 'missing', color: 'gray', text: 'Missing' };
    }
  };

  /**
   * Render field group
   */
  const renderFieldGroup = (groupKey, group) => {
    return (
      <div key={groupKey} className="mb-8">
        {/* Group header */}
        <div className="flex items-center space-x-3 mb-4">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center
            ${group.color === 'red' ? 'bg-red-100 text-red-600' :
              group.color === 'green' ? 'bg-green-100 text-green-600' :
              'bg-blue-100 text-blue-600'}
          `}>
            {group.icon}
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{group.name}</h3>
            <p className="text-sm text-gray-600">
              {group.fields.filter(f => financialData[f.slug]).length}/{group.fields.length} completed
            </p>
          </div>
        </div>

        {/* Fields grid */}
        <div className={`grid gap-4 ${isMobile ? 'grid-cols-1' : 'grid-cols-1 lg:grid-cols-2'}`}>
          {group.fields.map(field => {
            const fieldStatus = getFieldStatus(field);
            const currentValue = financialData[field.slug] || '';
            const isEditing = editingField === field.slug;

            return (
              <div
                key={field.slug}
                id={`financial-field-${field.slug}`}
                className={`
                  bg-white border-l-4 border rounded-lg transition-all duration-200
                  ${isEditing ? `border-${group.color}-500 shadow-lg` : 'border-gray-200 hover:border-gray-300'}
                  ${group.color === 'red' ? 'border-l-red-500' :
                    group.color === 'green' ? 'border-l-green-500' :
                    'border-l-blue-500'}
                  ${isMobile ? 'p-4' : 'p-6'}
                `}
              >
                {/* Field header */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2 mb-1">
                      <h4 className="text-sm font-medium text-gray-900 truncate">
                        {field.name}
                        {field.required && <span className="text-red-500 ml-1">*</span>}
                      </h4>
                      
                      {/* Calculated badge */}
                      {field.isCalculated && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                          <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"/>
                          </svg>
                          Calculated
                        </span>
                      )}
                      
                      {/* Points badge */}
                      <span className={`
                        inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium
                        ${group.color === 'red' ? 'bg-red-100 text-red-800' :
                          group.color === 'green' ? 'bg-green-100 text-green-800' :
                          'bg-blue-100 text-blue-800'}
                      `}>
                        +{field.points} pts
                      </span>
                    </div>
                    
                    <p className="text-xs text-gray-500 leading-relaxed">
                      {field.description}
                    </p>
                  </div>

                  {/* Status badge */}
                  <span className={`
                    inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ml-3 flex-shrink-0
                    ${fieldStatus.color === 'green' ? 'bg-green-100 text-green-800' :
                      fieldStatus.color === 'red' ? 'bg-red-100 text-red-800' :
                      fieldStatus.color === 'yellow' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-gray-100 text-gray-800'}
                  `}>
                    {fieldStatus.text}
                  </span>
                </div>

                {/* Field editor */}
                <FieldEditor
                  field={field}
                  value={currentValue}
                  isEditing={isEditing}
                  onEdit={() => !field.readonly && setEditingField(field.slug)}
                  onSave={handleSave}
                  onCancel={() => setEditingField(null)}
                  error={errors[field.slug]}
                  isMobile={isMobile}
                  disabled={loading || saving[field.slug] || field.readonly}
                />
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div id="financial-data-tab-container" className="p-6">
      {/* Section header */}
      <div id="financial-data-header" className="mb-6">
        <div className="flex items-center space-x-3 mb-2">
          <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
            <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1"/>
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Financial Data</h2>
            <p className="text-sm text-gray-600">
              Financial figures for {selectedYear?.display || 'selected year'}
            </p>
          </div>
        </div>

        {/* Progress summary */}
        <div className="flex items-center space-x-4 text-sm text-gray-600 bg-gray-50 rounded-lg p-3">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            <span>Complete: {Object.keys(financialData).length}</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-red-500 rounded-full"></div>
            <span>Required: {Object.values(financialFieldGroups).flatMap(g => g.fields).filter(f => f.required && !financialData[f.slug]).length}</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
            <span>Missing: {Object.values(financialFieldGroups).flatMap(g => g.fields).filter(f => !financialData[f.slug]).length}</span>
          </div>
        </div>
      </div>

      {/* Field groups */}
      {Object.entries(financialFieldGroups).map(([key, group]) => 
        renderFieldGroup(key, group)
      )}

      {/* Help text */}
      <div id="financial-data-help" className="mt-6 p-4 bg-purple-50 rounded-lg border border-purple-200">
        <div className="flex items-start space-x-3">
          <svg className="w-5 h-5 text-purple-600 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <div className="text-sm text-purple-800">
            <p className="font-medium mb-1">About Financial Data</p>
            <p>Financial figures are year-specific and help track council performance over time. All amounts should be entered in pounds (£) without currency symbols or commas.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FinancialDataTab;