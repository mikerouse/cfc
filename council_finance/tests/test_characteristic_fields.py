from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from council_finance.models import DataField

class CharacteristicFieldTests(TestCase):
    def test_protected_slug_sets_category(self):
        field, _ = DataField.objects.get_or_create(
            slug="council_website", defaults={"name": "Website"}
        )
        self.assertEqual(field.category, "characteristic")

class CharacteristicTabTests(TestCase):
    def setUp(self):
        self.superuser = get_user_model().objects.create_superuser(
            username="admin", email="a@example.com", password="pw"
        )
        DataField.objects.create(name="Headquarters", slug="council_location")

    def test_tab_visible_in_manager(self):
        self.client.login(username="admin", password="pw")
        resp = self.client.get(reverse("field_list"))
        self.assertContains(resp, "Characteristics")
