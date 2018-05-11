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
