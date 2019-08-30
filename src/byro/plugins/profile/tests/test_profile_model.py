import pytest

from byro.members.models import Member


@pytest.fixture
def member_bob():
    member = Member.objects.create(email="bob@hacker.space")
    yield member
    [profile.delete() for profile in member.profiles]
    member.delete()


@pytest.mark.django_db
def test_profile_models(member_bob):
    assert member_bob.profile_profile.nick is None
