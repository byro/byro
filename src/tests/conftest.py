import decimal

import pytest
from django.utils.timezone import now

from byro.bookkeeping.models import RealTransaction, TransactionChannel
from byro.members.models import Member


@pytest.fixture
def member():
    return Member.create_member(
        email='joe@hacker.space'
    )


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
