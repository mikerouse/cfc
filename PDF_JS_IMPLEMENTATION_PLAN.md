# PDF.js Integration Implementation Plan

*Detailed roadmap for implementing client-side PDF viewing with extraction highlighting*

## Overview

This document outlines the complete implementation plan for integrating PDF.js into the Council Finance Counters system to provide users with visual PDF viewing alongside AI-extracted financial data. This is **Option 2** from our research, chosen for its practical balance of functionality and implementation complexity.

## Why PDF.js? 

### ✅ **Advantages**
- **Client-Side Processing**: No server resources required for PDF rendering
- **Professional Experience**: Native PDF viewing (zoom, scroll, navigation)
- **Precise Highlighting**: Coordinate-based overlays show exact extraction locations
- **Cross-Platform**: Works on all modern browsers including mobile
- **Extensible**: Can add search, annotations, and advanced features
- **No Infrastructure Changes**: Builds on existing PDF upload system

### ❌ **Challenges We'll Address**
- Frontend complexity requiring React PDF components
- Need for PDF files to be URL-accessible with authentication
- Coordinate mapping from text extraction to visual highlights

## Architecture Design

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Uploads  │    │  Django Backend  │    │  PDF.js Viewer  │
│      PDF        │────│                  │────│                 │
│                 │    │ • Stores PDF     │    │ • Renders PDF   │
│                 │    │ • Extracts data  │    │ • Shows highlights│
│                 │    │ • Serves via URL │    │ • Interactive   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                ▲                        ▲
                                │                        │
                       ┌─────────────────┐    ┌─────────────────┐
                       │ Tika + AI       │    │ React Frontend  │
                       │ Text Extraction │    │ PDF Components  │
                       │ with Metadata   │    │ Highlight Layer │
                       └─────────────────┘    └─────────────────┘
```

## Implementation Phases

### **Phase 1: Foundation Setup (Day 1-2)**

#### 1.1 Install Dependencies
```bash
cd frontend
npm install react-pdf pdfjs-dist@3.11.174
```

#### 1.2 Configure PDF.js Worker
```javascript
// frontend/src/utils/pdfConfig.js
import { pdfjs } from 'react-pdf';

// Configure PDF.js worker for client-side rendering
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;

// PDF.js configuration options
export const PDF_CONFIG = {
  cMapUrl: `//unpkg.com/pdfjs-dist@${pdfjs.version}/cmaps/`,
  cMapPacked: true,
  standardFontDataUrl: `//unpkg.com/pdfjs-dist@${pdfjs.version}/standard_fonts/`,
};
```

#### 1.3 Create Basic PDF Viewer Component
```jsx
// frontend/src/components/council-edit/PDFViewer.jsx
import React, { useState, useCallback } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { PDF_CONFIG } from '../../utils/pdfConfig';

