# AI-POWERED FACTOIDS SYSTEM
*Generated: 2025-07-31*
*Status: NEW ARCHITECTURE - Replaces counter-based factoid system*

## Overview
Factoids are now AI-generated insights that appear once per council detail page, providing intelligent analysis of council financial data. This replaces the previous complex template-based system tied to individual counters.

## Architecture

### Core Concept
- **Single factoid playlist** per council detail page (below header)
- **AI-generated insights** based on council's complete financial dataset
- **Dynamic temporal analysis** (year-over-year, trends, peaks, comparisons)
- **No counter associations** - factoids are council-wide features
- **JSON API response** parsed dynamically via AJAX

## Implementation

### Backend API
```python
# views/api/factoid_api.py
@api_view(['GET'])
def ai_council_factoids(request, council_slug):
    """Generate AI factoids for a council"""
    
    # Gather comprehensive council data
    council_data = {
        'council': council,
        'financial_time_series': get_financial_time_series(council),
        'peer_comparisons': get_peer_council_data(council),
        'population_data': get_population_trends(council),
        'context': get_regional_context(council)
    }
    
    # Generate AI insights
    ai_factoids = AIFactoidGenerator.generate_insights(
        data=council_data,
        limit=3,
        style='news_ticker'
    )
    
    return JsonResponse({
        'success': True,
        'factoids': ai_factoids,
        'generated_at': timezone.now().isoformat(),
        'council': council_slug
    })
```

### AI Generator Service
```python
# services/ai_factoid_generator.py
class AIFactoidGenerator:
    
    @staticmethod
    def generate_insights(data, limit=3, style='news_ticker'):
        """Generate factoids using OpenAI API"""
        
        prompt = f"""
        Analyze this UK council's financial data and generate {limit} interesting factoids.
        
        Council: {data['council'].name}
        Population: {data['population_data']['latest']:,}
        
        Financial Data (last 5 years):
        {AIFactoidGenerator._format_financial_data(data['financial_time_series'])}
        
        Peer Comparison:
        {AIFactoidGenerator._format_peer_data(data['peer_comparisons'])}
        
        Requirements:
        - Maximum 25 words per factoid
        - Focus on trends, comparisons, notable patterns
        - Use specific figures and years
        - Write in news ticker style
        - Return as JSON array with 'text' and 'insight_type' fields
        
        Example format:
        [
            {{
                "text": "Interest payments peaked in 2023 at £3.8M, up 58% from 2019",
                "insight_type": "trend"
            }},
            {{
                "text": "Spends £205 per resident on interest - 23% above regional average",
                "insight_type": "comparison"
            }}
        ]
        """
        
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        
        # Parse JSON response
        try:
            factoids = json.loads(response.choices[0].message.content)
            return factoids
        except json.JSONDecodeError:
            # Fallback to basic factoids if AI fails
            return AIFactoidGenerator._generate_fallback_factoids(data)
```

### Frontend Integration
```javascript
// static/js/ai-factoids.js
class AIFactoidPlaylist {
    constructor(container) {
        this.container = container;
        this.council = container.dataset.council;
        this.factoids = [];
        this.currentIndex = 0;
        this.interval = null;
        
        this.init();
    }
    
    async init() {
        await this.loadFactoids();
        this.startPlaylist();
    }
    
    async loadFactoids() {
        try {
            const response = await fetch(`/api/factoids/ai/${this.council}/`);
            const data = await response.json();
            
            if (data.success) {
                this.factoids = data.factoids;
                console.log(`✅ Loaded ${this.factoids.length} AI factoids for ${this.council}`);
            }
        } catch (error) {
            console.error('❌ Failed to load AI factoids:', error);
            this.showError();
        }
    }
    
    startPlaylist() {
        if (this.factoids.length === 0) return;
        
        this.showFactoid(0);
        
        // Rotate every 8 seconds
        this.interval = setInterval(() => {
            this.currentIndex = (this.currentIndex + 1) % this.factoids.length;
            this.showFactoid(this.currentIndex);
        }, 8000);
    }
    
    showFactoid(index) {
        const factoid = this.factoids[index];
        
        // Smooth fade transition
        this.container.style.opacity = '0';
        
        setTimeout(() => {
            this.container.innerHTML = `
                <div class="flex items-center space-x-3 py-3 px-4 bg-blue-50 border-l-4 border-blue-400 rounded-r-lg">
                    <div class="flex-shrink-0">
                        ${this.getInsightIcon(factoid.insight_type)}
                    </div>
                    <div class="text-sm text-blue-900 font-medium">
                        ${factoid.text}
                    </div>
                    <div class="text-xs text-blue-600">
                        AI Insight
                    </div>
                </div>
            `;
            this.container.style.opacity = '1';
        }, 300);
    }
    
    getInsightIcon(type) {
        const icons = {
            'trend': '📈',
            'comparison': '⚖️', 
            'peak': '🏔️',
            'change': '🔄',
            'ranking': '🏆'
        };
        return icons[type] || '💡';
    }
}

// Initialize on council detail pages
document.addEventListener('DOMContentLoaded', () => {
    const container = document.querySelector('.ai-factoid-playlist');
    if (container) {
        new AIFactoidPlaylist(container);
    }
});
```

