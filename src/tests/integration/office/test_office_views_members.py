import pytest
from dateutil.relativedelta import relativedelta
from django.urls import reverse
from django.utils.timezone import now

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


@pytest.mark.django_db
def test_members_export_list_csv(member, membership, inactive_member, logged_in_client):
    response = logged_in_client.post(
        reverse('office:members.list.export'), {
            'member_filter': 'all',
            'export_format': 'csv',
            'field_list': ['_internal_id', 'member__name'],
        }
    )
    content = b"".join(response.streaming_content).decode()
    assert response.status_code == 200, content
    assert content == "\ufeffInternal database ID,Name\r\n{},{}\r\n{},{}\r\n".format(inactive_member.pk, inactive_member.name, member.pk, member.name)


@pytest.mark.django_db
def test_members_adjust_account_initial(member, logged_in_client):
    assert member.balance == 0
    response = logged_in_client.post(
        reverse('office:members.operations', kwargs={'pk': member.pk}), {
            'member_account_adjustment-date': str(now().date()),
            'member_account_adjustment-adjustment_reason': 'initial',
            'member_account_adjustment-adjustment_type': 'absolute',
            'member_account_adjustment-amount': '23',
            'submit_member_account_adjustment_adjust': 'adjust',
        }
    )
    content = response.content.decode()
    assert response.status_code == 302, content
    assert member.balance == 23


@pytest.mark.django_db
def test_members_adjust_account_waiver(member, logged_in_client):
    assert member.balance == 0
    response = logged_in_client.post(
        reverse('office:members.operations', kwargs={'pk': member.pk}), {
            'member_account_adjustment-date': str(now().date()),
            'member_account_adjustment-adjustment_reason': 'waiver',
            'member_account_adjustment-adjustment_type': 'relative',
            'member_account_adjustment-amount': '-2',
            'submit_member_account_adjustment_adjust': 'adjust',
        }
    )
    content = response.content.decode()
    assert response.status_code == 302, content
    assert member.balance == 2


@pytest.mark.django_db
def test_members_end_membership(member, membership, logged_in_client):
    assert member.is_active
    response = logged_in_client.post(
        reverse('office:members.operations', kwargs={'pk': member.pk}), {
            'ms_{}_leave-end'.format(membership.pk): (now() + relativedelta(days=-1)).date(),
            'submit_ms_{}_leave_end'.format(membership.pk): 'end',
        }
    )
    content = response.content.decode()
    assert response.status_code == 302, content
    assert not member.is_active
