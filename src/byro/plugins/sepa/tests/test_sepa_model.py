import pytest

from byro.members.models import Member


@pytest.fixture
def member():
    member = Member.objects.create(email='joe@hacker.space')
    yield member
    [profile.delete() for profile in member.profiles]
    member.delete()


@pytest.mark.django_db
def test_sepa_models(member):
    assert member.profile_sepa.iban is None
