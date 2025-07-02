from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.core.management import call_command
import django
django.setup()

from council_finance.models import CouncilList

class MyListsTests(TestCase):
    def setUp(self):
        call_command('runagent', 'ImporterAgent', '--source', 'councils-migration.json')
        self.user = get_user_model().objects.create_user(
            username='eve', email='eve@example.com', password='secret')
        # add a favourite
        council = self._get_council()
        self.user.profile.favourites.add(council)

    def _get_council(self):
        from council_finance.models import Council
        return Council.objects.first()

    def test_favourites_displayed(self):
        self.client.login(username='eve', password='secret')
        response = self.client.get(reverse('my_lists'))
        self.assertContains(response, self._get_council().name)

    def test_create_list_and_add_favourite(self):
        self.client.login(username='eve', password='secret')
        # create list
        response = self.client.post(reverse('my_lists'), {'name': 'Test', 'new_list': ''})
        clist = CouncilList.objects.get(name='Test')
        # add to list
        self.client.post(reverse('my_lists'), {
            'council': self._get_council().slug,
            'list': clist.id,
            'add_to_list': ''
        })
        self.assertTrue(clist.councils.filter(id=self._get_council().id).exists())

