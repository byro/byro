import pytest
from django.dispatch import receiver

from byro.bookkeeping.models import Account, AccountCategory, VirtualTransaction
from byro.bookkeeping.signals import derive_virtual_transactions
from byro.members.models import Member


@pytest.mark.django_db
def test_match_single_fee(member, real_transaction):

    @receiver(derive_virtual_transactions, dispatch_uid='test-plugin')
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

    real_transaction.derive_virtual_transactions()
    account = Account.objects.get(account_category=AccountCategory.MEMBER_FEES)
    assert account.total() == real_transaction.amount


@pytest.mark.django_db
def test_match_no_fee(member, real_transaction):

    @receiver(derive_virtual_transactions, dispatch_uid='test-plugin')
    def derive_test_transaction(sender, signal):
        return []

    with pytest.raises(Exception) as excinfo:
        real_transaction.derive_virtual_transactions()

    assert 'Transaction could not be matched' in str(excinfo)

    account = Account.objects.get(account_category=AccountCategory.MEMBER_FEES)
    assert account.total() == 0


@pytest.mark.django_db
def test_match_multiple_fees(member, real_transaction):

    @receiver(derive_virtual_transactions, dispatch_uid='test-plugin')
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

    real_transaction.derive_virtual_transactions()
    fees = Account.objects.get(account_category=AccountCategory.MEMBER_FEES)
    donations = Account.objects.get(account_category=AccountCategory.MEMBER_DONATION)
    assert fees.total() + donations.total() == real_transaction.amount