### Template Integration
```django
<!-- templates/council_detail.html -->
<div class="council-header">
    <!-- Existing header content -->
</div>

<!-- NEW: Single AI factoid playlist -->
<div class="mt-4 mb-6">
    <div class="ai-factoid-playlist transition-opacity duration-300" 
         data-council="{{ council.slug }}">
        <!-- Loading state -->
        <div class="flex items-center space-x-3 py-3 px-4 bg-gray-50 border-l-4 border-gray-300 rounded-r-lg">
            <div class="animate-spin">⏳</div>
            <div class="text-sm text-gray-600">Loading insights...</div>
        </div>
    </div>
</div>

<!-- Remove old counter-specific factoid containers -->
```

## Data Sources

### Available Data for AI Analysis
```python
# Data accessible to AI factoid generation
AVAILABLE_METRICS = {
    'financial_time_series': [
        'total_debt', 'current_liabilities', 'long_term_liabilities',
        'interest_payments', 'total_revenue', 'total_expenditure',
        'council_tax_income', 'government_grants', 'reserves'
    ],
    'temporal_analysis': [
        'year_over_year_changes', 'peak_years', 'trend_direction',
        'volatility_measures', 'compound_growth_rates'
    ],
    'comparative_data': [
        'peer_council_averages', 'regional_benchmarks', 
        'national_percentiles', 'council_type_comparisons'
    ],
    'contextual_data': [
        'population_trends', 'deprivation_indices', 
        'political_control_changes', 'major_events'
    ]
}
```

### Example AI Factoid Types
```python
FACTOID_PATTERNS = {
    'trend': "Interest payments {direction} by {percentage}% since {start_year}",
    'peak': "Debt peaked in {year} at £{amount}M, now {comparison} that level",
    'comparison': "Spends £{amount} per resident - {percentage}% {above_below} regional average",
    'volatility': "Most volatile year was {year} with {metric} swinging {range}%",
    'efficiency': "Debt-to-revenue ratio of {ratio}% ranks {position} among peers",
    'context': "Despite {population_change}% population growth, debt {trend_direction}"
}
```

## Migration from Old System

### Deprecated Components
- FactoidTemplate model (kept for rollback, marked inactive)
- Counter-factoid associations (ManyToMany relationships)
- Template-based factoid generation
- Multiple factoid playlists per page
- Factoid builder interface

### Migration Steps
1. **Phase 1**: Deploy AI system alongside old system
2. **Phase 2**: Switch council detail pages to AI factoids
3. **Phase 3**: Remove counter-specific factoid displays
4. **Phase 4**: Deprecate factoid builder
5. **Phase 5**: Clean up old models (after 30 days)

## Performance Considerations

### Caching Strategy
```python
# Cache AI-generated factoids for 6 hours
@cache_result(timeout=21600)  # 6 hours
def get_ai_factoids(council_slug):
    return AIFactoidGenerator.generate_insights(council_data)
```

### Cost Management
- **Rate limiting**: Max 10 AI requests per council per hour
- **Batch processing**: Generate factoids for multiple councils in single API call
- **Fallback system**: Static factoids if AI service unavailable
- **Smart refresh**: Only regenerate if council data changed significantly

## Error Handling

### AI Service Failures
```python
def handle_ai_failure(council):
    """Fallback when AI service fails"""
    return [
        {
            "text": f"Latest debt figure: £{council.latest_debt_amount}M for {council.latest_year}",
            "insight_type": "basic"
        },
        {
            "text": f"Population: {council.latest_population:,} residents",
            "insight_type": "basic"
        }
    ]
```

### Frontend Error States
- Loading indicators during AI generation
- Graceful degradation to basic stats
- Retry mechanisms for temporary failures
- Clear error messages for permanent failures

## Future Enhancements

### Phase 2 Features
- **Personalized insights**: Based on user's followed councils
- **Interactive factoids**: Click for detailed analysis
- **Insight explanations**: "Why is this interesting?" tooltips
- **Social sharing**: Share interesting factoids on social media

### Phase 3 Features
- **Predictive insights**: "Based on trends, expect..."
- **Alert system**: Notify when significant changes detected
- **Comparative insights**: "Similar to..." cross-council analysis
- **Historical context**: "Highest since 2008 financial crisis"

## API Reference

### Endpoints
```
GET /api/factoids/ai/{council_slug}/
    - Generates AI factoids for council
    - Returns: JSON with factoids array
    - Cache: 6 hours
    - Rate limit: 10/hour per council

GET /api/factoids/ai/batch/
    - Bulk generate for multiple councils
    - Body: {"councils": ["council-1", "council-2"]}
    - Returns: {"council-1": [...factoids], "council-2": [...factoids]}
```

### Response Format
```json
{
    "success": true,
    "council": "worcestershire",
    "factoids": [
        {
            "text": "Interest payments peaked in 2023 at £3.8M, up 58% from 2019",
            "insight_type": "trend",
            "confidence": 0.95
        }
    ],
    "generated_at": "2025-07-31T12:30:00Z",
    "data_period": "2019-2024",
    "ai_model": "gpt-4"
}
```

---

## Key Benefits of AI Approach

1. **Intelligent Insights**: Discovers patterns humans might miss
2. **Natural Language**: Reads like professional journalism
3. **Maintenance-Free**: No template creation or updates needed
4. **Scalable**: Works for any council automatically
5. **Fresh Content**: Different insights based on latest data
6. **Contextually Relevant**: Prioritizes most interesting findings

This system transforms factoids from static templates to dynamic, intelligent insights that provide genuine value to users exploring council finances.