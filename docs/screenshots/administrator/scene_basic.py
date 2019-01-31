import pytest

from utils import screenshot


@pytest.mark.django_db
def shot_login(client):
    client.go_to('common:login')
    screenshot(client, 'common_login.png')


@pytest.mark.django_db
def shot_dashboard(logged_in_client, full_testdata):
    logged_in_client.go_to('office:dashboard')
    screenshot(logged_in_client, 'office_dashboard.png')


@pytest.mark.django_db
def shot_member_list(logged_in_client, full_testdata):
    logged_in_client.go_to('office:members.list')
    screenshot(logged_in_client, 'office_members_list.png')


@pytest.mark.django_db
def shot_settings_base(logged_in_client, full_testdata):
    logged_in_client.go_to('office:settings.base')
    screenshot(logged_in_client, 'office_settings_base.png')
