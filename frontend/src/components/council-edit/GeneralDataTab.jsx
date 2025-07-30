import React, { useState, useCallback } from 'react';
import FieldEditor from './FieldEditor';

/**
 * General Data Editor - Temporal Non-Financial Data
 * 
 * Handles year-specific general information:
 * - Link to Financial Statement (URL, changes yearly)
 * - Political control (changes yearly)
 * - Chief Executive (changes yearly)
 * - Council meetings held
 * - Other year-specific non-financial data
 * 
 * Mobile-first design with year selection
 */
const GeneralDataTab = ({ 
  generalData, 
  selectedYear,
  onSave, 
  onValidate, 
  errors, 
  loading, 
  isMobile 
}) => {
  const [editingField, setEditingField] = useState(null);
  const [saving, setSaving] = useState({});

  // Define general data fields that change year-to-year but aren't financial
  const generalFields = [
    {
      slug: 'link-to-financial-statement',
      name: 'Link to Financial Statement',
      description: 'URL to the annual financial statement document for this year',
      contentType: 'url',
      required: false,
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
        </svg>
      ),
      points: 5,
      priority: 'high'
    },
    {
      slug: 'political-control',
      name: 'Political Control',
      description: 'Which party or coalition controls the council this year',
      contentType: 'list',
      required: false,
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>
        </svg>
      ),
      points: 3,
      priority: 'medium'
    },
    {
      slug: 'chief-executive',
      name: 'Chief Executive',
      description: 'Name of the Chief Executive Officer for this year',
      contentType: 'text',
      required: false,
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
        </svg>
      ),
      points: 2,
      priority: 'low'
    },
    {
      slug: 'budget-document-link',
      name: 'Budget Document Link',
      description: 'URL to the budget document for this financial year',
      contentType: 'url',
      required: false,
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"/>
        </svg>
      ),
      points: 4,
      priority: 'high'
    },
    {
      slug: 'audit-report-link',
      name: 'Audit Report Link',
      description: 'URL to the external auditor\'s report for this year',
      contentType: 'url',
      required: false,
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/>
        </svg>
      ),
      points: 4,
      priority: 'medium'
    },
    {
      slug: 'meetings-held',
      name: 'Council Meetings Held',
      description: 'Number of full council meetings held this year',
      contentType: 'integer',
      required: false,
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
        </svg>
      ),
      points: 2,
      priority: 'low'
    }
  ];

  /**
   * Handle field save with validation
   */
  const handleSave = useCallback(async (fieldSlug, value) => {
    setSaving(prev => ({ ...prev, [fieldSlug]: true }));
    
    try {
      // Validate URL fields with enhanced security
      const urlFields = ['link-to-financial-statement', 'budget-document-link', 'audit-report-link'];
      if (urlFields.includes(fieldSlug) && value) {
        const validation = await onValidate(fieldSlug, value);
        if (!validation.valid) {
          throw new Error(validation.message);
        }
      }

      const result = await onSave(fieldSlug, value);
      
      if (result.success) {
        setEditingField(null);
        return result;
      } else {
        throw new Error(result.error || 'Failed to save field');
      }
    } catch (error) {
      console.error('Error saving general data:', error);
      throw error;
    } finally {
      setSaving(prev => ({ ...prev, [fieldSlug]: false }));
    }
  }, [onSave, onValidate]);

  /**
   * Get field status and styling
   */
  const getFieldStatus = (field) => {
    const hasValue = generalData[field.slug] != null && generalData[field.slug] !== '';
    const hasError = errors[field.slug];
    const isSaving = saving[field.slug];
    
    if (isSaving) {
      return { status: 'saving', color: 'yellow', text: 'Saving...' };
    } else if (hasError) {
      return { status: 'error', color: 'red', text: 'Error' };
    } else if (hasValue) {
      return { status: 'complete', color: 'green', text: 'Complete' };
    } else {
      return { status: 'missing', color: 'gray', text: 'Missing' };
    }
  };

  /**
   * Get priority color for field cards
   */
  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'high': return 'border-l-red-500';
      case 'medium': return 'border-l-yellow-500';
      case 'low': return 'border-l-gray-400';
      default: return 'border-l-gray-300';
    }
  };

  /**
   * Render field card for mobile/desktop
   */
  const renderFieldCard = (field) => {
    const fieldStatus = getFieldStatus(field);
    const currentValue = generalData[field.slug] || '';
    const isEditing = editingField === field.slug;

    return (
      <div
        key={field.slug}
        id={`general-field-${field.slug}`}
        className={`
          bg-white border border-l-4 rounded-lg transition-all duration-200
          ${isEditing ? 'border-green-500 shadow-lg' : 'border-gray-200 hover:border-gray-300'}
          ${getPriorityColor(field.priority)}
          ${isMobile ? 'p-4' : 'p-6'}
        `}
      >
        {/* Field Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-start space-x-3 flex-1">
            <div className={`
              flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center
              ${fieldStatus.color === 'green' ? 'bg-green-100 text-green-600' : 
                fieldStatus.color === 'red' ? 'bg-red-100 text-red-600' :
                fieldStatus.color === 'yellow' ? 'bg-yellow-100 text-yellow-600' :
                'bg-gray-100 text-gray-600'}
            `}>
              {field.icon}
            </div>
            
            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-2">
                <h3 className="text-sm font-medium text-gray-900 truncate">
                  {field.name}
                </h3>
                
                {/* Priority badge */}
                <span className={`
                  inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium
                  ${field.priority === 'high' ? 'bg-red-100 text-red-800' :
                    field.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-gray-100 text-gray-800'}
                `}>
                  {field.priority}
                </span>

                {/* Points badge */}
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                  +{field.points} pts
                </span>
              </div>
              
              <p className="text-xs text-gray-500 mt-1 leading-relaxed">
                {field.description}
              </p>
            </div>
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

        {/* Field Editor */}
        <FieldEditor
          field={field}
          value={currentValue}
          isEditing={isEditing}
          onEdit={() => setEditingField(field.slug)}
          onSave={handleSave}
          onCancel={() => setEditingField(null)}
          error={errors[field.slug]}
          isMobile={isMobile}
          disabled={loading || saving[field.slug]}
        />
      </div>
    );
  };

  // Group fields by priority for better mobile UX
  const groupedFields = {
    high: generalFields.filter(f => f.priority === 'high'),
    medium: generalFields.filter(f => f.priority === 'medium'),
    low: generalFields.filter(f => f.priority === 'low')
  };

  return (
    <div id="general-data-tab-container" className="p-6">
      {/* Section Header */}
      <div id="general-data-header" className="mb-6">
        <div className="flex items-center space-x-3 mb-2">
          <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
            <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">General Data</h2>
            <p className="text-sm text-gray-600">
              Year-specific information for {selectedYear?.display || 'selected year'}
            </p>
          </div>
        </div>

        {/* Progress summary */}
        <div className="flex items-center space-x-4 text-sm text-gray-600 bg-gray-50 rounded-lg p-3">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            <span>Complete: {Object.keys(generalData).length}</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-red-500 rounded-full"></div>
            <span>High Priority: {groupedFields.high.filter(f => !generalData[f.slug]).length}</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
            <span>Missing: {generalFields.filter(f => !generalData[f.slug]).length}</span>
          </div>
        </div>
      </div>

      {/* High Priority Fields First (Mobile-First) */}
      {groupedFields.high.length > 0 && (
        <div className="mb-8">
          <h3 className="text-sm font-medium text-red-800 mb-3 flex items-center">
            <div className="w-2 h-2 bg-red-500 rounded-full mr-2"></div>
            High Priority Fields
          </h3>
          <div className={`grid gap-4 ${isMobile ? 'grid-cols-1' : 'grid-cols-1 lg:grid-cols-2'}`}>
            {groupedFields.high.map(renderFieldCard)}
          </div>
        </div>
      )}

      {/* Medium Priority Fields */}
      {groupedFields.medium.length > 0 && (
        <div className="mb-8">
          <h3 className="text-sm font-medium text-yellow-800 mb-3 flex items-center">
            <div className="w-2 h-2 bg-yellow-500 rounded-full mr-2"></div>
            Medium Priority Fields
          </h3>
          <div className={`grid gap-4 ${isMobile ? 'grid-cols-1' : 'grid-cols-1 lg:grid-cols-2'}`}>
            {groupedFields.medium.map(renderFieldCard)}
          </div>
        </div>
      )}

      {/* Low Priority Fields (Collapsible on Mobile) */}
      {groupedFields.low.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-medium text-gray-700 mb-3 flex items-center">
            <div className="w-2 h-2 bg-gray-400 rounded-full mr-2"></div>
            Additional Fields
          </h3>
          <div className={`grid gap-4 ${isMobile ? 'grid-cols-1' : 'grid-cols-1 lg:grid-cols-2'}`}>
            {groupedFields.low.map(renderFieldCard)}
          </div>
        </div>
      )}

      {/* Help Text */}
      <div id="general-data-help" className="mt-6 p-4 bg-green-50 rounded-lg border border-green-200">
        <div className="flex items-start space-x-3">
          <svg className="w-5 h-5 text-green-600 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <div className="text-sm text-green-800">
            <p className="font-medium mb-1">About General Data</p>
            <p>These are year-specific pieces of information that help provide context to the financial data. Links to documents are particularly valuable as they allow verification of financial figures and provide transparency for citizens.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GeneralDataTab;