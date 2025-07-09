from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from council_finance.models import (
    TrustTier,
    Notification,
    Contribution,
    Council,
    DataField,
    VerifiedIP,
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
        self.field, _ = DataField.objects.get_or_create(slug="council_website", defaults={"name": "Website"})

    def test_low_tier_pending(self):
        self.client.login(username="contrib", password="pass123")
        response = self.client.post(
            reverse("submit_contribution"),
            {"council": "test", "field": "council_website", "value": "http://a.com"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
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
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.json()["status"], "approved")
        self.assertEqual(Contribution.objects.last().status, "approved")

    def test_history_based_auto_approve(self):
        # Seed profile with enough approved contributions and a verified IP
        self.user.profile.email_confirmed = True
        self.user.profile.approved_submission_count = 3
        self.user.profile.verified_ip_count = 1
        self.user.profile.save()
        VerifiedIP.objects.create(user=self.user, ip_address="1.2.3.4")

        self.client.login(username="contrib", password="pass123")
        resp = self.client.post(
            reverse("submit_contribution"),
            {"council": "test", "field": "council_website", "value": "http://d.com"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(resp.json()["status"], "approved")

    def test_missing_history_no_auto_approve(self):
        """Without a confirmed email or enough history the submission stays pending."""
        self.user.profile.email_confirmed = True
        self.user.profile.approved_submission_count = 1
        self.user.profile.verified_ip_count = 0
        self.user.profile.save()

        self.client.login(username="contrib", password="pass123")
        resp = self.client.post(
            reverse("submit_contribution"),
            {"council": "test", "field": "council_website", "value": "http://e.com"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(resp.json()["status"], "pending")

    def test_standard_post_redirects(self):
        self.client.login(username="contrib", password="pass123")
        resp = self.client.post(
            reverse("submit_contribution"),
            {"council": "test", "field": "council_website", "value": "http://c.com"},
            follow=True,
        )
        msgs = list(resp.context["messages"])
        self.assertTrue(any("queued" in str(m) for m in msgs))
        self.assertContains(resp, "Website pending confirmation")


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

    def test_missing_data_section_shows(self):
        from council_finance.models import DataIssue

        DataIssue.objects.create(council=self.council, field=self.field, issue_type="missing")
        resp = self.client.get(reverse("contribute"))
        self.assertContains(resp, "Missing Financial Data")
        self.assertContains(resp, self.council.name)

    def test_characteristics_separate_table(self):
        from council_finance.models import DataIssue

        char_field = DataField.objects.create(name="HQ", slug="council_location", category="characteristic")
        DataIssue.objects.create(council=self.council, field=char_field, issue_type="missing")

        resp = self.client.get(reverse("contribute"))
        self.assertContains(resp, "Missing Characteristics")
        self.assertContains(resp, "HQ")


class SubmissionPointTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="spoints", email="s@example.com", password="pw"
        )
        self.council = Council.objects.create(name="Points", slug="points")
        self.field, _ = DataField.objects.get_or_create(slug="council_website", defaults={"name": "Website"})
        self.client.login(username="spoints", password="pw")

    def submit(self):
        return self.client.post(
            reverse("submit_contribution"),
            {"council": "points", "field": "council_website", "value": "http://x.com"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

    def test_points_awarded_once_per_period(self):
        self.submit()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.points, 2)

        c = Contribution.objects.latest("id")
        from django.utils import timezone
        from datetime import timedelta
        c.created = timezone.now() - timedelta(days=1)
        c.save()

        self.submit()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.points, 2)

        # Move both contributions outside the 3 week window
        Contribution.objects.all().update(created=timezone.now() - timedelta(days=22))
        self.submit()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.points, 4)


class CharacteristicPointsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="charpoints", email="c@example.com", password="pw"
        )
        self.council = Council.objects.create(name="Char", slug="char")
        self.field = DataField.objects.create(name="HQ", slug="council_location", category="characteristic")
        self.client.login(username="charpoints", password="pw")

    def test_extra_points_for_characteristics(self):
        self.client.post(
            reverse("submit_contribution"),
            {"council": "char", "field": "council_location", "value": "Town Hall"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.points, 2)
