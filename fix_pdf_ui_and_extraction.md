# Council PDF Upload Page Fix - Todo List

## UI Layout Issues
- [ ] Examine current AIExtractionReview.jsx component implementation
- [ ] Check site's standard grid system and CSS patterns
- [ ] Update container classes from `max-w-6xl` to site standard `max-w-none xl:max-w-desktop`
- [ ] Implement confidence-based grouping (High/Medium/Missing) instead of category grouping
- [ ] Ensure 44px minimum touch targets for mobile
- [ ] Apply consistent spacing patterns per design principles
- [ ] Test responsive behavior across breakpoints
- [ ] Verify GOV.UK design pattern compliance

## Data Extraction Issues
- [ ] Examine PDF processing pipeline in council_edit_api.py
- [ ] Test hybrid extraction system (regex + AI validation)
- [ ] Check TikaFinancialExtractor configuration
- [ ] Investigate why only 3 figures detected vs expected higher count
- [ ] Review confidence scoring thresholds
- [ ] Test with sample PDF to understand extraction gaps
- [ ] Check for temporal vs non-temporal data handling
- [ ] Verify field mapping completeness

## Testing & Validation
- [ ] Test UI changes with actual council PDF upload
- [ ] Verify grid layout matches site standard
- [ ] Confirm improved data extraction accuracy
- [ ] Test mobile responsiveness
- [ ] Validate accessibility compliance
