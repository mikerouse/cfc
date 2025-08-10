# Council Edit UI/UX Redesign Documentation

**Created**: 2025-01-07  
**Status**: Proposed Design  
**Context**: Complete redesign of the council edit interface to follow GOV.UK design patterns and improve user experience

## Executive Summary

The current council edit interface uses a confusing tab-based system with tabs at the bottom of the form. This document outlines a comprehensive redesign following GOV.UK design patterns, implementing a wizard-based approach that clearly separates temporal and non-temporal data editing.

## Current Problems

1. **Bottom tabs are confusing**: Non-standard placement creates poor user experience
2. **Mixed data types**: Temporal and non-temporal data mixed together creates cognitive overload
3. **No clear workflow**: Users don't know where to start or what order to complete tasks
4. **Mobile-unfriendly**: Tab navigation doesn't work well on mobile devices
5. **Poor progress tracking**: Users can't see what's complete or what needs attention

## Design Principles

### GOV.UK Standards Applied

- **Start with user needs**: Clear entry points based on task type
- **Do the hard work to make it simple**: Wizard flow reduces cognitive load
- **Design with data**: Progress indicators and completion status throughout
- **Make things open**: Clear process with no hidden steps
- **Iterate**: Each step focuses on one clear decision

### Accessibility Requirements

- **WCAG 2.1 AA compliance** minimum
- **44px minimum touch targets** for all interactive elements
- **Clear heading hierarchy** (H1 → H2 → H3)
- **Descriptive button labels** ("Upload & Process" not just "Submit")
- **Inline error messaging** with clear instructions
- **Screen reader compatible** progress indicators
- **Keyboard navigation** through entire wizard flow

## Information Architecture

### Data Classification

**1. Characteristics (Non-temporal)**
- Council name, type, nation
- Website and contact information
- Chief Executive, Leader, Political control
- Current population (see Population Handling below)

**2. Financial Data (Temporal)**
- All monetary figures (income, expenditure, assets, liabilities)
- Financial statement links and uploads
- Statement dates and audit information
- Historical population (for per capita calculations)

**3. General Temporal Data**
- Year-specific non-financial information
- Political control changes
- Temporary website URLs
- Annual report links

## Population Field Handling

The population field presents a unique challenge as it serves dual purposes:

### 1. Current Population (Characteristic)
- **Location**: Council Details/Characteristics section
- **Purpose**: Display current population on council pages
- **Update frequency**: Annually or when new census data available
- **Storage**: `council.latest_population` field

### 2. Historical Population (Temporal)
- **Location**: Financial Data section (per year)
- **Purpose**: Calculate accurate per capita figures for that financial year
- **Update frequency**: Locked to financial year
- **Storage**: `FinancialFigure` with `field.slug = 'population'`

### Implementation Strategy

```python
# Model structure
class Council(models.Model):
    latest_population = models.IntegerField(
        help_text="Current population for display purposes"
    )

class FinancialFigure(models.Model):
    council = models.ForeignKey(Council)
    year = models.ForeignKey(FinancialYear)
    field = models.ForeignKey(DataField)  # where field.slug = 'population'
    value = models.CharField()  # Historical population for that year
```

### UI Implementation

**In Characteristics Section:**
```
Current Population: [1,144,900]
ℹ️ This is the latest population figure for display on the council page
```

**In Financial Data Section:**
```
Population (2024/25): [1,141,374]
ℹ️ Used to calculate per capita figures for this financial year
💡 Different from current population (1,144,900) due to annual changes
```

## User Flow Diagrams

### Main Flow
```
Landing Page
    ├── Council Details → Single Form → Save
    └── Financial Data → Year Selection → Method Choice
                              ├── PDF Upload → Processing → Review → Save
                              └── Manual Entry → Form Fields → Save
```

## Page Specifications

### 1. Landing Page (`/councils/{slug}/edit/`)

**Purpose**: Clear choice between editing types

**Layout**:
```
┌─────────────────────────────────────────────────────────────┐
│ [< Back to Council]     Birmingham City Council              │
│                                                              │
│ Choose what you'd like to edit:                              │
│                                                              │
│ ┌─────────────────────┐  ┌─────────────────────────────────┐│
│ │  📋 Council Details │  │  💰 Financial Data              ││
│ │                     │  │                                 ││
│ │  Basic information  │  │  Upload statements or edit      ││
│ │  that doesn't       │  │  financial figures for a        ││
│ │  change by year     │  │  specific year                  ││
│ │                     │  │                                 ││
│ │  • Population       │  │  • Balance sheet items         ││
│ │  • Council type     │  │  • Income & expenditure        ││
│ │  • Website & links  │  │  • PDF upload & AI extraction  ││
│ │                     │  │                                 ││
│ │  [Edit Details →]   │  │  [Edit Financial Data →]       ││
│ └─────────────────────┘  └─────────────────────────────────┘│
│                                                              │
│ Recent activity:                                             │
│ • Financial data for 2024/25 - 80% complete                │
│ • Last updated 2 weeks ago by Mike Rouse                   │
└─────────────────────────────────────────────────────────────┘
```

