import React, { useState, useCallback, useMemo } from 'react';

/**
 * AI Extraction Review Component
 * 
 * Displays AI-extracted financial data for user review:
 * - Shows extracted values with confidence scores
 * - Allows editing, rejection, or confirmation
 * - Groups fields by category for easy review
 */
const AIExtractionReview = ({
  councilData,
  selectedYear,
  extractedData = {},
  confidenceScores = {},
  onConfirm,
  onReject,
  onBack,
  csrfToken,
  className = ""
}) => {
  const [editedValues, setEditedValues] = useState({});
  const [rejectedFields, setRejectedFields] = useState(new Set());
  const [saving, setSaving] = useState(false);

  // Group extracted fields by category
  const fieldGroups = useMemo(() => {
    const groups = {
      income: {
        title: '💷 Income & Expenditure',
        fields: [],
        icon: '💷'
      },
      balance: {
        title: '⚖️ Balance Sheet',
        fields: [],
        icon: '⚖️'
      },
      debt: {
        title: '📊 Debt & Obligations',
        fields: [],
        icon: '📊'
      },
      other: {
        title: '📁 Other Fields',
        fields: [],
        icon: '📁'
      }
    };

    // Map of field slugs to categories
    const categoryMap = {
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

    // Process extracted data
    Object.entries(extractedData).forEach(([fieldSlug, data]) => {
      const category = categoryMap[fieldSlug] || 'other';
      groups[category].fields.push({
        slug: fieldSlug,
        name: data.field_name || fieldSlug.replace(/-/g, ' '),
        value: data.value,
        confidence: confidenceScores[fieldSlug] || 0,
        source_text: data.source_text || '',
        page: data.page_number || null
      });
    });

    // Sort fields by confidence score (highest first)
    Object.values(groups).forEach(group => {
      group.fields.sort((a, b) => b.confidence - a.confidence);
    });

    return groups;
  }, [extractedData, confidenceScores]);

  const handleValueEdit = useCallback((fieldSlug, newValue) => {
    setEditedValues(prev => ({
      ...prev,
      [fieldSlug]: newValue
    }));
    // Remove from rejected if editing
    setRejectedFields(prev => {
      const newSet = new Set(prev);
      newSet.delete(fieldSlug);
      return newSet;
    });
  }, []);

  const handleFieldToggle = useCallback((fieldSlug) => {
    setRejectedFields(prev => {
      const newSet = new Set(prev);
      if (newSet.has(fieldSlug)) {
        newSet.delete(fieldSlug);
      } else {
        newSet.add(fieldSlug);
      }
      return newSet;
    });
  }, []);

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return 'text-green-600 bg-green-50 border-green-200';
    if (confidence >= 0.6) return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    return 'text-red-600 bg-red-50 border-red-200';
  };

  const getConfidenceLabel = (confidence) => {
    if (confidence >= 0.8) return 'High confidence';
    if (confidence >= 0.6) return 'Medium confidence';
    return 'Low confidence';
  };

  const formatCurrency = (value) => {
    if (!value) return '';
    const numValue = parseFloat(value);
    if (isNaN(numValue)) return value;
    
    // Format as millions
    const millions = numValue / 1000000;
    return millions.toFixed(3);
  };

  const handleConfirmAll = useCallback(async () => {
    setSaving(true);
    
    // Prepare final data (excluding rejected fields)
    const finalData = {};
    Object.entries(extractedData).forEach(([fieldSlug, data]) => {
      if (!rejectedFields.has(fieldSlug)) {
        finalData[fieldSlug] = editedValues[fieldSlug] !== undefined 
          ? editedValues[fieldSlug]
          : data.value;
      }
    });
    
    await onConfirm(finalData);
    setSaving(false);
  }, [extractedData, editedValues, rejectedFields, onConfirm]);

  const acceptedCount = Object.keys(extractedData).length - rejectedFields.size;
  const totalCount = Object.keys(extractedData).length;
  const hasEdits = Object.keys(editedValues).length > 0;

  return (
    <div className={`bg-white ${className}`}>
      <div className="max-w-6xl mx-auto px-4 py-6 sm:px-6 sm:py-8">
        
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={onBack}
            className="inline-flex items-center text-blue-600 hover:text-blue-800 text-sm font-medium mb-4"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
            </svg>
            Back to upload
          </button>
          
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Review Extracted Data
          </h2>
          <p className="text-gray-600">
            AI has extracted {totalCount} financial fields from the PDF. Please review and confirm.
          </p>
        </div>

        {/* Summary Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-600 mb-1">Total Fields</p>
            <p className="text-2xl font-bold text-gray-900">{totalCount}</p>
          </div>
          <div className="bg-green-50 rounded-lg p-4">
            <p className="text-sm text-green-600 mb-1">Accepted</p>
            <p className="text-2xl font-bold text-green-900">{acceptedCount}</p>
          </div>
          <div className="bg-red-50 rounded-lg p-4">
            <p className="text-sm text-red-600 mb-1">Rejected</p>
            <p className="text-2xl font-bold text-red-900">{rejectedFields.size}</p>
          </div>
          <div className="bg-blue-50 rounded-lg p-4">
            <p className="text-sm text-blue-600 mb-1">Edited</p>
            <p className="text-2xl font-bold text-blue-900">{Object.keys(editedValues).length}</p>
          </div>
        </div>

        {/* Field Groups */}
        <div className="space-y-8">
          {Object.entries(fieldGroups).map(([groupKey, group]) => {
            if (group.fields.length === 0) return null;
            
            return (
              <div key={groupKey} className="border border-gray-200 rounded-lg overflow-hidden">
                <div className="bg-gray-50 px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                    <span className="text-2xl mr-3">{group.icon}</span>
                    {group.title.replace(group.icon, '').trim()}
                    <span className="ml-3 text-sm text-gray-500">
                      ({group.fields.length} fields)
                    </span>
                  </h3>
                </div>
                
                <div className="divide-y divide-gray-200">
                  {group.fields.map((field) => {
                    const isRejected = rejectedFields.has(field.slug);
                    const isEdited = editedValues[field.slug] !== undefined;
                    const currentValue = isEdited ? editedValues[field.slug] : field.value;
                    
                    return (
                      <div
                        key={field.slug}
                        className={`p-6 ${isRejected ? 'bg-gray-50 opacity-60' : ''}`}
                      >
                        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
                          {/* Field Info */}
                          <div className="lg:col-span-3">
                            <h4 className="font-medium text-gray-900">{field.name}</h4>
                            <div className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium mt-2 border ${getConfidenceColor(field.confidence)}`}>
                              {getConfidenceLabel(field.confidence)} ({Math.round(field.confidence * 100)}%)
                            </div>
                            {field.page && (
                              <p className="text-xs text-gray-500 mt-1">Page {field.page}</p>
                            )}
                          </div>
                          
                          {/* Extracted Value */}
                          <div className="lg:col-span-3">
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              AI Extracted Value
                            </label>
                            <div className="p-2 bg-gray-50 rounded border border-gray-200">
                              <p className="text-sm font-mono text-gray-900">
                                £{formatCurrency(field.value)}m
                              </p>
                            </div>
                          </div>
                          
                          {/* Editable Value */}
                          <div className="lg:col-span-3">
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Final Value
                            </label>
                            <div className="relative">
                              <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500">
                                £
                              </span>
                              <input
                                type="number"
                                value={formatCurrency(currentValue)}
                                onChange={(e) => handleValueEdit(field.slug, e.target.value * 1000000)}
                                disabled={isRejected}
                                className={`w-full pl-7 pr-12 py-2 border rounded-md ${
                                  isRejected 
                                    ? 'bg-gray-100 border-gray-200 text-gray-400' 
                                    : isEdited
                                    ? 'border-blue-300 bg-blue-50'
                                    : 'border-gray-300'
                                }`}
                                step="0.001"
                                placeholder="0.000"
                              />
                              <span className="absolute right-3 top-1/2 transform -translate-y-1/2 text-sm text-gray-500">
                                millions
                              </span>
                            </div>
                            {isEdited && !isRejected && (
                              <p className="text-xs text-blue-600 mt-1">Modified from original</p>
                            )}
                          </div>
                          
                          {/* Actions */}
                          <div className="lg:col-span-3 flex items-center justify-end space-x-2">
                            <button
                              onClick={() => handleFieldToggle(field.slug)}
                              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                                isRejected
                                  ? 'bg-gray-600 text-white hover:bg-gray-700'
                                  : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                              }`}
                            >
                              {isRejected ? 'Include' : 'Reject'}
                            </button>
                          </div>
                        </div>
                        
                        {/* Source Text Preview */}
                        {field.source_text && (
                          <div className="mt-4 p-3 bg-gray-50 rounded border border-gray-200">
                            <p className="text-xs text-gray-600 mb-1">Source text from PDF:</p>
                            <p className="text-xs font-mono text-gray-700 line-clamp-2">
                              {field.source_text}
                            </p>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        {/* Info Box */}
        <div className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <h4 className="font-medium text-blue-900 mb-2">Review Tips</h4>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>• Check values match the financial statement (values should be in millions)</li>
            <li>• High confidence (green) fields are likely correct</li>
            <li>• Edit any incorrect values directly in the input fields</li>
            <li>• Reject fields that shouldn't be imported</li>
            <li>• All accepted fields will be saved to {councilData?.name} for {selectedYear?.label}</li>
          </ul>
        </div>

        {/* Action Buttons */}
        <div className="mt-8 flex justify-between">
          <button
            onClick={onReject}
            className="px-6 py-2 border border-red-300 text-red-700 rounded-md hover:bg-red-50 transition-colors"
          >
            Reject All & Start Over
          </button>
          
          <div className="flex space-x-4">
            <button
              onClick={onBack}
              className="px-6 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Back
            </button>
            <button
              onClick={handleConfirmAll}
              disabled={acceptedCount === 0 || saving}
              className={`px-6 py-2 rounded-md text-white transition-colors ${
                acceptedCount > 0 && !saving
                  ? 'bg-green-600 hover:bg-green-700'
                  : 'bg-gray-400 cursor-not-allowed'
              }`}
            >
              {saving ? (
                <>
                  <span className="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-2" />
                  Saving...
                </>
              ) : (
                <>Confirm & Import {acceptedCount} Fields</>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIExtractionReview;