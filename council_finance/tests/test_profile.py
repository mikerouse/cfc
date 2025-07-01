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

    def test_ajax_update_postcode(self):
        self.client.login(username="alice", password="secret")
        response = self.client.post(
            reverse("update_postcode"), {"postcode": "AB1 2CD"}
        )
        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.postcode, "AB1 2CD")


class SignUpTest(TestCase):
    def test_signup_requires_postcode(self):
        response = self.client.post(reverse("signup"), {
            "username": "bob",
            "password1": "Secr3tpass",
            "password2": "Secr3tpass",
            "email": "bob@example.com",
            # postcode missing on purpose
        })
        self.assertContains(response, "This field is required", status_code=200)

    def test_signup_creates_profile(self):
        response = self.client.post(reverse("signup"), {
            "username": "bob",
            "password1": "Secr3tpass",
            "password2": "Secr3tpass",
            "email": "bob@example.com",
            "postcode": "ZZ9 9ZZ",
        })
        self.assertEqual(response.status_code, 302)
        user = get_user_model().objects.get(username="bob")
        self.assertEqual(user.profile.postcode, "ZZ9 9ZZ")
