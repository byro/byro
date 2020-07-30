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
    from byro.members.models import Membership
    from byro.members.stats import get_member_statistics

    assert Membership.objects.count()

    member_stats = get_member_statistics()

    assert isinstance(member_stats, list)
    assert len(member_stats)
    assert member_stats[0][1] == 1
    assert member_stats[0][2] == 0
    assert member_stats[-1][1] == 0
    assert member_stats[-1][2] == 1
    for m in member_stats[1:-1]:
        assert m[1] == 0
        assert m[2] == 0
