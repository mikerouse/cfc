/**
 * TemplateEditor - Rich template editing component with drag-and-drop support
 * 
 * This component provides a sophisticated template editing experience with:
 * - Drag and drop field insertion
 * - Syntax highlighting for variables
 * - Auto-completion suggestions
 * - Form field management
 */

const { useState, useRef, useEffect } = React;

const TemplateEditor = ({ template, onChange, onFieldDrop }) => {
    const textareaRef = useRef(null);
    const [isDragOver, setIsDragOver] = useState(false);
    const [cursorPosition, setCursorPosition] = useState(0);
    
    // Track cursor position for drag and drop
    useEffect(() => {
        const textarea = textareaRef.current;
        if (!textarea) return;
        
        const handleSelectionChange = () => {
            setCursorPosition(textarea.selectionStart);
        };
        
        textarea.addEventListener('selectionchange', handleSelectionChange);
        textarea.addEventListener('click', handleSelectionChange);
        textarea.addEventListener('keyup', handleSelectionChange);
        
        return () => {
            textarea.removeEventListener('selectionchange', handleSelectionChange);
            textarea.removeEventListener('click', handleSelectionChange);
            textarea.removeEventListener('keyup', handleSelectionChange);
        };
    }, []);
    
    // Handle drag over
    const handleDragOver = (event) => {
        event.preventDefault();
        setIsDragOver(true);
        
        // Update cursor position based on mouse position
        const textarea = textareaRef.current;
        if (textarea) {
            // Get approximate cursor position from mouse coordinates
            const rect = textarea.getBoundingClientRect();
            const x = event.clientX - rect.left;
            const y = event.clientY - rect.top;
            
            // Rough estimation of character position
            const lineHeight = 24; // Approximate
            const charWidth = 8; // Approximate
            const lineNumber = Math.floor(y / lineHeight);
            const charNumber = Math.floor(x / charWidth);
            
            // This is a simplified approach - in production you'd want more precise positioning
            const lines = textarea.value.split('\n');
            let position = 0;
            for (let i = 0; i < lineNumber && i < lines.length; i++) {
                position += lines[i].length + 1; // +1 for newline
            }
            position += Math.min(charNumber, lines[lineNumber]?.length || 0);
            
            setCursorPosition(Math.min(position, textarea.value.length));
        }
    };
    
    // Handle drag leave
    const handleDragLeave = (event) => {
        // Only set drag over to false if we're actually leaving the textarea
        if (!event.currentTarget.contains(event.relatedTarget)) {
            setIsDragOver(false);
        }
    };
    
    // Handle drop
    const handleDrop = (event) => {
        event.preventDefault();
        setIsDragOver(false);
        
        try {
            const data = JSON.parse(event.dataTransfer.getData('application/json'));
            if (data.type === 'field') {
                // Determine appropriate format based on field type
                let formatSuffix = ':currency'; // default
                switch (data.format_hint) {
                    case 'percentage':
                        formatSuffix = ':percentage';
                        break;
                    case 'number':
                        formatSuffix = ':number';
                        break;
                    case 'text':
                        formatSuffix = '';
                        break;
                    case 'currency_per_capita':
                        formatSuffix = ':currency';
                        break;
                }
                
                const fieldVariable = `{${data.variable}${formatSuffix}}`;
                onFieldDrop(data.variable + formatSuffix, cursorPosition);
                
                // Focus back on textarea
                setTimeout(() => {
                    textareaRef.current?.focus();
                }, 50);
            }
        } catch (err) {
            console.error('Error handling drop:', err);
        }
    };
    
    // Handle template text change
    const handleTemplateTextChange = (event) => {
        const value = event.target.value;
        onChange('template_text', value);
        setCursorPosition(event.target.selectionStart);
    };
    
    // Highlight template variables in the text
    const highlightVariables = (text) => {
        // This is a simplified version - in production you'd want proper syntax highlighting
        return text.replace(/\{([^}]+)\}/g, '<mark class="bg-blue-100 text-blue-800 px-1 rounded">$&</mark>');
    };
    
    return (
        <div className="space-y-6">
            {/* Template Name */}
            <div className="form-group">
                <label className="form-label">
                    Template Name
                    <span className="text-red-500 ml-1">*</span>
                </label>
                <input
                    type="text"
                    value={template.name}
                    onChange={(e) => onChange('name', e.target.value)}
                    placeholder="e.g., Debt per capita comparison"
                    className="form-input"
                    required
                />
                <p className="mt-2 text-sm text-gray-600">
                    A descriptive name that helps identify this template
                </p>
            </div>
            
            {/* Template Text Editor */}
            <div className="form-group">
                <label className="form-label">
                    Template Text
                    <span className="text-red-500 ml-1">*</span>
                </label>
                
                {/* Drop Zone Overlay */}
                <div className="relative">
                    <textarea
                        ref={textareaRef}
                        value={template.template_text}
                        onChange={handleTemplateTextChange}
                        onDragOver={handleDragOver}
                        onDragLeave={handleDragLeave}
                        onDrop={handleDrop}
                        placeholder="**£{calculated.total_debt_per_capita:currency}** per head in {council_name} ({year_label})
                        
Drag fields from the sidebar to insert them, or type your template text using the {variable:format} syntax."
                        className={`form-textarea ${isDragOver ? 'drag-over border-blue-500 bg-blue-50' : ''}`}
                        rows="8"
                        required
                    />
                    
                    {/* Drop indicator */}
                    {isDragOver && (
                        <div className="absolute inset-0 border-2 border-dashed border-blue-500 bg-blue-50 bg-opacity-50 rounded-lg flex items-center justify-center pointer-events-none">
                            <div className="bg-white px-4 py-2 rounded-lg shadow-lg border-2 border-blue-500">
                                <p className="text-blue-700 font-semibold">Drop field here to insert</p>
                            </div>
                        </div>
                    )}
                </div>
                
                <div className="mt-2 text-sm text-gray-600">
                    <p className="mb-2">
                        <strong>Format examples:</strong>
                    </p>
                    <ul className="list-disc list-inside space-y-1 text-xs font-mono bg-gray-50 p-3 rounded">
                        <li><code>{`{calculated.total_debt_per_capita:currency}`}</code> → £1,234</li>
                        <li><code>{`{calculated.change_percent:percentage}`}</code> → 5.2%</li>
                        <li><code>{`{council_name}`}</code> → Worcestershire County Council</li>
                        <li><code>{`{financial.total_debt:number}`}</code> → 1,234,567</li>
                    </ul>
                </div>
            </div>
            
            {/* Template Settings Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Factoid Type */}
                <div className="form-group">
                    <label className="form-label">Factoid Type</label>
                    <select
                        value={template.factoid_type}
                        onChange={(e) => onChange('factoid_type', e.target.value)}
                        className="form-input"
                    >
                        <option value="context">Context</option>
                        <option value="comparison">Comparison</option>
                        <option value="trend">Trend</option>
                        <option value="ranking">Ranking</option>
                        <option value="per_capita">Per Capita</option>
                        <option value="ratio">Ratio</option>
                        <option value="milestone">Milestone</option>
                        <option value="sustainability">Sustainability</option>
                    </select>
                </div>
                
                {/* Emoji */}
                <div className="form-group">
                    <label className="form-label">Emoji</label>
                    <input
                        type="text"
                        value={template.emoji}
                        onChange={(e) => onChange('emoji', e.target.value)}
                        placeholder="📊"
                        className="form-input"
                        maxLength="10"
                    />
                </div>
                
                {/* Priority */}
                <div className="form-group">
                    <label className="form-label">Priority</label>
                    <input
                        type="number"
                        value={template.priority}
                        onChange={(e) => onChange('priority', parseInt(e.target.value) || 0)}
                        placeholder="50"
                        className="form-input"
                        min="0"
                        max="100"
                    />
                    <p className="mt-1 text-xs text-gray-500">Higher values show first</p>
                </div>
            </div>
            
            {/* Additional Settings Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Color Scheme */}
                <div className="form-group">
                    <label className="form-label">Color Scheme</label>
                    <select
                        value={template.color_scheme}
                        onChange={(e) => onChange('color_scheme', e.target.value)}
                        className="form-input"
                    >
                        <option value="blue">Blue</option>
                        <option value="green">Green</option>
                        <option value="red">Red</option>
                        <option value="purple">Purple</option>
                        <option value="orange">Orange</option>
                        <option value="gray">Gray</option>
                    </select>
                </div>
                
                {/* Active Toggle */}
                <div className="form-group">
                    <label className="form-label">Status</label>
                    <div className="flex items-center mt-2">
                        <input
                            type="checkbox"
                            id="is_active"
                            checked={template.is_active}
                            onChange={(e) => onChange('is_active', e.target.checked)}
                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        />
                        <label htmlFor="is_active" className="ml-2 block text-sm text-gray-900">
                            Active (will appear in factoid playlists)
                        </label>
                    </div>
                </div>
            </div>
            
            {/* Validation Messages */}
            {!template.name.trim() && (
                <div className="text-red-600 text-sm">
                    ⚠️ Template name is required
                </div>
            )}
            
            {!template.template_text.trim() && (
                <div className="text-red-600 text-sm">
                    ⚠️ Template text is required
                </div>
            )}
        </div>
    );
};

// Make component available globally
window.TemplateEditor = TemplateEditor;