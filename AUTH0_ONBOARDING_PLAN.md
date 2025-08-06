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

# EVENT VIEWER INTEGRATION & MONITORING PLAN

## User Registration Event Logging

### Registration Event Types

**All onboarding events will be logged to the Event Viewer system for monitoring and analytics.**

#### 1. User Registration Events
```python
# New user starts onboarding (via Auth0)
SystemEvent.objects.create(
    source='user_onboarding',
    level='info',
    category='user_activity',
    title='New User Registration Started',
    message=f'User {user.email} began onboarding via Auth0',
    user=user,
    details={
        'auth0_user_id': profile.auth0_user_id,
        'country_detected': profile.is_uk_user,
        'email_verified': profile.email_confirmed,
        'registration_method': 'auth0',
        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
    },
    tags=['onboarding', 'auth0', 'registration'],
    fingerprint=f'user_registration_started_{user.id}_{date.today()}'
)

# Onboarding step completion
SystemEvent.objects.create(
    source='user_onboarding',
    level='info', 
    category='user_activity',
    title=f'Onboarding Step Completed: {step_name}',
    message=f'User {user.username} completed {step_name} step',
    user=user,
    details={
        'step_name': step_name,
        'step_number': step_number,
        'total_steps': total_steps,
        'completion_time_seconds': completion_time,
        'skip_reasons': skip_reasons,  # If steps were skipped
    },
    tags=['onboarding', 'step_completion', step_name.lower()],
    fingerprint=f'onboarding_step_{step_name}_{user.id}'
)
```

#### 2. OSA Compliance Events
```python
# Age verification completed
SystemEvent.objects.create(
    source='osa_compliance',
    level='info',
    category='compliance',
    title='Age Verification Completed',
    message=f'User verified age: {age} years old',
    user=user,
    details={
        'age': age,
        'date_of_birth': dob.isoformat(),
        'is_adult': age >= 18,
        'verification_method': 'self_declared',
    },
    tags=['osa', 'age_verification', 'compliance'],
    fingerprint=f'age_verification_{user.id}'
)

# Content restrictions applied
SystemEvent.objects.create(
    source='osa_compliance',
    level='warning' if age < 18 else 'info',
    category='compliance',
    title='OSA Content Restrictions Applied',
    message=f'User under 18 - Feed/comments blocked per OSA requirements',
    user=user,
    details={
        'age': age,
        'restrictions_applied': ['feed_blocked', 'comments_blocked'],
        'compliance_reason': 'online_safety_act',
    },
    tags=['osa', 'content_restriction', 'minor_protection'],
    fingerprint=f'content_restrictions_{user.id}'
)
```

#### 3. Security & Validation Events
```python
# Suspicious registration patterns
SystemEvent.objects.create(
    source='security',
    level='warning',
    category='security',
    title='Suspicious Registration Pattern Detected',
    message=f'Multiple registrations from IP {ip} in short timeframe',
    details={
        'ip_address': ip,
        'registration_count': count,
        'timeframe_hours': timeframe,
        'user_agents': user_agents,
    },
    tags=['security', 'fraud_detection', 'registration'],
    fingerprint=f'suspicious_registration_{ip}_{date.today()}'
)

# Data validation failures
SystemEvent.objects.create(
    source='data_validation',
    level='warning',
    category='data_quality',
    title='User Registration Data Validation Failed',
    message=f'Invalid data submitted: {error_description}',
    user=user,
    details={
        'validation_errors': errors,
        'submitted_data': sanitized_data,
        'form_step': step_name,
    },
    tags=['validation', 'data_quality', 'form_errors'],
    fingerprint=f'validation_failure_{step_name}_{user.id}'
)
```

## Email Alert System Integration

### Midday Registration Digest

**Implementation**: Create a management command that sends a daily digest of new registrations at 12:00 PM.

#### Management Command Structure
```python
# management/commands/send_registration_digest.py
class Command(BaseCommand):
    help = 'Send daily digest of new user registrations'
    
    def handle(self, *args, **options):
        # Get yesterday's registrations
        yesterday = timezone.now() - timedelta(days=1)
        today = timezone.now()
        
        registration_events = SystemEvent.objects.filter(
            source='user_onboarding',
            title='New User Registration Started',
            timestamp__gte=yesterday.replace(hour=0, minute=0, second=0),
            timestamp__lt=today.replace(hour=0, minute=0, second=0)
        ).order_by('-timestamp')
        
        if registration_events.exists():
            self._send_digest_email(registration_events)
```

#### Email Template (`templates/emails/registration_digest.html`)
```html
<h2>Daily Registration Summary - {{ date|date:"F j, Y" }}</h2>

<div class="summary-stats">
    <p><strong>{{ total_registrations }}</strong> new users registered</p>
    <p><strong>{{ uk_users }}</strong> UK users, <strong>{{ non_uk_users }}</strong> international</p>
    <p><strong>{{ adult_users }}</strong> adults (18+), <strong>{{ minor_users }}</strong> minors (&lt;18)</p>
    <p><strong>{{ email_verified }}</strong> had pre-verified emails from Auth0</p>
</div>

<h3>Registration Details</h3>
<table class="registration-table">
    <thead>
        <tr>
            <th>Time</th>
            <th>User</th>
            <th>Location</th>
            <th>Age</th>
            <th>Method</th>
            <th>Status</th>
        </tr>
    </thead>
    <tbody>
        {% for reg in registrations %}
        <tr>
            <td>{{ reg.timestamp|date:"H:i" }}</td>
            <td>{{ reg.user.first_name }} {{ reg.user.last_name }} ({{ reg.user.email }})</td>
            <td>{{ reg.details.country_detected|yesno:"UK,International" }}</td>
            <td>{{ reg.details.age|default:"Pending" }}</td>
            <td>Auth0</td>
            <td>{{ reg.details.onboarding_status|default:"In Progress" }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>

<h3>Weekly Trends</h3>
<p>{{ weekly_comparison }}</p>

<hr>
<p><small>View full details at <a href="{{ base_url }}/system-events/">Event Viewer Dashboard</a></small></p>
```

