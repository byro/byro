import pytest
from django.shortcuts import reverse


@pytest.mark.parametrize('url', (
    'settings.base',
    'settings.registration',
    'dashboard',
    'members.typeahead',
    'members.list',
    'members.add',
    #'finance.transactions.list', ## FIXME
    'finance.uploads.list',
    'finance.uploads.add',
    'finance.accounts.list',
    'finance.accounts.add',
    'mails.sent',
    'mails.outbox.list',
    'mails.outbox.send',
    'mails.outbox.purge',
    'mails.templates.list',
))
@pytest.mark.parametrize('logged_in', (True, False))
@pytest.mark.django_db
def test_office_access_urls(client, user, url, logged_in):
    if logged_in:
        client.force_login(user)

    response = client.get(reverse('office:{}'.format(url)), follow=True)
    assert response.status_code == 200
    assert (response.resolver_match.url_name == 'login') is not logged_in
