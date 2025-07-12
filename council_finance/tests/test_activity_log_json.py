from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from council_finance.models import ActivityLog

class ActivityLogJsonTests(TestCase):
    def setUp(self):
        self.superuser = get_user_model().objects.create_superuser(
            username="boss", email="boss@example.com", password="secret"
        )
        self.client.login(username="boss", password="secret")
        ActivityLog.objects.create(
            user=self.superuser,
            page="/test",
            activity="unit_test",
            log_type="user",
            action="do",
            request="POST",
            response="ok",
            extra=""
        )

    def test_json_field_in_api(self):
        resp = self.client.get(reverse("activity_log_entries"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["results"][0]
        self.assertIn("json", data)
        import json
        obj = json.loads(data["json"])
        self.assertEqual(obj["activity"], "unit_test")
