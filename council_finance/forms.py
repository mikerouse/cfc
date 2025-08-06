from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from .models import UserProfile
from .models import CouncilList, Council
from .models import CounterDefinition, DataField
from .models.site_counter import SiteCounter, GroupCounter
# ``CHARACTERISTIC_SLUGS`` identifies slugs which represent council
# characteristics.  Their identifiers are fixed so forms prevent accidental
# renaming.
from .models.field import CHARACTERISTIC_SLUGS, PROTECTED_SLUGS
from django.contrib.contenttypes.models import ContentType


class SignUpForm(UserCreationForm):
    """Extend the built-in user creation form with an optional postcode."""

    postcode = forms.CharField(
        max_length=20, 
        required=False,  # Make postcode optional
        help_text="Optional - helps us provide location-specific features"
    )
    postcode_refused = forms.BooleanField(
        required=False,
        label="I prefer not to provide my postcode",
        help_text="Check this if you don't want to provide location information"
    )

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "email")  # Password fields provided by parent

    def save(self, commit=True):
        user = super().save(commit)
        postcode = self.cleaned_data["postcode"]
        postcode_refused = self.cleaned_data["postcode_refused"]
        
        # Ensure the profile exists (signal may have created it already)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        
        # Handle postcode logic
        if postcode_refused:
            profile.postcode_refused = True
            profile.postcode = ""
        elif postcode:
            profile.postcode = postcode
            profile.postcode_refused = False
        
        # Extra volunteer details are gathered later on the profile page
        # so signup only stores the essential postcode.
        if not profile.confirmation_token:
            profile.confirmation_token = get_random_string(32)
        if commit:
            profile.save()
        return user


class ProfileExtraForm(forms.ModelForm):
    """Collect optional volunteer information on the profile page.

    The form is intentionally lightweight. Additional fields can be
    added later without altering the signup process because they are
    saved via the user's profile page instead of during registration.
    """

    class Meta:
        model = UserProfile
        fields = [
            "political_affiliation",
            "works_for_council",
            "employer_council",
            "official_email",
        ]
        widgets = {
            "political_affiliation": forms.TextInput(attrs={"class": "border rounded p-1 w-full"}),
            "works_for_council": forms.CheckboxInput(attrs={"class": "mr-1"}),
            "employer_council": forms.Select(attrs={"class": "border rounded p-1 w-full"}),
            "official_email": forms.EmailInput(attrs={"class": "border rounded p-1 w-full"}),
        }


class ProfileBasicForm(forms.ModelForm):
    """Form for basic profile information including email and password changes."""
    
    # User fields
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'})
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'})
    )
# Email field removed - handled through modal
    
    # Password fields
    password1 = forms.CharField(
        label='New password',
        widget=forms.PasswordInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'}),
        required=False,
        help_text='Leave blank to keep current password'
    )
    password2 = forms.CharField(
        label='Confirm new password',
        widget=forms.PasswordInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'}),
        required=False
    )
    
    # Profile fields
    postcode = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'}),
        help_text='Optional - helps us provide location-specific features'
    )
    postcode_refused = forms.BooleanField(
        required=False,
        label="I prefer not to provide my postcode",
        widget=forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'})
    )

    class Meta:
        model = UserProfile
        fields = ['postcode', 'postcode_refused', 'visibility']
        widgets = {
            'visibility': forms.Select(attrs={'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'})
        }

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password1 != password2:
            raise forms.ValidationError('Passwords do not match.')
            
        if password1 and len(password1) < 8:
            raise forms.ValidationError('Password must be at least 8 characters long.')
            
        return cleaned_data


