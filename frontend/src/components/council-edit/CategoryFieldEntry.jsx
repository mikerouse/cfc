import React, { useState, useCallback } from 'react';
import SmartFieldEditor from './SmartFieldEditor';
import ChangeSummary from './ChangeSummary';

/**
 * Simplified field entry for a specific category
 * Shows only fields for the selected category with clean layout
 */
const CategoryFieldEntry = ({
  councilData,
  selectedYear,
  selectedCategory,
  financialData = {},
  availableFields = [],
  onSave,
  onValidate,
  onTrackChange,  // Add this prop to receive from parent
  errors = {},
  loading = false,
  className = ""
}) => {
  const [saving, setSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [trackedChanges, setTrackedChanges] = useState({});
  const [showChangeSummary, setShowChangeSummary] = useState(false);

  const handleSave = useCallback(async (fieldSlug, value) => {
    setSaving(true);
    setSuccessMessage('');
    
    try {
      const result = await onSave(fieldSlug, value, selectedYear?.id);
      if (result?.success) {
        // Remove this change from tracked changes after successful save
        setTrackedChanges(prev => {
          const updated = { ...prev };
          delete updated[fieldSlug];
          return updated;
        });
        
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
  }, [onSave, selectedYear?.id]);

  // Track changes for diff summary - use parent's handler if provided, otherwise local
  const handleTrackChange = useCallback((fieldSlug, changeData) => {
    // Update local state for immediate UI feedback
    setTrackedChanges(prev => ({
      ...prev,
      [fieldSlug]: changeData
    }));
    
    // Also notify parent component if handler provided
    if (onTrackChange) {
      onTrackChange(fieldSlug, changeData);
    }
  }, [onTrackChange]);

  // Handle change summary actions
  const handleShowChangeSummary = useCallback(() => {
    const changesArray = Object.values(trackedChanges);
    if (changesArray.length > 0) {
      setShowChangeSummary(true);
    }
  }, [trackedChanges]);

  const handleConfirmChanges = useCallback(async () => {
    // All changes are already saved via auto-save
    // Just clear tracked changes and hide summary
    setTrackedChanges({});
    setShowChangeSummary(false);
    setSuccessMessage(`All changes confirmed! Category progress updated.`);
    setTimeout(() => setSuccessMessage(''), 3000);
  }, []);

  const handleCancelChanges = useCallback(() => {
    setShowChangeSummary(false);
  }, []);

  const handleEditFieldFromSummary = useCallback((fieldSlug) => {
    setShowChangeSummary(false);
    // Find and focus the field - this would scroll to it in a real implementation
    const fieldElement = document.getElementById(`field-${fieldSlug}`);
    if (fieldElement) {
      fieldElement.focus();
      fieldElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, []);

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

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-500 border-t-transparent mr-3"></div>
        <span className="text-gray-600">Loading fields...</span>
      </div>
    );
  }

  if (!availableFields.length) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-400 text-4xl mb-4">📋</div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">No fields in this category</h3>
        <p className="text-gray-500">
          There are no fields available for this category yet.
        </p>
      </div>
    );
  }

  return (
    <div className={`${className}`}>
      {/* Progress indicator */}
      <div className="mb-8 p-4 bg-gray-50 border border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-gray-900">
            Category Progress
          </h3>
          <span className="text-2xl font-bold text-gray-900">{progress.percentage}%</span>
        </div>
        <div className="w-full bg-gray-200 h-2 mb-2">
          <div 
            className="bg-blue-600 h-2 transition-all duration-300"
            style={{ width: `${progress.percentage}%` }}
          />
        </div>
        <p className="text-sm text-gray-600">
          {progress.completed} of {progress.total} fields completed
        </p>
      </div>

      {/* Success Message */}
      {successMessage && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200">
          <div className="flex items-center">
            <svg className="w-5 h-5 text-green-400 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-green-800">{successMessage}</p>
          </div>
        </div>
      )}

      {/* Fields Grid - Improved layout */}
      <div className="space-y-4">
        {availableFields.map(field => (
          <div key={field.slug} className="bg-white p-4 border-l-4 border-blue-200">
            <SmartFieldEditor
              field={field}
              value={getFieldValue(field.slug)}
              onSave={(value) => handleSave(field.slug, value)}
              onValidate={onValidate}
              onTrackChange={handleTrackChange}
              error={errors[field.slug]}
              disabled={saving}
              showPopulationContext={field.slug === 'population'}
              yearContext={field.slug === 'population' ? selectedYear?.label : null}
              allFieldValues={financialData}
            />
          </div>
        ))}
      </div>

      {/* Review Changes Button */}
      {Object.keys(trackedChanges).length > 0 && (
        <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium text-yellow-900 mb-1">Changes Ready for Review</h4>
              <p className="text-sm text-yellow-800">
                {Object.keys(trackedChanges).length} field{Object.keys(trackedChanges).length !== 1 ? 's' : ''} updated in this category
              </p>
            </div>
            <button
              onClick={handleShowChangeSummary}
              className="px-4 py-2 bg-yellow-600 text-white hover:bg-yellow-700 font-medium transition-colors"
            >
              Review Changes
            </button>
          </div>
        </div>
      )}

      {/* Help Text */}
      <div className="mt-8 p-4 bg-blue-50 border border-blue-200">
        <h4 className="font-medium text-blue-900 mb-2">💡 Tips for this category</h4>
        <div className="text-sm text-blue-800 space-y-1">
          {selectedCategory === 'basic' && (
            <>
              <p>• <strong>Population:</strong> Use the population for the financial year, not current population</p>
              <p>• <strong>Statement Link:</strong> Link to the published annual financial statement PDF</p>
            </>
          )}
          {selectedCategory === 'income' && (
            <>
              <p>• <strong>Figures in millions:</strong> Enter "4.2" for £4.2 million</p>
              <p>• <strong>Find in:</strong> Comprehensive Income and Expenditure Statement</p>
              <p>• <strong>Use Group figures</strong> if the council has subsidiaries</p>
            </>
          )}
          {selectedCategory === 'balance' && (
            <>
              <p>• <strong>Figures in millions:</strong> Enter "15.7" for £15.7 million</p>
              <p>• <strong>Find in:</strong> Balance Sheet section of annual accounts</p>
              <p>• <strong>Negative values:</strong> Some reserves can be negative (deficit)</p>
            </>
          )}
          {selectedCategory === 'debt' && (
            <>
              <p>• <strong>Long-term focus:</strong> These are typically multi-year commitments</p>
              <p>• <strong>PFI contracts:</strong> Include in finance leases if applicable</p>
            </>
          )}
          <p>• Changes are saved automatically as you type</p>
          <p>• Click "Edit" on populated fields to modify existing data</p>
          <p>• Helper information appears when you focus on input fields</p>
        </div>
      </div>

      {/* Change Summary Modal */}
      <ChangeSummary
        changes={Object.values(trackedChanges)}
        isVisible={showChangeSummary}
        onConfirm={handleConfirmChanges}
        onCancel={handleCancelChanges}
        onEditField={handleEditFieldFromSummary}
      />
    </div>
  );
};

export default CategoryFieldEntry;