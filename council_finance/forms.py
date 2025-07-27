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
        ]
        widgets = {
            "explanation": forms.Textarea(
                attrs={"rows": 2, "class": "border rounded p-1 w-full"}
            ),
            "formula": forms.TextInput(attrs={"class": "border rounded p-1 w-full"}),
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

