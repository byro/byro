import pytest

from byro.bookkeeping.models import Account, AccountCategory
from byro.members.models import Member


@pytest.fixture
def member():
    return Member.create_member(
        email='joe@hacker.space'
    )