### 2. Council Details Section (`/councils/{slug}/edit/characteristics/`)

**Purpose**: Edit non-temporal council information

**Fields**:
- Council name (read-only)
- Council type (dropdown)
- Nation (dropdown)
- Current population (number input with formatting)
- Website URL (validated URL field)
- Chief Executive (text)
- Leader (text)
- Political control (dropdown)

**Validation**:
- URL validation for website
- Population must be positive integer
- Required fields marked with asterisk

### 3. Financial Data Wizard

#### Step 1: Year Selection (`/councils/{slug}/edit/financial/`)

**Purpose**: Choose which financial year to edit

**Features**:
- List of available years with completion status
- Visual indicators (✅ Complete, 📊 In Progress, ⚠️ Needs Review)
- Option to add new year (if permissions allow)
- Clear progression path

#### Step 2: Method Selection (`/councils/{slug}/edit/financial/{year}/`)

**Purpose**: Choose between PDF upload or manual entry

**Layout**:
- Two clear cards with benefits/drawbacks
- Recommended option highlighted (PDF upload)
- Clear CTAs for each option

#### Step 3a: PDF Upload (`/councils/{slug}/edit/financial/{year}/upload/`)

**Purpose**: Upload and process financial statement PDF

**Features**:
- Drag-and-drop upload zone
- File validation (PDF only, 50MB max)
- Real-time processing status
- Progress bar with stages:
  1. Uploading (0-20%)
  2. Extracting text (20-40%)
  3. AI analysis (40-80%)
  4. Preparing results (80-100%)

**Error Handling**:
- Clear error messages for invalid files
- Retry option for failed processing
- Fallback to manual entry if needed

#### Step 3b: Review Extracted Data (`/councils/{slug}/edit/financial/{year}/review/`)

**Purpose**: Review and confirm AI-extracted data

**Features**:
- Grouped display of extracted fields
- Confidence indicators per field
- Edit capability for each value
- Bulk accept/reject options
- Clear identification of missing fields

**Layout**:
```
High Confidence Fields (✅)
├── Total Income: £4,357.2m [Edit]
├── Total Expenditure: £4,202.7m [Edit]
└── Current Liabilities: £1,187.5m [Edit]

Medium Confidence Fields (⚠️)
├── Interest Payments: £178.3m [Edit]
└── Capital Expenditure: £247.2m [Edit]

Missing Fields (❌)
├── Total Debt: [Add Value]
└── Pension Liability: [Add Value]

[Reject All] [Save All Data]
```

#### Step 3c: Manual Entry (`/councils/{slug}/edit/financial/{year}/manual/`)

**Purpose**: Manually enter financial data

**Features**:
- Grouped fields by category
- Progress indicator
- Save draft functionality
- Inline help text
- Population field with temporal context
- Format guidance (e.g., "Enter in millions")

**Field Groups**:
1. Basic Information
   - Link to statement (URL or PDF upload)
   - Statement date
   - Population for this year
   
2. Income & Expenditure
   - Total income
   - Total expenditure
   - Interest payments
   - Capital expenditure
   
3. Balance Sheet
   - Current assets
   - Current liabilities
   - Long-term liabilities
   - Total reserves
   
4. Additional Metrics
   - Total debt
   - Pension liability
   - Other fields as needed

## React Component Architecture

```
CouncilEditApp.jsx
├── CouncilEditLanding.jsx
│   ├── EditChoiceCard.jsx
│   └── RecentActivity.jsx
├── CharacteristicsEditor.jsx
│   ├── CharacteristicsForm.jsx
│   └── PopulationField.jsx (with help text)
└── FinancialDataWizard.jsx
    ├── WizardProgress.jsx
    ├── YearSelectionStep.jsx
    ├── MethodSelectionStep.jsx
    ├── PdfUploadStep.jsx
    │   ├── FileDropzone.jsx
    │   ├── ProcessingStatus.jsx
    │   └── UploadProgress.jsx
    ├── DataReviewStep.jsx
    │   ├── ExtractedDataTable.jsx
    │   ├── ConfidenceIndicator.jsx
    │   └── FieldEditor.jsx
    └── ManualEntryStep.jsx
        ├── FieldGroup.jsx
        ├── PopulationField.jsx (with year context)
        └── SaveDraftButton.jsx
```

## API Endpoints

