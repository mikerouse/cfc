# DESIGN PRINCIPLES
*Council Finance Counters Platform*
*Generated: 2025-07-31*

## Mobile-First Design Philosophy
The Council Finance Counters platform prioritises mobile users, recognising that many citizens access council information on their phones. We design for mobile first, then enhance for larger screens and tablets.

## Core Design Principles

### 1. Touch-First Interaction
- **Minimum touch target size**: 44px (iOS) / 48dp (Android) 
- **Generous spacing**: Minimum 8px between interactive elements
- **Thumb-friendly zones**: Critical actions placed within easy thumb reach
- **Swipe gestures**: Support horizontal swipes for navigation where appropriate

### 2. Progressive Disclosure
- **Essential information first**: Show most important council data immediately
- **Expandable sections**: Use collapsible cards for detailed information
- **Layered navigation**: Deep content accessible through clear hierarchical paths
- **Context-aware hiding**: Hide less critical information on smaller screens

### 3. Mobile Layout Patterns
- **Single column layout**: Default to stacked layout on mobile
- **Responsive grid**: `sm:grid-cols-2 lg:grid-cols-4` progression
- **Flexible containers**: Use percentage-based widths with max-width constraints
- **Safe areas**: Respect device safe areas and notches

### 4. Typography and Readability
- **Minimum font size**: 16px for body text (prevents iOS zoom)
- **Sufficient contrast**: WCAG AA compliance (4.5:1 minimum)
- **Line height**: 1.5-1.6 for optimal mobile reading
- **Truncation**: Smart truncation with expand options for long text

### 5. Navigation Patterns
- **Bottom navigation**: Primary navigation at bottom for thumb access
- **Horizontal scrolling tabs**: For secondary navigation with indicators
- **Breadcrumbs**: Clear path indicators for deep navigation
- **Back button**: Always provide clear way to return to previous screen

### 6. Performance on Mobile
- **Fast loading**: Optimise for slower mobile connections
- **Progressive loading**: Load critical content first, enhance progressively
- **Offline graceful degradation**: Show cached content when connection fails
- **Image optimisation**: Use responsive images with appropriate formats

### 7. Grid System Implementation

The platform uses a consistent CSS Grid system to ensure uniform alignment across components:

#### Desktop Layout (1280px fixed width)
- **Main container**: `max-w-none xl:max-w-desktop` (1280px)
- **Grid structure**: `grid grid-cols-1 xl:grid-cols-4 gap-6 xl:gap-8`
- **Content distribution**: Main content (3 cols) + Sidebar (1 col)

#### Alignment Rules
- **Consistent margins**: All cards and panels align to the same grid lines
- **Uniform spacing**: `gap-6 xl:gap-8` for consistent visual rhythm
- **Breathing room**: Minimum `mt-6` spacing for interactive elements

### 8. Detail Pages

#### Council Detail Pages
- **Hero section**: Logo, name, and key stats in compact mobile header
- **Tabbed content**: Financial data, edit, and logs in swipeable tabs
- **Counter cards**: Financial counters in mobile-optimised card layout
- **Quick actions**: Follow, compare, and share as prominent mobile buttons

#### Data Tables
- **Horizontal scroll**: Allow tables to scroll horizontally on mobile
- **Column priority**: Hide less important columns on small screens
- **Row expansion**: Allow tap-to-expand for detailed row information
- **Sort and filter**: Mobile-friendly sort/filter controls

#### Forms and Input
- **Single column forms**: Stack form fields vertically on mobile
- **Contextual keyboards**: Use appropriate input types (numeric, email, etc.)
- **Validation feedback**: Clear, immediate validation messages
- **Autocomplete**: Support for browser and app autocomplete

### 9. Accessibility on Mobile
- **Screen reader support**: Proper ARIA labels and semantic HTML
- **Voice control**: Ensure voice navigation works correctly
- **Motor accessibility**: Support for switch control and assistive devices
- **Cognitive accessibility**: Clear, simple interface with consistent patterns

### 10. HTML Element ID Conventions

