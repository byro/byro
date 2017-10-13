import pytest

from byro.bookkeeping.models import Account, AccountCategory, VirtualTransaction
from byro.bookkeeping.signals import derive_virtual_transactions
from byro.members.models import Member


class connected_signal:
    """ connect a signal and make sure it is disconnected after use, so it doesn't leak into other tests. """

    def __init__(self, signal, receiver):
        self.signal = signal
        self.receiver = receiver

    def __enter__(self):
        self.signal.connect(self.receiver, dispatch_uid='test-plugin')

    def __exit__(self, exc_type, exc_value, tb):
        self.signal.disconnect(self.receiver, dispatch_uid='test-plugin')


@pytest.mark.django_db
def test_match_single_fee(member, real_transaction):

    def derive_test_transaction(sender, signal):
        member = Member.objects.first()
        account = Account.objects.get(account_category=AccountCategory.MEMBER_FEES)
        transaction = VirtualTransaction.objects.create(
            real_transaction=sender,
            destination_account=account,
            amount=sender.amount,
            value_datetime=sender.value_datetime,
            member=member,
        )
        return [transaction]

    with connected_signal(derive_virtual_transactions, derive_test_transaction):
        real_transaction.derive_virtual_transactions()

    account = Account.objects.get(account_category=AccountCategory.MEMBER_FEES)
    assert account.balance() == real_transaction.amount


@pytest.mark.django_db
def test_match_no_fee(member, real_transaction):

    def derive_test_transaction(sender, signal):
        return []

    with pytest.raises(Exception) as excinfo:
        with connected_signal(derive_virtual_transactions, derive_test_transaction):
            real_transaction.derive_virtual_transactions()

    assert 'Transaction could not be matched' in str(excinfo)

    account = Account.objects.get(account_category=AccountCategory.MEMBER_FEES)
    assert account.balance() == 0


@pytest.mark.django_db
def test_match_multiple_fees(member, real_transaction):

    def derive_test_transaction(sender, signal):
        member = Member.objects.first()
        account = Account.objects.get(account_category=AccountCategory.MEMBER_FEES)
        fee = VirtualTransaction.objects.create(
            real_transaction=sender,
            destination_account=account,
            amount=sender.amount / 2,
            value_datetime=sender.value_datetime,
            member=member,
        )
        account = Account.objects.get(account_category=AccountCategory.MEMBER_DONATION)
        donation = VirtualTransaction.objects.create(
            real_transaction=sender,
            destination_account=account,
            amount=sender.amount / 2,
            value_datetime=sender.value_datetime,
            member=member,
        )
        return [fee, donation]

    with connected_signal(derive_virtual_transactions, derive_test_transaction):
        real_transaction.derive_virtual_transactions()

    fees = Account.objects.get(account_category=AccountCategory.MEMBER_FEES)
    donations = Account.objects.get(account_category=AccountCategory.MEMBER_DONATION)
    assert fees.balance() + donations.balance() == real_transaction.amount
