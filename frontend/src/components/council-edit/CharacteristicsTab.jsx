import React, { useState, useCallback } from 'react';
import FieldEditor from './FieldEditor';

/**
 * Council Characteristics Editor - Non-Temporal Data
 * 
 * Handles council properties that don't change year-to-year:
 * - Council type
 * - Council website  
 * - Council nation
 * - Headquarters location
 * - Contact information
 * 
 * Mobile-first design with 44px touch targets
 */
const CharacteristicsTab = ({ 
  characteristics, 
  availableFields,
  onSave, 
  onValidate, 
  errors, 
  loading, 
  isMobile 
}) => {
  const [editingField, setEditingField] = useState(null);
  const [saving, setSaving] = useState({});

  // Icon mapping for field types
  const getFieldIcon = (slug, contentType) => {
    const iconMap = {
      'population': (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20h10M7 20v-2c0-.656.126-1.283.356-1.857M2 16.143A3.001 3.001 0 015 14c.842 0 1.592.348 2.144.857M2 16.143A3.001 3.001 0 013 14.015c0-.315.047-.623.127-.913M2 16.143v1.714A2.143 2.143 0 004.143 20M5 14c.842 0 1.592.348 2.144.857M5 14c0-.843-.263-1.623-.711-2.267M5 14s.77-.77 1.711-.77M17.711 11.733c.955.274 1.711.77 1.711 1.267"/>
        </svg>
      ),
      'households': (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2 2z"/>
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 21v-4a2 2 0 012-2h4a2 2 0 012 2v4"/>
        </svg>
      ),
      'postcode': (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
        </svg>
      ),
      'image': (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
        </svg>
      )
    };
    
    if (iconMap[slug]) return iconMap[slug];
    if (slug.includes('postcode') || slug.includes('post_code')) return iconMap['postcode'];
    if (contentType === 'image') return iconMap['image'];
    
    // Default icon
    return (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
      </svg>
    );
  };

  // Transform API fields into component format or use fallback
  const characteristicFields = (availableFields && availableFields.length > 0) 
    ? availableFields.map(field => ({
        slug: field.slug,
        name: field.name,
        description: field.description || `${field.name} for this council`,
        contentType: field.content_type,
        required: field.required,
        icon: getFieldIcon(field.slug, field.content_type),
        points: field.required ? 5 : 3  // More points for required fields
      }))
    : [
        // Fallback fields if no API data available
    {
      slug: 'council-type',
      name: 'Council Type',
      description: 'Type of local authority (e.g., District Council, County Council)',
      contentType: 'list',
      required: true,
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
        </svg>
      ),
      points: 5
    },
    {
      slug: 'council-website',
      name: 'Council Website',
      description: 'Official council website URL',
      contentType: 'url',
      required: true,
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9v-9m0-9v9"/>
        </svg>
      ),
      points: 3
    },
    {
      slug: 'council-nation',
      name: 'Council Nation',
      description: 'Country within the UK (England, Scotland, Wales, Northern Ireland)',
      contentType: 'list',
      required: true,
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
        </svg>
      ),
      points: 3
    },
    {
      slug: 'council-hq-address',
      name: 'Headquarters Address',
      description: 'Main office address for the council',
      contentType: 'text',
      required: false,
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
        </svg>
      ),
      points: 2
    },
    {
      slug: 'council-hq-postcode',
      name: 'Headquarters Postcode',
      description: 'Postcode for the main council offices',
      contentType: 'text',
      required: false,
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 8l7.89 7.89a2 2 0 002.83 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
        </svg>
      ),
      points: 2
    },
    {
      slug: 'population',
      name: 'Population',
      description: 'Latest population figure for the council area',
      contentType: 'integer',
      required: false,
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>
        </svg>
      ),
      points: 3
    }
  ];

  /**
   * Handle field save with validation
   */
  const handleSave = useCallback(async (fieldSlug, value) => {
    setSaving(prev => ({ ...prev, [fieldSlug]: true }));
    
    try {
      // Validate URL fields
      if (fieldSlug === 'council-website' && value) {
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
      console.error('Error saving characteristic:', error);
      throw error;
    } finally {
      setSaving(prev => ({ ...prev, [fieldSlug]: false }));
    }
  }, [onSave, onValidate]);

  /**
   * Get field status and styling
   */
  const getFieldStatus = (field) => {
    const hasValue = characteristics[field.slug] != null && characteristics[field.slug] !== '';
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
   * Render field card for mobile/desktop
   */
  const renderFieldCard = (field) => {
    const fieldStatus = getFieldStatus(field);
    const currentValue = characteristics[field.slug] || '';
    const isEditing = editingField === field.slug;

    return (
      <div
        key={field.slug}
        id={`characteristic-field-${field.slug}`}
        className={`
          bg-white border rounded-lg transition-all duration-200
          ${isEditing ? 'border-blue-500 shadow-lg' : 'border-gray-200 hover:border-gray-300'}
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
                  {field.required && <span className="text-red-500 ml-1">*</span>}
                </h3>
                
                {/* Points badge */}
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
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

  return (
    <div id="characteristics-tab-container" className="p-6">
      {/* Section Header */}
      <div id="characteristics-header" className="mb-6">
        <div className="flex items-center space-x-3 mb-2">
          <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
            <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Council Characteristics</h2>
            <p className="text-sm text-gray-600">Basic information that doesn't change year-to-year</p>
          </div>
        </div>

        {/* Progress summary */}
        <div className="flex items-center space-x-4 text-sm text-gray-600 bg-gray-50 rounded-lg p-3">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            <span>Complete: {Object.keys(characteristics).length}</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-red-500 rounded-full"></div>
            <span>Required: {characteristicFields.filter(f => f.required && !characteristics[f.slug]).length}</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
            <span>Missing: {characteristicFields.filter(f => !characteristics[f.slug]).length}</span>
          </div>
        </div>
      </div>

      {/* Fields Grid */}
      <div id="characteristics-fields-grid" className={`
        grid gap-4
        ${isMobile ? 'grid-cols-1' : 'grid-cols-1 lg:grid-cols-2'}
      `}>
        {characteristicFields.map(renderFieldCard)}
      </div>

      {/* Help Text */}
      <div id="characteristics-help" className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
        <div className="flex items-start space-x-3">
          <svg className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <div className="text-sm text-blue-800">
            <p className="font-medium mb-1">About Council Characteristics</p>
            <p>These are basic properties of the council that remain constant over time. Unlike financial data, these don't change from year to year. Your contributions help build a comprehensive database of UK local authorities.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CharacteristicsTab;