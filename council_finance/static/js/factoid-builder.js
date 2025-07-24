/**
 * Modern React-based Factoid Template Builder
 * 
 * Features:
 * - Drag and drop field insertion
 * - Live preview with real API data
 * - Rich UI with proper React patterns
 * - Full form handling and validation
 */

const { useState, useEffect, useCallback, useRef } = React;

// Main FactoidBuilder Component
const FactoidBuilder = ({ config }) => {
    console.log('🎨 FactoidBuilder initializing with config:', config);
    
    // State management
    const [fields, setFields] = useState(null);
    const [template, setTemplate] = useState({
        name: config.template?.name || '',
        template_text: config.template?.template_text || '',
        factoid_type: config.template?.factoid_type || 'context',
        emoji: config.template?.emoji || '📊',
        color_scheme: config.template?.color_scheme || 'blue',
        priority: config.template?.priority || 50,
        is_active: config.template?.is_active ?? true
    });
    const [previewText, setPreviewText] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [saving, setSaving] = useState(false);
    const [previewErrors, setPreviewErrors] = useState([]);
    
    const textareaRef = useRef(null);
    
    // API helper
    const apiCall = useCallback(async (url, options = {}) => {
        const headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': config.csrf_token,
            ...options.headers
        };
        
        const response = await fetch(url, {
            ...options,
            headers,
            credentials: 'same-origin'
        });
        
        if (!response.ok) {
            throw new Error(`API call failed: ${response.status} ${response.statusText}`);
        }
        
        return await response.json();
    }, [config.csrf_token]);
    
    // Load fields from API
    useEffect(() => {
        const loadFields = async () => {
            try {
                console.log('📡 Loading fields from API...');
                setLoading(true);
                const response = await apiCall(config.api_urls.fields);
                
                if (response.success) {
                    console.log('✅ Fields loaded:', response.fields);
                    setFields(response.fields);
                } else {
                    setError(response.error || 'Failed to load fields');
                }
            } catch (err) {
                console.error('❌ Field loading failed:', err);
                setError(`Failed to load fields: ${err.message}`);
            } finally {
                setLoading(false);
            }
        };
        
        loadFields();
    }, [apiCall, config.api_urls.fields]);
    
    // Update preview when template text changes
    useEffect(() => {
        const updatePreview = async () => {
            if (!template.template_text.trim()) {
                setPreviewText('Type some template text to see a live preview...');
                setPreviewErrors([]);
                return;
            }
            
            try {
                const response = await apiCall(config.api_urls.preview, {
                    method: 'POST',
                    body: JSON.stringify({
                        template_text: template.template_text,
                        council_slug: 'birmingham', // Use sample council
                        year_label: '2024/25'
                    })
                });
                
                if (response.success) {
                    setPreviewText(response.rendered_text || 'Preview not available');
                    setPreviewErrors(response.errors || []);
                } else {
                    setPreviewText(template.template_text); // Fallback
                    setPreviewErrors([response.error || 'Preview failed']);
                }
            } catch (err) {
                console.error('Preview error:', err);
                setPreviewErrors([`Preview error: ${err.message}`]);
            }
        };
        
        const debounce = setTimeout(updatePreview, 500);
        return () => clearTimeout(debounce);
    }, [template.template_text, apiCall, config.api_urls.preview]);
    
    // Insert field at cursor position
    const insertField = useCallback((fieldExpression) => {
        const textarea = textareaRef.current;
        if (!textarea) return;
        
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const text = template.template_text;
        const before = text.substring(0, start);
        const after = text.substring(end);
        
        const newText = before + `{${fieldExpression}}` + after;
        const newCursorPos = start + fieldExpression.length + 2;
        
        setTemplate(prev => ({ ...prev, template_text: newText }));
        
        // Set cursor position after React re-renders
        setTimeout(() => {
            textarea.selectionStart = newCursorPos;
            textarea.selectionEnd = newCursorPos;
            textarea.focus();
        }, 0);
    }, [template.template_text]);
    
    // Handle drag and drop
    const handleDragStart = useCallback((e, fieldExpression) => {
        e.dataTransfer.setData('text/plain', fieldExpression);
        e.dataTransfer.effectAllowed = 'copy';
    }, []);
    
    const handleDrop = useCallback((e) => {
        e.preventDefault();
        const fieldExpression = e.dataTransfer.getData('text/plain');
        if (fieldExpression) {
            insertField(fieldExpression);
        }
    }, [insertField]);
    
    const handleDragOver = useCallback((e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'copy';
    }, []);
    
    // Save template
    const saveTemplate = useCallback(async () => {
        if (!template.name.trim()) {
            alert('Please enter a template name');
            return;
        }
        
        if (!template.template_text.trim()) {
            alert('Please enter template text');
            return;
        }
        
        try {
            setSaving(true);
            
            const formData = new FormData();
            formData.append('name', template.name);
            formData.append('template_text', template.template_text);
            formData.append('factoid_type', template.factoid_type);
            formData.append('emoji', template.emoji);
            formData.append('color_scheme', template.color_scheme);
            formData.append('priority', template.priority.toString());
            formData.append('is_active', template.is_active ? 'on' : '');
            formData.append('csrfmiddlewaretoken', config.csrf_token);
            
            const response = await fetch(config.api_urls.save, {
                method: 'POST',
                body: formData,
                credentials: 'same-origin'
            });
            
            if (response.ok) {
                window.location.href = '/manage/factoid-templates/';
            } else {
                throw new Error(`Save failed: ${response.status}`);
            }
        } catch (err) {
            console.error('Save error:', err);
            alert('Error saving template: ' + err.message);
        } finally {
            setSaving(false);
        }
    }, [template, config]);
    
    // Update template field
    const updateTemplate = useCallback((field, value) => {
        setTemplate(prev => ({ ...prev, [field]: value }));
    }, []);
    
    // Render loading state
    if (loading) {
        return React.createElement('div', {
            className: 'flex items-center justify-center h-96'
        }, [
            React.createElement('div', {
                className: 'text-center',
                key: 'loading'
            }, [
                React.createElement('div', {
                    className: 'animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto',
                    key: 'spinner'
                }),
                React.createElement('p', {
                    className: 'mt-4 text-gray-600',
                    key: 'text'
                }, 'Loading Factoid Builder...')
            ])
        ]);
    }
    
    // Render error state
    if (error) {
        return React.createElement('div', {
            className: 'bg-red-50 border border-red-200 rounded-lg p-6'
        }, [
            React.createElement('h3', {
                className: 'text-lg font-semibold text-red-800 mb-2',
                key: 'title'
            }, '🚨 Error Loading Factoid Builder'),
            React.createElement('p', {
                className: 'text-red-700 mb-4',
                key: 'message'
            }, error),
            React.createElement('button', {
                className: 'bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700',
                onClick: () => window.location.reload(),
                key: 'retry'
            }, 'Retry')
        ]);
    }
    
    // Main render
    return React.createElement('div', {
        className: 'factoid-builder bg-white rounded-lg shadow-lg'
    }, [
        // Header
        React.createElement('div', {
            className: 'px-6 py-4 border-b border-gray-200',
            key: 'header'
        }, [
            React.createElement('h1', {
                className: 'text-2xl font-bold text-gray-900',
                key: 'title'
            }, config.template ? '✏️ Edit Factoid Template' : '➕ Create New Factoid Template'),
            React.createElement('p', {
                className: 'text-gray-600 mt-1',
                key: 'subtitle'
            }, 'Create dynamic templates with drag-and-drop field insertion and live preview')
        ]),
        
        // Main content grid
        React.createElement('div', {
            className: 'grid grid-cols-1 lg:grid-cols-12 gap-6 p-6',
            key: 'content'
        }, [
            // Fields Panel (3 columns)
            React.createElement('div', {
                className: 'lg:col-span-3',
                key: 'fields-panel'
            }, [
                React.createElement('h3', {
                    className: 'text-lg font-semibold text-gray-900 mb-4',
                    key: 'fields-title'
                }, '📋 Available Fields'),
                React.createElement('div', {
                    className: 'space-y-2 max-h-96 overflow-y-auto',
                    key: 'fields-list'
                }, fields ? Object.entries(fields).flatMap(([category, categoryFields]) => [
                    React.createElement('div', {
                        className: 'text-xs font-semibold text-gray-500 uppercase tracking-wider py-2',
                        key: `category-${category}`
                    }, category.replace('_', ' ')),
                    ...categoryFields.map((field, index) => 
                        React.createElement('div', {
                            className: 'bg-gray-50 border border-gray-200 rounded-lg p-3 cursor-move hover:bg-blue-50 hover:border-blue-300 transition-colors',
                            key: `field-${category}-${index}`,
                            draggable: true,
                            onDragStart: (e) => handleDragStart(e, field.expression),
                            onClick: () => insertField(field.expression)
                        }, [
                            React.createElement('div', {
                                className: 'font-mono text-sm text-blue-600 font-semibold',
                                key: 'expression'
                            }, `{${field.expression}}`),
                            React.createElement('div', {
                                className: 'text-xs text-gray-600 mt-1',
                                key: 'description'
                            }, field.description),
                            field.sample_value && React.createElement('div', {
                                className: 'text-xs text-green-600 mt-1 font-mono',
                                key: 'sample'
                            }, `Example: ${field.sample_value}`)
                        ])
                    )
                ]) : [React.createElement('div', {
                    key: 'loading-fields',
                    className: 'text-gray-500'
                }, 'Loading fields...')])
            ]),
            
            // Template Editor (6 columns)
            React.createElement('div', {
                className: 'lg:col-span-6 space-y-4',
                key: 'editor-panel'
            }, [
                React.createElement('h3', {
                    className: 'text-lg font-semibold text-gray-900',
                    key: 'editor-title'
                }, '✏️ Template Editor'),
                
                // Template Name
                React.createElement('div', { key: 'name-field' }, [
                    React.createElement('label', {
                        className: 'block text-sm font-medium text-gray-700 mb-2',
                        key: 'label'
                    }, 'Template Name'),
                    React.createElement('input', {
                        type: 'text',
                        value: template.name,
                        onChange: (e) => updateTemplate('name', e.target.value),
                        className: 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500',
                        placeholder: 'Enter template name...',
                        key: 'input'
                    })
                ]),
                
                // Template Text
                React.createElement('div', { key: 'text-field' }, [
                    React.createElement('label', {
                        className: 'block text-sm font-medium text-gray-700 mb-2',
                        key: 'label'
                    }, 'Template Text'),
                    React.createElement('textarea', {
                        ref: textareaRef,
                        value: template.template_text,
                        onChange: (e) => updateTemplate('template_text', e.target.value),
                        onDrop: handleDrop,
                        onDragOver: handleDragOver,
                        className: 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 font-mono text-sm',
                        rows: 4,
                        placeholder: 'Enter your factoid template. Drag fields from the left or click them to insert. Use expressions like {council_name} or {calculated.total_debt_per_capita:currency}',
                        key: 'textarea'
                    }),
                    React.createElement('p', {
                        className: 'text-xs text-gray-500 mt-1',
                        key: 'help'
                    }, '💡 Tip: Drag fields from the left panel or click them to insert into your template')
                ]),
                
                // Form fields row
                React.createElement('div', {
                    className: 'grid grid-cols-1 md:grid-cols-3 gap-4',
                    key: 'form-fields'
                }, [
                    // Factoid Type
                    React.createElement('div', { key: 'type-field' }, [
                        React.createElement('label', {
                            className: 'block text-sm font-medium text-gray-700 mb-2',
                            key: 'label'
                        }, 'Type'),
                        React.createElement('select', {
                            value: template.factoid_type,
                            onChange: (e) => updateTemplate('factoid_type', e.target.value),
                            className: 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500',
                            key: 'select'
                        }, [
                            React.createElement('option', { value: 'context', key: 'context' }, 'Context'),
                            React.createElement('option', { value: 'insight', key: 'insight' }, 'Insight'),
                            React.createElement('option', { value: 'comparison', key: 'comparison' }, 'Comparison'),
                            React.createElement('option', { value: 'per_capita', key: 'per_capita' }, 'Per Capita')
                        ])
                    ]),
                    
                    // Emoji
                    React.createElement('div', { key: 'emoji-field' }, [
                        React.createElement('label', {
                            className: 'block text-sm font-medium text-gray-700 mb-2',
                            key: 'label'
                        }, 'Emoji'),
                        React.createElement('input', {
                            type: 'text',
                            value: template.emoji,
                            onChange: (e) => updateTemplate('emoji', e.target.value),
                            className: 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-center text-lg',
                            maxLength: 2,
                            key: 'input'
                        })
                    ]),
                    
                    // Priority
                    React.createElement('div', { key: 'priority-field' }, [
                        React.createElement('label', {
                            className: 'block text-sm font-medium text-gray-700 mb-2',
                            key: 'label'
                        }, 'Priority'),
                        React.createElement('input', {
                            type: 'number',
                            value: template.priority,
                            onChange: (e) => updateTemplate('priority', parseInt(e.target.value) || 0),
                            className: 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500',
                            min: 0,
                            max: 100,
                            key: 'input'
                        })
                    ])
                ])
            ]),
            
            // Live Preview (3 columns)
            React.createElement('div', {
                className: 'lg:col-span-3',
                key: 'preview-panel'
            }, [
                React.createElement('h3', {
                    className: 'text-lg font-semibold text-gray-900 mb-4',
                    key: 'preview-title'
                }, '👀 Live Preview'),
                React.createElement('div', {
                    className: 'bg-blue-50 border border-blue-200 rounded-lg p-4 min-h-32',
                    key: 'preview-container'
                }, [
                    React.createElement('div', {
                        className: 'text-center',
                        key: 'preview-content'
                    }, [
                        template.emoji && React.createElement('div', {
                            className: 'text-2xl mb-2',
                            key: 'emoji'
                        }, template.emoji),
                        React.createElement('div', {
                            className: 'text-sm font-medium text-gray-800',
                            key: 'text'
                        }, previewText || 'Type template text to see preview...')
                    ])
                ]),
                
                // Preview errors
                previewErrors.length > 0 && React.createElement('div', {
                    className: 'mt-3 bg-yellow-50 border border-yellow-200 rounded-lg p-3',
                    key: 'preview-errors'
                }, [
                    React.createElement('h4', {
                        className: 'text-sm font-semibold text-yellow-800 mb-2',
                        key: 'title'
                    }, '⚠️ Preview Issues'),
                    React.createElement('ul', {
                        className: 'text-xs text-yellow-700 space-y-1',
                        key: 'list'
                    }, previewErrors.map((error, index) => 
                        React.createElement('li', {
                            key: index
                        }, `• ${error}`)
                    ))
                ])
            ])
        ]),
        
        // Action buttons
        React.createElement('div', {
            className: 'px-6 py-4 border-t border-gray-200 flex justify-between items-center',
            key: 'actions'
        }, [
            React.createElement('div', {
                className: 'flex items-center space-x-2',
                key: 'left-actions'
            }, [
                React.createElement('label', {
                    className: 'flex items-center',
                    key: 'active-toggle'
                }, [
                    React.createElement('input', {
                        type: 'checkbox',
                        checked: template.is_active,
                        onChange: (e) => updateTemplate('is_active', e.target.checked),
                        className: 'rounded border-gray-300 text-blue-600 focus:ring-blue-500',
                        key: 'checkbox'
                    }),
                    React.createElement('span', {
                        className: 'ml-2 text-sm text-gray-700',
                        key: 'label'
                    }, 'Active template')
                ])
            ]),
            React.createElement('div', {
                className: 'flex space-x-3',
                key: 'right-actions'
            }, [
                React.createElement('a', {
                    href: '/manage/factoid-templates/',
                    className: 'px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500',
                    key: 'cancel'
                }, '❌ Cancel'),
                React.createElement('button', {
                    onClick: saveTemplate,
                    disabled: saving || !template.name.trim() || !template.template_text.trim(),
                    className: `px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white ${
                        saving || !template.name.trim() || !template.template_text.trim()
                            ? 'bg-gray-400 cursor-not-allowed'
                            : 'bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
                    }`,
                    key: 'save'
                }, saving ? '⏳ Saving...' : '💾 Save Template')
            ])
        ])
    ]);
};

// Make component available globally
window.FactoidBuilder = FactoidBuilder;
console.log('✅ FactoidBuilder component loaded successfully');