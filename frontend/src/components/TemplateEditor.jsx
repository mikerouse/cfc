/**
 * TemplateEditor Component
 * 
 * Advanced template editor with drag-and-drop support, syntax highlighting,
 * and real-time validation.
 */
import { forwardRef, useImperativeHandle, useRef, useState, useEffect } from 'react';

const TemplateEditor = forwardRef(({ 
  template, 
  onChange, 
  onFieldDrop, 
  validationErrors, 
  isDirty 
}, ref) => {
  const textareaRef = useRef();
  const [cursorPosition, setCursorPosition] = useState(0);
  const [isDragOver, setIsDragOver] = useState(false);

  // Expose methods to parent component
  useImperativeHandle(ref, () => ({
    focus: () => textareaRef.current?.focus(),
    getCursorPosition: () => cursorPosition,
    setCursorPosition: (pos) => {
      if (textareaRef.current) {
        textareaRef.current.setSelectionRange(pos, pos);
        textareaRef.current.focus();
      }
    }
  }));

  // Track cursor position
  const handleSelectionChange = () => {
    if (textareaRef.current) {
      setCursorPosition(textareaRef.current.selectionStart);
    }
  };

  // Drag and drop handlers
  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    
    try {
      const data = JSON.parse(e.dataTransfer.getData('application/json'));
      if (data.type === 'field' && data.field) {
        const rect = textareaRef.current.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        // Approximate cursor position from mouse coordinates
        const textarea = textareaRef.current;
        const style = window.getComputedStyle(textarea);
        const lineHeight = parseInt(style.lineHeight);
        const charWidth = parseInt(style.fontSize) * 0.6; // Approximate
        
        const line = Math.floor(y / lineHeight);
        const char = Math.floor(x / charWidth);
        
        // Calculate approximate text position
        const lines = textarea.value.split('\n');
        let position = 0;
        for (let i = 0; i < line && i < lines.length; i++) {
          position += lines[i].length + 1; // +1 for newline
        }
        position += Math.min(char, lines[line]?.length || 0);
        
        // Update cursor position and insert field
        setCursorPosition(position);
        onFieldDrop(data.field.variable_name, 'default');
      }
    } catch (error) {
      console.error('Drop error:', error);
    }
  };

  return (
    <div className="template-editor flex flex-col h-full">
      {/* Editor Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          ✏️ Template Editor
        </h3>
        
        {/* Template Name */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Template Name *
          </label>
          <input
            type="text"
            value={template.name}
            onChange={(e) => onChange('name', e.target.value)}
            placeholder="e.g., Council debt per capita comparison"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Template Settings Row */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          {/* Factoid Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Type
            </label>
            <select
              value={template.factoid_type}
              onChange={(e) => onChange('factoid_type', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="context">📋 Context</option>
              <option value="comparison">⚖️ Comparison</option>
              <option value="trend">📈 Trend</option>
              <option value="ranking">🏆 Ranking</option>
              <option value="per_capita">👤 Per Capita</option>
              <option value="ratio">🔢 Ratio</option>
              <option value="milestone">🎯 Milestone</option>
              <option value="sustainability">🌱 Sustainability</option>
              <option value="percent_change">📊 % Change</option>
              <option value="anomaly">⚠️ Anomaly</option>
            </select>
          </div>

          {/* Emoji */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Emoji
            </label>
            <input
              type="text"
              value={template.emoji}
              onChange={(e) => onChange('emoji', e.target.value)}
              placeholder="📊"
              maxLength="10"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Color Scheme */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Color
            </label>
            <select
              value={template.color_scheme}
              onChange={(e) => onChange('color_scheme', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="blue">🔵 Blue</option>
              <option value="green">🟢 Green</option>
              <option value="red">🔴 Red</option>
              <option value="orange">🟠 Orange</option>
              <option value="purple">🟣 Purple</option>
            </select>
          </div>

          {/* Priority */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Priority
            </label>
            <input
              type="number"
              value={template.priority}
              onChange={(e) => onChange('priority', parseInt(e.target.value) || 0)}
              min="0"
              max="100"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Template Text Editor */}
      <div className="flex-1 p-6">
        <div className="h-full flex flex-col">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Template Text *
          </label>
          
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={template.template_text}
              onChange={(e) => {
                onChange('template_text', e.target.value);
                handleSelectionChange();
              }}
              onSelect={handleSelectionChange}
              onKeyUp={handleSelectionChange}
              onClick={handleSelectionChange}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              placeholder="Enter your factoid template. Drag fields from the sidebar or use {field_name} syntax.

Example: {council_name} has total debt of {financial.total_debt:currency} which is {calculated.debt_per_capita:currency} per resident."
              className={`w-full h-full p-4 border-2 border-dashed rounded-lg font-mono text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors ${
                isDragOver 
                  ? 'border-blue-400 bg-blue-50' 
                  : validationErrors.length > 0 
                    ? 'border-red-300 bg-red-50' 
                    : 'border-gray-300'
              }`}
            />
            
            {/* Drop Overlay */}
            {isDragOver && (
              <div className="absolute inset-0 bg-blue-100 bg-opacity-75 flex items-center justify-center rounded-lg pointer-events-none">
                <div className="text-blue-600 font-semibold text-lg">
                  📋 Drop field here
                </div>
              </div>
            )}
          </div>

          {/* Validation Errors */}
          {validationErrors.length > 0 && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <h4 className="text-sm font-semibold text-red-800 mb-2">
                ⚠️ Validation Errors
              </h4>
              <ul className="text-sm text-red-700 space-y-1">
                {validationErrors.map((error, index) => (
                  <li key={index}>• {error}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Help Text */}
          <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <h4 className="text-sm font-semibold text-blue-800 mb-2">
              💡 Template Help
            </h4>
            <div className="text-sm text-blue-700 space-y-1">
              <div><strong>Syntax:</strong> Use {`{field_name}`} or {`{field_name:format}`}</div>
              <div><strong>Formats:</strong> :currency, :percentage, :number, :decimal</div>
              <div><strong>Examples:</strong></div>
              <ul className="ml-4 mt-1 space-y-1 text-xs font-mono">
                <li>{`{council_name}`} → Worcestershire County Council</li>
                <li>{`{financial.total_debt:currency}`} → £1,234,567</li>
                <li>{`{calculated.change_percent:percentage}`} → 5.2%</li>
              </ul>
            </div>
          </div>

          {/* Active Toggle */}
          <div className="mt-4 flex items-center">
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
    </div>
  );
});

TemplateEditor.displayName = 'TemplateEditor';

export default TemplateEditor;
