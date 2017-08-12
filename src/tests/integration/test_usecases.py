import pytest
from django.utils.timezone import now

from byro.bookkeeping.models import Account, AccountCategory, RealTransaction, TransactionChannel, VirtualTransaction
from byro.members.models import Member


@pytest.mark.django_db
def test_normal_fees(member, member_fees_account):
    rt = RealTransaction.objects.create(
        channel=TransactionChannel.BANK,
        booking_datetime=now(),
        value_datetime=now(),
        amount='20.00',
        purpose='Erm, this is my fees for today',  # Matching is complex
        originator='Jane Doe',
    )
    rt.refresh_from_db()

    # Matching magic happens here later

    VirtualTransaction.objects.create(
        real_transaction=rt,
        destination_account=member_fees_account,
        amount=rt.amount,
        value_datetime=rt.value_datetime,
    )

    assert member_fees_account.total() == rt.amount
