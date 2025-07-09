from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
# django.setup() is handled by pytest-django when tests run

from council_finance.models import UserProfile


class LeaderboardTests(TestCase):
    def setUp(self):
        User = get_user_model()
        # Create two users with differing point totals so ordering can be
        # asserted in the view test below.
        self.alice = User.objects.create_user(
            username="alice", email="a@example.com", password="pw"
        )
        self.alice.profile.points = 60
        self.alice.profile.save()

        self.bob = User.objects.create_user(
            username="bob", email="b@example.com", password="pw"
        )
        self.bob.profile.points = 5
        self.bob.profile.save()

    def test_badge_and_level(self):
        profile = self.alice.profile
        # 60 points should place the user at level 4 with an "Expert" badge.
        self.assertEqual(profile.level(), 4)
        self.assertEqual(profile.badge(), "Expert")

    def test_leaderboard_view_orders_by_points(self):
        from django.test.utils import override_settings

        with override_settings(ALLOWED_HOSTS=["testserver"]):
            resp = self.client.get(reverse("leaderboards"))
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        # Alice should appear before Bob in the rendered HTML
        self.assertLess(body.index("alice"), body.index("bob"))