const PDFViewer = ({ 
  pdfUrl, 
  extractedData = {}, 
  highlightedField = null,
  onPageChange = () => {},
  className = ""
}) => {
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [scale, setScale] = useState(1.0);

  const onDocumentLoadSuccess = useCallback(({ numPages }) => {
    setNumPages(numPages);
    setLoading(false);
    onPageChange(1);
    console.log(`📄 PDF loaded successfully: ${numPages} pages`);
  }, [onPageChange]);

  const onDocumentLoadError = useCallback((error) => {
    setError(`Failed to load PDF: ${error.message}`);
    setLoading(false);
    console.error('📄 PDF load error:', error);
  }, []);

  const goToPage = useCallback((page) => {
    if (page >= 1 && page <= numPages) {
      setPageNumber(page);
      onPageChange(page);
    }
  }, [numPages, onPageChange]);

  const changeScale = useCallback((newScale) => {
    setScale(Math.max(0.5, Math.min(2.0, newScale)));
  }, []);

  if (error) {
    return (
      <div className={`pdf-viewer-error border border-red-300 bg-red-50 p-6 ${className}`}>
        <div className="text-center">
          <div className="text-red-600 mb-2">⚠️ PDF Loading Error</div>
          <p className="text-red-700 text-sm">{error}</p>
          <button 
            onClick={() => window.location.reload()} 
            className="mt-3 px-4 py-2 bg-red-600 text-white hover:bg-red-700 transition-colors"
          >
            Refresh Page
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`pdf-viewer border border-gray-300 bg-white ${className}`}>
      {/* PDF Controls */}
      <div className="pdf-controls bg-gray-50 border-b border-gray-300 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <button
              onClick={() => goToPage(pageNumber - 1)}
              disabled={pageNumber <= 1 || loading}
              className="px-3 py-1 bg-white border border-gray-300 text-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              ← Previous
            </button>
            
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-600">Page</span>
              <input
                type="number"
                value={pageNumber}
                onChange={(e) => goToPage(parseInt(e.target.value))}
                min={1}
                max={numPages || 1}
                className="w-16 px-2 py-1 border border-gray-300 text-sm text-center"
              />
              <span className="text-sm text-gray-600">of {numPages || '...'}</span>
            </div>
            
            <button
              onClick={() => goToPage(pageNumber + 1)}
              disabled={pageNumber >= numPages || loading}
              className="px-3 py-1 bg-white border border-gray-300 text-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Next →
            </button>
          </div>
          
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2">
              <button
                onClick={() => changeScale(scale - 0.25)}
                disabled={scale <= 0.5}
                className="w-8 h-8 bg-white border border-gray-300 text-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                −
              </button>
              <span className="text-sm text-gray-600 min-w-[60px] text-center">
                {Math.round(scale * 100)}%
              </span>
              <button
                onClick={() => changeScale(scale + 0.25)}
                disabled={scale >= 2.0}
                className="w-8 h-8 bg-white border border-gray-300 text-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                +
              </button>
            </div>
            
            {loading && (
              <div className="flex items-center text-sm text-gray-600">
                <div className="animate-spin w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full mr-2"></div>
                Loading...
              </div>
            )}
            
            {!loading && numPages && (
              <span className="text-sm text-gray-600">{numPages} pages</span>
            )}
          </div>
        </div>
      </div>

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
                <div className="flex items-center justify-center py-12">
                  <div className="text-center">
                    <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto mb-3"></div>
                    <span className="text-gray-600">Loading PDF...</span>
                  </div>
                </div>
              }
            >
              <Page
                pageNumber={pageNumber}
                scale={scale}
                renderTextLayer={false}
                renderAnnotationLayer={false}
                className="border border-gray-300 bg-white shadow-sm"
              />
            </Document>
            
            {/* Extraction Highlights Overlay */}
            <ExtractionHighlights 
              pageNumber={pageNumber}
              extractedData={extractedData}
              highlightedField={highlightedField}
              scale={scale}
            />
          </div>
        </div>
      </div>

      {/* Page Quick Navigation */}
      {numPages > 1 && (
        <div className="pdf-pagination bg-gray-50 border-t border-gray-300 px-4 py-2">
          <div className="flex items-center justify-center space-x-1">
            {[...Array(Math.min(numPages, 10))].map((_, i) => {
              const page = i + 1;
              return (
                <button
                  key={page}
                  onClick={() => goToPage(page)}
                  className={`w-8 h-8 text-xs border transition-colors ${
                    page === pageNumber
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  {page}
                </button>
              );
            })}
            {numPages > 10 && (
              <>
                <span className="text-gray-500 text-xs">...</span>
                <button
                  onClick={() => goToPage(numPages)}
                  className={`w-8 h-8 text-xs border transition-colors ${
                    numPages === pageNumber
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  {numPages}
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default PDFViewer;
```

### **Phase 2: Extraction Highlighting System (Day 3-4)**

#### 2.1 Create Highlight Overlay Component
```jsx
// frontend/src/components/council-edit/ExtractionHighlights.jsx
import React, { useMemo, useState } from 'react';

const ExtractionHighlights = ({ 
  pageNumber, 
  extractedData = {}, 
  highlightedField = null,
  scale = 1.0
}) => {
  const [hoveredField, setHoveredField] = useState(null);
  
  // Filter data for current page and calculate positions
  const pageHighlights = useMemo(() => {
    const highlights = [];
    
    Object.entries(extractedData).forEach(([fieldSlug, data]) => {
      if (data.page_number === pageNumber) {
        // For now, use approximate positioning based on field type
        // In a real implementation, this would use coordinate data from text extraction
        const position = getApproximatePosition(fieldSlug, data.source_text);
        
        highlights.push({
          fieldSlug,
          data,
          position: {
            ...position,
            // Scale positions based on PDF zoom level
            left: `${parseFloat(position.left) * scale}%`,
            top: `${parseFloat(position.top) * scale}%`,
            width: `${parseFloat(position.width) * scale}%`,
            height: `${parseFloat(position.height) * scale}%`,
          },
          color: getFieldColor(fieldSlug),
          isActive: highlightedField === fieldSlug,
        });
      }
    });
    
    return highlights;
  }, [extractedData, pageNumber, highlightedField, scale]);

  // Approximate positioning based on field type (placeholder for real coordinate data)
  const getApproximatePosition = (fieldSlug, sourceText) => {
    const positions = {
      'total-income': { left: '60%', top: '25%', width: '35%', height: '3%' },
      'total-expenditure': { left: '60%', top: '35%', width: '35%', height: '3%' },
      'current-liabilities': { left: '60%', top: '55%', width: '35%', height: '3%' },
      'long-term-liabilities': { left: '60%', top: '65%', width: '35%', height: '3%' },
      'total-reserves': { left: '60%', top: '75%', width: '35%', height: '3%' },
      'interest-payments': { left: '60%', top: '45%', width: '35%', height: '3%' },
    };
    
    return positions[fieldSlug] || { left: '10%', top: '10%', width: '30%', height: '3%' };
  };

  const getFieldColor = (fieldSlug) => {
    const colorMap = {
      'total-income': { bg: 'bg-green-200', border: 'border-green-400', text: 'text-green-800' },
      'total-expenditure': { bg: 'bg-red-200', border: 'border-red-400', text: 'text-red-800' },
      'current-liabilities': { bg: 'bg-yellow-200', border: 'border-yellow-400', text: 'text-yellow-800' },
      'long-term-liabilities': { bg: 'bg-orange-200', border: 'border-orange-400', text: 'text-orange-800' },
      'total-debt': { bg: 'bg-purple-200', border: 'border-purple-400', text: 'text-purple-800' },
      'interest-payments': { bg: 'bg-blue-200', border: 'border-blue-400', text: 'text-blue-800' },
      'total-reserves': { bg: 'bg-teal-200', border: 'border-teal-400', text: 'text-teal-800' },
    };
    
    return colorMap[fieldSlug] || { bg: 'bg-gray-200', border: 'border-gray-400', text: 'text-gray-800' };
  };

  const formatCurrency = (value) => {
    if (!value) return 'N/A';
    const millions = value / 1000000;
    return `£${millions.toFixed(1)}m`;
  };

  if (pageHighlights.length === 0) {
    return null; // No extractions on this page
  }

  return (
    <div className="absolute inset-0 pointer-events-none">
      {pageHighlights.map(({ fieldSlug, data, position, color, isActive }) => (
        <div
          key={fieldSlug}
          className={`absolute border-2 transition-all duration-200 pointer-events-auto cursor-pointer ${
            color.bg
          } ${color.border} ${
            isActive 
              ? 'opacity-90 border-4 shadow-lg z-20 scale-105' 
              : hoveredField === fieldSlug
              ? 'opacity-80 z-10'
              : 'opacity-60 hover:opacity-80'
          }`}
          style={{
            left: position.left,
            top: position.top,
            width: position.width,
            height: position.height,
          }}
          onMouseEnter={() => setHoveredField(fieldSlug)}
          onMouseLeave={() => setHoveredField(null)}
        >
          {/* Highlight tooltip */}
          <div 
            className={`absolute top-full left-0 mt-1 px-3 py-2 bg-black text-white text-sm rounded shadow-lg whitespace-nowrap z-30 transition-opacity ${
              isActive || hoveredField === fieldSlug ? 'opacity-100' : 'opacity-0'
            }`}
            style={{
              transform: 'translateX(-50%)',
              left: '50%',
            }}
          >
            <div className="font-medium">{data.field_name}</div>
            <div className="text-xs opacity-90">
              {formatCurrency(data.value)} 
              {data.confidence && ` (${Math.round(data.confidence * 100)}% confidence)`}
            </div>
            {data.source_text && (
              <div className="text-xs opacity-75 mt-1 max-w-xs">
                "{data.source_text.substring(0, 60)}..."
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

export default ExtractionHighlights;
```

### **Phase 3: Backend PDF Storage & Serving (Day 4-5)**

#### 3.1 PDF Storage Structure
```python
# council_finance/models.py - Add PDF storage model
import uuid
import os
from django.db import models
from django.conf import settings
from django.urls import reverse

class PDFDocument(models.Model):
    """Stores uploaded PDF documents with secure access."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    council = models.ForeignKey('Council', on_delete=models.CASCADE, related_name='pdf_documents')
    year = models.ForeignKey('FinancialYear', on_delete=models.CASCADE)
    
    # File storage
    filename = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    file_hash = models.CharField(max_length=64)  # SHA256 hash for deduplication
    
    # Metadata
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    # Processing status
    processing_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ], default='pending')
    
    processing_error = models.TextField(blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['council', 'year']  # One PDF per council per year
        
    def get_file_path(self):
        """Get the full file path for this PDF."""
        return os.path.join(settings.MEDIA_ROOT, 'council_pdfs', str(self.council.slug), self.filename)
    
    def get_serving_url(self):
        """Get the URL for serving this PDF with authentication."""
        return reverse('serve_pdf', kwargs={
            'council_slug': self.council.slug,
            'pdf_id': str(self.id)
        })
    
    def __str__(self):
        return f"{self.council.name} - {self.year.label} - {self.original_filename}"
```

#### 3.2 Secure PDF Serving View
```python
# council_finance/views/pdf_views.py
import os
import hashlib
import mimetypes
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.shortcuts import get_object_or_404
from django.conf import settings
from council_finance.models import PDFDocument

@require_GET
@login_required
def serve_pdf(request, council_slug, pdf_id):
    """
    Serve PDF files with proper authentication and security checks.
    
    URL: /pdf/<council_slug>/<pdf_id>/
    """
    
    # Get PDF document with security checks
    pdf_doc = get_object_or_404(
        PDFDocument, 
        id=pdf_id,
        council__slug=council_slug
    )
    
    # Authorization check: ensure user can access this council's data
    if not request.user.has_perm('council_finance.view_council', pdf_doc.council):
        return HttpResponseForbidden("Access denied: insufficient permissions")
    
    # Get file path
    file_path = pdf_doc.get_file_path()
    
    # Security checks
    if not os.path.exists(file_path):
        raise Http404("PDF file not found on disk")
    
    # Verify file integrity
    with open(file_path, 'rb') as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
        if file_hash != pdf_doc.file_hash:
            return HttpResponseForbidden("File integrity check failed")
    
    # Verify MIME type
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type != 'application/pdf':
        return HttpResponseForbidden("Invalid file type")
    
    # Serve file with proper headers
    response = FileResponse(
        open(file_path, 'rb'),
        content_type='application/pdf'
    )
    
    # Security headers
    response['X-Frame-Options'] = 'SAMEORIGIN'  # Allow embedding in same origin
    response['Content-Security-Policy'] = "frame-ancestors 'self'"
    response['X-Content-Type-Options'] = 'nosniff'
    
    # Cache control
    response['Cache-Control'] = 'private, max-age=3600'  # Cache for 1 hour
    
    # Optional: Set filename for downloads
    response['Content-Disposition'] = f'inline; filename="{pdf_doc.original_filename}"'
    
    return response


# Add URL pattern
# council_finance/urls.py
from django.urls import path
from council_finance.views.pdf_views import serve_pdf

urlpatterns = [
    # ... existing patterns
    path('pdf/<slug:council_slug>/<uuid:pdf_id>/', serve_pdf, name='serve_pdf'),
]
```

#### 3.3 Enhanced PDF Processing API
```python
# council_finance/views/council_edit_api.py - Enhanced PDF processing
import hashlib
import uuid
from council_finance.models import PDFDocument

@login_required
@require_http_methods(['POST'])
def process_pdf_with_viewing(request):
    """Enhanced PDF processing that stores file for viewing."""
    
    # ... existing validation code ...
    
    # Process uploaded file
    pdf_file = request.FILES.get('pdf_file')
    if not pdf_file:
        return JsonResponse({'success': False, 'error': 'PDF file required'})
    
    # Calculate file hash for deduplication
    file_content = pdf_file.read()
    file_hash = hashlib.sha256(file_content).hexdigest()
    
    # Reset file pointer
    pdf_file.seek(0)
    
    # Check for existing PDF
    existing_pdf = PDFDocument.objects.filter(
        council=council,
        year=year,
        file_hash=file_hash
    ).first()
    
    if existing_pdf and existing_pdf.processing_status == 'completed':
        # Return existing processed data
        return JsonResponse({
            'success': True,
            'pdf_url': request.build_absolute_uri(existing_pdf.get_serving_url()),
            'extracted_data': existing_pdf.extracted_data,  # Stored processing results
            'message': 'Using previously processed PDF'
        })
    
    # Create new PDF document record
    pdf_doc = PDFDocument.objects.create(
        council=council,
        year=year,
        filename=f"{uuid.uuid4().hex}.pdf",
        original_filename=pdf_file.name,
        file_size=len(file_content),
        file_hash=file_hash,
        uploaded_by=request.user,
        processing_status='processing'
    )
    
    try:
        # Save file to disk
        file_path = pdf_doc.get_file_path()
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        # Process with existing Tika + AI pipeline
        # ... existing processing code ...
        
        # Store processing results
        pdf_doc.processing_status = 'completed'
        pdf_doc.processed_at = timezone.now()
        # Store extracted_data as JSON field or related objects
        pdf_doc.save()
        
        # Return results with PDF viewing URL
        return JsonResponse({
            'success': True,
            'pdf_url': request.build_absolute_uri(pdf_doc.get_serving_url()),
            'pdf_id': str(pdf_doc.id),
            'extracted_data': formatted_results,
            'confidence_scores': confidence_scores,
            'processing_stats': processing_stats
        })
        
    except Exception as e:
        pdf_doc.processing_status = 'failed'
        pdf_doc.processing_error = str(e)
        pdf_doc.save()
        
        # Clean up file
        if os.path.exists(file_path):
            os.remove(file_path)
            
        raise e
```

### **Phase 4: Frontend Integration (Day 5-6)**

#### 4.1 Enhanced AIExtractionReview Component
```jsx
// frontend/src/components/council-edit/AIExtractionReview.jsx - Integration
import PDFViewer from './PDFViewer';

const AIExtractionReview = ({
  /* existing props */
  pdfUrl,        // New: URL to the uploaded PDF for viewing
  pdfId,         // New: PDF document ID
}) => {
  const [selectedField, setSelectedField] = useState(null);
  const [pdfCurrentPage, setPdfCurrentPage] = useState(1);
  
  // Handle field selection for highlighting
  const handleFieldSelect = useCallback((fieldSlug) => {
    setSelectedField(fieldSlug);
    
    // Navigate to page where this field was found
    const fieldData = extractedData[fieldSlug];
    if (fieldData?.page_number) {
      setPdfCurrentPage(fieldData.page_number);
    }
  }, [extractedData]);

  // Auto-navigate to page when field is focused
  const handleFieldFocus = useCallback((fieldSlug) => {
    handleFieldSelect(fieldSlug);
  }, [handleFieldSelect]);

  return (
    <div className={`bg-white ${className}`}>
      <div className="max-w-full mx-auto px-4 py-6">
        
        {/* Header - existing */}
        
        {/* Main Content - Two Column Layout */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
          
          {/* Left Column: Field Review (existing with enhancements) */}
          <div className="space-y-6">
            
            {/* Summary Stats - existing */}
            
            {/* Field Groups with PDF Navigation */}
            {Object.entries(fieldGroups).map(([groupKey, group]) => {
              if (group.fields.length === 0) return null;
              
              return (
                <div key={groupKey} className="border border-gray-300">
                  <div className="bg-gray-50 px-6 py-4 border-b border-gray-300">
                    <h3 className="text-lg font-semibold text-gray-900">
                      {group.title.replace(group.icon, '').trim()}
                      <span className="ml-3 text-sm font-normal text-gray-600">
                        ({group.fields.length} field{group.fields.length !== 1 ? 's' : ''})
                      </span>
                    </h3>
                  </div>
                  
                  <div className="divide-y divide-gray-200">
                    {group.fields.map((field) => {
                      const isSelected = selectedField === field.slug;
                      const isRejected = rejectedFields.has(field.slug);
                      const isEdited = editedValues[field.slug] !== undefined;
                      
                      return (
                        <div
                          key={field.slug}
                          className={`p-6 transition-colors cursor-pointer ${
                            isSelected 
                              ? 'bg-blue-50 border-l-4 border-blue-500' 
                              : isRejected 
                              ? 'bg-gray-50' 
                              : 'bg-white hover:bg-gray-50'
                          }`}
                          onClick={() => handleFieldSelect(field.slug)}
                        >
                          {/* Field Header with PDF Navigation */}
                          <div className="mb-4 pb-3 border-b border-gray-200">
                            <div className="flex items-start justify-between">
                              <div>
                                <h4 className="text-lg font-semibold text-gray-900 flex items-center">
                                  {field.name}
                                  {isSelected && (
                                    <span className="ml-2 inline-flex items-center px-2 py-1 bg-blue-100 text-blue-800 text-xs font-medium">
                                      👁️ Viewing in PDF
                                    </span>
                                  )}
                                </h4>
                                <div className="flex items-center space-x-4 mt-2">
                                  <div className={`inline-flex items-center px-2 py-1 text-xs font-medium border ${getConfidenceColor(field.confidence)}`}>
                                    {getConfidenceLabel(field.confidence)} ({Math.round(field.confidence * 100)}%)
                                  </div>
                                  {field.page && (
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        setPdfCurrentPage(field.page);
                                        handleFieldSelect(field.slug);
                                      }}
                                      className="inline-flex items-center px-2 py-1 bg-gray-100 text-gray-700 text-xs font-medium hover:bg-gray-200 transition-colors"
                                    >
                                      📄 Page {field.page}
                                    </button>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>

                          {/* Existing field content with enhanced interactivity */}
                          {/* ... value fields, action buttons, source text ... */}
                          
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
          
          {/* Right Column: PDF Viewer */}
          <div className="xl:sticky xl:top-4 xl:self-start">
            <div className="bg-white border border-gray-300 overflow-hidden">
              <div className="bg-gray-50 px-6 py-4 border-b border-gray-300">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                  📄 Source Document
                  {selectedField && (
                    <span className="ml-3 text-sm font-normal text-blue-600">
                      Highlighting: {extractedData[selectedField]?.field_name}
                    </span>
                  )}
                </h3>
                <p className="text-sm text-gray-600 mt-1">
                  Click on fields to see their location in the PDF
                </p>
              </div>
              
              {pdfUrl ? (
                <PDFViewer
                  pdfUrl={pdfUrl}
                  extractedData={extractedData}
                  highlightedField={selectedField}
                  onPageChange={setPdfCurrentPage}
                  className="border-0"
                />
              ) : (
                <div className="p-12 text-center text-gray-500">
                  <div className="text-4xl mb-4">📄</div>
                  <p>PDF not available for viewing</p>
                  <p className="text-sm mt-2">File may still be processing or was uploaded via URL</p>
                </div>
              )}
            </div>
          </div>
          
        </div>
        
        {/* Action buttons - existing */}
        
      </div>
    </div>
  );
};
```

### **Phase 5: Advanced Features (Day 7+)**

#### 5.1 Text Search in PDF
```jsx
// Enhanced PDFViewer with search capability
const PDFViewer = ({ /* existing props */, searchEnabled = false }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [currentSearchIndex, setCurrentSearchIndex] = useState(0);
  const [textLayer, setTextLayer] = useState(null);

  const performSearch = useCallback(async (term) => {
    if (!term.trim() || !textLayer) {
      setSearchResults([]);
      return;
    }

    // Search through text layer for matches
    const results = [];
    textLayer.textDivs.forEach((textDiv, index) => {
      const text = textDiv.textContent.toLowerCase();
      const searchLower = term.toLowerCase();
      
      if (text.includes(searchLower)) {
        results.push({
          pageNumber: pageNumber,
          elementIndex: index,
          text: textDiv.textContent,
          element: textDiv
        });
      }
    });
    
    setSearchResults(results);
    setCurrentSearchIndex(0);
  }, [textLayer, pageNumber]);

  // Add search UI to PDF controls
  return (
    <div className="pdf-viewer">
      {/* Enhanced controls with search */}
      <div className="pdf-controls bg-gray-50 border-b border-gray-300 px-4 py-3 space-y-2">
        {/* Navigation controls - existing */}
        
        {searchEnabled && (
          <div className="flex items-center space-x-2">
            <input
              type="text"
              placeholder="Search in document..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                performSearch(e.target.value);
              }}
              className="flex-1 px-3 py-1 border border-gray-300 text-sm"
            />
            {searchResults.length > 0 && (
              <div className="flex items-center space-x-2 text-sm text-gray-600">
                <span>{currentSearchIndex + 1} of {searchResults.length}</span>
                <button
                  onClick={() => setCurrentSearchIndex(Math.max(0, currentSearchIndex - 1))}
                  className="px-2 py-1 bg-white border border-gray-300 hover:bg-gray-50"
                >
                  ↑
                </button>
                <button
                  onClick={() => setCurrentSearchIndex(Math.min(searchResults.length - 1, currentSearchIndex + 1))}
                  className="px-2 py-1 bg-white border border-gray-300 hover:bg-gray-50"
                >
                  ↓
                </button>
              </div>
            )}
          </div>
        )}
      </div>
      
      {/* PDF display with search highlights */}
    </div>
  );
};
```

#### 5.2 User Annotations System
```jsx
// Annotation component for user feedback
const AnnotationLayer = ({ 
  pageNumber, 
  annotations = [], 
  onAddAnnotation,
  canEdit = false
}) => {
  const [newAnnotation, setNewAnnotation] = useState(null);
  const [showingAnnotations, setShowingAnnotations] = useState(true);

  const handleClick = (event) => {
    if (!canEdit) return;
    
    const rect = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 100;
    const y = ((event.clientY - rect.top) / rect.height) * 100;
    
    setNewAnnotation({ x, y, pageNumber });
  };

  return (
    <div className="absolute inset-0">
      {canEdit && (
        <div 
          className="absolute inset-0 cursor-crosshair"
          onClick={handleClick}
        />
      )}
      
      {showingAnnotations && annotations
        .filter(annotation => annotation.pageNumber === pageNumber)
        .map((annotation, index) => (
          <div
            key={index}
            className="absolute group"
            style={{
              left: `${annotation.x}%`,
              top: `${annotation.y}%`,
              transform: 'translate(-50%, -50%)'
            }}
          >
            {/* Annotation marker */}
            <div className="w-6 h-6 bg-red-500 rounded-full border-2 border-white shadow-lg cursor-pointer flex items-center justify-center text-white text-xs font-bold">
              {index + 1}
            </div>
            
            {/* Annotation tooltip */}
            <div className="absolute top-8 left-1/2 transform -translate-x-1/2 bg-black text-white px-3 py-2 text-sm rounded shadow-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity z-30 max-w-xs">
              <div className="font-medium">{annotation.type || 'Note'}</div>
              <div className="text-xs">{annotation.comment}</div>
              <div className="text-xs opacity-75 mt-1">
                By {annotation.author} • {new Date(annotation.created).toLocaleDateString()}
              </div>
            </div>
          </div>
        ))
      }
      
      {newAnnotation && (
        <AnnotationPopup 
          annotation={newAnnotation}
          onSave={(comment, type) => {
            onAddAnnotation({
              ...newAnnotation,
              comment,
              type,
              author: 'Current User',
              created: new Date()
            });
            setNewAnnotation(null);
          }}
          onCancel={() => setNewAnnotation(null)}
        />
      )}
    </div>
  );
};
```

## Implementation Timeline

### **Week 1: Core Implementation**
- **Day 1-2**: Setup dependencies, basic PDF viewer, PDF serving infrastructure
- **Day 3-4**: Extraction highlighting system, coordinate mapping
- **Day 5**: Frontend integration with existing extraction review
- **Day 6**: Backend PDF storage and secure serving
- **Day 7**: Testing, bug fixes, polish

### **Week 2: Advanced Features & Optimization**
- **Day 8-9**: Search functionality, user annotations
- **Day 10-11**: Mobile responsiveness, performance optimization
- **Day 12-13**: Error handling, edge cases, accessibility
- **Day 14**: Documentation, deployment preparation

## Testing Strategy

### **Unit Tests**
```javascript
// Test PDF viewer component
describe('PDFViewer', () => {
  test('renders PDF successfully', async () => {
    const { getByText } = render(
      <PDFViewer pdfUrl="/test.pdf" extractedData={{}} />
    );
    
    await waitFor(() => {
      expect(getByText(/pdf loaded/i)).toBeInTheDocument();
    });
  });
  
  test('handles PDF load errors gracefully', async () => {
    const { getByText } = render(
      <PDFViewer pdfUrl="/nonexistent.pdf" extractedData={{}} />
    );
    
    await waitFor(() => {
      expect(getByText(/failed to load pdf/i)).toBeInTheDocument();
    });
  });
});
```

### **Integration Tests**
```python
# Test PDF serving with authentication
class PDFServingTests(TestCase):
    def test_authenticated_pdf_access(self):
        """Test that authenticated users can access PDFs they have permission for."""
        user = self.create_user_with_permissions()
        pdf_doc = self.create_test_pdf()
        
        self.client.force_login(user)
        response = self.client.get(pdf_doc.get_serving_url())
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
    
    def test_unauthorized_pdf_access_denied(self):
        """Test that unauthorized users cannot access PDFs."""
        pdf_doc = self.create_test_pdf()
        
        response = self.client.get(pdf_doc.get_serving_url())
        self.assertEqual(response.status_code, 302)  # Redirect to login
```

## Performance Considerations

### **Client-Side Optimization**
```javascript
// Lazy loading for large PDFs
const PDFViewer = React.memo(({ pdfUrl, ...props }) => {
  const [shouldLoad, setShouldLoad] = useState(false);
  
  useEffect(() => {
    const timer = setTimeout(() => setShouldLoad(true), 100);
    return () => clearTimeout(timer);
  }, []);
  
  if (!shouldLoad) {
    return <PDFLoadingPlaceholder />;
  }
  
  return <ActualPDFViewer pdfUrl={pdfUrl} {...props} />;
});

// PDF page caching
const PAGE_CACHE = new Map();
const usePDFPageCache = (pdfUrl, pageNumber) => {
  const cacheKey = `${pdfUrl}-${pageNumber}`;
  
  return useMemo(() => {
    if (PAGE_CACHE.has(cacheKey)) {
      return PAGE_CACHE.get(cacheKey);
    }
    
    const pageData = renderPage(pdfUrl, pageNumber);
    PAGE_CACHE.set(cacheKey, pageData);
    return pageData;
  }, [cacheKey]);
};
```

### **Server-Side Optimization**
```python
# PDF caching and optimization
@cache_page(60 * 60)  # Cache for 1 hour
def serve_pdf(request, council_slug, pdf_id):
    # ... authentication checks ...
    
    # Add ETag for client-side caching
    file_path = pdf_doc.get_file_path()
    stat = os.stat(file_path)
    etag = f'"{pdf_doc.file_hash}-{stat.st_mtime}"'
    
    if request.META.get('HTTP_IF_NONE_MATCH') == etag:
        return HttpResponseNotModified()
    
    response = FileResponse(open(file_path, 'rb'), content_type='application/pdf')
    response['ETag'] = etag
    return response
```

## Security Considerations

### **Access Control**
- PDF URLs contain UUIDs to prevent enumeration attacks
- Authentication required for all PDF access
- User permissions checked against council data access rights
- File integrity verification using SHA256 hashes

### **File Security**
- PDFs stored outside web root directory
- MIME type validation on upload and serving
- File size limits to prevent storage abuse
- Virus scanning integration point (future enhancement)

### **Privacy & Data Protection**
- PDFs automatically purged after 90 days
- Processing logs exclude sensitive financial data
- User audit trail for all PDF access
- GDPR compliance for user data in annotations

## Deployment Checklist

### **Environment Setup**
- [ ] Install PDF.js dependencies: `npm install react-pdf pdfjs-dist`
- [ ] Configure PDF storage directory with proper permissions
- [ ] Set up media serving for authenticated PDF access
- [ ] Update CSP headers to allow PDF.js worker scripts

### **Database Migration**
- [ ] Create PDFDocument model migration
- [ ] Add indexes for performance (council, year, file_hash)
- [ ] Set up automated cleanup job for old PDFs

### **Frontend Build**
- [ ] Update build configuration to include PDF.js workers
- [ ] Test PDF rendering on different browsers
- [ ] Verify responsive design on mobile devices
- [ ] Performance test with large PDFs (>10MB)

### **Production Monitoring**
- [ ] Add logging for PDF access patterns
- [ ] Monitor PDF storage disk usage
- [ ] Set up alerts for PDF processing failures
- [ ] Track PDF viewing analytics (optional)

## Success Metrics

### **User Experience**
- **PDF Load Time**: <3 seconds for typical financial statements
- **Highlight Accuracy**: Users can locate extracted data in <10 seconds
- **Mobile Compatibility**: Full functionality on tablets and large phones
- **Browser Support**: Chrome, Firefox, Safari, Edge latest versions

### **System Performance**
- **Memory Usage**: <100MB per PDF viewer instance
- **Storage Efficiency**: PDF deduplication >80% for repeated uploads
- **Server Load**: <10% increase in CPU/memory usage
- **Caching Hit Rate**: >70% for frequently accessed PDFs

### **Feature Adoption**
- **PDF Viewing Usage**: >60% of PDF uploads result in viewing sessions
- **Highlight Interaction**: >40% of users click on extraction highlights
- **Error Rate**: <5% of PDF load attempts fail
- **User Satisfaction**: Positive feedback on extraction verification workflow

## Future Enhancements

### **Phase 2 Features**
- **Coordinate-Based Highlighting**: Precise text positioning using OCR coordinate data
- **PDF Comparison Mode**: Side-by-side view of multiple years for same council
- **Batch Processing Interface**: Upload and process multiple PDFs simultaneously
- **Mobile PDF Editor**: Touch-friendly interface for tablet users

### **Advanced Integrations**
- **OCR Enhancement**: Improve scanned PDF text extraction accuracy
- **Template Recognition**: Auto-detect common financial statement formats
- **Data Validation Rules**: Cross-check extracted values for consistency
- **Export Capabilities**: Download annotated PDFs with extraction highlights

This comprehensive implementation plan provides a clear roadmap for building a professional PDF viewing experience that enhances the AI extraction workflow. The phased approach allows for iterative development and testing, ensuring a robust and user-friendly result.

Ready to start implementing when you wake up! 🌅