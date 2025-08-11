# Apache Tika Service Enhancement Plan for PDF Page Image Extraction

*Analysis of requirements for implementing Option 3: Enhanced Tika Service*

## Current Tika Service Status

Your current Tika service endpoint: `https://cfc-tika.onrender.com/tika`

Based on your existing implementation, you're currently using:
- Basic text extraction via `/tika` endpoint
- Standard PUT requests with PDF data
- Text response format

## What Apache Tika CAN Do (Built-in Capabilities)

### 1. PDF Page Rendering 🎯
Apache Tika includes **PDFBoxRenderer** that can render individual PDF pages as images:
- Converts each PDF page to BufferedImage
- Configurable DPI (default: 300)
- Multiple image formats (PNG, JPEG, TIFF)
- Gray/color rendering options

### 2. Recursive Metadata Extraction 🎯  
The `/rmeta` endpoint can extract:
- Page-level metadata
- Embedded image references
- Content structure information
- JSON response format with nested objects

### 3. PDF Configuration Options 🎯
PDFParserConfig supports:
- `extractInlineImages`: Extract embedded images
- `extractUniqueInlineImagesOnly`: Avoid duplicates  
- `ocrStrategy`: Page rendering for OCR (renders pages as images)
- Image format/DPI configuration

## Required Tika Service Modifications

### Option A: Custom Endpoint Development (Recommended)
**Create new endpoint**: `/tika/pages-with-images`

```java
// New Java endpoint on your Tika service
@PUT
@Path("/pages-with-images")
@Produces(MediaType.APPLICATION_JSON)
public Response extractPagesWithImages(
    @Context HttpHeaders headers,
    InputStream inputStream) {
    
    try {
        PDDocument document = PDDocument.load(inputStream);
        PDFRenderer renderer = new PDFRenderer(document);
        
        List<PageData> pages = new ArrayList<>();
        
        for (int i = 0; i < document.getNumberOfPages(); i++) {
            // Render page to image
            BufferedImage image = renderer.renderImageWithDPI(i, 150, ImageType.RGB);
            
            // Convert to base64 for JSON response
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            ImageIO.write(image, "PNG", baos);
            String base64Image = Base64.getEncoder().encodeToString(baos.toByteArray());
            
            // Extract text for this specific page
            PDFTextStripper stripper = new PDFTextStripper();
            stripper.setStartPage(i + 1);
            stripper.setEndPage(i + 1);
            String pageText = stripper.getText(document);
            
            pages.add(new PageData(
                i + 1,                                    // page number
                pageText,                                 // text content
                "data:image/png;base64," + base64Image,   // image data
                image.getWidth(),                         // dimensions
                image.getHeight()
            ));
        }
        
        return Response.ok(new PagesResponse(pages)).build();
        
    } catch (Exception e) {
        return Response.serverError().entity(e.getMessage()).build();
    }
}

// Supporting classes
class PageData {
    public int pageNumber;
    public String textContent;
    public String imageBase64;
    public int width;
    public int height;
    
    // constructor, getters, setters
}

class PagesResponse {
    public List<PageData> pages;
    public int totalPages;
    public long processingTimeMs;
    
    // constructor, getters, setters
}
```

### Option B: Configuration-Based Enhancement (Easier)
**Modify existing service** to support new parameters:

```java
// Enhanced existing endpoint with query parameters
@PUT
@Path("/tika")
@Produces({MediaType.TEXT_PLAIN, MediaType.APPLICATION_JSON})
public Response parseDocument(
    @Context HttpHeaders headers,
    @QueryParam("includeImages") boolean includeImages,
    @QueryParam("format") @DefaultValue("text") String format,
    @QueryParam("dpi") @DefaultValue("150") int dpi,
    InputStream inputStream) {
    
    if (includeImages && "json".equals(format)) {
        // Return enhanced JSON with page images
        return extractWithImages(inputStream, dpi);
    } else {
        // Existing text extraction behavior
        return extractText(inputStream);
    }
}
```

## Implementation Requirements

### 1. Dependencies (Add to Tika service)
```xml
<!-- Already included with Tika -->
<dependency>
    <groupId>org.apache.pdfbox</groupId>
    <artifactId>pdfbox</artifactId>
    <version>2.0.29</version>
</dependency>

<!-- For image processing -->
<dependency>
    <groupId>org.apache.pdfbox</groupId>
    <artifactId>pdfbox-tools</artifactId>
    <version>2.0.29</version>
</dependency>
```

