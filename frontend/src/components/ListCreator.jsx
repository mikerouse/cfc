import React, { useState } from 'react';
import LoadingSpinner from './LoadingSpinner';

/**
 * Modal for creating new custom lists
 */
const ListCreator = ({ onClose, onCreate, loading = false }) => {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    color: 'blue'
  });
  const [errors, setErrors] = useState({});

  const colorOptions = [
    { value: 'blue', label: 'Blue', class: 'bg-blue-400' },
    { value: 'green', label: 'Green', class: 'bg-green-400' },
    { value: 'purple', label: 'Purple', class: 'bg-purple-400' },
    { value: 'red', label: 'Red', class: 'bg-red-400' },
    { value: 'yellow', label: 'Yellow', class: 'bg-yellow-400' },
    { value: 'indigo', label: 'Indigo', class: 'bg-indigo-400' },
    { value: 'pink', label: 'Pink', class: 'bg-pink-400' },
    { value: 'gray', label: 'Gray', class: 'bg-gray-400' },
  ];

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  const validateForm = () => {
    const newErrors = {};

    if (!formData.name.trim()) {
      newErrors.name = 'List name is required';
    } else if (formData.name.trim().length < 2) {
      newErrors.name = 'List name must be at least 2 characters';
    } else if (formData.name.trim().length > 100) {
      newErrors.name = 'List name must be less than 100 characters';
    }

    if (formData.description.length > 500) {
      newErrors.description = 'Description must be less than 500 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) return;

    try {
      await onCreate({
        name: formData.name.trim(),
        description: formData.description.trim(),
        color: formData.color
      });
    } catch (error) {
      setErrors({ submit: error.message });
    }
  };

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={handleBackdropClick}
    >
      <div className="bg-white rounded-xl shadow-2xl border border-gray-200 w-full max-w-lg max-h-screen overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900 flex items-center">
            <svg className="w-6 h-6 text-blue-500 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            Create New List
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors p-1"
            disabled={loading}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* List Name */}
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
              List Name *
            </label>
            <input
              type="text"
              id="name"
              name="name"
              value={formData.name}
              onChange={handleInputChange}
              className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                errors.name ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="e.g., North London Boroughs, Yorkshire Councils"
              maxLength={100}
              disabled={loading}
            />
            {errors.name && (
              <p className="mt-1 text-sm text-red-600">{errors.name}</p>
            )}
            <p className="mt-1 text-xs text-gray-500">
              {formData.name.length}/100 characters
            </p>
          </div>

          {/* Description */}
          <div>
            <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-2">
              Description
              <span className="text-gray-400 font-normal ml-1">(optional)</span>
            </label>
            <textarea
              id="description"
              name="description"
              value={formData.description}
              onChange={handleInputChange}
              rows={3}
              className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                errors.description ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="Add notes about what this list is for..."
              maxLength={500}
              disabled={loading}
            />
            {errors.description && (
              <p className="mt-1 text-sm text-red-600">{errors.description}</p>
            )}
            <p className="mt-1 text-xs text-gray-500">
              {formData.description.length}/500 characters
            </p>
          </div>

          {/* Color Theme */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Color Theme
            </label>
            <div className="grid grid-cols-4 gap-3">
              {colorOptions.map((option) => (
                <label
                  key={option.value}
                  className={`
                    relative flex items-center justify-center p-3 border rounded-lg cursor-pointer transition-all
                    ${formData.color === option.value
                      ? 'border-gray-800 bg-gray-50'
                      : 'border-gray-300 hover:border-gray-400'
                    }
                  `}
                >
                  <input
                    type="radio"
                    name="color"
                    value={option.value}
                    checked={formData.color === option.value}
                    onChange={handleInputChange}
                    className="sr-only"
                    disabled={loading}
                  />
                  <div className="text-center">
                    <div className={`w-8 h-8 rounded-full ${option.class} mx-auto mb-1`} />
                    <span className="text-xs font-medium text-gray-700">{option.label}</span>
                  </div>
                  {formData.color === option.value && (
                    <div className="absolute top-1 right-1">
                      <svg className="w-4 h-4 text-gray-800" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    </div>
                  )}
                </label>
              ))}
            </div>
            <p className="mt-2 text-xs text-gray-500">
              Choose a color to help identify this list at a glance
            </p>
          </div>

          {/* Submit Error */}
          {errors.submit && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-start">
                <svg className="w-5 h-5 text-red-500 mt-0.5 mr-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd"/>
                </svg>
                <div className="text-sm text-red-800">
                  <strong>Error:</strong> {errors.submit}
                </div>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="inline-flex items-center px-6 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={loading}
            >
              {loading ? (
                <>
                  <LoadingSpinner size="small" overlay={false} />
                  <span className="ml-2">Creating...</span>
                </>
              ) : (
                <>
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                  </svg>
                  Create List
                </>
              )}
            </button>
          </div>
        </form>

        {/* Example Lists */}
        <div className="px-6 pb-6 border-t border-gray-100">
          <h3 className="text-sm font-medium text-gray-700 mb-3">💡 List Ideas</h3>
          <div className="space-y-2 text-sm text-gray-600">
            <div>• <strong>By Region:</strong> North London Boroughs, Welsh Councils, Yorkshire Districts</div>
            <div>• <strong>By Type:</strong> Metropolitan Boroughs, County Councils, Unitary Authorities</div>
            <div>• <strong>By Interest:</strong> High Debt Councils, Growing Populations, Budget Comparisons</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ListCreator;