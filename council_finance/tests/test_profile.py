from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
import django
django.setup()

from unittest.mock import patch

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

    def test_email_warning_shown_if_not_confirmed(self):
        self.client.login(username="alice", password="secret")
        response = self.client.get(reverse("profile"))
        self.assertContains(response, "email-warning")

class SignUpTest(TestCase):
    def test_signup_requires_postcode(self):
        with patch("council_finance.emails.send_email"):
            response = self.client.post(
                reverse("signup"),
                {
                    "username": "bob",
                    "password1": "Secr3tpass",
                    "password2": "Secr3tpass",
                    "email": "bob@example.com",
                    # postcode missing on purpose
                },
            )
        self.assertContains(response, "This field is required", status_code=200)

    def test_signup_creates_profile(self):
        with patch("council_finance.emails.send_email"):
            response = self.client.post(
                reverse("signup"),
                {
                    "username": "bob",
                    "password1": "Secr3tpass",
                    "password2": "Secr3tpass",
                    "email": "bob@example.com",
                    "postcode": "ZZ9 9ZZ",
                },
            )
        self.assertEqual(response.status_code, 302)
        user = get_user_model().objects.get(username="bob")
        self.assertEqual(user.profile.postcode, "ZZ9 9ZZ")

    def test_signup_sends_confirmation_email(self):
        with patch("council_finance.emails.send_email") as mock_send:
            self.client.post(
                reverse("signup"),
                {
                    "username": "carol",
                    "password1": "Secr3tpass",
                    "password2": "Secr3tpass",
                    "email": "carol@example.com",
                    "postcode": "AA1 1AA",
                },
            )
            user = get_user_model().objects.get(username="carol")
            self.assertTrue(user.profile.confirmation_token)
            self.assertEqual(mock_send.call_count, 1)


class EmailConfirmationTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="dave", email="dave@example.com", password="secret"
        )
        self.profile = self.user.profile
        self.profile.confirmation_token = "token123"
        self.profile.save()

    def test_confirm_email(self):
        url = reverse("confirm_email", args=["token123"])
        self.client.get(url)
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.email_confirmed)
        self.assertEqual(self.profile.confirmation_token, "")

    def test_resend_confirmation(self):
        self.client.login(username="dave", password="secret")
        with patch("council_finance.emails.send_email") as mock_send:
            self.client.get(reverse("resend_confirmation"))
            self.assertEqual(mock_send.call_count, 1)

    def test_resend_confirmation_handles_api_error(self):
        """If Brevo raises an ApiException, the user sees an error message."""
        self.client.login(username="dave", password="secret")
        from brevo_python.rest import ApiException
        with patch("council_finance.views.send_confirmation_email") as mock_send:
            class Resp:
                status = 400
                reason = "Bad Request"
                data = '{"message": "invalid"}'

                @staticmethod
                def getheaders():
                    return {}

            mock_send.side_effect = ApiException(http_resp=Resp())
            response = self.client.get(
                reverse("resend_confirmation"), follow=True
            )
        messages = list(response.context["messages"])
        self.assertTrue(
            any("Email not sent: invalid" in str(m) for m in messages)
        )
