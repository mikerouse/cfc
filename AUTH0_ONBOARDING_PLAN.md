# Auth0 Onboarding & Online Safety Act Compliance Plan

## Project Overview

Implementing a comprehensive user onboarding system that integrates Auth0 authentication with Online Safety Act (OSA) compliance requirements, using GOV.UK-inspired design patterns.

## Key Requirements

### 1. Online Safety Act Compliance
- **Age verification**: Collect date of birth (mandatory)
- **Geographic considerations**: Different rules for UK vs non-UK users
- **Content restrictions**: Block comments/Feed for under-18s instead of requiring parental consent
- **Community guidelines**: Mandatory acceptance during onboarding

### 2. Geographic User Handling
- **UK Users**: Request postcode (optional but helpful for local council features)
- **Non-UK Users**: Skip postcode collection entirely
- **Detection**: Use Auth0 location data or IP geolocation as fallback

### 3. Age-Based Content Restrictions
- **Under 18**: Block access to Feed/comments section entirely
- **18+**: Full access to all features
- **No parental consent required**: Simplified approach using content blocking

### 4. Design Principles
- **GOV.UK-inspired**: Use GOV.UK patterns as inspiration, not exact implementation
- **No GOV.UK Frontend**: Custom Tailwind CSS implementation following GOV.UK principles
- **Progressive disclosure**: One thing per page
- **Mobile-first**: Responsive design
- **Accessible**: WCAG 2.1 AA compliance

## Technical Architecture

### User Profile Extensions
```python
class UserProfile(models.Model):
    # Existing fields...
    
    # OSA Compliance fields
    date_of_birth = models.DateField(null=True, blank=True)
    age_verified = models.BooleanField(default=False)
    is_uk_user = models.BooleanField(default=True)
    can_access_comments = models.BooleanField(default=True)
    community_guidelines_accepted = models.BooleanField(default=False)
    community_guidelines_accepted_at = models.DateTimeField(null=True, blank=True)
    
    # Geographic fields
    country = models.CharField(max_length=2, blank=True)  # ISO country code
    postcode = models.CharField(max_length=20, blank=True)  # Only for UK users
    postcode_refused = models.BooleanField(default=False)  # UK users can opt out
    
    def age(self):
        if not self.date_of_birth:
            return None
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
    
    def is_adult(self):
        return self.age() >= 18 if self.age() is not None else False
    
    def needs_onboarding(self):
        return not (self.date_of_birth and self.community_guidelines_accepted)
```

## Onboarding Flow Design

### Step 1: Welcome & Data Extraction
- Extract data from Auth0 profile (name, email, location hints)
- Determine if user is likely UK-based
- Auto-confirm email if Auth0 verified

### Step 2: Basic Information
**Page: `/welcome/details/`**
- First name, Last name (pre-populated from Auth0 if available)
- Clear, simple form following GOV.UK patterns

### Step 3: Age Verification (OSA Requirement)
**Page: `/welcome/age/`**
- Date of birth collection using GOV.UK date input pattern
- Clear explanation: "We need this to comply with the Online Safety Act"
- Validation: Must be 13+ to continue

### Step 4: Location Information (Conditional)
**Page: `/welcome/location/`**
- **If UK user**: Ask for postcode (optional with clear opt-out)
- **If non-UK user**: Skip this step entirely
- Country selection if location unclear

### Step 5: Community Guidelines
**Page: `/welcome/guidelines/`**
- Mandatory acceptance of community guidelines
- Clear explanation of reporting mechanisms
- Age-appropriate messaging

### Step 6: Welcome Complete
**Page: `/welcome/complete/`**
- Confirmation of successful setup
- Different messaging based on age:
  - **18+**: "You now have full access to all features"
  - **Under 18**: "You can explore councils and data, but comments are restricted for your safety"

## Content Restriction Strategy

### Feed Section Access Control
```python
# Template context processor or middleware
def check_feed_access(user):
    if not user.is_authenticated:
        return False
    
    profile = getattr(user, 'profile', None)
    if not profile:
        return False
        
    # Must have completed age verification
    if not profile.age_verified or not profile.date_of_birth:
        return False
        
    # Must be 18+ for comments/feed
    return profile.is_adult()

# In Feed templates
{% if user.profile.can_access_comments %}
    <!-- Show feed/comments -->
{% else %}
    <div class="restricted-content-notice">
        <h3>Content Restricted</h3>
        <p>As you are under the age of 18, the Online Safety Act requires us to hide user-generated content from you in case any of it may be harmful.</p>
        <p>Whilst you may be able to vote at 16 years old, you cannot view these comments until you turn 18.</p>
        <p>You can still explore all council financial data and use our comparison tools.</p>
    </div>
{% endif %}
```

