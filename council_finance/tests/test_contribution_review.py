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
        self.field = DataField.objects.create(name="Website", slug="website")
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
        self.assertEqual(self.user.profile.points, 2)
        self.assertTrue(Notification.objects.filter(user=self.user, message__contains="accepted").exists())
        self.assertEqual(DataChangeLog.objects.count(), 1)

    def test_edit_then_approve_one_point(self):
        self.client.post(
            reverse("review_contribution", args=[self.contrib.id, "edit"]),
            {"value": "http://new.com"}
        )
        self.client.post(
            reverse("review_contribution", args=[self.contrib.id, "approve"]),
            {}
        )
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.points, 1)

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
