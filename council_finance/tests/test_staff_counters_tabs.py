from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model


class StaffCounterPagesTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="staff", email="staff@example.com", password="secret", is_staff=True
        )

    def test_site_counter_pages(self):
        self.client.login(username="staff", password="secret")
        resp = self.client.get(reverse("site_counter_list"))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("site_counter_add"))
        self.assertEqual(resp.status_code, 200)

    def test_group_counter_pages(self):
        self.client.login(username="staff", password="secret")
        resp = self.client.get(reverse("group_counter_list"))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("group_counter_add"))
        self.assertEqual(resp.status_code, 200)
