from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from council_finance.models import (
    TrustTier,
    Notification,
    Contribution,
    Council,
    DataField,
)

class TierNotificationTests(TestCase):
    def setUp(self):
        self.tier1, _ = TrustTier.objects.get_or_create(level=1, name="New Counter")
        self.tier3, _ = TrustTier.objects.get_or_create(level=3, name="Approved Counter")
        self.user = get_user_model().objects.create_user(
            username="vol", email="vol@example.com", password="pass123"
        )

    def test_default_tier_assigned(self):
        self.assertEqual(self.user.profile.tier.level, 1)

    def test_notification_on_tier_change(self):
        self.user.profile.tier = self.tier3
        self.user.profile.save()
        self.assertTrue(
            Notification.objects.filter(user=self.user, message__contains="trust tier").exists()
        )

class ContributionApprovalTests(TestCase):
    def setUp(self):
        self.tier1, _ = TrustTier.objects.get_or_create(level=1, name="New Counter")
        self.tier3, _ = TrustTier.objects.get_or_create(level=3, name="Approved Counter")
        self.user = get_user_model().objects.create_user(
            username="contrib", email="c@example.com", password="pass123"
        )
        self.council = Council.objects.create(name="Test", slug="test")
        self.field = DataField.objects.create(name="Website", slug="council_website")

    def test_low_tier_pending(self):
        self.client.login(username="contrib", password="pass123")
        response = self.client.post(
            reverse("submit_contribution"),
            {"council": "test", "field": "council_website", "value": "http://a.com"},
        )
        self.assertEqual(response.json()["status"], "pending")
        self.assertEqual(Contribution.objects.first().status, "pending")

    def test_high_tier_auto_approved(self):
        self.user.profile.tier = self.tier3
        self.user.profile.save()
        self.client.login(username="contrib", password="pass123")
        response = self.client.post(
            reverse("submit_contribution"),
            {"council": "test", "field": "council_website", "value": "http://b.com"},
        )
        self.assertEqual(response.json()["status"], "approved")
        self.assertEqual(Contribution.objects.last().status, "approved")


class EditTabTests(TestCase):
    def setUp(self):
        self.council = Council.objects.create(name="EditTown", slug="edittown")

    def test_edit_message_shown(self):
        resp = self.client.get(reverse("council_detail", args=["edittown"]), {"tab": "edit"})
        self.assertContains(resp, "contribute to our dataset")


class ContributeQueueTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="quser", email="q@example.com", password="pw"
        )
        self.council = Council.objects.create(name="Queue", slug="queue")
        self.field = DataField.objects.filter(slug="council_website").first()
        if not self.field:
            self.field = DataField.objects.create(name="Website", slug="council_website")
        from council_finance.models.council_type import CouncilType
        from django.contrib.contenttypes.models import ContentType
        self.ct_field = DataField.objects.filter(slug="council_type").first()
        if not self.ct_field:
            self.ct_field = DataField.objects.create(
                name="Type",
                slug="council_type",
                content_type="list",
                dataset_type=ContentType.objects.get_for_model(CouncilType),
            )
        self.ct, _ = CouncilType.objects.get_or_create(name="County")
        Contribution.objects.create(
            user=self.user,
            council=self.council,
            field=self.field,
            value="http://q.com",
        )
        Contribution.objects.create(
            user=self.user,
            council=self.council,
            field=self.ct_field,
            value=str(self.ct.id),
        )

    def test_queue_table_renders(self):
        resp = self.client.get(reverse("contribute"))
        self.assertContains(resp, "Queue")

    def test_queue_displays_human_value(self):
        resp = self.client.get(reverse("contribute"))
        self.assertContains(resp, "http://q.com")

    def test_list_value_rendered(self):
        resp = self.client.get(reverse("contribute"))
        self.assertContains(resp, "County")