from django.test import TestCase, RequestFactory
from django.template import Context
from django.contrib.auth import get_user_model
from django.db.utils import OperationalError
from unittest.mock import patch

from council_finance.templatetags.extras import get_item
from council_finance.templatetags.notifications import (
    unread_count,
    recent_notifications,
    profile_progress,
)
from council_finance.models import Notification


class ExtrasTagTests(TestCase):
    def test_get_item(self):
        self.assertEqual(get_item({"a": 1}, "a"), 1)
        self.assertIsNone(get_item("foo", "a"))


class NotificationTagTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_user(
            username="note", email="n@example.com", password="pw"
        )

    def _context(self):
        request = self.factory.get("/")
        return Context({"user": self.user, "request": request})

    def test_unread_count(self):
        Notification.objects.create(user=self.user, message="hi")
        Notification.objects.create(user=self.user, message="bye", read=True)
        ctx = self._context()
        self.assertEqual(unread_count(ctx), 1)

    def test_unread_count_missing_table(self):
        with patch.object(self.user.notifications, "filter", side_effect=OperationalError):
            ctx = self._context()
            self.assertEqual(unread_count(ctx), 0)

    def test_recent_notifications_limited(self):
        n1 = Notification.objects.create(user=self.user, message="1")
        n2 = Notification.objects.create(user=self.user, message="2")
        n3 = Notification.objects.create(user=self.user, message="3")
        ctx = self._context()
        notes = recent_notifications(ctx, limit=2)
        self.assertEqual(notes[0], n3)
        self.assertEqual(notes[1], n2)

    def test_recent_notifications_missing_table(self):
        # Patch QuerySet.order_by to simulate a missing table error
        with patch("django.db.models.query.QuerySet.order_by", side_effect=OperationalError):
            ctx = self._context()
            self.assertEqual(recent_notifications(ctx), [])

    def test_profile_progress(self):
        self.user.profile.postcode = "AA1 1AA"
        self.user.profile.political_affiliation = "Party"
        self.user.profile.save()
        ctx = self._context()
        self.assertGreater(profile_progress(ctx), 0)

    def test_profile_progress_missing_table(self):
        with patch.object(self.user.profile, "completion_percent", side_effect=OperationalError):
            ctx = self._context()
            self.assertEqual(profile_progress(ctx), 0)
