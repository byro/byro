import pytest


@pytest.mark.django_db
def test_profiles(member, membership):
    from byro.plugins.profile.models import MemberProfile

    profiles = member.profiles

    assert len(profiles) > 1
    assert any([isinstance(profile, MemberProfile) for profile in profiles])
