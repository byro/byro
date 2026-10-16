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


@pytest.mark.django_db
def test_member_record_disclosure_email_without_template_uses_the_default(
    configuration, member_with_sepa_profile
):
    configuration.record_disclosure_template = None
    configuration.save()

    email = member_with_sepa_profile.record_disclosure_email

    assert email.template is None
    assert email.subject == "Your data at Association Name (member number 1)"
    assert email.text.startswith(
        "Hello,\n\nThis is an overview of the data Association Name currently "
        "stores about you and your membership."
    )
    assert member_with_sepa_profile.profile_sepa.iban in email.text
