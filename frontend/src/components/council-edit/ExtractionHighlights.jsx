/**
 * ExtractionHighlights Component
 * 
 * Renders clickable highlight overlays on PDF pages to show where
 * financial data was extracted from. Provides visual feedback and
 * allows users to verify extraction accuracy.
 * 
 * Features:
 * - Coordinate-based positioning over PDF canvas
 * - Field-specific color coding
 * - Interactive tooltips with extraction details
 * - Responsive scaling with PDF zoom
 * - Click handlers for field selection
 */

import React, { useMemo } from 'react';
import { getFieldColor, formatCurrency } from '../../utils/pdfConfig';

const ExtractionHighlights = ({ 
  pageNumber,
  extractedData = {},
  highlightedField = null,
  scale = 1.0,
  onFieldClick = () => {},
}) => {
  // Filter extractions for current page
  const currentPageExtractions = useMemo(() => {
    return Object.entries(extractedData).filter(([fieldSlug, data]) => {
      return data.page_number === pageNumber && data.coordinates;
    });
  }, [extractedData, pageNumber]);

  // No extractions to show
  if (currentPageExtractions.length === 0) {
    return null;
  }

  return (
    <div className="absolute inset-0 pointer-events-none">
      {currentPageExtractions.map(([fieldSlug, data]) => {
        const { coordinates, value, field_name, confidence = 0.7, detection_method = 'unknown' } = data;
        const { x, y, width, height } = coordinates;
        
        // Apply scale transformation
        const scaledX = x * scale;
        const scaledY = y * scale;
        const scaledWidth = width * scale;
        const scaledHeight = height * scale;
        
        // Get field-specific colors
        const colors = getFieldColor(fieldSlug);
        const isActive = highlightedField === fieldSlug;
        const isHighConfidence = confidence >= 0.8;
        
        return (
          <div
            key={fieldSlug}
            className={`absolute pointer-events-auto cursor-pointer pdf-highlight ${colors.bg} ${colors.border} border-2 ${
              isActive ? 'active' : ''
            } ${isHighConfidence ? 'opacity-80' : 'opacity-60'}`}
            style={{
              left: `${scaledX}px`,
              top: `${scaledY}px`,
              width: `${scaledWidth}px`,
              height: `${scaledHeight}px`,
              zIndex: isActive ? 50 : 10,
            }}
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onFieldClick(fieldSlug);
            }}
            title={`${field_name}: ${formatCurrency(value)} (${Math.round(confidence * 100)}% confidence)`}
          >
            {/* Field label - only show for larger highlights */}
            {scaledWidth > 120 && scaledHeight > 20 && (
              <div className={`absolute -top-6 left-0 text-xs font-medium px-2 py-1 bg-white border ${colors.border} rounded shadow-sm ${colors.text}`}>
                {field_name}
              </div>
            )}
            
            {/* Confidence indicator */}
            <div 
              className={`absolute top-1 right-1 w-2 h-2 rounded-full ${
                isHighConfidence ? 'bg-green-500' : confidence >= 0.6 ? 'bg-yellow-500' : 'bg-red-500'
              }`}
              title={`${Math.round(confidence * 100)}% confidence (${detection_method})`}
            />
            
            {/* Value preview for larger highlights */}
            {scaledWidth > 100 && scaledHeight > 30 && (
              <div className={`absolute bottom-1 left-1 text-xs font-bold ${colors.text} bg-white bg-opacity-90 px-1 rounded`}>
                {formatCurrency(value)}
              </div>
            )}
            
            {/* Interactive overlay for better click detection */}
            <div className="absolute inset-0 hover:bg-black hover:bg-opacity-10 transition-colors duration-200" />
          </div>
        );
      })}
    </div>
  );
};

export default ExtractionHighlights;