from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
import json

from council_finance.models import Council
from council_finance.models import DataField


class AdminImportTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="pass"
        )

    def test_import_flow_creates_council(self):
        self.client.login(username="admin", password="pass")

        DataField.objects.get_or_create(slug="total_debt", defaults={"name": "Total Debt"})

        data = {
            "fields": [{"name": "total_debt"}],
            "councils": [
                {
                    "slug": "test",
                    "name": "Test",
                    "council_type": "Unitary",
                    "values": {"total_debt": {"2024": "1"}},
                }
            ],
        }
        file = SimpleUploadedFile(
            "c.json",
            json.dumps(data).encode("utf-8"),
            content_type="application/json",
        )

        url = reverse("admin:council_finance_council_import")
        # Step 1: upload
        response = self.client.post(url, {"step": "upload", "json_file": file})
        self.assertContains(response, "Map Fields")

        # Step 2: mapping
        response = self.client.post(url, {"step": "map", "total_debt": "total_debt"})
        self.assertContains(response, "Importing Councils")

        # Step 3: run progress until complete
        progress_url = reverse("admin:council_finance_council_import_progress")
        progress = self.client.get(progress_url).json()
        self.assertFalse(progress["complete"])  # first item processed
        progress = self.client.get(progress_url).json()
        self.assertTrue(progress["complete"])  # finished

        council = Council.objects.get(slug="test")
        self.assertEqual(council.council_type.name, "Unitary")


