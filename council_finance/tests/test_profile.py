from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from council_finance.models import UserProfile


class ProfileViewTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="alice", email="alice@example.com", password="secret"
        )
        # Ensure the profile exists via signal
        self.profile = UserProfile.objects.get(user=self.user)

    def test_profile_view_requires_login(self):
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 302)

    def test_profile_view_shows_name(self):
        self.client.login(username="alice", password="secret")
        response = self.client.get(reverse("profile"))
        self.assertContains(response, "alice@example.com")
