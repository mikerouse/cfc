from django.test import TestCase
from django.contrib.auth import get_user_model

class ProfileCompletionTest(TestCase):
    def test_completion_percent(self):
        user = get_user_model().objects.create_user(
            username="prog", email="p@example.com", password="pw"
        )
        profile = user.profile
        # initially nothing provided so progress is 0
        self.assertEqual(profile.completion_percent(), 0)
        # add postcode and affiliation
        profile.postcode = "AA1 1AA"
        profile.political_affiliation = "Party"
        profile.save()
        self.assertEqual(profile.completion_percent(), 50)
