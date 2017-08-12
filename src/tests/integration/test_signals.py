import pytest
from django.dispatch import receiver
from django.utils.timezone import now

from byro.bookkeeping.models import Account, AccountCategory, RealTransaction, TransactionChannel, VirtualTransaction
from byro.bookkeeping.signals import derive_virtual_transactions
from byro.members.models import Member


@pytest.mark.django_db
def test_match_single_fee(member, real_transaction):

    @receiver(derive_virtual_transactions, dispatch_uid='test-plugin')
    def derive_test_transaction(sender, signal):
        member = Member.objects.first()
        account = member.get_account(category=AccountCategory.MEMBER_FEES)
        transaction = VirtualTransaction.objects.create(
            real_transaction=sender,
            destination_account=account,
            amount=sender.amount,
            value_datetime=sender.value_datetime,
        )
        return [transaction]

    real_transaction.derive_virtual_transactions()
    account = member.get_account(category=AccountCategory.MEMBER_FEES)
    assert account.total() == real_transaction.amount


@pytest.mark.django_db
def test_match_no_fee(member, real_transaction):

    @receiver(derive_virtual_transactions, dispatch_uid='test-plugin')
    def derive_test_transaction(sender, signal):
        return []

    with pytest.raises(Exception) as excinfo:
        real_transaction.derive_virtual_transactions()

    assert 'Transaction could not be matched' in str(excinfo)

    account = member.get_account(category=AccountCategory.MEMBER_FEES)
    assert account.total() == 0
