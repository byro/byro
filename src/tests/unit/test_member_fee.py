from itertools import repeat

import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from freezegun import freeze_time

from byro.bookkeeping.models import Transaction
from byro.bookkeeping.special_accounts import SpecialAccounts
from byro.common.models import Configuration
from byro.members.models import FeeIntervals, Member, Membership


@pytest.fixture
@pytest.mark.django_db
def new_member():
    return Member.objects.create(number="007")


@pytest.fixture
def member_membership(new_member):
    today = timezone.now()
    begin_last_month = today.replace(day=1) - relativedelta(months=+1)
    end_this_month = today.replace(day=1) + relativedelta(months=+1, days=-1)
    return Membership.objects.create(
        member=new_member,
        start=begin_last_month,
        end=end_this_month,
        amount=20,
        interval=FeeIntervals.MONTHLY,
    )


@pytest.mark.django_db
def test_liabilities_easy(member_membership):
    member_membership.member.update_liabilites()
    bookings = member_membership.member.bookings.all()
    credits = member_membership.member.bookings.filter(
        debit_account=SpecialAccounts.fees_receivable
    ).all()
    assert len(bookings) == 4
    assert sum(i.amount for i in bookings) == 80
    assert sum(i.amount for i in credits) == 40


@pytest.mark.django_db
def test_liabilities_future_transactions(member_membership):
    end_this_month = member_membership.end
    end_next_month = member_membership.end + relativedelta(months=+1)
    member_membership.end = end_next_month
    member_membership.save()

    member_membership.member.update_liabilites()
    bookings = member_membership.member.bookings.filter(
        debit_account=SpecialAccounts.fees_receivable
    ).all()
    assert len(bookings) == 3
    assert sum(i.amount for i in bookings) == 60

    # set back to current month, this leaves a transaction in the future
    member_membership.end = end_this_month
    member_membership.save()
    member_membership.member.update_liabilites()

    bookings = member_membership.member.bookings.filter(
        debit_account=SpecialAccounts.fees_receivable
    ).all()
    assert len(bookings) == 3
    assert sum(i.amount for i in bookings) == 60

    correction_bookings = member_membership.member.bookings.filter(
        credit_account=SpecialAccounts.fees_receivable
    ).all()
    assert len(correction_bookings) == 1
    assert sum(i.amount for i in correction_bookings) == 20


@pytest.mark.django_db
def test_liabilities_change(member_membership):
    member_membership.member.update_liabilites()
    bookings = member_membership.member.bookings.filter(
        debit_account=SpecialAccounts.fees_receivable
    ).all()
    assert len(bookings) == 2
    assert sum(i.amount for i in bookings) == 40

    member_membership.amount = 20 + 10
    member_membership.save()
    member_membership.member.update_liabilites()

    # Old amount should be canceled, new amount set
    debits = member_membership.member.bookings.filter(
        debit_account=SpecialAccounts.fees_receivable
    ).all()
    credits = member_membership.member.bookings.filter(
        credit_account=SpecialAccounts.fees_receivable
    ).all()
    assert len(debits) == 4
    assert len(credits) == 2
    assert sum(i.amount for i in credits) == 40
    assert sum(i.amount for i in debits) == 40 + 60


@pytest.fixture
def member_membership_second(new_member):
    today = timezone.now().date()
    begin_some_time_ago = today.replace(day=1) - relativedelta(months=4)
    end_two_months_ago = today.replace(day=1) + relativedelta(months=-2, days=-1)
    return Membership.objects.create(
        member=new_member,
        start=begin_some_time_ago,
        end=end_two_months_ago,
        amount=8,
        interval=FeeIntervals.MONTHLY,
    )


@pytest.mark.django_db
def test_liabilities_complicated_example(member_membership, member_membership_second):
    member_membership.member.update_liabilites()
    virtual_transactions = member_membership.member.bookings.filter(
        debit_account=SpecialAccounts.fees_receivable
    ).all()
    assert len(virtual_transactions) == 4
    assert sum(i.amount for i in virtual_transactions) == 8 + 8 + 20 + 20

    end_this_month = member_membership.end
    end_next_month = member_membership.end + relativedelta(months=+1)
    member_membership.end = end_next_month
    member_membership.save()

    member_membership.member.update_liabilites()
    virtual_transactions = member_membership.member.bookings.filter(
        debit_account=SpecialAccounts.fees_receivable
    ).all()
    assert len(virtual_transactions) == 5
    assert sum(i.amount for i in virtual_transactions) == 8 + 8 + 20 + 20 + 20

    member_membership.end = end_this_month
    member_membership.save()

    for _ in repeat(None, 2):  # Ensure that update_liabilities() is idempotent
        member_membership.member.update_liabilites()

        bookings = member_membership.member.bookings.filter(
            debit_account=SpecialAccounts.fees_receivable
        ).all()
        assert len(bookings) == 5
        assert sum(i.amount for i in bookings) == 8 + 8 + 20 + 20 + 20

        correction_bookings = member_membership.member.bookings.filter(
            credit_account=SpecialAccounts.fees_receivable
        ).all()
        assert len(correction_bookings) == 1
        assert sum(i.amount for i in correction_bookings) == 20


@pytest.mark.django_db
def test_liabilities_limit(member):
    config = Configuration.get_solo()
    config.liability_interval = 36
    config.save()

    test_date = timezone.now().date().replace(year=2010, month=12, day=31)

    with freeze_time(test_date) as frozen_time:
        Membership.objects.create(
            member=member,
            start=test_date.replace(year=2007, month=5, day=1),
            amount=20,
            interval=FeeIntervals.MONTHLY,
        )
        member.update_liabilites()

        assert member.balance == -880.0
        assert member.statute_barred_debt() == 0

        frozen_time.move_to(test_date.replace(year=2011, month=1, day=1))
        member.update_liabilites()

        assert member.balance == -900.0
        assert member.statute_barred_debt() == 160.0

        t = Transaction.objects.create(value_datetime=test_date, user_or_context="test")
        t.debit(account=SpecialAccounts.bank, amount=12, user_or_context="test")
        t.credit(
            account=SpecialAccounts.fees_receivable,
            amount=12,
            member=member,
            user_or_context="test",
        )
        t.save()

        assert member.balance == -888.0
        assert member.statute_barred_debt() == 148.0

        t = Transaction.objects.create(
            value_datetime=test_date.replace(year=2007, month=7, day=1),
            user_or_context="test",
        )
        t.debit(account=SpecialAccounts.bank, amount=13, user_or_context="test")
        t.credit(
            account=SpecialAccounts.fees_receivable,
            amount=13,
            member=member,
            user_or_context="test",
        )
        t.save()

        assert member.balance == -875.0
        assert member.statute_barred_debt() == 135.0

        t = Transaction.objects.create(
            value_datetime=test_date.replace(year=2007, month=12, day=31),
            user_or_context="test",
        )
        t.debit(account=SpecialAccounts.bank, amount=136, user_or_context="test")
        t.credit(
            account=SpecialAccounts.fees_receivable,
            amount=136,
            member=member,
            user_or_context="test",
        )
        t.save()

        assert member.balance == -739.0
        assert member.statute_barred_debt() == 0

        assert member.statute_barred_debt(relativedelta(years=1)) == 239.0
