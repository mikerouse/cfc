from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from council_finance.models import Notification
from council_finance.notifications import create_notification


class NotificationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="notify", email="notify@example.com", password="pass123"
        )

    def test_create_notification_helper(self):
        create_notification(self.user, "Hello")
        self.assertTrue(Notification.objects.filter(user=self.user, message="Hello").exists())

    def test_notification_view_requires_login(self):
        response = self.client.get(reverse("notifications"))
        self.assertEqual(response.status_code, 302)
        self.client.login(username="notify", password="pass123")
        response = self.client.get(reverse("notifications"))
        self.assertEqual(response.status_code, 200)

    def test_dismiss_notification(self):
        note = Notification.objects.create(user=self.user, message="hi")
        self.client.login(username="notify", password="pass123")
        self.client.get(reverse("dismiss_notification", args=[note.id]))
        note.refresh_from_db()
        self.assertTrue(note.read)

    def test_html_message_rendered(self):
        """Notifications with HTML should be rendered unescaped in the menu."""
        Notification.objects.create(
            user=self.user,
            message="Test <a href='/foo'>link</a>"
        )
        self.client.login(username="notify", password="pass123")
        resp = self.client.get(reverse("home"))
        self.assertContains(resp, "<a href='/foo'>link</a>", html=True)

