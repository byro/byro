import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from byro.bookkeeping.models import Transaction
from byro.members.models import FeeIntervals, Member, Membership


@pytest.fixture
@pytest.mark.django_db
def new_member():
    m = Member.objects.create(number='007')
    yield m
    m.delete()


@pytest.fixture
def member_membership(new_member):
    today = timezone.now()
    begin_last_month = today.replace(day=1) - relativedelta(months=+1)
    end_this_month = today.replace(day=1) + relativedelta(months=+1, days=-1)
    ms = Membership.objects.create(member=new_member,
                                   start=begin_last_month,
                                   end=end_this_month,
                                   amount=20,
                                   interval=FeeIntervals.MONTHLY)
    yield ms
    [ (t.bookings.all().delete(), t.delete()) for t in Transaction.objects.filter(bookings__member=ms.member).all() ]
    ms.delete()


@pytest.mark.django_db
def test_liabilities_easy(member_membership):
    member_membership.member.update_liabilites()
    bookings = member_membership.member.bookings.all()
    credits = member_membership.member.bookings.filter(credit_account__isnull=False).all()
    assert len(bookings) == 4
    assert sum([i.amount for i in bookings]) == 80
    assert sum([i.amount for i in credits]) == 40


@pytest.mark.django_db
def test_liabilities_future_transactions(member_membership):
    end_this_month = member_membership.end
    end_next_month = member_membership.end + relativedelta(months=+1)
    member_membership.end = end_next_month
    member_membership.save()

    member_membership.member.update_liabilites()
    bookings = member_membership.member.bookings.filter(credit_account__isnull=False).all()
    assert len(bookings) == 3
    assert sum([i.amount for i in bookings]) == 60

    # set back to current month, this leaves a transaction in the future
    member_membership.end = end_this_month
    member_membership.save()
    member_membership.member.update_liabilites()
    # NOTE: update liabilites doesn't delete transactions
    bookings = member_membership.member.bookings.filter(credit_account__isnull=False).all()
    assert len(bookings) == 3

    # but the new (temporary?) helper cleans them
    member_membership.member.remove_future_liabilites_on_leave()
    bookings = member_membership.member.bookings.filter(credit_account__isnull=False).all()
    assert len(bookings) == 2
    assert sum([i.amount for i in bookings]) == 40


@pytest.fixture
def member_membership_second(new_member):
    today = timezone.now().date()
    begin_some_time_ago = today.replace(day=1) - relativedelta(months=4)
    end_two_months_ago = today.replace(day=1) + relativedelta(months=-2, days=-1)
    ms = Membership.objects.create(member=new_member,
                                   start=begin_some_time_ago,
                                   end=end_two_months_ago,
                                   amount=8,
                                   interval=FeeIntervals.MONTHLY)
    yield ms
    [ (t.bookings.all().delete(), t.delete()) for t in Transaction.objects.filter(bookings__member=ms.member).all() ]
    ms.delete()


@pytest.mark.django_db
def test_liabilities_complicated_example(member_membership, member_membership_second):
    member_membership.member.update_liabilites()
    virtual_transactions = member_membership.member.bookings.filter(credit_account__isnull=False).all()
    assert len(virtual_transactions) == 4
    assert sum([i.amount for i in virtual_transactions]) == 8 + 8 + 20 + 20

    end_this_month = member_membership.end
    end_next_month = member_membership.end + relativedelta(months=+1)
    member_membership.end = end_next_month
    member_membership.save()

    member_membership.member.update_liabilites()
    virtual_transactions = member_membership.member.bookings.filter(credit_account__isnull=False).all()
    assert len(virtual_transactions) == 5
    assert sum([i.amount for i in virtual_transactions]) == 8 + 8 + 20 + 20 + 20

    member_membership.end = end_this_month
    member_membership.save()
    member_membership.member.update_liabilites()
    # NOTE: update liabilites doesn't delete transactions
    virtual_transactions = member_membership.member.bookings.filter(credit_account__isnull=False).all()
    assert len(virtual_transactions) == 5
    assert sum([i.amount for i in virtual_transactions]) == 8 + 8 + 20 + 20 + 20

    # but the new (temporary?) helper cleans them
    member_membership.member.remove_future_liabilites_on_leave()
    virtual_transactions = member_membership.member.bookings.filter(credit_account__isnull=False).all()
    assert len(virtual_transactions) == 4
    assert sum([i.amount for i in virtual_transactions]) == 8 + 8 + 20 + 20
