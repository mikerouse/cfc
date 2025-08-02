applyTo: '**'

# PROJECT DOCUMENTATION INDEX

**IMPORTANT**: This project has multiple documentation files. Always check these additional files for context:

- **FACTOIDS.md** - Complete AI-powered factoids system architecture and implementation
- **DESIGN_PRINCIPLES.md** - Mobile-first design patterns, grid system, and UI/UX guidelines
- **PAGE_SPECIFICATIONS.md** - Detailed page rules, user flows, and business logic for key pages
- **AGENTS.md** - Counter agent system and calculation logic
- **LEADERBOARDS.md** - Complete leaderboards system implementation, API, and enhancement roadmap
- **README.md** - Project setup and deployment instructions

When working on factoids, design/UI, specific pages (Contribute/Lists/Following), counters, leaderboards, or system architecture, **ALWAYS** reference the relevant documentation files above for complete context.

---

# COMPREHENSIVE TESTING INTEGRATION (2025-07-30)

## Enhanced Reload Command with Testing

The reload command has been enhanced to include comprehensive testing capabilities:

### New Command Options
```bash
# Default behavior - runs tests AND starts server
python manage.py reload

# Skip tests (faster startup)
python manage.py reload --no-tests

# Run only tests, don't start server  
python manage.py reload --test-only

# Run both validation and tests (maximum checks)
python manage.py reload --validate

# Legacy validation only
python manage.py reload --validate --no-tests
```

### Testing Integration Details

**run_all_tests.py Integration**: The reload command now calls the comprehensive test suite that includes:
1. **Python Import Tests** - Validates all critical model and view imports
2. **Django Template Tests** - Checks template syntax and loading
3. **React Build Tests** - Verifies React build files and manifest
4. **API Endpoint Tests** - Confirms URL routing works
5. **Database Integrity Tests** - Checks migrations and model queries
6. **Static Files Tests** - Validates static file configuration
7. **Management Commands Tests** - Ensures Django commands work
8. **JavaScript Template Tests** - Validates JS syntax in templates
9. **Programming Error Detection** - Tests critical pages and model methods for runtime errors

**Test Results**: 
- **SUCCESS**: Condensed summary shown in console, server starts normally
- **FAILURES**: Detailed errors written to `syntax_errors.log` (OVERWRITTEN each time)
- Test failures noted but server still starts (unless `--test-only`)
- 5-minute timeout prevents hanging on problematic tests

**Usage Patterns**:
- **Default** (`python manage.py reload`): Always runs tests + starts server
- `--no-tests`: Skip tests for faster startup during development
- `--test-only`: Perfect for CI/CD or quick validation after changes
- `--validate`: Maximum validation (syntax + comprehensive tests) before server start

### Legacy Testing Tools

The following standalone tools are still available but are now consolidated into `run_all_tests.py`:
- `test_imports.py` - Now integrated as "Python Import Tests"
- `test_templates.py` - Now integrated as "Django Template Tests" 
- Individual validation commands - Now part of comprehensive suite

### Best Practices

**After Making Changes**:
```bash
# Normal development (tests run automatically)
python manage.py reload

# Quick validation without server
python manage.py reload --test-only

# Maximum validation with server start
python manage.py reload --validate

# Fast startup (skip tests temporarily)
python manage.py reload --no-tests
```

**Error Resolution**:
1. Check console output for immediate feedback
2. **Review `syntax_errors.log`** for detailed error information (OVERWRITTEN each reload)
3. Fix issues and re-run `python manage.py reload --test-only` to verify fixes
4. Use `--no-tests` for rapid iteration during complex debugging

This integration ensures that all changes are validated before the server starts, preventing deployment of broken code and catching issues early in the development cycle.

### Programming Error Detection Details

