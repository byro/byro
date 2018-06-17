import pytest
from django.utils.timezone import now

from byro.bookkeeping.models import (
    AccountCategory, AccountTag, Booking, Transaction,
)
from byro.bookkeeping.special_accounts import SpecialAccounts


@pytest.mark.django_db
def test_account_model_str(fee_account):
    assert str(fee_account) == 'member_fees account #{}'.format(fee_account.id)
    fee_account.name = 'foo'
    assert str(fee_account) == 'foo'


@pytest.mark.django_db
def test_account_methods(fee_account):
    assert not fee_account.transactions
    assert fee_account.balances(start=now())['credit'] == 0
    assert fee_account.balances(start=now())['debit'] == 0


@pytest.mark.django_db
def test_account_tags(fee_account):
    assert fee_account.tags.all().count() == 0
    fee_account.tags.get_or_create(name='fees')
    assert fee_account.tags.all().count() == 1
    assert fee_account in AccountTag.objects.get_or_create(name='fees')[0].account_set.all()


@pytest.mark.django_db
def test_special_accounts():
    donations = SpecialAccounts.donations
    fees = SpecialAccounts.fees
    fees_receivable = SpecialAccounts.fees_receivable

    assert donations.account_category == AccountCategory.INCOME
    assert fees_receivable.account_category == AccountCategory.ASSET
    assert fees_receivable != fees


@pytest.mark.django_db
def test_transaction_balances(receivable_account, income_account):
    t = Transaction.objects.create(memo='Member fee is due', value_datetime=now())
    for booking in [
            dict(amount=10, debit_account=receivable_account),
            dict(amount=10, credit_account=income_account)
    ]:
        Booking.objects.create(transaction=t, **booking)
    assert t.is_balanced


@pytest.mark.django_db
def test_transaction_methods(bank_account):
    t = Transaction.objects.create(value_datetime=now())
    t.debit(amount=10, account=bank_account)
    t.save()

    assert t.balances['credit'] == 0
    assert t.balances['debit'] == 10
    assert not t.is_balanced


@pytest.mark.django_db
def test_transaction_balance_accesses(bank_account):
    t = Transaction.objects.create(value_datetime=now())
    t.debit(amount=10, account=bank_account)
    t.save()

    t1 = Transaction.objects.with_balances().get(pk=t.pk)

    assert t1.balances_credit == 0
    assert t1.balances_debit == 10
    assert not t1.is_balanced
    assert t1.balances['credit'] == 0
    assert t1.balances['debit'] == 10


@pytest.mark.django_db
def test_account_balances(bank_account, receivable_account, income_account):
    t1 = Transaction.objects.create(memo='Member fee is due', value_datetime=now())
    t1.debit(amount=10, account=receivable_account),
    t1.credit(amount=10, account=income_account)
    t1.save()

    assert income_account.balances(end=None)['net'] == 10
    assert receivable_account.balances(end=None)['net'] == 10

    t2 = Transaction.objects.create(memo='Member fee payment', value_datetime=now())
    t2.debit(amount=10, account=bank_account)
    t2.credit(amount=10, account=receivable_account),
    t2.save()

    assert income_account.balances(end=None)['net'] == 10
    assert receivable_account.balances(end=None)['net'] == 0
    assert bank_account.balances(end=None)['net'] == 10