### 2. Configuration Updates
```xml
<!-- tika-config.xml -->
<properties>
  <parsers>
    <parser class="org.apache.tika.parser.pdf.PDFParser">
      <params>
        <param name="extractInlineImages" type="bool">true</param>
        <param name="extractUniqueInlineImagesOnly" type="bool">true</param>
        <param name="ocrStrategy" type="string">ocr_and_text</param>
        <param name="imageStrategy" type="string">render_pages</param>
      </params>
    </parser>
  </parsers>
</properties>
```

### 3. Memory and Performance Configuration
```java
// Required JVM settings for image processing
-Xmx2G                    // Increased heap for image processing
-XX:+UseG1GC             // Better garbage collection for large objects
-Djava.awt.headless=true // Headless mode for image rendering
```

## API Usage After Enhancement

### New Request Format
```python
# Your updated Python code
import requests
import json

def extract_pdf_with_images(pdf_content, council_name="", year=""):
    """Extract text and page images from PDF using enhanced Tika service."""
    
    # Option A: New dedicated endpoint
    response = requests.put(
        'https://cfc-tika.onrender.com/tika/pages-with-images',
        data=pdf_content,
        headers={
            'Content-Type': 'application/pdf',
            'Accept': 'application/json',
            'X-Council-Name': council_name,
            'X-Year': year
        },
        timeout=180  # Longer timeout for image processing
    )
    
    # Option B: Enhanced existing endpoint
    response = requests.put(
        'https://cfc-tika.onrender.com/tika?includeImages=true&format=json&dpi=150',
        data=pdf_content,
        headers={
            'Content-Type': 'application/pdf',
            'Accept': 'application/json'
        },
        timeout=180
    )
    
    return response.json()
```

### Expected Response Format
```json
{
  "success": true,
  "totalPages": 42,
  "processingTimeMs": 8500,
  "pages": [
    {
      "pageNumber": 1,
      "textContent": "COUNCIL FINANCIAL STATEMENTS 2023/24...",
      "imageBase64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
      "width": 1240,
      "height": 1754,
      "containsFinancialData": true
    },
    {
      "pageNumber": 2,
      "textContent": "INCOME STATEMENT\nTotal Income £4,357.2...",
      "imageBase64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
      "width": 1240,
      "height": 1754,
      "containsFinancialData": true
    }
  ]
}
```

## Deployment Considerations

### 1. Render.com Resource Requirements
```yaml
# render.yaml updates needed
services:
  - type: web
    name: cfc-tika
    env: java
    buildCommand: mvn clean package -DskipTests
    startCommand: java -Xmx2G -XX:+UseG1GC -Djava.awt.headless=true -jar target/tika-server.jar
    plan: standard  # Upgrade from free tier - need more memory/CPU
    envVars:
      - key: JAVA_OPTS
        value: "-Xmx2G -XX:+UseG1GC -Djava.awt.headless=true"
```

### 2. Performance Impact
- **Memory usage**: 2-4x increase due to image rendering
- **Processing time**: 3-5x slower (text + image generation)
- **Response size**: 10-50x larger (base64 images)
- **CPU usage**: Significant increase for PDF rendering

### 3. Rate Limiting & Caching
```java
// Recommended additions
@Component
public class TikaRateLimiter {
    private final RedisTemplate<String, String> redis;
    
    public boolean allowRequest(String clientId) {
        // Limit to 10 PDF image requests per hour
        String key = "tika_images:" + clientId;
        String current = redis.opsForValue().get(key);
        
        if (current == null) {
            redis.opsForValue().set(key, "1", Duration.ofHours(1));
            return true;
        }
        
        int count = Integer.parseInt(current);
        if (count >= 10) {
            return false;
        }
        
        redis.opsForValue().increment(key);
        return true;
    }
}
```

## Integration with Your Existing System

### 1. Update PDF Processing Service
```python
# council_finance/services/pdf_processing.py
class TikaFinancialExtractor:
    def extract_text_and_images_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Extract both text and page images from PDF using enhanced Tika."""
        
        with open(pdf_path, 'rb') as pdf_file:
            response = requests.put(
                f'{self.tika_endpoint}/pages-with-images',
                data=pdf_file.read(),
                headers={'Content-Type': 'application/pdf'},
                timeout=180
            )
            
        if response.status_code == 200:
            data = response.json()
            return {
                'success': True,
                'pages': data['pages'],
                'total_pages': data['totalPages'],
                'processing_time': data['processingTimeMs'] / 1000
            }
        else:
            return {'success': False, 'error': response.text}

    def analyze_with_page_context(self, pages_data: List[Dict]) -> Dict:
        """Analyze extracted data with page-specific context."""
        
        financial_data = {}
        page_mapping = {}
        
        for page in pages_data:
            page_num = page['pageNumber']
            page_text = page['textContent']
            
            # Run regex extraction on this page's text
            page_results = self._extract_financial_data_fallback(page_text)
            
            for field, value in page_results.items():
                if value and field != '_metadata':
                    financial_data[field] = value
                    page_mapping[field] = {
                        'page_number': page_num,
                        'page_image': page['imageBase64'],
                        'source_text': page_results.get('_metadata', {}).get(field, {}).get('source_text', '')
                    }
        
        return {
            'extracted_data': financial_data,
            'page_mapping': page_mapping
        }
```

