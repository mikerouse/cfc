# PDF Page Image Extraction - Implementation Options

*Research conducted 2025-08-11 for enhancing the AI PDF processing system*

## Current System Overview

The current system extracts text from PDFs using Apache Tika and identifies financial data using hybrid regex+AI analysis. Users have requested the ability to view the actual PDF pages where data was extracted to verify accuracy.

## Implementation Options

### Option 1: Server-Side PDF-to-Image Conversion
**Implementation**: Add `pdf2image` library + `poppler-utils` dependency

```python
# Example implementation
from pdf2image import convert_from_path
import io
import base64

def extract_page_images(pdf_path: str) -> Dict[int, str]:
    """Convert PDF pages to base64-encoded images for display."""
    images = convert_from_path(pdf_path, dpi=150, fmt='PNG')
    page_images = {}
    
    for i, image in enumerate(images, 1):
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        base64_image = base64.b64encode(buffer.getvalue()).decode()
        page_images[i] = f"data:image/png;base64,{base64_image}"
    
    return page_images
```

**Pros**:
- Server controls image quality and format
- Works with any PDF, regardless of browser capabilities
- Can highlight specific regions where data was extracted
- Images can be cached server-side

**Cons**:
- Requires system dependencies (poppler-utils on Linux, additional setup on Windows)
- Increases server resource usage (CPU, memory, storage)
- Larger API responses due to base64-encoded images
- Additional dependency management

**Estimated Development Time**: 2-3 days

### Option 2: Client-Side PDF.js Integration
**Implementation**: Use PDF.js library in React frontend

```javascript
// Example React component
import { pdfjs, Document, Page } from 'react-pdf';

const PDFPageViewer = ({ pdfUrl, pageNumber, extractedData }) => {
  return (
    <div className="pdf-viewer">
      <Document file={pdfUrl}>
        <Page 
          pageNumber={pageNumber}
          renderTextLayer={false}
          renderAnnotationLayer={false}
        />
      </Document>
      {/* Overlay extraction highlights */}
      <ExtractionHighlights data={extractedData} />
    </div>
  );
};
```

**Pros**:
- No server-side processing required
- Native PDF rendering in browser
- Can overlay extraction highlights precisely
- Smaller API responses (just PDF URLs)
- User can navigate full PDF if needed

**Cons**:
- Requires PDF files to be accessible via URL
- Client-side PDF processing can be slow/memory intensive
- Browser compatibility considerations
- More complex frontend implementation

**Estimated Development Time**: 3-4 days

### Option 3: Enhanced Tika Service
**Implementation**: Extend the Tika service to return page images alongside text

```python
# Enhanced Tika request
def extract_text_and_images(pdf_path: str) -> Dict:
    """Extract both text content and page images from PDF."""
    
    # Text extraction (existing)
    text_response = requests.put(
        f'{tika_endpoint}/text',
        data=pdf_content,
        headers={'Content-Type': 'application/pdf'}
    )
    
    # Image extraction (new)
    image_response = requests.put(
        f'{tika_endpoint}/rmeta/images',
        data=pdf_content,
        headers={'Content-Type': 'application/pdf'}
    )
    
    return {
        'text': text_response.text,
        'images': image_response.json()
    }
```

**Pros**:
- Leverages existing Tika infrastructure
- Centralized PDF processing
- Consistent with current architecture
- Can extract embedded images and render pages

**Cons**:
- Requires Tika service modifications (may not be under our control)
- Still requires server-side image processing resources
- May not provide fine-grained page control
- Dependent on Tika service capabilities

**Estimated Development Time**: 1-2 days (if Tika supports it), 1-2 weeks (if Tika needs extension)

### Option 4: Hybrid Approach - PDF Preview URLs
**Implementation**: Generate temporary PDF preview URLs for specific pages

```python
def create_pdf_page_preview(pdf_path: str, page_number: int) -> str:
    """Create a temporary URL for viewing a specific PDF page."""
    
    # Extract single page to temporary file
    from PyPDF2 import PdfReader, PdfWriter
    
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    writer.add_page(reader.pages[page_number - 1])
    
    # Save to temporary file with expiring URL
    temp_filename = f"preview_{uuid4().hex}.pdf"
    temp_path = os.path.join(settings.MEDIA_ROOT, 'temp', temp_filename)
    
    with open(temp_path, 'wb') as output_file:
        writer.write(output_file)
    
    # Return URL that expires in 1 hour
    return f"{settings.MEDIA_URL}temp/{temp_filename}?expires={int(time.time()) + 3600}"
```

**Pros**:
- Browser-native PDF rendering
- Focused view (single page only)
- No complex image conversion
- Lightweight API responses

**Cons**:
- Temporary file management required
- Security considerations (PDF access control)
- Limited highlighting capabilities
- Additional file I/O operations

**Estimated Development Time**: 2-3 days

## Recommendations

### Immediate Implementation (Phase 1): Option 4 - PDF Preview URLs
**Reasoning**: 
- Quick to implement with current infrastructure
- Leverages browser PDF capabilities
- Minimal server resource impact
- Good user experience for verification

### Future Enhancement (Phase 2): Option 2 - PDF.js Integration  
**Reasoning**:
- Superior user experience with highlighting
- Full PDF navigation capabilities
- Better integration with extraction workflow
- Industry standard for web PDF viewing

### Implementation Plan

#### Phase 1 (Week 1):
1. Add PyPDF2 dependency to requirements.txt
2. Implement single-page PDF extraction function
3. Create temporary file management with expiration
4. Add page preview URL to API response
5. Update React component to show PDF preview link
6. Add security middleware for temp file access

#### Phase 2 (Future):
1. Add react-pdf dependency to frontend
2. Implement PDF.js viewer component
3. Add extraction result highlighting overlay
4. Integrate with existing UI workflow
5. Add PDF navigation controls

### Security Considerations

1. **File Access Control**: Ensure temp PDF files are only accessible to authorized users
2. **File Cleanup**: Implement automatic cleanup of expired temp files
3. **Resource Limits**: Set limits on PDF processing to prevent DoS
4. **Input Validation**: Validate PDF content and page numbers

### Performance Considerations

1. **Caching**: Cache generated page previews for repeated requests
2. **Compression**: Compress PDF pages when possible
3. **Rate Limiting**: Limit preview generation requests per user
4. **Async Processing**: Consider background processing for large PDFs

## Example Integration

```javascript
// React component showing extraction with page preview
const FinancialFieldCard = ({ field, extraction }) => {
  return (
    <div className="field-card">
      <h3>{field.name}</h3>
      <p>Value: £{field.value}m</p>
      <p>Confidence: {field.confidence}%</p>
      
      {extraction.page_preview_url && (
        <div className="pdf-preview">
          <h4>Source Document:</h4>
          <iframe 
            src={extraction.page_preview_url}
            width="400" 
            height="300"
            title={`PDF page ${extraction.page_number}`}
          />
          <p>Page {extraction.page_number}</p>
        </div>
      )}
      
      <div className="source-context">
        <h4>Extracted from:</h4>
        <blockquote>"{extraction.source_text}"</blockquote>
      </div>
    </div>
  );
};
```

This research provides a clear path forward for implementing PDF page image extraction with both immediate and future enhancement options.