/**
 * FieldPicker - Drag-and-drop field selection component
 * 
 * This component displays all available fields organized by category
 * and enables drag-and-drop functionality for building templates.
 */

const { useState, useEffect } = React;

const FieldPicker = ({ fields, onFieldDrop }) => {
    const [searchTerm, setSearchTerm] = useState('');
    const [expandedCategories, setExpandedCategories] = useState({
        core_variables: true,
        calculated: true,
        characteristics: false,
        financial: false,
        counters: false
    });
    
    // Filter fields based on search term
    const filterFields = (fieldList) => {
        if (!searchTerm) return fieldList;
        
        return fieldList.filter(field => 
            field.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            field.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
            field.variable.toLowerCase().includes(searchTerm.toLowerCase())
        );
    };
    
    // Handle drag start
    const handleDragStart = (event, field) => {
        event.dataTransfer.setData('application/json', JSON.stringify({
            type: 'field',
            variable: field.variable,
            name: field.name,
            format_hint: field.format_hint
        }));
        
        // Add visual feedback
        event.target.style.opacity = '0.7';
    };
    
    // Handle drag end
    const handleDragEnd = (event) => {
        event.target.style.opacity = '1';
    };
    
    // Toggle category expansion
    const toggleCategory = (categoryKey) => {
        setExpandedCategories(prev => ({
            ...prev,
            [categoryKey]: !prev[categoryKey]
        }));
    };
    
    // Get icon for field type
    const getFieldIcon = (field) => {
        switch (field.format_hint) {
            case 'currency':
            case 'currency_per_capita':
                return '💰';
            case 'percentage':
                return '📊';
            case 'number':
                return '🔢';
            case 'text':
                return '📝';
            default:
                return '📊';
        }
    };
    
    // Format sample value for display
    const formatSampleValue = (value, formatHint) => {
        if (value === null || value === undefined) return 'No data';
        
        switch (formatHint) {
            case 'currency':
            case 'currency_per_capita':
                if (typeof value === 'number') {
                    return `£${value.toLocaleString()}`;
                }
                return `£${value}`;
            case 'percentage':
                return `${value}%`;
            case 'number':
                if (typeof value === 'number') {
                    return value.toLocaleString();
                }
                return value;
            default:
                return String(value);
        }
    };
    
    // Render a single field item
    const renderField = (field, index) => (
        <div
            key={`${field.slug}-${index}`}
            className="field-item"
            draggable
            onDragStart={(e) => handleDragStart(e, field)}
            onDragEnd={handleDragEnd}
            title={`Drag to add: {${field.variable}}`}
        >
            <div className="field-icon text-xl">
                {getFieldIcon(field)}
            </div>
            <div className="field-content">
                <div className="field-name">{field.name}</div>
                <div className="field-description">{field.description}</div>
                <div className="field-sample">
                    Sample: {formatSampleValue(field.sample_value, field.format_hint)}
                </div>
            </div>
        </div>
    );
    
    // Render a field category
    const renderCategory = (categoryKey, categoryData, title, icon) => {
        if (!categoryData || categoryData.length === 0) return null;
        
        const filteredFields = filterFields(categoryData);
        if (filteredFields.length === 0 && searchTerm) return null;
        
        const isExpanded = expandedCategories[categoryKey];
        
        return (
            <div className="field-category" key={categoryKey}>
                <div 
                    className="flex items-center justify-between cursor-pointer px-4 py-2 hover:bg-gray-100 rounded-lg mx-2"
                    onClick={() => toggleCategory(categoryKey)}
                >
                    <h3 className="flex items-center text-sm font-semibold text-gray-700">
                        <span className="mr-2 text-lg">{icon}</span>
                        {title}
                        <span className="ml-2 text-xs bg-gray-200 px-2 py-1 rounded-full">
                            {filteredFields.length}
                        </span>
                    </h3>
                    <svg 
                        className={`w-4 h-4 transform transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                        fill="none" 
                        stroke="currentColor" 
                        viewBox="0 0 24 24"
                    >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                    </svg>
                </div>
                
                {isExpanded && (
                    <div className="mt-2">
                        {filteredFields.map(renderField)}
                    </div>
                )}
            </div>
        );
    };
    
    // Show loading state
    if (!fields) {
        return (
            <div className="p-6">
                <div className="animate-pulse">
                    <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
                    <div className="space-y-3">
                        {[...Array(6)].map((_, i) => (
                            <div key={i} className="h-16 bg-gray-200 rounded"></div>
                        ))}
                    </div>
                </div>
            </div>
        );
    }
    
    return (
        <div className="h-full flex flex-col">
            {/* Header */}
            <div className="p-4 border-b border-gray-200">
                <h2 className="text-lg font-bold text-gray-800 mb-3">
                    📋 Available Fields
                </h2>
                <p className="text-sm text-gray-600 mb-4">
                    Drag fields into your template text to create dynamic factoids
                </p>
                
                {/* Search */}
                <div className="relative">
                    <input
                        type="text"
                        placeholder="Search fields..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                    <svg 
                        className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" 
                        fill="none" 
                        stroke="currentColor" 
                        viewBox="0 0 24 24"
                    >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                </div>
            </div>
            
            {/* Field Categories */}
            <div className="flex-1 overflow-y-auto p-2">
                {/* Core Variables - Always most important */}
                {renderCategory(
                    'core_variables', 
                    fields.core_variables, 
                    'Core Variables', 
                    '⭐'
                )}
                
                {/* Calculated Fields - Usually what people want */}
                {renderCategory(
                    'calculated', 
                    fields.calculated, 
                    'Calculated Values', 
                    '📊'
                )}
                
                {/* Council Characteristics */}
                {renderCategory(
                    'characteristics', 
                    fields.characteristics, 
                    'Council Info', 
                    '🏛️'
                )}
                
                {/* Financial Data */}
                {renderCategory(
                    'financial', 
                    fields.financial, 
                    'Financial Figures', 
                    '💰'
                )}
                
                {/* Counter Values */}
                {renderCategory(
                    'counters', 
                    fields.counters, 
                    'Counter Values', 
                    '🔢'
                )}
            </div>
            
            {/* Help Text */}
            <div className="p-4 border-t border-gray-200 bg-blue-50">
                <div className="text-xs text-blue-800">
                    <p className="font-semibold mb-1">💡 Quick Tips:</p>
                    <ul className="space-y-1 text-blue-700">
                        <li>• Drag fields into the template editor</li>
                        <li>• Fields auto-format as currency/numbers</li>
                        <li>• Preview updates in real-time</li>
                        <li>• Use search to find specific fields</li>
                    </ul>
                </div>
            </div>
        </div>
    );
};

// Make component available globally
window.FieldPicker = FieldPicker;