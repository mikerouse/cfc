from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from council_finance.models import Council, CouncilList

class CompareTests(TestCase):
    def setUp(self):
        self.council = Council.objects.create(name="Town", slug="town")
        self.user = get_user_model().objects.create_user(
            username="bob", email="bob@example.com", password="secret"
        )

    def test_add_to_compare_session(self):
        self.client.post(reverse("add_to_compare", args=["town"]))
        session = self.client.session
        self.assertIn("town", session.get("compare_basket", []))

    def test_save_basket_as_list(self):
        self.client.post(reverse("add_to_compare", args=["town"]))
        self.client.login(username="bob", password="secret")
        self.client.post(reverse("compare_basket"), {"save_list": "1", "name": "Mine"})
        self.assertTrue(CouncilList.objects.filter(name="Mine", user=self.user).exists())

