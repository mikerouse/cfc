from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from council_finance.models import (
    TrustTier,
    Council,
    DataField,
    Contribution,
    DataChangeLog,
    Notification,
    RejectionLog,
    BlockedIP,
)

class ContributionReviewTests(TestCase):
    def setUp(self):
        self.tier3 = TrustTier.objects.get(level=3)
        self.mod = get_user_model().objects.create_user(
            username="mod", email="mod@example.com", password="pw"
        )
        self.mod.profile.tier = self.tier3
        self.mod.profile.save()
        self.user = get_user_model().objects.create_user(
            username="contrib", email="c@example.com", password="pw"
        )
        self.council = Council.objects.create(name="Test", slug="test")
        self.field, _ = DataField.objects.get_or_create(slug="council_website", defaults={"name": "Website"})
        self.contrib = Contribution.objects.create(
            user=self.user,
            council=self.council,
            field=self.field,
            value="http://example.com",
        )
        self.client.login(username="mod", password="pw")

    def test_approve_awards_points(self):
        self.client.post(
            reverse("review_contribution", args=[self.contrib.id, "approve"]),
            {}
        )
        self.contrib.refresh_from_db()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.contrib.status, "approved")
        self.assertEqual(self.user.profile.points, 3)
        note = Notification.objects.latest("id")
        self.assertIn(self.council.name, note.message)
        self.assertIn(self.field.name, note.message)
        self.assertIn("3 points", note.message)
        self.assertEqual(DataChangeLog.objects.count(), 1)

    def test_edit_then_approve_two_points(self):
        self.client.post(
            reverse("review_contribution", args=[self.contrib.id, "edit"]),
            {"value": "http://new.com"}
        )
        self.client.post(
            reverse("review_contribution", args=[self.contrib.id, "approve"]),
            {}
        )
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.points, 3)

    def test_reject_creates_log(self):
        self.client.post(
            reverse("review_contribution", args=[self.contrib.id, "reject"]),
            {"reason": "data_incorrect"}
        )
        self.contrib.refresh_from_db()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.contrib.status, "rejected")
        self.assertEqual(self.user.profile.rejection_count, 1)
        self.assertEqual(RejectionLog.objects.count(), 1)

    def test_reject_log_records_ip(self):
        self.contrib.ip_address = "1.1.1.1"
        self.contrib.save()
        self.client.post(
            reverse("review_contribution", args=[self.contrib.id, "reject"]),
            {"reason": "no_sources"},
        )
        log = RejectionLog.objects.latest("id")
        self.assertEqual(log.ip_address, "1.1.1.1")

    def test_blocked_ip_prevents_submission(self):
        BlockedIP.objects.create(ip_address="2.2.2.2")
        self.client.login(username="contrib", password="pw")
        resp = self.client.post(
            reverse("submit_contribution"),
            {
                "council": self.council.slug,
                "field": self.field.slug,
                "value": "http://foo",
            },
            REMOTE_ADDR="2.2.2.2",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(resp.status_code, 403)

    def test_invalid_field_returns_error(self):
        """Submitting with a non-existent field should return a 400 JSON error."""
        self.client.login(username="contrib", password="pw")
        resp = self.client.post(
            reverse("submit_contribution"),
            {
                "council": self.council.slug,
                "field": "does-not-exist",
                "value": "foo",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"], "invalid_field")
        log = RejectionLog.objects.latest("id")
        self.assertEqual(log.reason, "invalid_field")
        self.assertIsNone(log.field)
        self.assertIn("does-not-exist", log.value)

    def test_delete_requires_god_mode(self):
        """Tier 3 moderators should not be allowed to delete."""
        resp = self.client.post(
            reverse("review_contribution", args=[self.contrib.id, "delete"]),
            {},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(Contribution.objects.filter(pk=self.contrib.id).exists())

    def test_superuser_can_delete(self):
        boss = get_user_model().objects.create_superuser(
            username="boss", email="boss@example.com", password="pw"
        )
        self.client.login(username="boss", password="pw")
        self.client.post(
            reverse("review_contribution", args=[self.contrib.id, "delete"]),
            {},
        )
        self.assertFalse(Contribution.objects.filter(pk=self.contrib.id).exists())
