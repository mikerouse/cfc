from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from .models import UserProfile
from .models import CouncilList, Council
from .models import CounterDefinition, DataField
from .models.site_counter import SiteCounter, GroupCounter
from .models.field import PROTECTED_SLUGS
from django.contrib.contenttypes.models import ContentType


class SignUpForm(UserCreationForm):
    """Extend the built-in user creation form with a required postcode."""

    postcode = forms.CharField(max_length=20, help_text="Required")

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "email")  # Password fields provided by parent

    def save(self, commit=True):
        user = super().save(commit)
        postcode = self.cleaned_data["postcode"]
        # Ensure the profile exists (signal may have created it already)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.postcode = postcode
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


# Simple upload form used by the Django admin to accept a JSON file.
# The file is expected to match the structure exported by the
# WordPress plugin (see `councils-migration.json`).
class CouncilImportForm(forms.Form):
    # Django handles temporary storage of uploaded files automatically.
    # We only need the file object which will be read directly in the view.
    json_file = forms.FileField(
        help_text="Upload a JSON export containing councils and figures."
    )


class CouncilImportMappingForm(forms.Form):
    """Allow admins to map JSON fields to internal figure names."""

    def __init__(self, *args, available_fields=None, **kwargs):
        # ``available_fields`` is a list of field names present in the uploaded
        # JSON file. We dynamically create a ChoiceField for each so the admin
        # can specify how it maps to our internal field names.
        super().__init__(*args, **kwargs)
        if available_fields:
            field_choices = [(f.slug, f.slug) for f in DataField.objects.all()]
            for field in available_fields:
                self.fields[field] = forms.ChoiceField(
                    label=f"Map '{field}' to",
                    choices=[("", "-- ignore --")] + field_choices,
                    required=False,
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
            ),
            "show_currency": forms.CheckboxInput(attrs={"class": "mr-2"}),
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
        # Prevent editing the slug of protected fields so managers can't rename
        # important built-in definitions. The value itself can still change.
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

