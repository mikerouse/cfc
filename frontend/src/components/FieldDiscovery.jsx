/**
 * FieldDiscovery Component
 * 
 * Displays available data fields in organized categories with drag-and-drop support.
 * Features real-time search and formatting options.
 */
import { useState, useMemo } from 'react';

const FieldDiscovery = ({ fieldGroups, isLoading, onFieldDrop, onRefresh }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [expandedCategories, setExpandedCategories] = useState(new Set(['characteristic', 'financial']));

  // Filter fields based on search and category
  const filteredFields = useMemo(() => {
    if (!fieldGroups || Object.keys(fieldGroups).length === 0) {
      return {};
    }

    let filtered = { ...fieldGroups };

    // Filter by category
    if (selectedCategory !== 'all') {
      filtered = { [selectedCategory]: filtered[selectedCategory] || [] };
    }

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      const searchFiltered = {};

      Object.entries(filtered).forEach(([category, fields]) => {
        const matchingFields = fields.filter(field =>
          field.name.toLowerCase().includes(query) ||
          field.variable_name.toLowerCase().includes(query) ||
          (field.description && field.description.toLowerCase().includes(query))
        );
        
        if (matchingFields.length > 0) {
          searchFiltered[category] = matchingFields;
        }
      });

      filtered = searchFiltered;
    }

    return filtered;
  }, [fieldGroups, searchQuery, selectedCategory]);

  // Category management
  const toggleCategory = (category) => {
    setExpandedCategories(prev => {
      const newSet = new Set(prev);
      if (newSet.has(category)) {
        newSet.delete(category);
      } else {
        newSet.add(category);
      }
      return newSet;
    });
  };

  // Drag and drop handlers
  const handleDragStart = (e, field) => {
    e.dataTransfer.setData('application/json', JSON.stringify({
      type: 'field',
      field: field,
    }));
    e.dataTransfer.effectAllowed = 'copy';
    
    // Visual feedback
    e.target.classList.add('opacity-75');
  };

  const handleDragEnd = (e) => {
    e.target.classList.remove('opacity-75');
  };

  // Click to insert field
  const handleFieldClick = (field, formatType = 'default') => {
    onFieldDrop(field.variable_name, formatType);
  };

  // Get category icon
  const getCategoryIcon = (category) => {
    const icons = {
      characteristic: '👥',
      financial: '💰',
      calculated: '🔢',
      computed: '⚙️',
    };
    return icons[category] || '📊';
  };

  // Get category label
  const getCategoryLabel = (category) => {
    const labels = {
      characteristic: 'Council Characteristics',
      financial: 'Financial Figures',
      calculated: 'Calculated Fields',
      computed: 'Computed Values',
    };
    return labels[category] || category.charAt(0).toUpperCase() + category.slice(1);
  };

  // Get field type color
  const getFieldTypeColor = (dataType) => {
    const colors = {
      text: 'bg-blue-100 text-blue-800',
      integer: 'bg-green-100 text-green-800',
      decimal: 'bg-green-100 text-green-800',
      percentage: 'bg-yellow-100 text-yellow-800',
      boolean: 'bg-purple-100 text-purple-800',
      date: 'bg-gray-100 text-gray-800',
    };
    return colors[dataType] || 'bg-gray-100 text-gray-800';
  };

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
          <div className="space-y-3">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-3 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const totalFields = Object.values(filteredFields).flat().length;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">
            🔍 Available Fields
          </h3>
          <button
            onClick={onRefresh}
            className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
            title="Refresh fields"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>

        {/* Search */}
        <div className="relative mb-4">
          <input
            type="text"
            placeholder="Search fields..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-3 py-2 pl-8 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <svg className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>

        {/* Category Filter */}
        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="all">All Categories ({Object.values(fieldGroups).flat().length})</option>
          {Object.entries(fieldGroups).map(([category, fields]) => (
            <option key={category} value={category}>
              {getCategoryLabel(category)} ({fields.length})
            </option>
          ))}
        </select>
      </div>

      {/* Field List */}
      <div className="flex-1 overflow-y-auto">
        {totalFields === 0 ? (
          <div className="p-4 text-center text-gray-500">
            {searchQuery ? 'No fields match your search' : 'No fields available'}
          </div>
        ) : (
          <div className="space-y-2 p-4">
            {Object.entries(filteredFields).map(([category, fields]) => (
              <div key={category} className="border border-gray-200 rounded-lg overflow-hidden">
                {/* Category Header */}
                <button
                  onClick={() => toggleCategory(category)}
                  className="w-full px-4 py-3 bg-gray-50 hover:bg-gray-100 flex items-center justify-between text-left transition-colors"
                >
                  <div className="flex items-center">
                    <span className="text-lg mr-2">{getCategoryIcon(category)}</span>
                    <span className="font-medium text-gray-900">
                      {getCategoryLabel(category)}
                    </span>
                    <span className="ml-2 text-sm text-gray-500">
                      ({fields.length})
                    </span>
                  </div>
                  <svg
                    className={`w-4 h-4 text-gray-500 transition-transform ${
                      expandedCategories.has(category) ? 'rotate-90' : ''
                    }`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                  </svg>
                </button>

                {/* Field Items */}
                {expandedCategories.has(category) && (
                  <div className="border-t border-gray-200">
                    {fields.map((field) => (
                      <div
                        key={field.id}
                        draggable
                        onDragStart={(e) => handleDragStart(e, field)}
                        onDragEnd={handleDragEnd}
                        onClick={() => handleFieldClick(field)}
                        className="p-3 border-b border-gray-100 last:border-b-0 hover:bg-blue-50 cursor-move group transition-colors"
                        title={`Drag to template or click to insert: {${field.variable_name}}`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center mb-1">
                              <span className="font-medium text-gray-900 text-sm">
                                {field.name}
                              </span>
                              <span className={`ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getFieldTypeColor(field.data_type)}`}>
                                {field.data_type}
                              </span>
                            </div>
                            
                            <div className="text-xs font-mono text-blue-600 mb-1">
                              {`{${field.variable_name}}`}
                            </div>
                            
                            {field.description && (
                              <p className="text-xs text-gray-600 line-clamp-2">
                                {field.description}
                              </p>
                            )}
                            
                            {field.sample_value && (
                              <div className="text-xs text-green-600 font-mono mt-1">
                                Example: {field.sample_value}
                              </div>
                            )}
                          </div>

                          {/* Formatting Options */}
                          {field.formatting_options && field.formatting_options.length > 1 && (
                            <div className="ml-2 opacity-0 group-hover:opacity-100 transition-opacity">
                              <div className="flex flex-col space-y-1">
                                {field.formatting_options.slice(1).map((format) => (
                                  <button
                                    key={format}
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleFieldClick(field, format);
                                    }}
                                    className="px-2 py-1 text-xs bg-white border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                                    title={`Insert as {${field.variable_name}:${format}}`}
                                  >
                                    :{format}
                                  </button>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-gray-200 p-4 bg-gray-50">
        <div className="text-xs text-gray-600 space-y-1">
          <div>💡 <strong>Tip:</strong> Drag fields to the template editor</div>
          <div>⌨️ <strong>Formats:</strong> :currency, :percentage, :number</div>
          <div>🔍 <strong>Search:</strong> Find fields by name or description</div>
        </div>
      </div>
    </div>
  );
};

export default FieldDiscovery;
