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
  const [approvedFields, setApprovedFields] = useState(new Set());
  const [editingFields, setEditingFields] = useState(new Set());
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
        page: data.page_number || null,
        ai_reasoning: data.ai_reasoning || ''
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

  const handleApprove = useCallback((fieldSlug) => {
    // Remove from other states and add to approved
    setApprovedFields(prev => new Set(prev).add(fieldSlug));
    setRejectedFields(prev => {
      const newSet = new Set(prev);
      newSet.delete(fieldSlug);
      return newSet;
    });
    setEditingFields(prev => {
      const newSet = new Set(prev);
      newSet.delete(fieldSlug);
      return newSet;
    });
  }, []);

  const handleEdit = useCallback((fieldSlug) => {
    // Remove from other states and add to editing
    setEditingFields(prev => new Set(prev).add(fieldSlug));
    setApprovedFields(prev => {
      const newSet = new Set(prev);
      newSet.delete(fieldSlug);
      return newSet;
    });
    setRejectedFields(prev => {
      const newSet = new Set(prev);
      newSet.delete(fieldSlug);
      return newSet;
    });
  }, []);

  const handleReject = useCallback((fieldSlug) => {
    // Remove from other states and add to rejected
    setRejectedFields(prev => new Set(prev).add(fieldSlug));
    setApprovedFields(prev => {
      const newSet = new Set(prev);
      newSet.delete(fieldSlug);
      return newSet;
    });
    setEditingFields(prev => {
      const newSet = new Set(prev);
      newSet.delete(fieldSlug);
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

        {/* Summary Stats - GOV.UK Style */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="border-l-4 border-gray-400 bg-gray-50 p-4">
            <p className="text-sm text-gray-600 mb-1">Total Fields</p>
            <p className="text-2xl font-bold text-gray-900">{totalCount}</p>
          </div>
          <div className="border-l-4 border-green-600 bg-white p-4 border border-gray-200">
            <p className="text-sm text-gray-600 mb-1">Approved</p>
            <p className="text-2xl font-bold text-gray-900">{approvedFields.size}</p>
          </div>
          <div className="border-l-4 border-red-600 bg-white p-4 border border-gray-200">
            <p className="text-sm text-gray-600 mb-1">Rejected</p>
            <p className="text-2xl font-bold text-gray-900">{rejectedFields.size}</p>
          </div>
          <div className="border-l-4 border-blue-600 bg-white p-4 border border-gray-200">
            <p className="text-sm text-gray-600 mb-1">Edited</p>
            <p className="text-2xl font-bold text-gray-900">{Object.keys(editedValues).length}</p>
          </div>
        </div>

        {/* Field Groups */}
        <div className="space-y-8">
          {Object.entries(fieldGroups).map(([groupKey, group]) => {
            if (group.fields.length === 0) return null;
            
            return (
              <div key={groupKey} className="border border-gray-300 mb-6">
                <div className="bg-gray-50 px-6 py-4 border-b border-gray-300">
                  <h3 className="text-lg font-semibold text-gray-900">
                    {group.title.replace(group.icon, '').trim()}
                    <span className="ml-3 text-sm font-normal text-gray-600">
                      ({group.fields.length} field{group.fields.length !== 1 ? 's' : ''})
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
                        className={`p-6 ${isRejected ? 'bg-gray-50' : 'bg-white'}`}
                      >
                        {/* Field Header */}
                        <div className="mb-4 pb-3 border-b border-gray-200">
                          <div className="flex items-start justify-between">
                            <div>
                              <h4 className="text-lg font-semibold text-gray-900">{field.name}</h4>
                              <div className="flex items-center space-x-4 mt-2">
                                <div className={`inline-flex items-center px-2 py-1 text-xs font-medium border ${getConfidenceColor(field.confidence)}`}>
                                  {getConfidenceLabel(field.confidence)} ({Math.round(field.confidence * 100)}%)
                                </div>
                                {field.page && (
                                  <p className="text-sm text-gray-600">Page {field.page}</p>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Value Fields - Stacked Layout */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                          {/* AI Extracted Value */}
                          <div>
                            <label className="block text-sm font-medium text-gray-900 mb-2">
                              AI extracted value
                            </label>
                            <div className="p-3 border-2 border-gray-300 bg-gray-50">
                              <p className="text-lg font-mono font-semibold text-gray-900">
                                £{formatCurrency(field.value)}m
                              </p>
                            </div>
                          </div>
                          
                          {/* Editable Final Value */}
                          <div>
                            <label className="block text-sm font-medium text-gray-900 mb-2">
                              Final value for import
                            </label>
                            <div className="relative">
                              <div className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-700 font-bold text-lg pointer-events-none">
                                £
                              </div>
                              <input
                                type="number"
                                value={formatCurrency(currentValue)}
                                onChange={(e) => {
                                  handleValueEdit(field.slug, e.target.value * 1000000);
                                  handleEdit(field.slug);
                                }}
                                disabled={isRejected}
                                className={`w-full pl-10 pr-24 py-3 border-2 focus:ring-0 focus:ring-offset-0 text-lg font-mono ${
                                  isRejected 
                                    ? 'bg-gray-100 border-gray-300 text-gray-500' 
                                    : isEdited || editingFields.has(field.slug)
                                    ? 'border-blue-600 bg-white focus:border-blue-700'
                                    : approvedFields.has(field.slug)
                                    ? 'border-green-600 bg-white focus:border-green-700'
                                    : 'border-gray-400 bg-white focus:border-black'
                                }`}
                                step="0.001"
                                placeholder="0.000"
                              />
                              <div className="absolute right-4 top-1/2 transform -translate-y-1/2 text-sm text-gray-600 font-medium pointer-events-none">
                                millions
                              </div>
                            </div>
                            <div className="mt-2 min-h-[1.25rem]">
                              {(isEdited || editingFields.has(field.slug)) && !isRejected && (
                                <p className="text-sm text-blue-600 font-medium">Value modified</p>
                              )}
                              {approvedFields.has(field.slug) && (
                                <p className="text-sm text-green-600 font-medium">✓ Approved for import</p>
                              )}
                              {isRejected && (
                                <p className="text-sm text-red-600 font-medium">✗ Rejected</p>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Action Buttons - Full Width */}
                        <div className="flex space-x-3 mb-4">
                          <button
                            onClick={() => handleApprove(field.slug)}
                            disabled={isRejected}
                            className={`flex-1 py-2 px-4 text-sm font-medium border-2 transition-colors ${
                              approvedFields.has(field.slug)
                                ? 'bg-green-600 text-white border-green-600'
                                : isRejected
                                ? 'bg-gray-100 text-gray-400 border-gray-300 cursor-not-allowed'
                                : 'bg-white text-green-600 border-green-600 hover:bg-green-50'
                            }`}
                          >
                            {approvedFields.has(field.slug) ? 'Approved ✓' : 'Approve'}
                          </button>
                          <button
                            onClick={() => handleEdit(field.slug)}
                            disabled={isRejected}
                            className={`flex-1 py-2 px-4 text-sm font-medium border-2 transition-colors ${
                              editingFields.has(field.slug) || isEdited
                                ? 'bg-blue-600 text-white border-blue-600'
                                : isRejected
                                ? 'bg-gray-100 text-gray-400 border-gray-300 cursor-not-allowed'
                                : 'bg-white text-blue-600 border-blue-600 hover:bg-blue-50'
                            }`}
                          >
                            {editingFields.has(field.slug) || isEdited ? 'Editing ✎' : 'Edit'}
                          </button>
                          <button
                            onClick={() => handleReject(field.slug)}
                            className={`flex-1 py-2 px-4 text-sm font-medium border-2 transition-colors ${
                              isRejected
                                ? 'bg-red-600 text-white border-red-600'
                                : 'bg-white text-red-600 border-red-600 hover:bg-red-50'
                            }`}
                          >
                            {isRejected ? 'Rejected ✗' : 'Reject'}
                          </button>
                        </div>
                        
                        {/* Source Text & AI Reasoning - GOV.UK Style */}
                        <div className="space-y-4">
                          {field.source_text && (
                            <div className="border-l-4 border-gray-400 p-4 bg-gray-50">
                              <h5 className="text-sm font-medium text-gray-900 mb-2">
                                Source text from PDF{field.page ? ` (page ${field.page})` : ''}:
                              </h5>
                              <blockquote className="text-sm text-gray-700 leading-relaxed font-mono border-l-2 border-gray-300 pl-3">
                                "{field.source_text}"
                              </blockquote>
                            </div>
                          )}
                          
                          {field.ai_reasoning && (
                            <div className="border-l-4 border-blue-600 p-4 bg-white border border-gray-200">
                              <h5 className="text-sm font-medium text-gray-900 mb-2">AI analysis:</h5>
                              <p className="text-sm text-gray-700 leading-relaxed">
                                {field.ai_reasoning}
                              </p>
                            </div>
                          )}
                          
                          {!field.page && !field.ai_reasoning && field.source_text && (
                            <div className="border-l-4 border-yellow-400 p-4 bg-yellow-50">
                              <h5 className="text-sm font-medium text-gray-900 mb-1">Warning:</h5>
                              <p className="text-sm text-gray-700">
                                AI extracted this value from the document but page number and detailed reasoning are not available.
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        {/* Info Box - GOV.UK Style */}
        <div className="mt-8 border-l-4 border-blue-600 p-4 bg-blue-50">
          <h4 className="font-medium text-gray-900 mb-3">Review guidance</h4>
          <ul className="text-sm text-gray-700 space-y-2">
            <li>• Check values match the financial statement (values should be in millions)</li>
            <li>• High confidence fields are likely to be correct</li>
            <li>• Edit any incorrect values directly in the input fields</li>
            <li>• Reject fields that should not be imported</li>
            <li>• All approved fields will be saved to {councilData?.name} for {selectedYear?.label}</li>
          </ul>
        </div>

        {/* Action Buttons - GOV.UK Style */}
        <div className="mt-8 border-t border-gray-300 pt-6">
          <div className="flex flex-col sm:flex-row sm:justify-between space-y-3 sm:space-y-0 sm:space-x-4">
            <button
              onClick={onReject}
              className="px-4 py-2 border-2 border-red-600 text-red-600 bg-white hover:bg-red-50 transition-colors font-medium"
            >
              Reject all and start over
            </button>
            
            <div className="flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-3">
              <button
                onClick={onBack}
                className="px-4 py-2 border-2 border-gray-400 text-gray-700 bg-white hover:bg-gray-50 transition-colors font-medium"
              >
                Back to upload
              </button>
              <button
                onClick={handleConfirmAll}
                disabled={approvedFields.size === 0 || saving}
                className={`px-4 py-2 border-2 font-medium transition-colors ${
                  approvedFields.size > 0 && !saving
                    ? 'bg-green-600 text-white border-green-600 hover:bg-green-700'
                    : 'bg-gray-400 text-white border-gray-400 cursor-not-allowed'
                }`}
              >
                {saving ? (
                  <>
                    <span className="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent mr-2" />
                    Saving...
                  </>
                ) : (
                  <>Import {approvedFields.size} approved field{approvedFields.size !== 1 ? 's' : ''}</>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIExtractionReview;