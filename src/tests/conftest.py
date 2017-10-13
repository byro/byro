import decimal

import pytest
from django.utils.timezone import now

from byro.bookkeeping.models import RealTransaction, TransactionChannel
from byro.members.models import Member


@pytest.fixture
def member():
    member = Member.objects.create(email='joe@hacker.space')
    yield member

    # dirty hack until we find the real issue of the problem
    import time
    time.sleep(1)

    [profile.delete() for profile in member.profiles]
    member.transactions.all().delete()
    member.delete()


@pytest.fixture
def real_transaction():
    return RealTransaction.objects.create(
        channel=TransactionChannel.BANK,
        booking_datetime=now(),
        value_datetime=now(),
        amount=decimal.Decimal('20.00'),
        purpose='Erm, this is my fees for today',
        originator='Jane Doe',
    )
