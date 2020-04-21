import pytest
from byro.plugins.sepa.signals import (
    leave_member_office_mail_info_sepa,
    new_member_mail_info_sepa,
    new_member_office_mail_info_sepa,
)


@pytest.mark.django_db
def test_new_member_info_sepa(member_with_sepa_profile):
    assert str(new_member_mail_info_sepa(member_with_sepa_profile, None)).startswith(
        "Your SEPA"
    )


@pytest.mark.django_db
def test_new_member_info_sepa_without_mandate(member):
    assert new_member_mail_info_sepa(member, None) == ""


@pytest.mark.django_db
def test_new_member_office_mail_info_sepa(member_with_sepa_profile, membership):
    assert str(
        new_member_office_mail_info_sepa(member_with_sepa_profile, None)
    ).startswith("The new member")


@pytest.mark.django_db
def test_leave_member_office_info_sepa(member_with_sepa_profile, membership):
    assert str(leave_member_office_mail_info_sepa(membership, None)).startswith(
        "Please terminate"
    )


@pytest.mark.django_db
def test_leave_member_office_info_sepa_without_mandate(membership):
    assert leave_member_office_mail_info_sepa(membership, None) == ""
