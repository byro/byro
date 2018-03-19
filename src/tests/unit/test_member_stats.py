import pytest


@pytest.mark.django_db
def test_stats_no_members():
    from byro.members.stats import get_member_statistics

    member_stats = get_member_statistics()

    assert isinstance(member_stats, list)
    assert len(member_stats) == 0


@pytest.mark.django_db
def test_stats_one_member(member):
    from byro.members.stats import get_member_statistics

    member_stats = get_member_statistics()

    assert isinstance(member_stats, list)
    assert len(member_stats) == 0


@pytest.mark.django_db
def test_stats_one_inactive_member(inactive_member):
    from byro.members.stats import get_member_statistics

    member_stats = get_member_statistics()

    assert isinstance(member_stats, list)
    assert len(member_stats) == 0, member_stats
