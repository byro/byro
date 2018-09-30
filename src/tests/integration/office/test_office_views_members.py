import pytest
from django.urls import reverse

pytestmark = pytest.mark.usefixtures('configuration')


@pytest.mark.django_db
def test_members_list(member, membership, inactive_member, logged_in_client):
    response = logged_in_client.get(reverse('office:members.list'))
    content = response.content.decode()
    assert response.status_code == 200, content
    assert member.name in content
    assert inactive_member.name not in content


@pytest.mark.django_db
def test_filtered_members_list(member, membership, inactive_member, logged_in_client):
    response = logged_in_client.get(
        reverse('office:members.list') + '?filter=all&q=' + member.name[:4]
    )
    content = response.content.decode()
    assert response.status_code == 200, content
    assert member.name in content
    assert inactive_member.name not in content


@pytest.mark.django_db
def test_inactive_members_list(member, membership, inactive_member, logged_in_client):
    response = logged_in_client.get(reverse('office:members.list') + '?filter=inactive')
    content = response.content.decode()
    assert response.status_code == 200, content
    assert member.name not in content
    assert inactive_member.name in content


@pytest.mark.django_db
def test_all_members_list(member, membership, inactive_member, logged_in_client):
    response = logged_in_client.get(reverse('office:members.list') + '?filter=all')
    content = response.content.decode()
    assert response.status_code == 200, content
    assert member.name in content
    assert inactive_member.name in content