**STANDING ORDER**: All significant DIV elements and containers must have meaningful IDs that clearly describe their purpose or content.

#### ID Naming Convention
Use kebab-case with a clear hierarchy that describes the element's function:

```html
<!-- Page/Section Pattern: [page]-[section]-[element] -->
<div id="my-lists-main-container">           <!-- Main page container -->
<div id="my-lists-page-header">              <!-- Page header section -->
<div id="my-lists-quick-stats">              <!-- Statistics display -->
<div id="my-lists-favourites-section">       <!-- Favourites content area -->
<div id="my-lists-search-results">           <!-- Search results dropdown -->
```

#### Required ID Categories

1. **Container Elements**
   - `[page]-main-container` - Primary page wrapper
   - `[page]-[section]-container` - Section wrappers

2. **Functional Sections**
   - `[page]-header` - Page headers
   - `[page]-navigation` - Navigation elements
   - `[page]-content` - Main content areas
   - `[page]-sidebar` - Sidebar elements
   - `[page]-footer` - Footer elements

3. **Interactive Elements**
   - `[page]-search-form` - Search forms
   - `[page]-search-results` - Search result containers
   - `[page]-create-form` - Creation forms
   - `[page]-action-buttons` - Button groups

4. **Data Display Elements**
   - `[page]-[data]-table` - Data tables
   - `[page]-[data]-list` - Data lists
   - `[page]-[data]-empty` - Empty state displays
   - `[page]-stats-[metric]` - Statistic displays

5. **State Elements**
   - `[page]-loading-state` - Loading indicators
   - `[page]-error-state` - Error displays
   - `[page]-success-state` - Success messages
   - `[page]-fallback-interface` - Fallback content

#### Benefits of Consistent IDs
- **Testing**: Easier to write Playwright/Selenium tests
- **CSS targeting**: Specific styling without class conflicts
- **JavaScript**: Reliable element selection
- **Debugging**: Clear element identification in dev tools
- **Accessibility**: Better screen reader navigation
- **Documentation**: Self-documenting HTML structure

#### Examples from My Lists Page
```html
<div id="my-lists-main-container">
  <div id="my-lists-page-header">
    <div id="my-lists-quick-stats">
      <div id="my-lists-stats-total">4 lists</div>
      <div id="my-lists-stats-favourites">1 favourite</div>
    </div>
  </div>
  
  <div id="my-lists-favourites-section">
    <div id="my-lists-favourites-header">My Favourites</div>
    <div id="my-lists-favourites-table-container">
      <table id="my-lists-favourites-table">
        <tbody id="my-lists-favourites-tbody">
          <!-- Council rows -->
        </tbody>
      </table>
    </div>
    <div id="my-lists-favourites-empty">No favourites yet</div>
  </div>
</div>
```

**Enforcement**: All new templates and template modifications must include meaningful IDs. Code reviews should verify ID consistency and usefulness.

## Implementation Guidelines

### Tailwind CSS Mobile-First Approach
```css
/* Mobile first - no prefix */
.council-header { padding: 1rem; }

/* Small screens and up */
@screen sm {
  .council-header { padding: 1.5rem; }
}

/* Large screens and up */  
@screen lg {
  .council-header { padding: 2rem; }
}
```

### Responsive Breakpoint Strategy
- **xs (default)**: 0px - 639px (Mobile phones)
- **sm**: 640px - 767px (Large phones, small tablets)
- **md**: 768px - 1023px (Tablets, small laptops)
- **lg**: 1024px - 1279px (Laptops, desktops)
- **xl**: 1280px+ (Large desktops)

## Common Mobile Anti-Patterns to Avoid
- **Hover-dependent interactions**: Don't rely on hover states
- **Tiny touch targets**: Avoid buttons smaller than 44px
- **Horizontal scrolling**: Avoid accidental horizontal scroll
- **Modal overuse**: Minimize modal dialogs on mobile
- **Fixed positioning**: Be careful with fixed elements that block content
- **Auto-zoom prevention**: Don't disable zoom unless absolutely necessary

We aim to create an app-like experience that is also beautiful on tablets and desktops for power users.