## Auth0 Pipeline Integration

### Enhanced Pipeline for OSA Compliance
```python
def save_profile_osa_compliant(backend, user, response, *args, **kwargs):
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    # Extract Auth0 data
    profile.auth0_user_id = kwargs.get('uid', '')
    
    # Auto-confirm email if Auth0 verified
    if response.get('email_verified', False):
        profile.confirm_email()
    
    # Extract geographic hints from Auth0
    locale = response.get('locale', '')
    country = response.get('country', '')
    
    # Determine if likely UK user
    if country == 'GB' or locale.endswith('GB') or user.email.endswith('.uk'):
        profile.is_uk_user = True
    else:
        profile.is_uk_user = False
    
    profile.save()
    
    # Redirect to onboarding if needed
    if profile.needs_onboarding():
        request = kwargs.get('request')
        if request:
            request.session['needs_onboarding'] = True
```

## URL Structure

```python
# Onboarding URLs
urlpatterns = [
    path('welcome/', onboarding_views.welcome, name='welcome'),
    path('welcome/details/', onboarding_views.basic_details, name='onboarding_details'),
    path('welcome/age/', onboarding_views.age_verification, name='onboarding_age'),
    path('welcome/location/', onboarding_views.location_info, name='onboarding_location'),
    path('welcome/guidelines/', onboarding_views.community_guidelines, name='onboarding_guidelines'),
    path('welcome/complete/', onboarding_views.onboarding_complete, name='onboarding_complete'),
]
```

## Design Patterns (GOV.UK-Inspired)

### Form Structure
- One primary action per page
- Clear headings (H1 for main question)
- Hint text for complex fields
- Progressive enhancement
- Error summary at top of page
- Inline validation

### Error Handling
```html
<!-- Error summary (top of page) -->
<div class="error-summary" role="alert" tabindex="-1">
    <h2>There is a problem</h2>
    <ul>
        <li><a href="#date-of-birth">Enter your date of birth</a></li>
    </ul>
</div>

<!-- Form field with error -->
<div class="form-group error">
    <label for="date-of-birth">
        <span class="label-text">Date of birth</span>
        <span class="error-message">Enter your date of birth</span>
    </label>
    <input id="date-of-birth" class="form-control error" type="date" />
</div>
```

### Accessibility Features
- Proper ARIA labels and roles
- Focus management between pages
- High contrast support
- Screen reader announcements for dynamic content
- Keyboard navigation

## Implementation Phases

### Phase 1: Foundation (2-3 days)
- [ ] Update UserProfile model with OSA fields
- [ ] Create migration for new fields
- [ ] Update Auth0 pipeline for data extraction
- [ ] Create onboarding middleware/decorators

### Phase 2: Onboarding Views (3-4 days)
- [ ] Create onboarding view classes
- [ ] Implement form validation
- [ ] Add geographic detection logic
- [ ] Create GOV.UK-inspired templates

### Phase 3: Content Restrictions (2 days)
- [ ] Implement Feed access control
- [ ] Create age-appropriate messaging
- [ ] Update navigation based on permissions
- [ ] Add template context processors

### Phase 4: Testing & Polish (2 days)
- [ ] Test complete onboarding flow
- [ ] Accessibility testing
- [ ] Cross-browser testing
- [ ] Age restriction testing

## Success Criteria

1. **Legal Compliance**: All OSA requirements met
2. **User Experience**: Smooth, clear onboarding process
3. **Accessibility**: WCAG 2.1 AA compliance
4. **Geographic Handling**: Appropriate UX for UK vs non-UK users
5. **Age Restrictions**: Proper content blocking for under-18s
6. **Integration**: Seamless Auth0 to onboarding flow

## Notes & Considerations

- **Privacy**: Clear explanation of why we collect each piece of data
- **GDPR**: Ensure all data collection has legal basis
- **Flexibility**: System should handle Auth0 data variations gracefully
- **Performance**: Onboarding should be fast and lightweight
- **Monitoring**: Track onboarding completion rates and drop-off points

---

*Last updated: 2025-08-06*
*Status: Planning phase - ready for implementation*