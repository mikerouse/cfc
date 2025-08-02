# LEADERBOARDS SYSTEM DOCUMENTATION

**Status:** Phase 1 Implementation in Progress  
**Created:** 2025-08-02  
**Last Updated:** 2025-08-02  

## Overview

The leaderboards system provides comprehensive rankings for both contributors and council financial metrics at `/leaderboards/`. The system features a modern Django REST API backend with beautiful mobile-first frontend and export capabilities.

## Current Implementation Status

### ✅ COMPLETED COMPONENTS

**Backend Architecture:**
- Complete REST API with proper throttling and caching
- `LeaderboardService` class with 9 predefined categories
- Export service supporting CSV, XLSX, PDF, PNG formats
- Proper error handling and logging
- Cache system (5-10 minute TTL)

**Frontend Implementation:**
- Responsive HTML template with mobile-first design
- Interactive category navigation with loading states
- Per capita toggle and year filtering
- Export controls integrated into UI
- Accessibility features and proper ARIA labels

**Categories Implemented:**
1. **contributors** - Top Contributors (functional ✅)
2. **total-debt** - Total Debt (needs data ❌)
3. **interest-payments** - Interest Payments (needs data ❌)
4. **current-liabilities** - Current Liabilities (needs data ❌)
5. **long-term-liabilities** - Long-term Liabilities (needs data ❌)
6. **reserves-balances** - Reserves & Balances (needs data ❌)
7. **council-tax-income** - Council Tax Income (needs data ❌)
8. **lowest-debt** - Lowest Debt (needs data ❌)
9. **lowest-interest** - Lowest Interest Payments (needs data ❌)

### ❌ COMPLETION GAPS

**Critical Issues:**
- Financial leaderboards return 0 entries (no FinancialFigure data)
- No current financial year set (`is_current=False` for all years)
- Field slug mappings may not match actual DataField records

**Enhancement Opportunities:**
- Real-time ranking updates via WebSocket
- Interactive charts and visualizations
- Regional/council type filtering
- Historical trend analysis

## Implementation Plan

### Phase 1: Core Data & Functionality (IN PROGRESS)

**Priority:** HIGH - Essential for basic functionality

**Tasks:**
1. **Data Population Fixes**
   - [ ] Set current financial year properly
   - [ ] Validate FinancialFigure data exists for core metrics
   - [ ] Verify field slug mappings match DataField records
   - [ ] Create sample data if needed for testing

2. **Data Validation**
   - [ ] Add management command for data health checks
   - [ ] Implement graceful fallbacks for missing data
   - [ ] Add logging for data availability issues

3. **Testing & Validation**
   - [ ] Test all 9 leaderboard categories
   - [ ] Verify per capita calculations
   - [ ] Test export functionality
   - [ ] Validate responsive design on all devices

### Phase 2: Enhanced UX & Features

**Priority:** MEDIUM - Value-added functionality

**Tasks:**
1. **Interactive Features**
   - [ ] AJAX-powered filtering without page reload
   - [ ] Progressive loading for better performance
   - [ ] "Compare Selected" functionality from rankings
   - [ ] Bookmarking and sharing specific views

2. **Visual Enhancements**
   - [ ] Chart.js integration for trend visualization
   - [ ] Progress bars showing council rankings
   - [ ] Animated rank change indicators
   - [ ] Council detail integration from rankings

### Phase 3: Advanced Features

**Priority:** LOW - Future enhancements

**Tasks:**
1. **Real-time Updates**
   - [ ] WebSocket integration for live ranking updates
   - [ ] Notifications for ranking changes
   - [ ] Historical trend analysis

2. **Social Features**
   - [ ] Follow councils in rankings
   - [ ] Share leaderboard snapshots
   - [ ] Community insights

## Technical Architecture

### API Endpoints

```
# Main leaderboard view
GET /leaderboards/

# API endpoints
GET /api/leaderboards/                           # Default contributors
GET /api/leaderboards/{category}/                # Specific category
GET /api/leaderboards/categories/                # Available categories
GET /api/councils/{council_slug}/rankings/       # Council-specific rankings

# Legacy support
GET /api/leaderboards/legacy/
```

### Service Classes

**LeaderboardService** (`council_finance/services/leaderboard_service.py`)
- Core business logic for ranking calculations
- Caching with 5-minute TTL
- Per capita calculations with population lookup
- Percentile calculations

**ExportService** (`council_finance/services/export_service.py`)
- Multi-format export (CSV, XLSX, PDF, PNG)
- Conditional imports for optional dependencies
- Template-based PDF generation

### Data Models