### Existing Endpoints (Keep)
- `GET /api/council/{slug}/characteristics/`
- `POST /api/council/{slug}/characteristics/save/`
- `GET /api/council/{slug}/temporal/{year_id}/`
- `POST /api/council/{slug}/temporal/{year_id}/save/`

### New Endpoints (Add)
- `POST /api/council/{slug}/upload-pdf/` - Handle PDF upload
- `GET /api/council/{slug}/pdf-status/{processing_id}/` - Check processing status
- `POST /api/council/{slug}/financial/{year}/apply-extracted/` - Apply AI-extracted data
- `GET /api/council/{slug}/financial/{year}/progress/` - Get completion progress

## State Management

### Local State (React useState)
- Current wizard step
- Selected year
- Upload progress
- Form validation errors
- Extracted data preview

### Server State
- Council data (via API)
- Processing status (polling)
- Saved draft data
- User permissions

## Mobile Considerations

### Responsive Breakpoints
- Mobile: < 640px (single column)
- Tablet: 640px - 1024px (flexible grid)
- Desktop: > 1024px (full layout)

### Mobile-Specific Features
- Bottom sheet for file upload
- Simplified navigation
- Touch-friendly inputs
- Swipe between wizard steps
- Condensed data review

## Performance Optimizations

### Code Splitting
- Lazy load wizard steps
- Separate PDF processing components
- Dynamic import for file upload

### Caching Strategy
- Cache council characteristics (5 minutes)
- Cache year list (10 minutes)
- Don't cache financial data
- Clear cache on saves

## Security Considerations

### File Upload Security
- Validate file type (PDF magic number)
- Maximum file size (50MB)
- Scan for malware (if available)
- Sanitize filenames
- Secure storage location

### Data Validation
- Server-side validation for all inputs
- CSRF protection on all POST requests
- Rate limiting on file uploads
- Permission checks per council

## Implementation Priority

### Phase 1: Core Redesign (Next)
1. **Landing page redesign** - Replace tabs with choice cards
2. **Characteristics section** - Simple form for non-temporal data
3. **Year selection wizard** - GOV.UK style step-by-step process
4. **Manual entry improvements** - Better field grouping and progress tracking

### Phase 2: PDF Integration (After Phase 1)
1. PDF upload interface in financial wizard
2. Processing status display with real-time updates
3. Data review interface for AI-extracted values
4. Apply extracted data to financial fields

### Phase 3: Advanced Features (Future)
1. Progress tracking across all sections
2. Draft saves and auto-save functionality
3. Bulk operations for multiple years
4. Advanced validation and data quality checks

## Population Integration Status

### ✅ Backend Complete (2025-01-07)
- Year-specific population storage implemented
- Per capita calculations use correct population by year
- Management command created for data migration
- All historical population data populated

### 🔄 Frontend Integration Needed
The new UI will include population fields in both sections:

**Characteristics Section:**
```
Current Population: [1,144,900] 
ℹ️ This is the current population for display on council pages
```

**Financial Data Section (per year):**
```
Population (2024/25): [1,141,374]
ℹ️ Used for per capita calculations in this financial year
💡 Different from current population due to historical changes
```

## Testing Requirements

### Unit Tests
- Component rendering
- Form validation
- API error handling
- File upload validation

### Integration Tests
- Full wizard flow
- PDF processing pipeline
- Data saving
- Permission checks

### E2E Tests
- Complete user journey
- Mobile responsiveness
- Error scenarios
- Performance under load

## Accessibility Testing
- Screen reader navigation
- Keyboard-only usage
- Color contrast validation
- Focus management

## Success Metrics

### User Experience
- Time to complete edit: < 5 minutes
- Error rate: < 5%
- Mobile completion rate: > 80%
- User satisfaction: > 4/5

### Technical
- Page load time: < 2 seconds
- PDF processing: < 2 minutes
- API response time: < 500ms
- Upload success rate: > 95%

## Migration Strategy

### Phase 1: Parallel Running
- Keep old system accessible
- Add feature flag for new UI
- Gather user feedback

### Phase 2: Gradual Rollout
- Enable for power users
- Monitor error rates
- Fix issues

### Phase 3: Full Migration
- Switch all users
- Deprecate old UI
- Remove old code

## Future Enhancements

### Potential Features
- Bulk PDF upload for multiple years
- Comparison with previous years
- Auto-save functionality
- Collaborative editing
- Change history/audit trail
- Email notifications for processing

### Integration Opportunities
- Link to data quality checks
- Automatic factoid generation
- Trigger counter recalculation
- Update leaderboards

## Conclusion

This redesign transforms the council edit experience from a confusing tab-based system to a clear, wizard-based flow that follows GOV.UK design patterns. By separating temporal and non-temporal data, providing multiple entry methods, and handling the special case of population data, we create a more intuitive and efficient system for users while maintaining data integrity and accuracy throughout the platform.