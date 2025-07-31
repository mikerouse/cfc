/**
 * FactoidBuilder - Main React component for visual factoid template creation
 * 
 * This component orchestrates the entire factoid building experience:
 * - Field discovery and display
 * - Template editing with live preview
 * - Drag and drop functionality
 * - Saving and validation
 */

import React, { useState, useEffect, useCallback } from 'react';
import LegacyFieldPicker from './LegacyFieldPicker';
import LegacyTemplateEditor from './LegacyTemplateEditor';
import LegacyLivePreview from './LegacyLivePreview';

const FactoidBuilder = ({ config }) => {
    console.log('🎨 FactoidBuilder component mounting with config:', config);
    
    // Component state
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
    
    console.log('📊 Initial component state:', {
        fields,
        template,
        loading,
        error,
        saving
    });
    
    // API helper function
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
    
    // Load available fields on component mount
    useEffect(() => {
        console.log('🔍 FactoidBuilder: Starting field loading...');
        console.log('🔗 API URL:', config.api_urls.fields);
        console.log('🔑 CSRF Token:', config.csrf_token);
        
        const loadFields = async () => {
            try {
                console.log('📡 Making API call to load fields...');
                setLoading(true);
                const response = await apiCall(config.api_urls.fields);
                
                console.log('📥 API Response:', response);
                
                if (response.success) {
                    console.log('✅ Fields loaded successfully:', response.fields);
                    setFields(response.fields);
                } else {
                    console.error('❌ API returned error:', response.error);
                    setError(response.error || 'Failed to load fields');
                }
            } catch (err) {
                console.error('❌ API call failed:', err);
                console.error('Error details:', {
                    message: err.message,
                    stack: err.stack,
                    url: config.api_urls.fields
                });
                setError(`Failed to load fields: ${err.message}`);
            } finally {
                console.log('🏁 Field loading completed, setting loading=false');
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
                        council_slug: 'worcestershire', // Use sample council
                        year_label: '2024/25'
                    })
                });
                
                if (response.success) {
                    setPreviewText(response.rendered_text || 'Preview not available');
                    setPreviewErrors(response.errors || []);
                } else {
                    setPreviewText(template.template_text); // Fallback to original
                    setPreviewErrors([response.error || 'Preview failed']);
                }
            } catch (err) {
                setPreviewText(template.template_text); // Fallback to original
                setPreviewErrors([`Preview error: ${err.message}`]);
            }
        };
        
        // Debounce preview updates
        const timeoutId = setTimeout(updatePreview, 500);
        return () => clearTimeout(timeoutId);
    }, [template.template_text, apiCall, config.api_urls.preview]);
    
    // Handle field drag and drop
    const handleFieldDrop = useCallback((fieldVariable, cursorPosition) => {
        const textBefore = template.template_text.substring(0, cursorPosition);
        const textAfter = template.template_text.substring(cursorPosition);
        const newText = `${textBefore}{${fieldVariable}:currency}${textAfter}`;
        
        setTemplate(prev => ({
            ...prev,
            template_text: newText
        }));
    }, [template.template_text]);
    
    // Handle template save
    const handleSave = async () => {
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
            
            // Create form data for Django form submission
            const formData = new FormData();
            formData.append('name', template.name);
            formData.append('template_text', template.template_text);
            formData.append('factoid_type', template.factoid_type);
            formData.append('emoji', template.emoji);
            formData.append('color_scheme', template.color_scheme);
            formData.append('priority', template.priority);
            formData.append('is_active', template.is_active ? 'on' : '');
            formData.append('csrfmiddlewaretoken', config.csrf_token);
            
            const response = await fetch(config.api_urls.save, {
                method: 'POST',
                body: formData,
                credentials: 'same-origin',
                headers: {
                    'X-CSRFToken': config.csrf_token
                }
            });
            
            if (response.ok && response.url !== window.location.href) {
                // Django redirected, which means success
                window.location.href = response.url;
            } else {
                // Handle error case
                const text = await response.text();
                console.error('Save failed:', text);
                alert('Failed to save template. Please check the form and try again.');
            }
        } catch (err) {
            console.error('Save error:', err);
            alert(`Save failed: ${err.message}`);
        } finally {
            setSaving(false);
        }
    };
    
    // Handle template field changes
    const handleTemplateChange = (field, value) => {
        setTemplate(prev => ({
            ...prev,
            [field]: value
        }));
    };
    
    // Render loading state
    if (loading) {
        return (
            <div className="loading-spinner">
                <div className="animate-pulse">
                    <svg className="w-8 h-8 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                    </svg>
                    Loading Visual Factoid Builder...
                </div>
            </div>
        );
    }
    
    // Render error state
    if (error) {
        return (
            <div className="error-message">
                <h3 className="font-bold mb-2">Error Loading Builder</h3>
                <p>{error}</p>
                <button 
                    onClick={() => window.location.reload()} 
                    className="mt-4 btn btn-primary"
                >
                    Retry
                </button>
            </div>
        );
    }
    
    // Main render
    return (
        <div className="grid grid-cols-12 h-full">
            {/* Field Picker Sidebar */}
            <div className="col-span-4 field-picker">
                <LegacyFieldPicker
                    fields={fields}
                    onFieldDrop={handleFieldDrop}
                />
            </div>
            
            {/* Template Editor Main Area */}
            <div className="col-span-8 template-editor">
                <div className="editor-header">
                    <h1 className="editor-title">
                        {config.template ? 'Edit' : 'Create'} Factoid Template
                    </h1>
                    <p className="editor-subtitle">
                        Build dynamic factoids with drag-and-drop fields and live preview
                    </p>
                </div>
                
                <div className="editor-content">
                    <LegacyTemplateEditor
                        template={template}
                        onChange={handleTemplateChange}
                        onFieldDrop={handleFieldDrop}
                    />
                    
                    <LegacyLivePreview
                        previewText={previewText}
                        errors={previewErrors}
                        template={template}
                    />
                </div>
                
                <div className="action-buttons">
                    <button 
                        onClick={handleSave}
                        disabled={saving}
                        className="btn btn-primary"
                    >
                        {saving ? (
                            <>
                                <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                                </svg>
                                Saving...
                            </>
                        ) : (
                            <>
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
                                </svg>
                                {config.template ? 'Update Template' : 'Create Template'}
                            </>
                        )}
                    </button>
                    
                    <a 
                        href="/manage/factoid-templates/" 
                        className="btn btn-secondary"
                    >
                        Cancel
                    </a>
                </div>
            </div>
        </div>
    );
};

export default FactoidBuilder;