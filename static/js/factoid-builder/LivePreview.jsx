/**
 * LivePreview - Real-time preview of factoid templates
 * 
 * This component shows how the factoid will look with actual data,
 * including error handling and formatting preview.
 */

const { useState, useEffect } = React;

const LivePreview = ({ previewText, errors, template }) => {
    const [isLoading, setIsLoading] = useState(false);
    
    // Simulate loading state for better UX
    useEffect(() => {
        setIsLoading(true);
        const timer = setTimeout(() => setIsLoading(false), 300);
        return () => clearTimeout(timer);
    }, [previewText]);
    
    // Get color scheme styles
    const getColorScheme = (scheme) => {
        const schemes = {
            blue: {
                bg: 'bg-blue-50',
                border: 'border-blue-200',
                text: 'text-blue-900',
                accent: 'text-blue-600'
            },
            green: {
                bg: 'bg-green-50',
                border: 'border-green-200',
                text: 'text-green-900',
                accent: 'text-green-600'
            },
            red: {
                bg: 'bg-red-50',
                border: 'border-red-200',
                text: 'text-red-900',
                accent: 'text-red-600'
            },
            purple: {
                bg: 'bg-purple-50',
                border: 'border-purple-200',
                text: 'text-purple-900',
                accent: 'text-purple-600'
            },
            orange: {
                bg: 'bg-orange-50',
                border: 'border-orange-200',
                text: 'text-orange-900',
                accent: 'text-orange-600'
            },
            gray: {
                bg: 'bg-gray-50',
                border: 'border-gray-200',
                text: 'text-gray-900',
                accent: 'text-gray-600'
            }
        };
        
        return schemes[scheme] || schemes.blue;
    };
    
    const colorScheme = getColorScheme(template.color_scheme);
    
    // Format preview text for display (convert markdown-style bold)
    const formatPreviewText = (text) => {
        if (!text) return '';
        
        // Convert **text** to bold
        return text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    };
    
    // Check if preview text contains unresolved variables
    const hasUnresolvedVariables = (text) => {
        return text && /\{[^}]+\}/.test(text);
    };
    
    return (
        <div className="live-preview">
            <div className="preview-content">
                <div className="preview-title">
                    📱 Live Preview
                    {template.emoji && (
                        <span className="ml-2 text-2xl">{template.emoji}</span>
                    )}
                </div>
                
                {/* Loading State */}
                {isLoading ? (
                    <div className="preview-text bg-gray-100 text-gray-500">
                        <div className="flex items-center justify-center">
                            <svg className="animate-spin -ml-1 mr-3 h-5 w-5" fill="none" viewBox="0 0 24 24">
                                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25"></circle>
                                <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" className="opacity-75"></path>
                            </svg>
                            Updating preview...
                        </div>
                    </div>
                ) : (
                    <>
                        {/* Preview Text */}
                        <div className={`preview-text ${colorScheme.bg} ${colorScheme.border} ${colorScheme.text} border-2`}>
                            {previewText ? (
                                <div 
                                    dangerouslySetInnerHTML={{ 
                                        __html: formatPreviewText(previewText) 
                                    }} 
                                />
                            ) : (
                                <div className="preview-empty">
                                    Type template text to see preview...
                                </div>
                            )}
                            
                            {/* Warning for unresolved variables */}
                            {hasUnresolvedVariables(previewText) && (
                                <div className="mt-3 p-2 bg-yellow-100 border border-yellow-300 rounded text-yellow-800 text-sm">
                                    ⚠️ Contains unresolved variables - check field names and formatting
                                </div>
                            )}
                        </div>
                        
                        {/* Error Messages */}
                        {errors && errors.length > 0 && (
                            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                                <h4 className="font-semibold text-red-800 mb-2">
                                    ⚠️ Preview Errors
                                </h4>
                                <ul className="text-sm text-red-700 space-y-1">
                                    {errors.map((error, index) => (
                                        <li key={index} className="flex items-start">
                                            <span className="mr-2">•</span>
                                            <span>{error}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
                        
                        {/* Factoid Metadata Preview */}
                        <div className="mt-4 p-3 bg-gray-50 border border-gray-200 rounded-lg">
                            <h4 className="font-semibold text-gray-700 mb-2">
                                📋 Factoid Properties
                            </h4>
                            <div className="grid grid-cols-2 gap-4 text-sm">
                                <div>
                                    <span className="text-gray-600">Type:</span>
                                    <span className="ml-2 font-medium capitalize">
                                        {template.factoid_type.replace('_', ' ')}
                                    </span>
                                </div>
                                <div>
                                    <span className="text-gray-600">Priority:</span>
                                    <span className="ml-2 font-medium">{template.priority}</span>
                                </div>
                                <div>
                                    <span className="text-gray-600">Color:</span>
                                    <span className={`ml-2 font-medium capitalize ${colorScheme.accent}`}>
                                        {template.color_scheme}
                                    </span>
                                </div>
                                <div>
                                    <span className="text-gray-600">Status:</span>
                                    <span 
                                        className={`ml-2 font-medium ${
                                            template.is_active ? 'text-green-600' : 'text-red-600'
                                        }`}
                                    >
                                        {template.is_active ? 'Active' : 'Inactive'}
                                    </span>
                                </div>
                            </div>
                        </div>
                        
                        {/* Usage Example */}
                        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                            <h4 className="font-semibold text-blue-800 mb-2">
                                💡 How it will appear
                            </h4>
                            <div className="text-sm text-blue-700">
                                <p className="mb-2">This factoid will appear:</p>
                                <ul className="list-disc list-inside space-y-1">
                                    <li>Below counters on council detail pages</li>
                                    <li>In animated factoid playlists</li>
                                    <li>With {template.emoji} emoji and {template.color_scheme} colors</li>
                                    <li>
                                        Priority {template.priority} 
                                        {template.priority > 70 ? ' (high - shows first)' : 
                                         template.priority > 30 ? ' (medium)' : ' (low - shows last)'}
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};

// Make component available globally
window.LivePreview = LivePreview;