import pytest

from byro.members.models import Member, get_next_member_number


@pytest.mark.django_db
def test_profiles(member, membership):
    from byro.plugins.profile.models import MemberProfile

    profiles = member.profiles

    assert len(profiles) > 1
    assert any([isinstance(profile, MemberProfile) for profile in profiles])


@pytest.mark.django_db
def test_next_member_number(member):
    assert get_next_member_number() == Member.objects.count() + 1


@pytest.mark.django_db
def test_next_member_number_without_member():
    assert get_next_member_number() == 1


@pytest.mark.django_db
def test_member_model_methods(member):
    assert member.balance == 0
    assert not member.donations
    assert not member.fee_payments
    assert str(member)
    assert not member.is_active


@pytest.mark.django_db
def test_member_record_disclosure_email(member_with_sepa_profile):
    email = member_with_sepa_profile.record_disclosure_email
    member = member_with_sepa_profile
    assert member.number in email.subject
    assert member.profile_sepa.iban in email.text
    assert member.name in email.text