**Primary Models Used:**
- `FinancialFigure` - Core financial data
- `DataField` - Field definitions and slugs
- `FinancialYear` - Year management
- `CouncilCharacteristic` - Population data for per capita
- `UserProfile` - Contributor points

### Caching Strategy

```python
# Cache keys pattern
cache_key = f"leaderboard:{category}:{year}:{per_capita}:{limit}"

# TTL: 300 seconds (5 minutes)
# Automatic invalidation on data updates
```

## Data Requirements

### Required DataField Slugs
- `total-debt` → Total Debt calculations
- `interest-paid` → Interest Payments
- `current-liabilities` → Current Liabilities  
- `long-term-liabilities` → Long-term Liabilities
- `reserves-and-balances` → Reserves & Balances
- `council-tax-income` → Council Tax Income
- `population` → Per capita calculations

### Database Health Checks

Run these commands to verify data availability:

```python
# Check current financial year
FinancialYear.objects.filter(is_current=True).exists()

# Check financial figures
FinancialFigure.objects.filter(field__slug='total-debt').count()

# Check field mappings
DataField.objects.filter(slug__in=['total-debt', 'interest-paid']).values('slug', 'name')
```

## Frontend Integration

### Template Structure
```
leaderboards.html
├── Page Header with Export Controls
├── Category Navigation (horizontal scroll)
├── Controls Bar (per capita toggle, year selector)
├── Main Content
│   ├── Contributors Grid (when category=contributors)
│   └── Financial Rankings Grid (when category≠contributors)
└── Empty State (when no data)
```

### JavaScript Features
- Loading states for category changes
- Per capita toggle with URL updates
- Year selector with form submission
- Smooth scrolling and transitions

### Mobile-First Design
- Horizontal scrolling category navigation
- Responsive grid layouts
- Touch-friendly controls
- Optimized typography scales

## Performance Considerations

### Current Optimizations
- Database query optimization with `select_related()`
- Caching at service layer (5 minutes)
- Pagination with configurable limits
- Conditional loading of optional features

### Future Optimizations
- Redis caching for high-traffic scenarios
- Background processing for complex calculations
- CDN integration for static assets
- Progressive loading for large datasets

## Security & Rate Limiting

### Current Implementation
- DRF throttling: 60 requests/hour for anonymous users
- Permission classes: AllowAny for public data
- Input validation and sanitization
- CSRF protection on form submissions

### Export Security
- File size limits on exports
- Rate limiting on export endpoints
- Secure temporary file handling

## Troubleshooting

### Common Issues

**"No data available" for financial categories:**
1. Check if FinancialFigure data exists for the category's field_slug
2. Verify current financial year is set (`is_current=True`)
3. Check DataField.slug matches category configuration

**Contributors showing 0 entries:**
1. Verify UserProfile.points > 0 for some users
2. Check user authentication and profile creation

**Export functionality not working:**
1. Verify optional dependencies (openpyxl, reportlab, PIL)
2. Check file permissions for temporary export files
3. Review export service logs for specific errors

### Debugging Commands

```bash
# Test leaderboard service
python manage.py shell -c "
from council_finance.services.leaderboard_service import LeaderboardService
service = LeaderboardService()
data = service.get_leaderboard('total-debt')
print(f'Entries: {len(data.entries) if data else 0}')
"

# Check data health
python manage.py shell -c "
from council_finance.models import FinancialFigure, FinancialYear
current_year = FinancialYear.objects.filter(is_current=True).first()
print(f'Current year: {current_year}')
print(f'Total figures: {FinancialFigure.objects.count()}')
"
```

## Testing Strategy

### Unit Tests
- Service layer method testing
- Ranking calculation validation
- Per capita computation accuracy
- Cache behavior verification

### Integration Tests
- API endpoint responses
- Template rendering with data
- Export functionality
- Error handling scenarios

### Performance Tests
- Load testing with large datasets
- Cache hit rate optimization
- Database query efficiency
- Memory usage monitoring

## Maintenance Notes

### Regular Tasks
- Monitor cache hit rates and adjust TTL if needed
- Review and update category definitions
- Performance monitoring of ranking calculations
- Data quality checks for financial figures

### Future Enhancements
- Consider WebSocket integration for real-time updates
- Explore GraphQL for more efficient data fetching
- Add machine learning for trend prediction
- Implement advanced filtering and search

---

## Change Log

**2025-08-02:** Initial documentation created
- Documented current implementation status
- Created comprehensive implementation plan
- Established technical architecture documentation
- Set up troubleshooting and maintenance guidelines

---

**Next Update:** After Phase 1 completion - document data fixes and validation results