#### Cron Job Configuration
```bash
# Add to crontab for daily execution at 12:00 PM
0 12 * * * /path/to/python manage.py send_registration_digest
```

### Alert Thresholds for Registration Events

#### Custom Registration Alert Thresholds
```python
# In settings.py - extend existing EVENT_VIEWER_SETTINGS
EVENT_VIEWER_SETTINGS = {
    # ... existing settings ...
    'REGISTRATION_ALERT_THRESHOLDS': {
        'unusual_registration_spike': {
            'threshold': 10,  # More than 10 registrations per hour
            'timeframe_hours': 1,
            'alert_level': 'warning',
        },
        'potential_fraud': {
            'same_ip_registrations': 5,  # 5+ registrations from same IP
            'timeframe_hours': 24,
            'alert_level': 'critical',
        },
        'failed_validations': {
            'threshold': 20,  # 20+ validation failures per day
            'timeframe_hours': 24,
            'alert_level': 'warning',
        },
        'onboarding_abandonment': {
            'threshold_percent': 70,  # >70% abandon onboarding
            'alert_level': 'info',
        }
    }
}
```

## Implementation Timeline

### Phase 1: Event Logging Integration (2-3 hours)
- [ ] Add SystemEvent logging to all onboarding views
- [ ] Create event logging helper functions
- [ ] Add OSA compliance event tracking
- [ ] Test event creation and Event Viewer display

### Phase 2: Registration Digest System (3-4 hours)
- [ ] Create management command for digest generation
- [ ] Design email template with registration statistics
- [ ] Implement weekly comparison analytics
- [ ] Test email delivery and formatting
- [ ] Set up cron job for automated execution

### Phase 3: Advanced Monitoring & Alerts (2-3 hours)
- [ ] Implement fraud detection patterns
- [ ] Add onboarding abandonment tracking
- [ ] Create custom alert thresholds for registration events
- [ ] Integrate with existing alert system
- [ ] Test alert generation and delivery

### Phase 4: Analytics Dashboard Enhancement (2 hours)
- [ ] Add registration-specific analytics to Event Viewer
- [ ] Create onboarding funnel analysis
- [ ] Add geographical distribution charts
- [ ] Implement age demographics tracking

## Event Logging Helper Functions

### Onboarding Event Logger
```python
# council_finance/services/onboarding_logger.py
class OnboardingLogger:
    @staticmethod
    def log_registration_started(user, request, profile):
        from event_viewer.models import SystemEvent
        SystemEvent.objects.create(
            source='user_onboarding',
            level='info',
            category='user_activity', 
            title='New User Registration Started',
            message=f'User {user.email} began onboarding via Auth0',
            user=user,
            request_path=request.path,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={
                'auth0_user_id': profile.auth0_user_id,
                'country_detected': profile.is_uk_user,
                'email_verified': profile.email_confirmed,
                'registration_method': 'auth0',
                'detection_data': {
                    'locale': profile.auth0_metadata.get('locale', ''),
                    'email_domain': user.email.split('@')[1] if user.email else '',
                }
            },
            tags=['onboarding', 'auth0', 'registration'],
            fingerprint=f'user_registration_started_{user.id}_{date.today()}'
        )
    
    @staticmethod
    def log_step_completion(user, request, step_name, step_number, total_steps, details=None):
        from event_viewer.models import SystemEvent
        SystemEvent.objects.create(
            source='user_onboarding',
            level='info',
            category='user_activity',
            title=f'Onboarding Step Completed: {step_name}',
            message=f'User {user.username or user.email} completed {step_name} step ({step_number}/{total_steps})',
            user=user,
            request_path=request.path,
            ip_address=request.META.get('REMOTE_ADDR'),
            details={
                'step_name': step_name,
                'step_number': step_number,
                'total_steps': total_steps,
                'progress_percent': round((step_number / total_steps) * 100),
                **(details or {})
            },
            tags=['onboarding', 'step_completion', step_name.lower().replace(' ', '_')],
            fingerprint=f'onboarding_step_{step_name.lower()}_{user.id}'
        )
```

## Integration Points

### Existing System Compatibility
- **Email System**: Uses existing `ERROR_ALERTS_EMAIL_ADDRESS` configuration
- **Activity Logging**: Complements (doesn't replace) existing ActivityLog system
- **User Management**: Integrates with existing UserProfile and trust tier system
- **Event Viewer**: Utilizes existing monitoring infrastructure

### Data Privacy Considerations
- **GDPR Compliance**: Registration events include only necessary data
- **Data Retention**: Follow existing Event Viewer retention policies
- **User Consent**: Registration logging covered by terms of service
- **Anonymization**: Personal data can be anonymized in older events

---

## SUCCESS METRICS

### Registration Monitoring KPIs
- **Registration Volume**: Daily/weekly registration trends
- **Completion Rate**: Percentage completing full onboarding
- **Drop-off Points**: Which steps cause abandonment
- **Geographic Distribution**: UK vs international user patterns  
- **Age Demographics**: Adult vs minor user breakdown
- **Verification Success**: Auth0 email verification rates

### Alert Effectiveness
- **False Positive Rate**: <5% for fraud detection alerts
- **Response Time**: <2 hours for critical registration issues
- **Digest Delivery**: 100% successful daily digest delivery
- **Event Capture**: >99% of registration events logged

---

*Last updated: 2025-08-06*
*Status: Ready for Event Viewer integration implementation*