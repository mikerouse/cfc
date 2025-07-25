/**
 * LivePreview Component
 * 
 * Shows real-time preview of factoid templates with actual data,
 * validation feedback, and usage examples.
 */
import { useMemo } from 'react';

const LivePreview = ({ template, previewData, validationErrors, isLoading }) => {
  // Process markdown in preview text
  const processMarkdown = (text) => {
    if (!text) return '';
    return text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  };

  // Get color scheme classes
  const getColorScheme = (scheme) => {
    const schemes = {
      blue: {
        bg: 'bg-blue-50',
        border: 'border-blue-200',
        text: 'text-blue-800',
        accent: 'text-blue-600',
      },
      green: {
        bg: 'bg-green-50',
        border: 'border-green-200', 
        text: 'text-green-800',
        accent: 'text-green-600',
      },
      red: {
        bg: 'bg-red-50',
        border: 'border-red-200',
        text: 'text-red-800', 
        accent: 'text-red-600',
      },
      orange: {
        bg: 'bg-orange-50',
        border: 'border-orange-200',
        text: 'text-orange-800',
        accent: 'text-orange-600',
      },
      purple: {
        bg: 'bg-purple-50',
        border: 'border-purple-200',
        text: 'text-purple-800',
        accent: 'text-purple-600',
      },
    };
    return schemes[scheme] || schemes.blue;
  };

  const colorScheme = getColorScheme(template.color_scheme);

  // Memoized preview content
  const previewContent = useMemo(() => {
    if (isLoading) {
      return (
        <div className="flex items-center justify-center p-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-gray-600">Generating preview...</span>
        </div>
      );
    }

    if (!template.template_text.trim()) {
      return (
        <div className="text-center p-8 text-gray-500">
          <div className="text-4xl mb-2">✍️</div>
          <p>Start typing template text to see preview</p>
        </div>
      );
    }

    if (!previewData) {
      return (
        <div className="text-center p-8 text-gray-500">
          <div className="text-4xl mb-2">⏳</div>
          <p>Preview will appear here...</p>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        {/* Main Preview */}
        <div className={`p-4 rounded-lg border ${colorScheme.bg} ${colorScheme.border}`}>
          <div className="flex items-start space-x-3">
            {template.emoji && (
              <div className="text-2xl flex-shrink-0">
                {template.emoji}
              </div>
            )}
            <div 
              className={`text-sm leading-relaxed ${colorScheme.text}`}
              dangerouslySetInnerHTML={{ 
                __html: processMarkdown(previewData.rendered_text || template.template_text)
              }}
            />
          </div>
        </div>

        {/* Preview Context */}
        {previewData.council_name && (
          <div className="text-xs text-gray-600 bg-gray-50 p-3 rounded border">
            <div className="font-medium mb-1">Preview Context:</div>
            <div>Council: {previewData.council_name}</div>
            <div>Year: {previewData.year_label}</div>
          </div>
        )}

        {/* Referenced Fields */}
        {previewData.referenced_fields && previewData.referenced_fields.length > 0 && (
          <div className="bg-gray-50 p-3 rounded border">
            <div className="text-xs font-medium text-gray-700 mb-2">
              Referenced Fields ({previewData.referenced_fields.length}):
            </div>
            <div className="flex flex-wrap gap-1">
              {previewData.referenced_fields.map((field, index) => (
                <span
                  key={index}
                  className="inline-flex items-center px-2 py-1 rounded text-xs font-mono bg-blue-100 text-blue-800"
                >
                  {field}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }, [template, previewData, isLoading, colorScheme]);

  return (
    <div className="live-preview h-full flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-4">
        <h3 className="text-lg font-semibold text-gray-900">
          👁️ Live Preview
        </h3>
        <p className="text-sm text-gray-600 mt-1">
          See how your factoid will look
        </p>
      </div>

      {/* Preview Content */}
      <div className="flex-1 p-4 overflow-y-auto">
        {previewContent}

        {/* Validation Errors in Preview */}
        {validationErrors.length > 0 && (
          <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <h4 className="text-sm font-semibold text-yellow-800 mb-2">
              ⚠️ Issues Found
            </h4>
            <ul className="text-sm text-yellow-700 space-y-1">
              {validationErrors.map((error, index) => (
                <li key={index}>• {error}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Template Properties */}
        {template.name && (
          <div className="mt-6 p-3 bg-gray-50 border border-gray-200 rounded-lg">
            <h4 className="text-sm font-semibold text-gray-700 mb-2">
              📋 Template Properties
            </h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Name:</span>
                <span className="font-medium">{template.name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Type:</span>
                <span className="font-medium capitalize">
                  {template.factoid_type.replace('_', ' ')}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Priority:</span>
                <span className="font-medium">{template.priority}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Color:</span>
                <span className={`font-medium capitalize ${colorScheme.accent}`}>
                  {template.color_scheme}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Status:</span>
                <span 
                  className={`font-medium ${
                    template.is_active ? 'text-green-600' : 'text-red-600'
                  }`}
                >
                  {template.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Usage Tips */}
        <div className="mt-6 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <h4 className="text-sm font-semibold text-blue-800 mb-2">
            💡 How it will appear
          </h4>
          <div className="text-sm text-blue-700 space-y-1">
            <div>• Below counters on council detail pages</div>
            <div>• In animated factoid playlists</div>
            <div>• With {template.emoji} emoji and {template.color_scheme} styling</div>
            <div>
              • Priority {template.priority} 
              {template.priority > 70 ? ' (high - shows first)' : 
               template.priority < 30 ? ' (low - shows last)' : ' (medium)'}
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-gray-200 p-4 bg-gray-50">
        <div className="text-xs text-gray-600 space-y-1">
          <div>🔄 <strong>Live:</strong> Updates automatically as you type</div>
          <div>📊 <strong>Data:</strong> Uses real council information</div>
          <div>✅ <strong>Validation:</strong> Checks syntax and field references</div>
        </div>
      </div>
    </div>
  );
};

export default LivePreview;
