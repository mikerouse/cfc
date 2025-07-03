from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string

from .models import UserProfile
from .models import CouncilList
from .models import CounterDefinition, DataField
from .models.field import PROTECTED_SLUGS


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
        if not profile.confirmation_token:
            profile.confirmation_token = get_random_string(32)
        if commit:
            profile.save()
        return user


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
    """Edit counter definitions from the staff page."""

    class Meta:
        model = CounterDefinition
        fields = [
            "name",
            "slug",
            "formula",
            "explanation",
            "duration",
            "precision",
            "show_currency",
            "friendly_format",
        ]
        widgets = {
            "explanation": forms.Textarea(attrs={"rows": 2, "class": "border rounded p-1 w-full"}),
            "duration": forms.NumberInput(attrs={"min": 0, "class": "border rounded p-1 w-full"}),
            "precision": forms.NumberInput(attrs={"min": 0, "class": "border rounded p-1 w-full"}),
            "show_currency": forms.CheckboxInput(attrs={"class": "mr-2"}),
            "friendly_format": forms.CheckboxInput(attrs={"class": "mr-2"}),
        }

    def __init__(self, *args, **kwargs):
        """Add Tailwind classes to text inputs for consistency."""
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in ["show_currency", "friendly_format"]:
                continue
            field.widget.attrs.setdefault("class", "border rounded p-1 w-full")



class DataFieldForm(forms.ModelForm):
    """Form for creating and editing data fields."""

    class Meta:
        model = DataField
        fields = [
            "name",
            "slug",
            "category",
            "explanation",
            "content_type",
            "formula",
            "required",
        ]
        widgets = {
            "explanation": forms.Textarea(attrs={"rows": 2, "class": "border rounded p-1 w-full"}),
            "formula": forms.TextInput(attrs={"class": "border rounded p-1 w-full"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Prevent editing the slug of protected fields so staff can't rename
        # important built-in definitions. The value itself can still change.
        if self.instance and self.instance.pk and self.instance.slug in PROTECTED_SLUGS:
            self.fields["slug"].disabled = True
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "mr-2")
            else:
                field.widget.attrs.setdefault("class", "border rounded p-1 w-full")
