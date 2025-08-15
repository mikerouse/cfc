/**
 * PDF.js Configuration and Worker Setup
 * 
 * Configures PDF.js for client-side PDF rendering with proper worker paths
 * and performance optimizations for council financial documents.
 */

import { pdfjs } from 'react-pdf';

// Configure PDF.js worker for client-side rendering
// Use unpkg CDN for reliable worker script delivery
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;

/**
 * PDF.js configuration options optimized for financial documents
 */
export const PDF_CONFIG = {
  // Character maps for better text extraction
  cMapUrl: `//unpkg.com/pdfjs-dist@${pdfjs.version}/cmaps/`,
  cMapPacked: true,
  
  // Standard fonts for consistent rendering
  standardFontDataUrl: `//unpkg.com/pdfjs-dist@${pdfjs.version}/standard_fonts/`,
  
  // Disable text layer initially for better performance
  // We'll enable it selectively when needed for search
  renderTextLayer: false,
  renderAnnotationLayer: false,
  
  // Performance settings for large financial PDFs
  maxImageSize: 16777216, // 16MB - financial PDFs can have large images
  disableFontFace: false,
  disableStream: false,
  disableAutoFetch: false,
  
  // Error handling
  stopAtErrors: false,
  
  // Experimental features
  enableXfa: false, // Disable XFA forms (not needed for financial statements)
};

/**
 * Default scale options for PDF viewing
 */
export const SCALE_OPTIONS = [
  { value: 0.5, label: '50%' },
  { value: 0.75, label: '75%' },
  { value: 1.0, label: '100%' },
  { value: 1.25, label: '125%' },
  { value: 1.5, label: '150%' },
  { value: 2.0, label: '200%' },
];

/**
 * Color schemes for different field types in highlights
 */
export const FIELD_COLORS = {
  'total-income': { 
    bg: 'bg-green-200', 
    border: 'border-green-400', 
    text: 'text-green-800',
    accent: '#10b981'
  },
  'total-expenditure': { 
    bg: 'bg-red-200', 
    border: 'border-red-400', 
    text: 'text-red-800',
    accent: '#ef4444'
  },
  'current-liabilities': { 
    bg: 'bg-yellow-200', 
    border: 'border-yellow-400', 
    text: 'text-yellow-800',
    accent: '#f59e0b'
  },
  'long-term-liabilities': { 
    bg: 'bg-orange-200', 
    border: 'border-orange-400', 
    text: 'text-orange-800',
    accent: '#f97316'
  },
  'total-debt': { 
    bg: 'bg-purple-200', 
    border: 'border-purple-400', 
    text: 'text-purple-800',
    accent: '#a855f7'
  },
  'interest-payments': { 
    bg: 'bg-blue-200', 
    border: 'border-blue-400', 
    text: 'text-blue-800',
    accent: '#3b82f6'
  },
  'total-reserves': { 
    bg: 'bg-teal-200', 
    border: 'border-teal-400', 
    text: 'text-teal-800',
    accent: '#14b8a6'
  },
  // Default fallback color
  default: { 
    bg: 'bg-gray-200', 
    border: 'border-gray-400', 
    text: 'text-gray-800',
    accent: '#6b7280'
  },
};

/**
 * Get color scheme for a specific field
 * @param {string} fieldSlug - The field slug to get colors for
 * @returns {object} Color scheme object
 */
export const getFieldColor = (fieldSlug) => {
  return FIELD_COLORS[fieldSlug] || FIELD_COLORS.default;
};

/**
 * Format currency values for display
 * @param {number} value - Raw currency value in pounds
 * @returns {string} Formatted currency string
 */
export const formatCurrency = (value) => {
  if (!value || value === 0) return '£0';
  
  const absValue = Math.abs(value);
  
  if (absValue >= 1000000) {
    const millions = value / 1000000;
    return `£${millions.toFixed(1)}m`;
  } else if (absValue >= 1000) {
    const thousands = value / 1000;
    return `£${thousands.toFixed(1)}k`;
  } else {
    return `£${value.toLocaleString()}`;
  }
};

/**
 * PDF viewer configuration presets
 */
export const VIEWER_PRESETS = {
  // Preset for financial document review
  financial: {
    defaultScale: 1.0,
    showControls: true,
    showSearch: false,
    showThumbnails: false,
    enableHighlights: true,
    enableAnnotations: false,
  },
  
  // Preset for detailed analysis
  analysis: {
    defaultScale: 1.25,
    showControls: true,
    showSearch: true,
    showThumbnails: true,
    enableHighlights: true,
    enableAnnotations: true,
  },
  
  // Preset for mobile viewing
  mobile: {
    defaultScale: 0.75,
    showControls: true,
    showSearch: false,
    showThumbnails: false,
    enableHighlights: true,
    enableAnnotations: false,
  },
};

/**
 * Error messages for common PDF loading issues
 */
export const PDF_ERROR_MESSAGES = {
  'InvalidPDFException': 'The uploaded file is not a valid PDF document.',
  'MissingPDFException': 'The PDF file could not be found.',
  'PasswordException': 'This PDF is password protected and cannot be displayed.',
  'UnexpectedResponseException': 'There was an error loading the PDF. Please try again.',
  'UnknownErrorException': 'An unknown error occurred while loading the PDF.',
  'NetworkError': 'Network error: Please check your connection and try again.',
  'TimeoutError': 'The PDF took too long to load. Please try again.',
  default: 'Failed to load PDF. Please try refreshing the page.',
};

/**
 * Get user-friendly error message for PDF loading errors
 * @param {Error} error - The error object from PDF.js
 * @returns {string} User-friendly error message
 */
export const getPDFErrorMessage = (error) => {
  const errorName = error?.name || 'UnknownError';
  return PDF_ERROR_MESSAGES[errorName] || PDF_ERROR_MESSAGES.default;
};

console.log('🔧 PDF.js configured:', {
  version: pdfjs.version,
  workerSrc: pdfjs.GlobalWorkerOptions.workerSrc,
  config: PDF_CONFIG
});