class ProfileAdditionalForm(forms.ModelForm):
    """Form for additional profile information."""
    
    class Meta:
        model = UserProfile
        fields = [
            'political_affiliation',
            'works_for_council',
            'employer_council',
            'official_email'
        ]
        widgets = {
            'political_affiliation': forms.TextInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'}),
            'works_for_council': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'}),
            'employer_council': forms.Select(attrs={'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'}),
            'official_email': forms.EmailInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set up council choices with empty option
        self.fields['employer_council'].empty_label = "Select a council..."
        # Make sure councils are ordered by name
        from .models import Council
        self.fields['employer_council'].queryset = Council.objects.filter(status='active').order_by('name')


class ProfileCustomizationForm(forms.ModelForm):
    """Form for profile customization settings."""
    
    class Meta:
        model = UserProfile
        fields = [
            'preferred_font',
            'font_size',
            'color_theme',
            'high_contrast_mode'
        ]
        widgets = {
            'preferred_font': forms.Select(attrs={'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'}),
            'font_size': forms.Select(attrs={'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'}),
            'color_theme': forms.Select(attrs={'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'}),
            'high_contrast_mode': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Define font choices
        font_choices = [
            ('Arial', 'Arial'),
            ('Helvetica', 'Helvetica'),
            ('Georgia', 'Georgia'),
            ('Times New Roman', 'Times New Roman'),
            ('Verdana', 'Verdana'),
            ('Tahoma', 'Tahoma'),
            ('Cairo', 'Cairo'),
            ('Inter', 'Inter'),
            ('Open Sans', 'Open Sans'),
            ('Roboto', 'Roboto'),
        ]
        
        self.fields['preferred_font'].widget.choices = font_choices


class ProfileNotificationForm(forms.Form):
    """Form for notification preferences."""
    
    email_notifications = forms.BooleanField(
        required=False,
        label="Email notifications",
        help_text="Receive email notifications for important updates",
        widget=forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'})
    )
    
    contribution_notifications = forms.BooleanField(
        required=False,
        label="Contribution notifications",
        help_text="Get notified when your contributions are reviewed",
        widget=forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'})
    )
    
    council_update_notifications = forms.BooleanField(
        required=False,
        label="Council update notifications",
        help_text="Receive notifications about councils you follow",
        widget=forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'})
    )
    
    weekly_digest = forms.BooleanField(
        required=False,
        label="Weekly digest",
        help_text="Receive a weekly summary of activity and updates",
        widget=forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'})
    )
class CouncilListForm(forms.ModelForm):
    """Create a simple list of councils."""

    # Provide a short helper text so users know why lists are useful
    name = forms.CharField(
        help_text="Use custom lists to group and compare councils",
        # Tailwind classes provide a border and padding so the input stands out
        widget=forms.TextInput(attrs={"class": "border rounded p-1 flex-1"}),
    )

    class Meta:
        model = CouncilList
        fields = ["name"]


class CounterDefinitionForm(forms.ModelForm):
    """Edit counter definitions from the management pages."""

    # Select which council types a counter should apply to. An empty selection
    # means the counter is universal.
    council_types = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        widget=forms.SelectMultiple,
        label="Council types",
    )
    

    class Meta:
        model = CounterDefinition
        fields = [
            "name",
            "formula",
            "explanation",
            "duration",
            "precision",
            "show_currency",
            "friendly_format",
            "show_by_default",
            "headline",
            "council_types",
        ]
        widgets = {
            "explanation": forms.Textarea(
                attrs={"rows": 2, "class": "border rounded p-1 w-full"}
            ),
            "duration": forms.NumberInput(
                attrs={"min": 0, "class": "border rounded p-1 w-full"}
            ),
            "precision": forms.NumberInput(
                attrs={"min": 0, "class": "border rounded p-1 w-full"}
            ),            "show_currency": forms.CheckboxInput(attrs={"class": "mr-2"}),
            "friendly_format": forms.CheckboxInput(attrs={"class": "mr-2"}),
            "show_by_default": forms.CheckboxInput(attrs={"class": "mr-2"}),
            "headline": forms.CheckboxInput(attrs={"class": "mr-2"}),
            "council_types": forms.SelectMultiple(attrs={"class": "border rounded p-1 w-full"}),
        }

    def __init__(self, *args, **kwargs):
        """Add Tailwind classes to text inputs for consistency."""
        super().__init__(*args, **kwargs)
        from .models import CouncilType
        
        # Ensure council type options reflect the current set without code changes.
        self.fields["council_types"].queryset = CouncilType.objects.all()
        
        for name, field in self.fields.items():
            if name in ["show_currency", "friendly_format", "show_by_default", "headline"]:
                continue
            field.widget.attrs.setdefault("class", "border rounded p-1 w-full")



class CounterFactoidAssignmentForm(forms.Form):
    """Form for assigning factoid templates to an existing counter."""
    
    factoid_templates = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Factoid Templates",
        help_text="Templates that will generate automatic insights for this counter",
    )
    
    def __init__(self, counter_instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models.factoid import FactoidTemplate
        
        self.counter_instance = counter_instance
        self.fields["factoid_templates"].queryset = FactoidTemplate.objects.filter(is_active=True).order_by('name')
        
        # Set initial values if counter already has factoids assigned
        if counter_instance and counter_instance.pk:
            self.fields["factoid_templates"].initial = counter_instance.factoid_templates.all()
    
    def save(self):
        """Save the factoid template associations."""
        if not self.counter_instance:
            return
            
        factoid_templates = self.cleaned_data.get('factoid_templates', [])
        
        # Clear existing associations and set new ones
        self.counter_instance.factoid_templates.set(factoid_templates)
        
        return self.counter_instance


class DataFieldForm(forms.ModelForm):
    """Form for creating and editing data fields."""

    # Dataset selection only applies when ``content_type`` is ``list``. The
    # queryset is limited to models within this app so admins can't accidentally
    # bind to unrelated tables.
    dataset_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(app_label="council_finance"),
        required=False,
        label="Dataset",
        help_text="Model used for list options",
    )
    # Allow multiple council types so managers can limit where a field appears.
    # When no types are chosen the field applies to all councils.
    council_types = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        widget=forms.SelectMultiple,
        label="Council types",
    )

    class Meta:
        model = DataField
        fields = [
            "name",
            "category",
            "explanation",
            "content_type",
            "dataset_type",
            "council_types",
            # ``formula`` is rarely needed and shown under an advanced section
            "formula",
            "required",
            # Image field configuration options
            "image_max_width",
            "image_max_height", 
            "image_max_file_size",
            "image_default_alt_text",
            "image_copyright_text",
            "image_ai_generated_flag",
        ]
        widgets = {
            "explanation": forms.Textarea(
                attrs={"rows": 2, "class": "border rounded p-1 w-full"}
            ),
            "formula": forms.TextInput(attrs={"class": "border rounded p-1 w-full"}),
            # Image field widgets
            "image_max_width": forms.NumberInput(attrs={"class": "border rounded p-1 w-full", "min": "1", "placeholder": "e.g. 500"}),
            "image_max_height": forms.NumberInput(attrs={"class": "border rounded p-1 w-full", "min": "1", "placeholder": "e.g. 500"}),
            "image_max_file_size": forms.NumberInput(attrs={"class": "border rounded p-1 w-full", "min": "1", "placeholder": "Size in KB"}),
            "image_default_alt_text": forms.TextInput(attrs={"class": "border rounded p-1 w-full", "placeholder": "Default alt text for accessibility"}),
            "image_copyright_text": forms.Textarea(attrs={"rows": 2, "class": "border rounded p-1 w-full", "placeholder": "Copyright notice or attribution"}),
            "image_ai_generated_flag": forms.CheckboxInput(attrs={"class": "mr-2"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Prevent editing the slug of characteristic fields so managers can't
        # rename these core identifiers. The values themselves remain editable.
        if "slug" in self.fields and self.instance and self.instance.pk and self.instance.slug in PROTECTED_SLUGS:
            self.fields["slug"].disabled = True
        # Populate the council type choices dynamically so any new types appear
        # automatically without code changes.
        from .models import CouncilType
        self.fields["council_types"].queryset = CouncilType.objects.all()
        # Style widgets consistently and apply an id to the dataset row so it can
        # be toggled via JavaScript when the content type changes.
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "mr-2")
            else:
                field.widget.attrs.setdefault("class", "border rounded p-1 w-full")
        self.fields["dataset_type"].widget.attrs["id"] = "id_dataset_type"

class SiteCounterForm(forms.ModelForm):
    """Form for creating and editing site-wide counters."""

    class Meta:
        model = SiteCounter
        fields = [
            "name",
            "explanation",
            "counter",
            "year",
            "columns",
            "duration",
            "precision",
            "show_currency",
            "friendly_format",
            "promote_homepage",
        ]
        widgets = {
            "explanation": forms.Textarea(
                attrs={"rows": 2, "class": "border rounded p-1 w-full"}
            ),
            "year": forms.Select(attrs={"class": "border rounded p-1 w-full"}),
            "duration": forms.NumberInput(attrs={"min": 0, "class": "border rounded p-1 w-full"}),
            "precision": forms.NumberInput(attrs={"min": 0, "class": "border rounded p-1 w-full"}),
            "show_currency": forms.CheckboxInput(attrs={"class": "mr-2"}),
            "friendly_format": forms.CheckboxInput(attrs={"class": "mr-2"}),
            "promote_homepage": forms.CheckboxInput(attrs={"class": "mr-2"}),
            "columns": forms.Select(attrs={"class": "border rounded p-1 w-full"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import FinancialYear
        # Exclude the special "general" year used for aggregated data and
        # present an explicit option for using all years combined. Setting the
        # ``empty_label`` ensures the first drop-down choice reads nicely.
        self.fields["year"].queryset = FinancialYear.objects.order_by("-label").exclude(label__iexact="general")
        self.fields["year"].empty_label = "All Available Years"
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                continue
            field.widget.attrs.setdefault("class", "border rounded p-1 w-full")


class GroupCounterForm(forms.ModelForm):
    """Form for creating and editing custom group counters."""

    class Meta:
        model = GroupCounter
        fields = [
            "name",
            "counter",
            "year",
            "councils",
            "council_list",
            "council_types",
            "duration",
            "precision",
            "show_currency",
            "friendly_format",
            "promote_homepage",
        ]
        widgets = {
            "councils": forms.SelectMultiple(attrs={"class": "border rounded p-1 w-full"}),
            "council_list": forms.Select(attrs={"class": "border rounded p-1 w-full"}),
            "council_types": forms.SelectMultiple(attrs={"class": "border rounded p-1 w-full"}),
            "year": forms.Select(attrs={"class": "border rounded p-1 w-full"}),
            "duration": forms.NumberInput(attrs={"min": 0, "class": "border rounded p-1 w-full"}),
            "precision": forms.NumberInput(attrs={"min": 0, "class": "border rounded p-1 w-full"}),
            "show_currency": forms.CheckboxInput(attrs={"class": "mr-2"}),
            "friendly_format": forms.CheckboxInput(attrs={"class": "mr-2"}),
            "promote_homepage": forms.CheckboxInput(attrs={"class": "mr-2"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Council, CouncilType, CouncilList
        from .models import FinancialYear
        self.fields["councils"].queryset = Council.objects.all().order_by("name")
        self.fields["council_types"].queryset = CouncilType.objects.all()
        self.fields["council_list"].queryset = CouncilList.objects.all()
        self.fields["year"].queryset = FinancialYear.objects.order_by("-label")
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                continue
            field.widget.attrs.setdefault("class", "border rounded p-1 w-full")


class UpdateCommentForm(forms.ModelForm):
    """Simple form to add a comment to a council update."""

    class Meta:
        from .models import CouncilUpdateComment

        model = CouncilUpdateComment
        fields = ["text"]
        widgets = {
            "text": forms.Textarea(attrs={"rows": 2, "class": "border rounded p-1 w-full"}),
        }


# Heroicon SVG paths for common icons
HEROICON_CHOICES = [
    ('', '-- Select an icon --'),
    # Buildings & Government
    ('M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4', '🏛️ Building Office'),
    ('M12 21V7m0 14l9-5V3l-9 5m0 14l-9-5V3l9 5M3 7l9 5 9-5M12 12l9-5m-9 5l-9-5', '🏢 Office Building'),
    
    # Location
    ('M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z M15 11a3 3 0 11-6 0 3 3 0 016 0z', '📍 Location Pin'),
    ('M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7', '🗺️ Map'),
    
    # People
    ('M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z', '👥 User Group'),
    ('M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z', '👤 User'),
    ('M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z', '👥 Users'),
    
    # Home & Housing
    ('M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6', '🏠 Home'),
    
    # Communication
    ('M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z', '✉️ Mail'),
    ('M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z', '📞 Phone'),
    
    # External/Web
    ('M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14', '🔗 External Link'),
    ('M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9', '🌐 Globe'),
    
    # Finance
    ('M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z', '💰 Currency Pound'),
    ('M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z', '💳 Cash'),
    
    # Data
    ('M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z', '📊 Chart Bar'),
    ('M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z', '📈 Presentation Chart'),
    
    # Other
    ('M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z', 'ℹ️ Information Circle'),
    ('M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z', '🕐 Clock'),
    ('M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z', '📅 Calendar'),
]


class DataFieldForm(forms.ModelForm):
    """Form for creating and editing data fields with meta display options."""
    
    icon_svg_path = forms.ChoiceField(
        choices=HEROICON_CHOICES,
        required=False,
        label="Icon",
        help_text="Select an icon to display in the council meta bar",
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
        })
    )
    
    class Meta:
        model = DataField
        fields = [
            'name', 'slug', 'category', 'explanation', 'content_type',
            'dataset_type', 'council_types', 'formula', 'required',
            # Meta display fields
            'show_in_meta', 'display_order', 'icon_svg_path', 'meta_display_format',
            # Image field options
            'image_max_width', 'image_max_height', 'image_max_file_size',
            'image_default_alt_text', 'image_copyright_text', 'image_ai_generated_flag',
            # URL security options
            'url_validation_enabled', 'url_allow_redirects', 'url_require_https',
            'url_blocked_domains', 'url_allowed_domains'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'slug': forms.TextInput(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'category': forms.Select(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'explanation': forms.Textarea(attrs={
                'rows': 3,
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'content_type': forms.Select(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'dataset_type': forms.Select(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'council_types': forms.SelectMultiple(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'formula': forms.TextInput(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'required': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            'show_in_meta': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            'display_order': forms.NumberInput(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'meta_display_format': forms.TextInput(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
                'placeholder': '{value} (e.g., "{value} residents")'
            }),
            # Image fields
            'image_max_width': forms.NumberInput(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'image_max_height': forms.NumberInput(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'image_max_file_size': forms.NumberInput(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'image_default_alt_text': forms.TextInput(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'image_copyright_text': forms.Textarea(attrs={
                'rows': 2,
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'image_ai_generated_flag': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            # URL security field widgets
            'url_validation_enabled': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            'url_allow_redirects': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            'url_require_https': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            'url_blocked_domains': forms.Textarea(attrs={
                'rows': 2,
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
                'placeholder': 'example.com, malicious.site, spam.domain'
            }),
            'url_allowed_domains': forms.Textarea(attrs={
                'rows': 2,
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
                'placeholder': 'gov.uk, parliament.uk, local-authority.org'
            }),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make slug read-only for protected fields
        if self.instance and self.instance.is_protected:
            self.fields['slug'].widget.attrs['readonly'] = True
            self.fields['slug'].help_text = "This is a protected field - slug cannot be changed"
            
        # Only show dataset_type when content_type is 'list'
        if self.instance and self.instance.content_type != 'list':
            self.fields['dataset_type'].widget = forms.HiddenInput()
            
    def clean_slug(self):
        """Prevent modification of protected slugs."""
        slug = self.cleaned_data.get('slug')
        if self.instance and self.instance.is_protected and self.instance.slug != slug:
            raise forms.ValidationError("This field's slug is protected and cannot be changed.")
        return slug


class CouncilListForm(forms.ModelForm):
    """Form for creating and editing council lists with enhanced functionality."""
    
    class Meta:
        model = CouncilList
        fields = ['name', 'description', 'color']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter list name (e.g., "North London Boroughs")',
                'maxlength': 100
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Optional description or notes about this list...',
                'rows': 3
            }),
            'color': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            })
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].help_text = "Give your list a descriptive name"
        self.fields['description'].help_text = "Add notes about what this list is for (optional)"
        self.fields['color'].help_text = "Choose a color theme for this list"


# ============================================================================
# ONBOARDING FORMS - Auth0 Integration & OSA Compliance
# ============================================================================

class BasicDetailsForm(forms.ModelForm):
    """
    Form for collecting basic user details (first name, last name).
    GOV.UK-inspired styling and validation.
    """
    
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your first name',
            'autocomplete': 'given-name',
        }),
        help_text="Your first name as you'd like it to appear on your profile",
        error_messages={
            'required': 'Enter your first name',
            'max_length': 'First name must be 150 characters or fewer',
        }
    )
    
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your last name',
            'autocomplete': 'family-name',
        }),
        help_text="Your last name or surname",
        error_messages={
            'required': 'Enter your last name',
            'max_length': 'Last name must be 150 characters or fewer',
        }
    )
    
    class Meta:
        from django.contrib.auth import get_user_model
        model = get_user_model()
        fields = ['first_name', 'last_name']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add required asterisk to labels
        for field_name, field in self.fields.items():
            if field.required:
                field.label = f"{field.label or field_name.replace('_', ' ').title()}"
    
    def clean_first_name(self):
        """Validate first name field"""
        first_name = self.cleaned_data.get('first_name', '').strip()
        
        if not first_name:
            raise forms.ValidationError("Enter your first name")
        
        # Basic validation for reasonable names
        if len(first_name) < 2:
            raise forms.ValidationError("First name must be at least 2 characters long")
        
        # Check for obvious invalid entries
        invalid_patterns = ['test', 'user', 'admin', '123', 'null', 'undefined']
        if first_name.lower() in invalid_patterns:
            raise forms.ValidationError("Please enter your real first name")
        
        return first_name.title()  # Capitalise properly
    
    def clean_last_name(self):
        """Validate last name field"""
        last_name = self.cleaned_data.get('last_name', '').strip()
        
        if not last_name:
            raise forms.ValidationError("Enter your last name")
        
        if len(last_name) < 2:
            raise forms.ValidationError("Last name must be at least 2 characters long")
        
        # Check for obvious invalid entries
        invalid_patterns = ['test', 'user', 'admin', '123', 'null', 'undefined']
        if last_name.lower() in invalid_patterns:
            raise forms.ValidationError("Please enter your real last name")
        
        return last_name.title()  # Capitalise properly


class AgeVerificationForm(forms.Form):
    """
    Form for age verification (date of birth collection).
    Required for Online Safety Act compliance.
    """
    from datetime import date, timedelta
    
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control form-control-lg',
            'max': date.today().isoformat(),  # Cannot be in future
            'min': (date.today() - timedelta(days=365 * 120)).isoformat(),  # Max 120 years old
        }),
        help_text="We need this to comply with the Online Safety Act and ensure age-appropriate content",
        error_messages={
            'required': 'Enter your date of birth',
            'invalid': 'Enter a valid date of birth',
        }
    )
    
    def clean_date_of_birth(self):
        """Validate date of birth and check minimum age"""
        from datetime import date
        dob = self.cleaned_data.get('date_of_birth')
        
        if not dob:
            raise forms.ValidationError("Enter your date of birth")
        
        # Check if date is not in future
        if dob > date.today():
            raise forms.ValidationError("Date of birth cannot be in the future")
        
        # Calculate age
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        
        # Check minimum age (13 for OSA compliance)
        if age < 13:
            raise forms.ValidationError(
                "You must be at least 13 years old to use this service"
            )
        
        # Check maximum reasonable age
        if age > 120:
            raise forms.ValidationError("Please check your date of birth is correct")
        
        return dob


class LocationInfoForm(forms.ModelForm):
    """
    Form for collecting location information from UK users.
    Postcode is optional but helps provide location-specific features.
    """
    
    postcode = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g. SW1A 1AA',
            'pattern': '[A-Za-z]{1,2}[0-9Rr][0-9A-Za-z]? [0-9][ABD-HJLNP-UW-Zabd-hjlnp-uw-z]{2}',
        }),
        help_text="Optional - helps us show you relevant local council information",
        error_messages={
            'invalid': 'Enter a valid UK postcode',
        }
    )
    
    postcode_refused = forms.BooleanField(
        required=False,
        label="I prefer not to provide my postcode",
        help_text="Check this if you don't want to provide location information",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = UserProfile
        fields = ['postcode', 'postcode_refused']
    
    def clean(self):
        """Custom validation to ensure either postcode is provided or refused"""
        cleaned_data = super().clean()
        postcode = cleaned_data.get('postcode')
        postcode_refused = cleaned_data.get('postcode_refused')
        
        # If neither postcode nor refusal is provided, that's fine - user can skip
        # But if both are provided, that's inconsistent
        if postcode and postcode_refused:
            raise forms.ValidationError(
                "Please either provide your postcode or indicate you prefer not to share it, not both."
            )
        
        return cleaned_data
    
    def clean_postcode(self):
        """Validate UK postcode format"""
        postcode = self.cleaned_data.get('postcode')
        
        if not postcode:
            return postcode
        
        # Remove spaces and convert to uppercase for validation
        postcode_clean = postcode.replace(' ', '').upper()
        
        # Basic UK postcode validation pattern
        import re
        uk_postcode_pattern = r'^[A-Z]{1,2}[0-9R][0-9A-Z]?[0-9][A-Z]{2}$'
        
        if not re.match(uk_postcode_pattern, postcode_clean):
            raise forms.ValidationError(
                "Enter a valid UK postcode (e.g. SW1A 1AA, M1 1AA, B33 8TH)"
            )
        
        # Return properly formatted postcode (with space)
        if len(postcode_clean) == 6:
            return f"{postcode_clean[:3]} {postcode_clean[3:]}"
        elif len(postcode_clean) == 7:
            return f"{postcode_clean[:4]} {postcode_clean[4:]}"
        else:
            return postcode.upper()


class CommunityGuidelinesForm(forms.Form):
    """
    Form for accepting community guidelines.
    Required for all users to complete onboarding.
    """
    
    accept_guidelines = forms.BooleanField(
        required=True,
        label="I accept the community guidelines",
        help_text="You must accept our community guidelines to use this service",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input form-check-input-lg'}),
        error_messages={
            'required': 'You must accept the community guidelines to continue',
        }
    )
    
    def clean_accept_guidelines(self):
        """Ensure guidelines are accepted"""
        accepted = self.cleaned_data.get('accept_guidelines')
        
        if not accepted:
            raise forms.ValidationError(
                "You must accept the community guidelines to use this service"
            )
        
        return accepted

