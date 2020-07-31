import pytest

from byro.plugins.sepa.signals import (
    leave_member_office_mail_info_sepa,
    new_member_mail_info_sepa,
    new_member_office_mail_info_sepa,
)


@pytest.mark.django_db
def test_new_member_info_sepa(member_with_sepa_profile):
    assert any(
        str(new_member_mail_info_sepa(member_with_sepa_profile, None)).startswith(s)
        for s in ["Your SEPA", "Deine SEPA"]
    )


@pytest.mark.django_db
def test_new_member_info_sepa_without_mandate(member):
    assert new_member_mail_info_sepa(member, None) == ""


@pytest.mark.django_db
def test_new_member_office_mail_info_sepa(member_with_sepa_profile, membership):
    assert any(
        str(
            new_member_office_mail_info_sepa(member_with_sepa_profile, None)
        ).startswith(s)
        for s in ["The new member", "Das neue Mitglied"]
    )


@pytest.mark.django_db
def test_leave_member_office_info_sepa(member_with_sepa_profile, membership):
    assert any(
        str(leave_member_office_mail_info_sepa(membership, None)).startswith(s)
        for s in ["Please terminate", "Bitte beende"]
    )


@pytest.mark.django_db
def test_leave_member_office_info_sepa_without_mandate(membership):
    assert leave_member_office_mail_info_sepa(membership, None) == ""
