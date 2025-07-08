from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from council_finance.models import Council, CouncilFollow, CouncilUpdate


class FollowingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="tester", email="test@example.com", password="pass123"
        )
        self.council = Council.objects.create(name="Town", slug="town")

    def test_follow_unfollow_api(self):
        self.client.login(username="tester", password="pass123")
        self.client.post(reverse("follow_council", args=["town"]))
        self.assertTrue(CouncilFollow.objects.filter(user=self.user, council=self.council).exists())
        self.client.post(reverse("unfollow_council", args=["town"]))
        self.assertFalse(CouncilFollow.objects.filter(user=self.user, council=self.council).exists())

    def test_following_feed_shows_update(self):
        CouncilUpdate.objects.create(council=self.council, message="New data")
        CouncilFollow.objects.create(user=self.user, council=self.council)
        self.client.login(username="tester", password="pass123")
        resp = self.client.get(reverse("following"))
        self.assertContains(resp, "New data")
