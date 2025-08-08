import React, { useState, useCallback } from 'react';
import FieldEditor from './FieldEditor';

/**
 * Simple form for editing council characteristics (non-temporal data)
 * Replaces the old characteristics tab with a focused single-page experience
 */
const CharacteristicsEditor = ({ 
  councilData,
  characteristics = {},
  availableFields = [],
  onSave,
  onValidate,
  onBack,
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
      description: 'Core council details',
      fields: availableFields.filter(field => 
        ['name', 'council-type', 'nation', 'population'].includes(field.slug)
      )
    },
    contact: {
      title: 'Contact Information',
      description: 'How to reach the council',
      fields: availableFields.filter(field => 
        ['website', 'contact-url', 'email'].includes(field.slug)
      )
    },
    leadership: {
      title: 'Leadership',
      description: 'Key people and political control',
      fields: availableFields.filter(field => 
        ['chief-executive', 'leader', 'political-control'].includes(field.slug)
      )
    },
    other: {
      title: 'Other Information',
      description: 'Additional council details',
      fields: availableFields.filter(field => 
        !['name', 'council-type', 'nation', 'population', 'website', 'contact-url', 
          'email', 'chief-executive', 'leader', 'political-control'].includes(field.slug)
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
    return characteristics[fieldSlug] || '';
  }, [characteristics]);

  const calculateProgress = () => {
    const completedFields = availableFields.filter(field => 
      characteristics[field.slug] && characteristics[field.slug].toString().trim().length > 0
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
      <div key={groupKey} id={`characteristics-group-${groupKey}`} className="mb-8">
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
              />
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div id="characteristics-editor-main" className={`bg-white ${className}`}>
      <div className="max-w-4xl mx-auto px-4 py-6 sm:px-6 sm:py-8">
        
        {/* Header with Back Navigation */}
        <div id="characteristics-editor-header" className="mb-8">
          <button 
            onClick={onBack}
            className="inline-flex items-center text-blue-600 hover:text-blue-800 text-sm font-medium mb-4"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
            </svg>
            Back
          </button>
          
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-2">
            Council Details
          </h1>
          <p className="text-lg text-gray-600">
            Edit basic information for {councilData?.name}
          </p>
        </div>

        {/* Progress Bar */}
        <div id="characteristics-progress" className="mb-8">
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
          <div id="characteristics-success" className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-center">
              <svg className="w-5 h-5 text-green-400 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-green-800">{successMessage}</p>
            </div>
          </div>
        )}

        {/* Field Groups */}
        <div id="characteristics-field-groups">
          {Object.entries(fieldGroups).map(([groupKey, group]) => 
            renderFieldGroup(group, groupKey)
          )}
        </div>

        {/* Loading State */}
        {loading && (
          <div id="characteristics-loading" className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-500 border-t-transparent mr-3"></div>
            <span className="text-gray-600">Loading council data...</span>
          </div>
        )}

        {/* Action Buttons */}
        <div id="characteristics-actions" className="flex flex-col sm:flex-row gap-4 pt-8 border-t border-gray-200">
          <button
            onClick={onBack}
            className="px-6 py-3 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 font-medium transition-colors"
          >
            Back to Overview
          </button>
          
          <div className="flex-1"></div>
          
          <div className="text-sm text-gray-500 self-center">
            Changes are saved automatically
          </div>
        </div>

        {/* Help Section */}
        <div id="characteristics-help" className="mt-8 p-4 bg-blue-50 rounded-lg border border-blue-200">
          <h4 className="font-medium text-blue-900 mb-2">Tips for completing council details</h4>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>• <strong>Population:</strong> This is the current population used for display on council pages</li>
            <li>• <strong>Website:</strong> Must be a valid URL starting with https://</li>
            <li>• <strong>Political Control:</strong> Current party or coalition in control</li>
            <li>• All changes are reviewed before being published</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default CharacteristicsEditor;