from django.core.exceptions import ValidationError
from django.test import TestCase

from council_finance.forms import DataFieldForm, FactoidForm
from council_finance.models import DataField, CouncilType


class FactoidFormTests(TestCase):
    """Tests for the FactoidForm behaviour."""

    def test_slug_is_generated_when_blank(self):
        """Saving without a slug should generate one automatically."""
        form = FactoidForm(
            data={
                "name": "Amazing Fact",
                "slug": "",
                "factoid_type": "highest",
                "text": "Highest value is {name}",
            }
        )
        self.assertTrue(form.is_valid())
        factoid = form.save()
        self.assertEqual(factoid.slug, "amazing-fact")


class DataFieldFormTests(TestCase):
    """Behaviour specific to DataFieldForm."""

    def setUp(self):
        # Use unique names so default fixtures don't clash with our tests.
        self.ct1 = CouncilType.objects.create(name="Demo District")
        self.ct2 = CouncilType.objects.create(name="Demo County")

    def _base_data(self):
        return {
            "name": "Website",
            "category": "characteristic",
            "explanation": "",
            "content_type": "text",
            "dataset_type": "",
            "council_types": [],
            "formula": "",
            "required": False,
        }

    def test_protected_slug_cannot_be_changed_or_deleted(self):
        """Protected slugs should remain immutable and undeletable."""
        field, _ = DataField.objects.get_or_create(
            slug="council_website",
            defaults={"name": "Website", "category": "characteristic"},
        )
        # Attempt to change the slug via the instance
        field.slug = "new-slug"
        form = DataFieldForm(data=self._base_data(), instance=field)
        self.assertTrue(form.is_valid())
        with self.assertRaises(ValidationError):
            form.save()
        reloaded = DataField.objects.get(pk=field.pk)
        self.assertEqual(reloaded.slug, "council_website")
        with self.assertRaises(ValidationError):
            reloaded.delete()

    def test_council_types_queryset_contains_all_types(self):
        """Form should list all CouncilType objects."""
        form = DataFieldForm()
        qs = form.fields["council_types"].queryset
        self.assertIn(self.ct1, qs)
        self.assertIn(self.ct2, qs)

    def test_valid_form_saves_instance(self):
        """A fully populated form should persist a new DataField."""
        data = self._base_data()
        data.update({"name": "Employees", "category": "general", "content_type": "integer", "council_types": [self.ct1.pk]})
        form = DataFieldForm(data=data)
        self.assertTrue(form.is_valid())
        field = form.save()
        self.assertIsInstance(field, DataField)
        self.assertTrue(DataField.objects.filter(slug=field.slug).exists())
        self.assertIn(self.ct1, field.council_types.all())
