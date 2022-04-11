from contextlib import suppress

import pytest
from django.utils.timezone import now

from byro.bookkeeping.models import (
    Account,
    AccountCategory,
    AccountTag,
    Booking,
    Transaction,
)
from byro.bookkeeping.special_accounts import SpecialAccounts


@pytest.mark.django_db
def test_account_model_str(bank_account):
    assert str(bank_account) == f"asset account #{bank_account.id}"
    bank_account.name = "foo"
    assert str(bank_account) == "foo"


@pytest.mark.django_db
def test_account_methods(bank_account):
    assert not bank_account.transactions
    assert bank_account.balances(start=now())["credit"] == 0
    assert bank_account.balances(start=now())["debit"] == 0


@pytest.mark.django_db
def test_account_tags(bank_account):
    assert bank_account.tags.all().count() == 0
    tag, _ignore = AccountTag.objects.get_or_create(name="TEST")
    bank_account.tags.add(tag)
    assert not bank_account.bookings
    assert not bank_account.unbalanced_transactions
    assert str(tag) == tag.name
    assert bank_account.tags.all().count() == 1
    assert (
        bank_account in AccountTag.objects.get_or_create(name="TEST")[0].accounts.all()
    )


@pytest.mark.django_db
def test_special_accounts():
    donations = SpecialAccounts.donations
    fees = SpecialAccounts.fees
    fees_receivable = SpecialAccounts.fees_receivable

    assert donations.account_category == AccountCategory.INCOME
    assert fees_receivable.account_category == AccountCategory.ASSET
    assert fees_receivable != fees

    bank = SpecialAccounts.bank
    assert Account.objects.filter(tags__name="bank").count() == 1
    assert bank in Account.objects.filter(tags__name="bank").all()


@pytest.mark.django_db
def test_transaction_balances(receivable_account, income_account):
    t = Transaction.objects.create(
        memo="Member fee is due", value_datetime=now(), user_or_context="test"
    )
    for booking in [
        dict(amount=10, debit_account=receivable_account),
        dict(amount=10, credit_account=income_account),
    ]:
        Booking.objects.create(transaction=t, **booking)
    assert t.is_balanced


@pytest.mark.django_db
def test_transaction_balances_decimal(bank_account, receivable_account):
    t = Transaction.objects.create(value_datetime=now(), user_or_context="test")
    for booking in [
        dict(amount=9.5, debit_account=bank_account),
        dict(amount=9.95, credit_account=receivable_account),
    ]:
        Booking.objects.create(transaction=t, **booking)
    t = Transaction.objects.with_balances().get(pk=t.pk)
    assert not t.balances_credit == t.balances_debit


@pytest.mark.django_db
def test_transaction_methods(bank_account):
    t = Transaction.objects.create(value_datetime=now(), user_or_context="test")
    t.debit(amount=10, account=bank_account, user_or_context="test")
    t.save()

    assert t.balances["credit"] == 0
    assert t.balances["debit"] == 10
    assert not t.is_balanced


@pytest.mark.django_db
def test_transaction_balance_accesses(bank_account):
    t = Transaction.objects.create(value_datetime=now(), user_or_context="test")
    t.debit(amount=10, account=bank_account, user_or_context="test")
    t.save()

    t1 = Transaction.objects.with_balances().get(pk=t.pk)

    assert t1.balances_credit == 0
    assert t1.balances_debit == 10
    assert not t1.is_balanced
    assert t1.balances["credit"] == 0
    assert t1.balances["debit"] == 10


@pytest.mark.django_db
def test_account_balances(bank_account, receivable_account, income_account):
    t1 = Transaction.objects.create(
        memo="Member fee is due", value_datetime=now(), user_or_context="test"
    )
    t1.debit(amount=10, account=receivable_account, user_or_context="test")
    t1.credit(amount=10, account=income_account, user_or_context="test")
    t1.save()

    assert income_account.balances(end=None)["net"] == 10
    assert receivable_account.balances(end=None)["net"] == 10

    t2 = Transaction.objects.create(
        memo="Member fee payment", value_datetime=now(), user_or_context="test"
    )
    t2.debit(amount=10, account=bank_account, user_or_context="test")
    t2.credit(amount=10, account=receivable_account, user_or_context="test")
    t2.save()

    assert income_account.balances(end=None)["net"] == 10
    assert receivable_account.balances(end=None)["net"] == 0
    assert bank_account.balances(end=None)["net"] == 10


@pytest.mark.django_db
def test_real_transaction_source_process(real_transaction_source):
    with suppress(Exception):
        real_transaction_source.process()
