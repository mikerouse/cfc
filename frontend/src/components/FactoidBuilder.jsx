/**
 * Enhanced Factoid Builder - Main Component
 * 
 * A modern React component that provides:
 * - Real-time field discovery and updates
 * - Drag-and-drop template building
 * - Live preview with actual data
 * - Seamless Django API integration
 */
import { useState, useEffect, useCallback, useRef } from 'react';
// Logger utility for capturing client-side issues
import { logActivity } from '../utils/logger';
import FieldDiscovery from './FieldDiscovery';
import TemplateEditor from './TemplateEditor';
import LivePreview from './LivePreview';
import { useFactoidAPI } from '../hooks/useFactoidAPI';

const FactoidBuilder = () => {
  console.log('🎨 Enhanced FactoidBuilder mounting...');

  // Check if we're in integrated mode
  const isIntegratedMode = window?.FACTOID_BUILDER_CONFIG?.isIntegratedMode || false;

  // Core state
  const [template, setTemplate] = useState({
    name: '',
    template_text: '',
    factoid_type: 'context',
    emoji: '📊',
    color_scheme: 'blue',
    priority: 50,
    is_active: true,
  });
  const [templateId, setTemplateId] = useState(null);

  const [isDirty, setIsDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  
  // API hook for real-time features
  const {
    fields,
    fieldGroups,
    previewData,
    validationErrors,
    isLoading,
    discoverFields,
    validateTemplate,
    generatePreview,
    saveTemplate,
  } = useFactoidAPI();

  // Refs for drag and drop
  const templateEditorRef = useRef();

  // Initialize field discovery on mount
  useEffect(() => {
    console.log('🔍 Discovering available fields...');
    discoverFields();
    
    // Emit ready event for integration
    if (isIntegratedMode) {
      const readyEvent = new CustomEvent('factoidBuilderReady', {
        detail: { component: 'FactoidBuilder' }
      });
      window.dispatchEvent(readyEvent);
    }
  }, [discoverFields, isIntegratedMode]);

  // Template change handler
  const handleTemplateChange = useCallback((field, value) => {
    setTemplate(prev => ({
      ...prev,
      [field]: value
    }));
    setIsDirty(true);

    // Auto-validate on template text changes
    if (field === 'template_text') {
      try {
        validateTemplate(value, templateId);
        generatePreview(value, { templateId });
      } catch (err) {
        console.error('Template change processing failed:', err);
        logActivity('template_change_error', { field }, err);
      }
    }
  }, [validateTemplate, generatePreview]);

  // Field drop handler for drag and drop
  const handleFieldDrop = useCallback((fieldVariable, formatType = 'default') => {
    try {
      const cursorPosition = templateEditorRef.current?.getCursorPosition() || 0;
      const currentText = template.template_text;

      // Build field placeholder with formatting
      const formatSuffix = formatType !== 'default' ? `:${formatType}` : '';
      const fieldPlaceholder = `{${fieldVariable}${formatSuffix}}`;

      // Insert at cursor position
      const newText =
        currentText.substring(0, cursorPosition) +
        fieldPlaceholder +
        currentText.substring(cursorPosition);

      handleTemplateChange('template_text', newText);

      // Focus back to editor
      setTimeout(() => {
        templateEditorRef.current?.focus();
        templateEditorRef.current?.setCursorPosition(cursorPosition + fieldPlaceholder.length);
      }, 50);
    } catch (err) {
      console.error('Field drop failed:', err);
      logActivity('field_drop_error', { fieldVariable }, err);
    }
  }, [template.template_text, handleTemplateChange]);

  // Save handler
  const handleSave = async () => {
    if (!template.name.trim()) {
      alert('Please enter a template name');
      return;
    }

    if (!template.template_text.trim()) {
      alert('Please enter template text');
      return;
    }

    setSaving(true);
    try {
      const result = await saveTemplate(template);
      if (result.success) {
        setTemplateId(result.data.id);
        setIsDirty(false);
        logActivity('template_saved', { id: result.data.id });
        alert('Template saved successfully!');
      } else {
        logActivity('template_save_failed', { error: result.error });
        alert(`Save failed: ${result.error}`);
      }
    } catch (error) {
      console.error('Save error:', error);
      logActivity('template_save_error', {}, error);
      alert(`Save failed: ${error.message}`);
    } finally {
      setSaving(false);
    }
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.ctrlKey && e.key === 's') {
        e.preventDefault();
        handleSave();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleSave]);

  return (
    <div className={`factoid-builder ${isIntegratedMode ? 'integrated-mode' : 'standalone-mode'} ${isIntegratedMode ? 'p-6' : 'h-full'} flex flex-col`}>
      {/* Header - simplified for integrated mode */}
      {!isIntegratedMode && (
        <div className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">
                ✨ Enhanced Factoid Builder
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                Build dynamic factoids with real-time field integration
              </p>
            </div>
            
            <div className="flex items-center space-x-3">
              {isDirty && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                  <div className="w-2 h-2 bg-yellow-400 rounded-full mr-1.5"></div>
                  Unsaved changes
                </span>
              )}
              
              <button
                onClick={handleSave}
                disabled={saving || !template.name.trim() || !template.template_text.trim()}
                className={`inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white ${
                  saving || !template.name.trim() || !template.template_text.trim()
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
                }`}
              >
                {saving ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-3 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Saving...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
                    </svg>
                    Save Template
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Integrated mode toolbar */}
      {isIntegratedMode && (
        <div className="flex items-center justify-between mb-6 p-4 bg-white rounded-lg border border-gray-200">
          <div className="flex items-center space-x-4">
            <h3 className="text-lg font-semibold text-gray-900">Factoid Builder</h3>
            {isDirty && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                <div className="w-2 h-2 bg-yellow-400 rounded-full mr-1.5"></div>
                Unsaved changes
              </span>
            )}
          </div>
          
          <button
            onClick={handleSave}
            disabled={saving || !template.name.trim() || !template.template_text.trim()}
            className={`inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white ${
              saving || !template.name.trim() || !template.template_text.trim()
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500'
            }`}
          >
            {saving ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Saving...
              </>
            ) : (
              <>
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
                </svg>
                Save Template
              </>
            )}
          </button>
        </div>
      )}

      {/* Main Content Grid */}
      <div className={`flex-1 grid grid-cols-12 ${isIntegratedMode ? 'gap-6' : 'h-full'}`}>
        
        {/* Field Discovery Sidebar */}
        <div className={`col-span-3 ${isIntegratedMode ? 'bg-white rounded-lg border border-gray-200' : 'bg-gray-50 border-r border-gray-200'} overflow-y-auto`}>
          <FieldDiscovery
            fieldGroups={fieldGroups}
            isLoading={isLoading}
            onFieldDrop={handleFieldDrop}
            onRefresh={discoverFields}
          />
        </div>

        {/* Template Editor */}
        <div className={`col-span-6 ${isIntegratedMode ? 'bg-white rounded-lg border border-gray-200' : ''} flex flex-col`}>
          <TemplateEditor
            ref={templateEditorRef}
            template={template}
            onChange={handleTemplateChange}
            onFieldDrop={handleFieldDrop}
            validationErrors={validationErrors}
            isDirty={isDirty}
          />
        </div>

        {/* Live Preview Sidebar */}
        <div className={`col-span-3 ${isIntegratedMode ? 'bg-white rounded-lg border border-gray-200' : 'bg-gray-50 border-l border-gray-200'} overflow-y-auto`}>
          <LivePreview
            template={template}
            previewData={previewData}
            validationErrors={validationErrors}
            isLoading={isLoading}
          />
        </div>
      </div>

      {/* Status Bar - only show in standalone mode */}
      {!isIntegratedMode && (
        <div className="bg-gray-50 border-t border-gray-200 px-6 py-3">
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center space-x-4">
              <span className="text-gray-600">
                Fields available: {Object.values(fieldGroups).flat().length}
              </span>
              
              {template.template_text && (
                <span className="text-gray-600">
                  Referenced fields: {(template.template_text.match(/\{[^}]+\}/g) || []).length}
                </span>
              )}
              
              {validationErrors.length > 0 && (
                <span className="text-red-600 font-medium">
                  ⚠️ {validationErrors.length} validation error{validationErrors.length !== 1 ? 's' : ''}
                </span>
              )}
            </div>
            
            <div className="text-gray-500">
              Press Ctrl+S to save
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FactoidBuilder;
