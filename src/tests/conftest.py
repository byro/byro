import pytest

from byro.bookkeeping.models import Account, AccountCategory
from byro.members.models import Member


@pytest.fixture
def member():
    return Member.objects.create(
        email='joe@hacker.space'
    )


@pytest.fixture
def member_fees_account(member):
    return Account.objects.create(
        member=member,
        account_category=AccountCategory.MEMBER_FEES,
    )


@pytest.fixture
def member_donations_account(member):
    return Account.objects.create(
        member=member,
        account_category=AccountCategory.MEMBER_DONATIONS,
    )