### 2. Update API Response Format
```python
# council_finance/views/council_edit_api.py
def process_pdf_with_page_images(request):
    """Enhanced PDF processing with page images."""
    
    extractor = TikaFinancialExtractor()
    
    # Extract text and images from all pages
    extraction_result = extractor.extract_text_and_images_from_pdf(pdf_path)
    
    if not extraction_result['success']:
        return JsonResponse({'success': False, 'error': extraction_result['error']})
    
    # Analyze with page context
    analysis_result = extractor.analyze_with_page_context(extraction_result['pages'])
    
    # Format for frontend
    formatted_results = {}
    for field_slug, value in analysis_result['extracted_data'].items():
        page_info = analysis_result['page_mapping'].get(field_slug, {})
        
        formatted_results[field_slug] = {
            'value': value,
            'field_name': field_definitions[field_slug]['name'],
            'source_text': page_info.get('source_text', ''),
            'page_number': page_info.get('page_number'),
            'page_image': page_info.get('page_image'),  # Base64 image data
            'confidence': 0.8
        }
    
    return JsonResponse({
        'success': True,
        'extracted_data': formatted_results,
        'total_pages': extraction_result['total_pages']
    })
```

## Pros and Cons of Tika Enhancement

### ✅ Advantages
1. **Centralized Processing**: All PDF work in one service
2. **Native PDF Rendering**: Uses PDFBox's proven rendering engine
3. **Page-Level Accuracy**: Exact page identification for extracted data
4. **Professional Image Quality**: High DPI rendering (300+ DPI)
5. **Consistent Architecture**: Extends existing Tika integration
6. **Built-in Capabilities**: Uses Tika's existing PDF parsing infrastructure

### ❌ Disadvantages  
1. **Significant Resource Requirements**: 2-4x memory, 3-5x processing time
2. **Large Response Payloads**: Base64 images dramatically increase response size
3. **Deployment Complexity**: Requires Render.com plan upgrade and Java heap tuning
4. **Single Point of Failure**: If Tika service fails, both text AND images fail
5. **Rate Limiting Needed**: Resource-intensive operations require strict limits
6. **Development Effort**: Requires Java development on the Tika service

## Recommended Implementation Timeline

### Phase 1 (Week 1-2): Preparation
1. **Upgrade Render.com Plan**: Move to Standard plan for resources
2. **Java Development**: Implement `/pages-with-images` endpoint
3. **Configuration**: Add PDF rendering config to tika-config.xml
4. **Testing**: Test memory usage and performance with sample PDFs

### Phase 2 (Week 3): Integration
1. **Python Client**: Update TikaFinancialExtractor for new endpoint
2. **API Enhancement**: Modify council_edit_api.py for page images
3. **Frontend Updates**: Enhance React component to display page images
4. **Caching Strategy**: Implement response caching for expensive operations

### Phase 3 (Week 4): Optimization
1. **Rate Limiting**: Add request limits and user quotas
2. **Performance Tuning**: Optimize image DPI, compression, format
3. **Error Handling**: Graceful fallback to text-only mode
4. **Monitoring**: Add performance metrics and alerting

## Alternative: Hybrid Approach

If full Tika enhancement proves too resource-intensive, consider:

1. **Keep existing Tika for text extraction**
2. **Add lightweight page preview service** (Option 4 from original research)
3. **Use PDFBox directly** in your Python service for single-page rendering
4. **Progressive enhancement**: Start with text, add images on-demand

This approach provides the benefits while minimizing risks and resource requirements.

## Conclusion

Enhancing your Tika service for Option 3 is technically feasible and would provide excellent integration with your existing architecture. However, it requires significant resource investment and Java development work.

**Recommendation**: Start with Option 4 (PDF Preview URLs) for immediate functionality, then consider Tika enhancement as a Phase 2 improvement once you validate user demand for full page image integration.