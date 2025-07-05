from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model


class GodModeAccessTests(TestCase):
    """Ensure the God Mode link and view are accessible to superadmins."""

    def setUp(self):
        # Create a superuser who should bypass the tier restriction
        self.superuser = get_user_model().objects.create_superuser(
            username="boss", email="boss@example.com", password="secret"
        )

    def test_superuser_sees_link(self):
        """The secondary nav should include God Mode for superusers."""
        self.client.login(username="boss", password="secret")
        resp = self.client.get(reverse("home"))
        self.assertContains(resp, reverse("god_mode"))

    def test_superuser_can_access_view(self):
        """The God Mode page itself should load for superusers."""
        self.client.login(username="boss", password="secret")
        resp = self.client.get(reverse("god_mode"))
        self.assertEqual(resp.status_code, 200)
