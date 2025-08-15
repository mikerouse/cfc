/**
 * PDFViewer Component
 * 
 * Professional PDF viewer component using PDF.js for displaying council
 * financial statements with extraction highlighting capabilities.
 * 
 * Features:
 * - Page navigation and zoom controls
 * - Extraction result highlighting
 * - Mobile-responsive design
 * - Error handling and loading states
 * - Keyboard shortcuts
 */

import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { PDF_CONFIG, SCALE_OPTIONS, getPDFErrorMessage } from '../../utils/pdfConfig';
import ExtractionHighlights from './ExtractionHighlights';
import './PDFViewer.css';

// Initialize PDF.js configuration
import '../../utils/pdfConfig';

const PDFViewer = ({ 
  pdfUrl, 
  extractedData = {}, 
  highlightedField = null,
  onPageChange = () => {},
  onFieldClick = () => {},
  className = "",
  preset = 'financial',
  showControls = true,
  initialPage = 1,
}) => {
  // Component state
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(initialPage);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [scale, setScale] = useState(1.0);
  const [pageInput, setPageInput] = useState(initialPage.toString());

  // Memoized values
  const hasExtractions = useMemo(() => {
    return Object.keys(extractedData).length > 0;
  }, [extractedData]);

  const currentPageExtractions = useMemo(() => {
    return Object.entries(extractedData).filter(([_, data]) => 
      data.page_number === pageNumber
    ).length;
  }, [extractedData, pageNumber]);

  // PDF.js event handlers
  const onDocumentLoadSuccess = useCallback(({ numPages }) => {
    setNumPages(numPages);
    setLoading(false);
    setError(null);
    onPageChange(pageNumber);
    
    console.log(`📄 PDF loaded successfully: ${numPages} pages`, {
      url: pdfUrl,
      pages: numPages,
      currentPage: pageNumber
    });
  }, [onPageChange, pageNumber, pdfUrl]);

  const onDocumentLoadError = useCallback((error) => {
    const errorMessage = getPDFErrorMessage(error);
    setError(errorMessage);
    setLoading(false);
    
    console.error('📄 PDF load error:', {
      error: error,
      message: errorMessage,
      url: pdfUrl
    });
  }, [pdfUrl]);

  const onPageLoadSuccess = useCallback((page) => {
    console.log(`📄 Page ${page.pageNumber} loaded successfully`);
  }, []);

  const onPageLoadError = useCallback((error) => {
    console.warn(`📄 Page load error:`, error);
  }, []);

  // Navigation functions
  const goToPage = useCallback((page) => {
    const targetPage = Math.max(1, Math.min(page, numPages || 1));
    setPageNumber(targetPage);
    setPageInput(targetPage.toString());
    onPageChange(targetPage);
  }, [numPages, onPageChange]);

  const nextPage = useCallback(() => {
    if (pageNumber < numPages) {
      goToPage(pageNumber + 1);
    }
  }, [pageNumber, numPages, goToPage]);

  const previousPage = useCallback(() => {
    if (pageNumber > 1) {
      goToPage(pageNumber - 1);
    }
  }, [pageNumber, goToPage]);

  // Zoom functions
  const changeScale = useCallback((newScale) => {
    const clampedScale = Math.max(0.5, Math.min(2.0, newScale));
    setScale(clampedScale);
    console.log(`🔍 PDF zoom changed to ${Math.round(clampedScale * 100)}%`);
  }, []);

  const zoomIn = useCallback(() => {
    changeScale(scale + 0.25);
  }, [scale, changeScale]);

  const zoomOut = useCallback(() => {
    changeScale(scale - 0.25);
  }, [scale, changeScale]);

  const resetZoom = useCallback(() => {
    changeScale(1.0);
  }, [changeScale]);

  // Page input handler
  const handlePageInputChange = useCallback((e) => {
    const value = e.target.value;
    setPageInput(value);
  }, []);

  const handlePageInputKeyDown = useCallback((e) => {
    if (e.key === 'Enter') {
      const page = parseInt(pageInput, 10);
      if (!isNaN(page)) {
        goToPage(page);
      } else {
        setPageInput(pageNumber.toString());
      }
    } else if (e.key === 'Escape') {
      setPageInput(pageNumber.toString());
      e.target.blur();
    }
  }, [pageInput, pageNumber, goToPage]);

  const handlePageInputBlur = useCallback(() => {
    const page = parseInt(pageInput, 10);
    if (!isNaN(page)) {
      goToPage(page);
    } else {
      setPageInput(pageNumber.toString());
    }
  }, [pageInput, goToPage, pageNumber]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Only handle shortcuts when not typing in an input
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        return;
      }

      switch (e.key) {
        case 'ArrowLeft':
        case 'ArrowUp':
          e.preventDefault();
          previousPage();
          break;
        case 'ArrowRight':
        case 'ArrowDown':
          e.preventDefault();
          nextPage();
          break;
        case 'Home':
          e.preventDefault();
          goToPage(1);
          break;
        case 'End':
          e.preventDefault();
          goToPage(numPages || 1);
          break;
        case '+':
        case '=':
          e.preventDefault();
          zoomIn();
          break;
        case '-':
        case '_':
          e.preventDefault();
          zoomOut();
          break;
        case '0':
          e.preventDefault();
          resetZoom();
          break;
        default:
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [previousPage, nextPage, goToPage, numPages, zoomIn, zoomOut, resetZoom]);

  // Update page input when page changes externally
  useEffect(() => {
    setPageInput(pageNumber.toString());
  }, [pageNumber]);

  // Error state
  if (error) {
    return (
      <div className={`pdf-viewer-error border border-red-300 bg-red-50 p-6 rounded-lg ${className}`}>
        <div className="text-center">
          <div className="text-red-600 mb-3 text-4xl">⚠️</div>
          <h3 className="text-lg font-medium text-red-800 mb-2">PDF Loading Error</h3>
          <p className="text-red-700 text-sm mb-4 max-w-md mx-auto">{error}</p>
          <div className="space-x-3">
            <button 
              onClick={() => window.location.reload()} 
              className="px-4 py-2 bg-red-600 text-white hover:bg-red-700 transition-colors rounded"
            >
              Refresh Page
            </button>
            <button 
              onClick={() => setError(null)} 
              className="px-4 py-2 bg-white text-red-600 border border-red-300 hover:bg-red-50 transition-colors rounded"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`pdf-viewer border border-gray-300 bg-white ${className}`}>
      {/* PDF Controls */}
      {showControls && (
        <div className="pdf-controls bg-gray-50 border-b border-gray-300 px-4 py-3">
          <div className="flex items-center justify-between flex-wrap gap-3">
            {/* Navigation Controls */}
            <div className="flex items-center space-x-3">
              <button
                onClick={previousPage}
                disabled={pageNumber <= 1 || loading}
                className="px-3 py-1 bg-white border border-gray-300 text-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors rounded"
                title="Previous page (←)"
              >
                ← Previous
              </button>
              
              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-600 whitespace-nowrap">Page</span>
                <input
                  type="number"
                  value={pageInput}
                  onChange={handlePageInputChange}
                  onKeyDown={handlePageInputKeyDown}
                  onBlur={handlePageInputBlur}
                  min={1}
                  max={numPages || 1}
                  className="pdf-page-input w-16 px-2 py-1 border border-gray-300 text-sm text-center rounded"
                  title="Page number"
                />
                <span className="text-sm text-gray-600 whitespace-nowrap">
                  of {numPages || '...'}
                </span>
              </div>
              
              <button
                onClick={nextPage}
                disabled={pageNumber >= numPages || loading}
                className="px-3 py-1 bg-white border border-gray-300 text-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors rounded"
                title="Next page (→)"
              >
                Next →
              </button>
            </div>
            
            {/* Zoom and Status Controls */}
            <div className="flex items-center space-x-4">
              {/* Extraction Status */}
              {hasExtractions && (
                <div className="text-sm text-gray-600 bg-white px-2 py-1 rounded border border-gray-200">
                  {currentPageExtractions > 0 ? (
                    <span className="text-blue-600 font-medium">
                      {currentPageExtractions} extraction{currentPageExtractions !== 1 ? 's' : ''} on this page
                    </span>
                  ) : (
                    <span>No extractions on this page</span>
                  )}
                </div>
              )}
              
              {/* Zoom Controls */}
              <div className="zoom-controls flex items-center space-x-2">
                <button
                  onClick={zoomOut}
                  disabled={scale <= 0.5}
                  className="zoom-button bg-white border border-gray-300 text-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed rounded"
                  title="Zoom out (-)"
                >
                  −
                </button>
                <button
                  onClick={resetZoom}
                  className="px-2 py-1 bg-white border border-gray-300 text-xs hover:bg-gray-50 transition-colors rounded min-w-[60px]"
                  title="Reset zoom (0)"
                >
                  {Math.round(scale * 100)}%
                </button>
                <button
                  onClick={zoomIn}
                  disabled={scale >= 2.0}
                  className="zoom-button bg-white border border-gray-300 text-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed rounded"
                  title="Zoom in (+)"
                >
                  +
                </button>
              </div>
              
              {/* Loading Indicator */}
              {loading && (
                <div className="flex items-center text-sm text-gray-600">
                  <div className="animate-spin w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full mr-2"></div>
                  Loading...
                </div>
              )}
              
              {/* Page Count */}
              {!loading && numPages && (
                <span className="text-sm text-gray-600 whitespace-nowrap">
                  {numPages} page{numPages !== 1 ? 's' : ''}
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* PDF Display Container */}
      <div className="pdf-container bg-gray-100 p-4 overflow-auto" style={{ minHeight: '400px', maxHeight: '80vh' }}>
        <div className="flex justify-center">
          <div className="relative inline-block">
            <Document
              file={pdfUrl}
              onLoadSuccess={onDocumentLoadSuccess}
              onLoadError={onDocumentLoadError}
              options={PDF_CONFIG}
              loading={
                <div className="flex items-center justify-center py-16 min-w-[400px]">
                  <div className="text-center">
                    <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto mb-4"></div>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">Loading PDF...</h3>
                    <p className="text-sm text-gray-600">Please wait while we load your document</p>
                  </div>
                </div>
              }
            >
              <Page
                pageNumber={pageNumber}
                scale={scale}
                onLoadSuccess={onPageLoadSuccess}
                onLoadError={onPageLoadError}
                renderTextLayer={false}
                renderAnnotationLayer={false}
                className="border border-gray-300 bg-white shadow-sm"
                loading={
                  <div className="flex items-center justify-center py-12 bg-gray-50 border border-gray-300 min-w-[400px]">
                    <div className="text-center">
                      <div className="pdf-loading w-6 h-6 bg-blue-600 rounded-full mx-auto mb-2"></div>
                      <p className="text-sm text-gray-600">Loading page {pageNumber}...</p>
                    </div>
                  </div>
                }
              />
            </Document>
            
            {/* Extraction Highlights Overlay */}
            {!loading && hasExtractions && (
              <ExtractionHighlights 
                pageNumber={pageNumber}
                extractedData={extractedData}
                highlightedField={highlightedField}
                scale={scale}
                onFieldClick={onFieldClick}
              />
            )}
          </div>
        </div>
      </div>

      {/* Page Quick Navigation */}
      {numPages > 1 && (
        <div className="pdf-pagination bg-gray-50 border-t border-gray-300 px-4 py-2">
          <div className="flex items-center justify-center space-x-1">
            {/* Show first few pages */}
            {[...Array(Math.min(numPages, 8))].map((_, i) => {
              const page = i + 1;
              return (
                <button
                  key={page}
                  onClick={() => goToPage(page)}
                  className={`w-8 h-8 text-xs border transition-colors rounded ${
                    page === pageNumber
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                  }`}
                  title={`Go to page ${page}`}
                >
                  {page}
                </button>
              );
            })}
            
            {/* Show ellipsis and last page for large PDFs */}
            {numPages > 8 && (
              <>
                <span className="text-gray-500 text-xs px-1">...</span>
                <button
                  onClick={() => goToPage(numPages)}
                  className={`w-8 h-8 text-xs border transition-colors rounded ${
                    numPages === pageNumber
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                  }`}
                  title={`Go to page ${numPages}`}
                >
                  {numPages}
                </button>
              </>
            )}
          </div>
          
          {/* Keyboard shortcuts hint */}
          <div className="text-center mt-2">
            <p className="text-xs text-gray-500">
              Use arrow keys to navigate • +/- to zoom • 0 to reset zoom
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default PDFViewer;