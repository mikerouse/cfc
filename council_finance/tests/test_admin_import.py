from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
import json

from council_finance.models import Council


class AdminImportTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="pass"
        )

    def test_import_view_creates_councils(self):
        self.client.login(username="admin", password="pass")
        data = {
            "councils": [
                {"slug": "test", "name": "Test Council", "values": {}}
            ]
        }
        file = SimpleUploadedFile(
            "councils.json",
            json.dumps(data).encode("utf-8"),
            content_type="application/json",
        )
        url = reverse("admin:council_finance_council_import")
        response = self.client.post(url, {"json_file": file})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Council.objects.filter(slug="test").exists())


