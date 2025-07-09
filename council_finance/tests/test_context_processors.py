from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware

from council_finance.context_processors import compare_count, font_family


def add_session(request):
    """Attach a session to the request for testing."""
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    request.session.save()


class ContextProcessorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_compare_count_from_session(self):
        request = self.factory.get("/")
        add_session(request)
        request.session["compare_basket"] = ["a", "b", "c"]
        request.user = AnonymousUser()

        context = compare_count(request)
        self.assertEqual(context["compare_count"], 3)

    def test_compare_count_default_zero(self):
        request = self.factory.get("/")
        add_session(request)
        request.user = AnonymousUser()

        context = compare_count(request)
        self.assertEqual(context["compare_count"], 0)

    def test_font_family_from_profile(self):
        user = get_user_model().objects.create_user(
            username="font", email="f@example.com", password="pw"
        )
        user.profile.preferred_font = "Roboto"
        user.profile.save()
        request = self.factory.get("/")
        add_session(request)
        request.user = user

        context = font_family(request)
        self.assertEqual(context["font_family"], "Roboto")

    def test_font_family_default(self):
        request = self.factory.get("/")
        add_session(request)
        request.user = AnonymousUser()

        self.assertEqual(font_family(request)["font_family"], "Cairo")
