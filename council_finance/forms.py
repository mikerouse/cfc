from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string

from .models import UserProfile


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


# Available internal fields that council figures can map to. This keeps
# the mapping logic explicit and future-proof.
INTERNAL_FIELDS = [
    "population",
    "elected_members",
    "total_debt",
    "band_d_properties",
    "current_liabilities",
    "long_term_liabilities",
    "counter_start_date",
    "households",
]


class CouncilImportMappingForm(forms.Form):
    """Allow admins to map JSON fields to internal figure names."""

    def __init__(self, *args, available_fields=None, **kwargs):
        # ``available_fields`` is a list of field names present in the uploaded
        # JSON file. We dynamically create a ChoiceField for each so the admin
        # can specify how it maps to our internal field names.
        super().__init__(*args, **kwargs)
        if available_fields:
            choices = [(f, f) for f in INTERNAL_FIELDS]
            for field in available_fields:
                self.fields[field] = forms.ChoiceField(
                    label=f"Map '{field}' to",
                    choices=[("", "-- ignore --")] + choices,
                    required=False,
                )

