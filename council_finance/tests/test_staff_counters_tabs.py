from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from council_finance.models import TrustTier


class ManagementCounterPagesTests(TestCase):
    def setUp(self):
        self.tier4, _ = TrustTier.objects.get_or_create(level=4, defaults={"name": "Manager"})
        self.user = get_user_model().objects.create_user(
            username="manager", email="manager@example.com", password="secret"
        )
        self.user.profile.tier = self.tier4
        self.user.profile.save()

    def test_site_counter_pages(self):
        self.client.login(username="manager", password="secret")
        resp = self.client.get(reverse("site_counter_list"))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("site_counter_add"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"name=\"explanation\"", resp.content)

    def test_group_counter_pages(self):
        self.client.login(username="manager", password="secret")
        resp = self.client.get(reverse("group_counter_list"))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("group_counter_add"))
        self.assertEqual(resp.status_code, 200)
