import pytest


@pytest.mark.django_db
def test_profiles(member):
    from byro.plugins.profile.models import MemberProfile

    profiles = member.profiles

    assert len(profiles) > 1
    assert any([isinstance(profile, MemberProfile) for profile in profiles])


@pytest.mark.django_db
def test_stats_no_members():
    from byro.members.stats import get_member_statistics

    member_stats = get_member_statistics()

    assert isinstance(member_stats, list)
    assert len(member_stats) == 0