The new **Programming Error Detection** test (#9) specifically catches runtime errors like:

- **Database ProgrammingErrors**: Detects SQL errors like "function sum(text) does not exist"
- **Template Rendering Errors**: Catches errors when templates access broken model methods
- **AttributeErrors**: Identifies missing methods or properties 
- **Authentication Issues**: Tests both anonymous and authenticated user workflows

**Recent Fix Example**: Fixed `CouncilList.get_total_population()` which was attempting to `SUM()` a text field, causing PostgreSQL errors. The method now properly handles text-to-integer conversion with error handling for malformed data.

**Detection Method**: The test suite makes actual HTTP requests to critical pages (/lists/, /contribute/, etc.) and calls specific model methods known to cause issues, catching errors before users encounter them.

# Design Principles

**CRITICAL**: All UI/UX design follows mobile-first principles. See **DESIGN_PRINCIPLES.md** for complete guidelines.

**Key Rules**:
- 44px minimum touch targets
- Mobile-first responsive design (xs → sm → md → lg → xl)
- All significant DIVs must have meaningful IDs (`[page]-[section]-[element]`)
- Grid system: `max-w-none xl:max-w-desktop` with consistent spacing

# CRITICAL: Avoiding Context Loss and Over-Engineering

## The Problem
AI agents lose context over long conversations and tend to re-engineer existing systems, creating overly complex, cross-cutting code that becomes wrapped up in itself. This leads to:

1. **Competing Systems**: Multiple ways to do the same thing (e.g., different API endpoints, multiple data access patterns)
2. **Field Name Mismatches**: Converting between slug formats (`interest-payments-per-capita`) and variable names (`interest_payments_per_capita`) 
3. **Cached State Issues**: New systems bypass existing caches/instances, creating inconsistent data
4. **Incomplete Integration**: New APIs don't integrate with existing frontend code

## Critical Context Loss Prevention Rules

### 1. UNDERSTAND BEFORE CHANGING
- **ALWAYS** check existing patterns before creating new ones
- Run `grep_search` to find how similar problems are already solved
- Test existing systems before assuming they're broken
- Check for existing API endpoints before creating new ones

### 2. DATA FIELD NAMING CONVENTIONS
The system has TWO field naming formats that must be handled correctly:

- **Slug format**: `interest-payments-per-capita` (used in URLs, templates, database slugs)
- **Variable format**: `interest_payments_per_capita` (used in code, context data)

**CRITICAL**: Template rendering must convert between formats:
```python
# WRONG - looking for slug format in context
value = context_data.get('interest-payments-per-capita')  # Will be None

# CORRECT - convert to variable format  
field_variable_name = field_name.replace('-', '_')
value = context_data.get(field_variable_name)  # Will find the value
```

### 3. FACTOID SYSTEM DEBUGGING
When factoids show "N/A":

1. **Check field categories**: Ensure FactoidEngine handles the field's category (`spending`, `financial`, etc.)
2. **Test field lookup directly**: Use `engine.get_field_value(field_name, council, year)` 
3. **Check for stale instances**: Look for cached FactoidInstance objects that might be outdated
4. **Verify counter-specific vs generic instances**: Counter-specific instances override generic ones

When factoids appear on wrong counters:
1. **Check counter assignments**: Use `FactoidTemplate.objects.filter(counters=counter)` 
2. **Verify no generic logic**: Ensure `FactoidEngine.get_factoids_for_counter()` only returns assigned factoids
3. **Test counter isolation**: Each counter should only show its assigned factoids

Common issues:
- Field category not supported in FactoidEngine
- Template uses slug format but context has variable format
- Stale cached instances with outdated data
- Missing field mappings for calculated fields
- Generic factoid logic causing factoids to appear on all counters

### 4. API INTEGRATION RULES
- **Check existing API endpoints** before creating new ones
- **Test frontend expectations** - what URL pattern does JavaScript expect?
- **Avoid URL pattern conflicts** - `/api/factoids/<template>` vs `/api/factoids/<counter>` will conflict
- **Use consistent response formats** - match what frontend expects

### 5. DEBUGGING STRATEGY
When things don't work:

1. **Test the lowest level first**: Direct field access, then computation, then API
2. **Check for multiple instances**: Look for competing cached data
3. **Verify integration points**: Template → Engine → API → Frontend  
4. **Clear caches when needed**: Delete stale instances to force recomputation
5. **Check data format mismatches**: Refer to "SYSTEM DATA FORMATS & INTEGRATION POINTS" section for known format differences

### 6. SYSTEM INTEGRITY
- Use the integrity checker script to validate the entire pipeline
- Monitor for competing systems doing the same job
- Ensure frontend JavaScript matches backend API patterns
- Test end-to-end user flows, not just individual components

## Example Fix Pattern
```bash
# 1. Understand the problem
python manage.py shell -c "engine.get_field_value('field_name', council, year)"

# 2. Check for stale data  
python manage.py shell -c "FactoidInstance.objects.filter(...).delete()"

# 3. Test integration
python test_frontend_api.py

# 4. Verify end-to-end
# Check actual webpage, not just API
```

Remember: **Simple fixes are usually better than complex re-engineering.**

### 7. PERFORMANCE OPTIMIZATION LESSONS

**CRITICAL**: The council detail page was significantly slowed by duplicate database queries and N+1 query patterns.

#### Common Performance Anti-Patterns to Avoid:

1. **Duplicate Systems Running in Parallel**
   ```python
   # BAD - Old and new meta fields systems both running
   meta_fields = ["population", "elected_members"]  # Hardcoded system
   for slug in meta_fields:
       field = DataField.objects.filter(slug=slug).first()  # Individual queries
   
   # Plus new dynamic system also running:
   meta_data_fields = DataField.objects.filter(show_in_meta=True)  # More queries
   ```

2. **N+1 Query Patterns**
   ```python
   # BAD - Queries inside loops
   for field in meta_data_fields:
       characteristic = CouncilCharacteristic.objects.get(council=council, field=field)
   
   # GOOD - Bulk query with lookup map
   characteristics_qs = CouncilCharacteristic.objects.filter(
       council=council, field__show_in_meta=True
   ).select_related('field')
   characteristics_map = {char.field.id: char for char in characteristics_qs}
   ```

3. **Expensive Operations on Every Request**
   ```python
   # BAD - CounterAgent runs complex calculations every time
   agent = CounterAgent()
   values = agent.run(council_slug=slug, year_label=year)  # Slow database operations
   
   # BETTER - Would be to cache results for 5-10 minutes
   ```

#### Performance Fix Results:
- **Before optimization**: ~6-8 seconds average load time
- **After Phase 1 fixes**: ~3 seconds average (50% improvement)
  - First request: 5.9s (cold)
  - Subsequent requests: 1.4-1.5s (cache warming)
- **Remaining bottleneck**: CounterAgent calculations (Phase 2 opportunity)

#### Key Optimizations Made:
1. **Removed duplicate meta fields logic** - eliminated redundant database queries
2. **Fixed N+1 queries** - replaced individual `objects.get()` calls with bulk query + lookup map  
3. **Added proper select_related()** - reduced database round trips
4. **Maintained backwards compatibility** - kept population fallback to `council.latest_population`

#### Phase 2 Optimizations (IMPLEMENTED):

**Counter Result Caching System:**
```python
# Cache counter calculations for 10 minutes to improve performance
cache_key_current = f"counter_values:{slug}:{selected_year.label}"
values = cache.get(cache_key_current)

if values is None:
    values = agent.run(council_slug=slug, year_label=selected_year.label)
    cache.set(cache_key_current, values, 600)  # 10 minutes
```

**CounterAgent Field Caching:**
```python
# Use instance-level cache to avoid repeated DataField queries
if not hasattr(self, '_field_cache'):
    self._field_cache = {}

if field_slug not in self._field_cache:
    self._field_cache[field_slug] = DataField.objects.get(slug=field_slug)
```

**Strategic Database Indexes:**
- `idx_datafield_meta_display`: Optimizes meta fields lookup
- `idx_counter_council_types`: Faster counter definition filtering  
- `idx_datafield_slug_content_type`: Accelerates CounterAgent field lookups

#### Phase 2 Performance Results:
- **Cold request**: ~5 seconds (first visit)
- **Cached requests**: ~0.65 seconds (**86.6% faster**)
- **Year switching**: Near-instant when cached
- **Overall average**: 1.5 seconds (50% improvement from Phase 1)

#### Combined Phase 1 + 2 Results:
- **Before optimization**: 6-8 seconds
- **After both phases**: 0.65s cached, 1.5s average (**75-90% improvement**)

#### Remaining Opportunities (Phase 3):
- Background processing for heavy calculations
- Additional query optimization in calculators.py
- Frontend lazy loading for non-critical sections

# SYSTEM DATA FORMATS & INTEGRATION POINTS

**CRITICAL**: Document data formats and API contracts to prevent integration mismatches. Add new formats to this section as the system evolves.

## Factoid System Data Formats

### Counter Assignment Logic
**CRITICAL**: Factoids only appear on counters they are specifically assigned to via the `FactoidTemplate.counters` ManyToMany relationship.

```python
# CORRECT: Only counter-specific factoids
templates = FactoidTemplate.objects.filter(
    is_active=True,
    counters=counter  # Only templates assigned to this specific counter
)

# WRONG: Shows factoids on all counters
templates = FactoidTemplate.objects.filter(
    Q(target_content_type=None) |  # Generic templates (shows everywhere)
    Q(counters=counter)  # Counter-specific (correct)
)
```

### Counter-Factoid Assignments
- **Interest Payments Counter**: Shows interest per capita and compares cost of interest payments to costs of running services 
- **Total Debt Counter**: Shows current liabilities, long-term liabilities, finance leases as the core components that make up the headline debt for a council. Factoids should therefore be related to these component parts or comparing debt levels to other councils, or showing per capita breakdowns.
- **Current Liabilities Counter**: Shows current liabilities specific data or short-term position information and insights
- **Long-term Liabilities Counter**: Shows data relating to the long-term position of the council

**Rule**: If a counter has no factoid assignments, it shows no factoids. No "generic" factoids exist. The space should remain blank and unfilled. 

### API Response Format (from backend)
```json
{
  "success": true,
  "count": 8,
  "factoids": [
    {
      "id": 87,
      "template_name": "Interest payments per capita",
      "template_slug": "interest-payments-per-capita", 
      "rendered_text": "Equivalent to 150.19 per head.",  // ← Backend uses "rendered_text"
      "relevance_score": 0.65,
      "is_significant": true,
      "computed_at": "2025-07-28T20:58:11.501402+00:00",
      "expires_at": "2025-07-29T20:58:11.238419+00:00"
    }
  ]
}
```

### JavaScript Expected Format (factoid-playlist.js)
```javascript
{
  text: "Equivalent to 150.19 per head.",     // ← Frontend expects "text"
  emoji: "📊",                               // ← Default if not provided
  color: "blue",                             // ← Default if not provided  
  id: 87,
  template_name: "Interest payments per capita",
  relevance_score: 0.65
}
```

### Data Transformation Required
The `factoid-playlist.js` must transform API response:
```javascript
this.factoids = (data.factoids || []).map(factoid => ({
    text: factoid.rendered_text,  // ← KEY: Convert rendered_text → text
    emoji: factoid.emoji || '📊',
    color: factoid.color || 'blue',
    // ... other fields
}));
```

## HTML Data Attributes (Frontend → Backend)

### Counter Factoid Elements
```html
<div class="counter-factoid" 
     data-counter="interest-payments"     // ← Slug format with dashes
     data-council="worcestershire"        // ← Council slug  
     data-year="2024/25">                 // ← Year with forward slash
```

### JavaScript URL Construction  
```javascript
// Frontend converts year format for URLs
const urlSafeYear = year.replace(/\//g, '-');  // 2024/25 → 2024-25
const url = `/api/factoids/counter/${counterSlug}/${councilSlug}/${urlSafeYear}/`;
```

## Field Naming Conventions

### URL/Template Format (Slugs)
- `interest-payments-per-capita` 
- `total-debt`
- `current-liabilities`

### Code/Context Format (Variables)
- `interest_payments_per_capita`
- `total_debt` 
- `current_liabilities`

### Conversion Required
```python
# Template rendering - ALWAYS convert slug to variable format
field_variable_name = field_name.replace('-', '_')
value = context_data.get(field_variable_name)  # Will find the value
```

## Common Integration Gotchas

1. **Factoid "No data available"**: Check if frontend expects `text` but API returns `rendered_text`
2. **Factoid shows "N/A"**: Check for stale `FactoidInstance` cache objects
3. **Factoids appear on wrong counters**: Factoids only show on assigned counters - check `FactoidTemplate.counters` assignments
4. **API 404 errors**: Verify slug formats match between frontend/backend 
5. **Year format mismatches**: Frontend uses `2024-25`, backend expects `2024/25`
6. **Field not found**: Check if using slug format (`interest-payments`) vs variable format (`interest_payments`)
7. **All factoids showing everywhere**: Ensure no "generic" factoid logic - only counter-specific assignments

## Adding New Data Formats

**INSTRUCTION**: When creating new API endpoints or data structures, document the format here immediately. Include:

1. **API Response Schema**: Exact JSON structure with field names
2. **Frontend Expected Format**: What JavaScript/HTML expects
3. **Transformation Code**: How to convert between formats
4. **Common Pitfalls**: Known issues to watch for

Example template:
```markdown
### [New System Name] Data Format
API Response: { "field_name": "value" }
Frontend Expects: { "different_field": "value" }  
Transformation: frontend.field = api.field_name
Common Issues: [List potential problems]
```

# CRITICAL: Testing After Changes

**ALWAYS run testing tools after making changes to prevent deployment issues:**

1. **Template Testing**: Run `python diagnose_template_error.py` after template changes
2. **Import Testing**: Test imports after model changes with `python manage.py shell`
3. **React Build**: After JS changes, run `npm run build` and update template with new hash
4. **API Testing**: Test new endpoints with curl or browser before marking complete

**Common Issues to Check:**
- Import errors after moving/renaming models
- Template syntax errors (missing load tags, wrong filter names)
- JavaScript build failures or wrong file hashes
- CSRF token issues with new API endpoints
- Data format mismatches between frontend/backend

# Page-Specific Rules

**CRITICAL**: Each major page has detailed specifications and business rules. See **PAGE_SPECIFICATIONS.md** for complete details.

**Key Pages**:
- **Contribute**: Wikipedia-style data contribution system with light-touch moderation
- **Lists**: Custom council grouping (like wish lists) with data aggregation
- **Following**: Social media-style following of councils, lists, figures, and contributors
- **Backend Management**: Custom control panel only (no Django admin for users)

## Factoids

**CRITICAL**: Factoids are now AI-powered, NOT template-based. See **FACTOIDS.md** for complete implementation details.

**Summary**: Single AI-generated news ticker per council detail page (below header). AI analyzes complete financial dataset to generate intelligent insights like "Interest payments peaked in 2023 at £3.8M, up 58% from 2019".

**Key Changes**: 
- One playlist per council (not per counter)
- AI-generated via OpenAI API 
- No user templates or builders
- All counter associations DEPRECATED

# Creator's rules that AI should follow

- We care about comments. There should be useful and descriptive comments.
- We care about helpers in the UI for the benefit of users.
- We care about realtime and live data using websockets or polling.
- We care about taking a holistic app-wide view - this means if we adjust functionality that affects one place we look around the app to see where else might be affected and act accordingly.
- We prioritise the user experience and ease-of-use. That means we do not use things like alert() we use modals instead.
- We care about accessibility, but not when it compromises design. We should do both.
- We log, log, log.
- We like loading indicators and progress indicators.
- We like verbose status and debugging information.
- We delete legacy work and replace it with better.
- We use Tailwind CSS for styling. We do not need to use Bootstrap or any other CSS framework, even if it was used in the past.
- **We do not break other parts of the system** when fixing things, and we **do not** stub things out.
- **Run the check_templates.py script** to ensure all templates are valid and do not contain any errors.
- **Use UK English throughout the system** - this means "analyse" not "analyze", "colour" not "color", "favourite" not "favorite", etc. All text, comments, variable names, and user-facing content should follow UK English conventions.

# User System

**CRITICAL**: 5-tier user system with role-based permissions. See **PAGE_SPECIFICATIONS.md** for complete user level specifications.

**Tiers**: Public (1) → Contributors (2) → Council Staff (3) → Experts (4) → God Mode (5)
**Features**: API key generation, custom control panel, no Django admin access for users

# System Rules

## IMPORTANT: Console Commands

- You don't need to do `cd` before every python command - you are already in the project directory.
- Avoid using `&&` in terminal commands. Use PowerShell friendly commands.

## 🛠 Configuration

- Use `.env` files for API keys and database URLs.
- `config/settings.py` is loaded dynamically and supports overrides via environment.
- Store config overrides or user-specified parameters via a `settings` model or flatfile.

## 🔑 Authentication for Testing and Debugging

The `.env` file contains `ADMIN_USER` and `ADMIN_PASSWORD` environment variables that should be used for authenticated testing and debugging. This eliminates the need to create additional test users.

**Usage in Testing:**
```python
# Example: Authenticating in tests
from django.contrib.auth import authenticate, login
import os

admin_user = os.getenv('ADMIN_USER')
admin_password = os.getenv('ADMIN_PASSWORD')

# Use these credentials for:
- API endpoint testing that requires authentication
- Accessing protected pages during debugging
- Running comprehensive tests that need authenticated access
- Simulating admin actions in test scenarios
```

**Benefits:**
- Consistent authentication across all test environments
- No need to create or manage test user accounts
- Secure credential storage via environment variables
- Easy to update credentials without code changes

---

## 🔄 Scheduling

Use cron or Django-Q/Celery for periodic agents (e.g. daily imports):

```cron
0 3 * * * /path/to/venv/bin/python manage.py runagent ImporterAgent
```