import pytest
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from byro.members.models import FeeIntervals, Member, Membership


@pytest.fixture
@pytest.mark.django_db
def new_member():
    m = Member.objects.create(number='007')
    yield m
    m.delete()


@pytest.fixture
def member_membership(new_member):
    today = timezone.now().date()
    begin_last_month = today.replace(day=1) - relativedelta(months=+1)
    end_this_month = today.replace(day=1) + relativedelta(months=+1, days=-1)
    ms = Membership.objects.create(member=new_member,
                                   start=begin_last_month,
                                   end=end_this_month,
                                   amount=20,
                                   interval=FeeIntervals.MONTHLY)
    yield ms
    ms.member.transactions.all().delete()
    ms.delete()


@pytest.mark.django_db
def test_liabilities_easy(member_membership):
    member_membership.member.update_liabilites()
    virtual_transactions = member_membership.member.transactions.all()
    assert len(virtual_transactions) == 2
    assert sum([i.amount for i in virtual_transactions]) == 40


@pytest.mark.django_db
def test_liabilities_future_virtualtransactions(member_membership):
    end_this_month = member_membership.end
    end_next_month = member_membership.end + relativedelta(months=+1)
    member_membership.end = end_next_month
    member_membership.save()

    member_membership.member.update_liabilites()
    virtual_transactions = member_membership.member.transactions.all()
    assert len(virtual_transactions) == 3
    assert sum([i.amount for i in virtual_transactions]) == 60

    # set back to current month, this leaves a transaction in the future
    member_membership.end = end_this_month
    member_membership.save()
    member_membership.member.update_liabilites()
    # NOTE: update liabilites doesn't delete transactions
    virtual_transactions = member_membership.member.transactions.all()
    assert len(virtual_transactions) == 3

    # but the new (temporary?) helper cleans them
    member_membership.member.remove_future_liabilites_on_leave()
    virtual_transactions = member_membership.member.transactions.all()
    assert len(virtual_transactions) == 2
    assert sum([i.amount for i in virtual_transactions]) == 40


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
    ms.member.transactions.all().delete()
    ms.delete()


@pytest.mark.django_db
def test_liabilities_complicated_example(member_membership, member_membership_second):
    member_membership.member.update_liabilites()
    virtual_transactions = member_membership.member.transactions.all()
    assert len(virtual_transactions) == 4
    assert sum([i.amount for i in virtual_transactions]) == 8 + 8 + 20 + 20

    end_this_month = member_membership.end
    end_next_month = member_membership.end + relativedelta(months=+1)
    member_membership.end = end_next_month
    member_membership.save()

    member_membership.member.update_liabilites()
    virtual_transactions = member_membership.member.transactions.all()
    assert len(virtual_transactions) == 5
    assert sum([i.amount for i in virtual_transactions]) == 8 + 8 + 20 + 20 + 20

    member_membership.end = end_this_month
    member_membership.save()
    member_membership.member.update_liabilites()
    # NOTE: update liabilites doesn't delete transactions
    virtual_transactions = member_membership.member.transactions.all()
    assert len(virtual_transactions) == 5
    assert sum([i.amount for i in virtual_transactions]) == 8 + 8 + 20 + 20 + 20

    # but the new (temporary?) helper cleans them
    member_membership.member.remove_future_liabilites_on_leave()
    virtual_transactions = member_membership.member.transactions.all()
    assert len(virtual_transactions) == 4
    assert sum([i.amount for i in virtual_transactions]) == 8 + 8 + 20 + 20
