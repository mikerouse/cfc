from django.test import TestCase
import os
from unittest.mock import patch, MagicMock

from brevo_python.rest import ApiException
from council_finance.emails import send_email


class SendEmailTest(TestCase):
    def test_send_email_propagates_api_exception(self):
        os.environ["BREVO_API_KEY"] = "dummy"
        with patch("council_finance.emails.TransactionalEmailsApi") as mock_api:
            instance = mock_api.return_value
            instance.send_transac_email.side_effect = ApiException(status=400)
            with self.assertRaises(ApiException):
                send_email("subject", "message", "test@example.com")
            self.assertEqual(instance.send_transac_email.call_count, 1)

    def test_default_sender_address(self):
        os.environ["BREVO_API_KEY"] = "dummy"
        with patch("council_finance.emails.TransactionalEmailsApi") as mock_api:
            instance = mock_api.return_value
            send_email("subject", "message", "test@example.com")
            email_obj = instance.send_transac_email.call_args[0][0]
            self.assertEqual(email_obj.sender["email"], "counters@mikerouse.co.uk")
