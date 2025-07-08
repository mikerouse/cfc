from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from council_finance.models import Factoid, TrustTier


class FactoidDeleteTests(TestCase):
    """Ensure factoids can be removed only by God Mode users."""

    def setUp(self):
        self.factoid = Factoid.objects.create(
            name="Example", slug="example", factoid_type="highest", text="t"
        )
        # Superuser bypasses tier restriction
        self.superuser = get_user_model().objects.create_superuser(
            username="boss", email="boss@example.com", password="secret"
        )
        # Manager at tier 4 should not have delete access
        tier4, _ = TrustTier.objects.get_or_create(level=4, defaults={"name": "Manager"})
        self.manager = get_user_model().objects.create_user(
            username="mgr", email="mgr@example.com", password="pass"
        )
        self.manager.profile.tier = tier4
        self.manager.profile.save()

    def test_superuser_can_delete_factoid(self):
        self.client.login(username="boss", password="secret")
        self.client.get(reverse("factoid_delete", args=[self.factoid.slug]))
        self.assertFalse(Factoid.objects.filter(pk=self.factoid.pk).exists())

    def test_manager_cannot_delete_factoid(self):
        self.client.login(username="mgr", password="pass")
        resp = self.client.get(reverse("factoid_delete", args=[self.factoid.slug]))
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(Factoid.objects.filter(pk=self.factoid.pk).exists())
