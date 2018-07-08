import decimal

import pytest
from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils.timezone import now

from byro.bookkeeping.models import Account, AccountCategory, Transaction
from byro.mails.models import EMail, MailTemplate
from byro.members.models import FeeIntervals, Member, Membership


@pytest.fixture
def full_testdata(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command('loaddata', 'tests/fixtures/test_full_testdata.json')


@pytest.fixture
def user():
    user = get_user_model().objects.create(username='regular_user', is_staff=True)
    yield user
    user.delete()


@pytest.fixture
def logged_in_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def member():
    member = Member.objects.create(email='joe@hacker.space', number='1')
    yield member

    [profile.delete() for profile in member.profiles]
    [(t.bookings.all().delete(), t.delete()) for t in Transaction.objects.filter(bookings__member=member).all()]
    member.delete()


@pytest.fixture
def membership(member):
    today = now()
    begin_last_month = today.replace(day=1) - relativedelta(months=+1)
    end_this_month = today.replace(day=1) + relativedelta(months=+1, days=-1)
    ms = Membership.objects.create(
        member=member,
        start=begin_last_month,
        end=end_this_month,
        amount=20,
        interval=FeeIntervals.MONTHLY,
    )
    yield ms
    ms.delete()


@pytest.fixture
def inactive_member():
    member = Member.objects.create(email='joe@ex-hacker.space')
    today = now()
    begin = today.replace(day=1) - relativedelta(months=3)
    end = today.replace(day=1) - relativedelta(months=1, days=-1)
    Membership.objects.create(
        member=member,
        start=begin,
        end=end,
        amount=20,
        interval=FeeIntervals.MONTHLY,
    )
    yield member
    [profile.delete() for profile in member.profiles]
    [(t.bookings.all().delete(), t.delete()) for t in Transaction.objects.filter(bookings__member=member).all()]
    member.delete()


@pytest.fixture
def mail_template():
    return MailTemplate.objects.create(
        subject='Test Mail',
        text='Hi!\nThis is just a test mail.\nThe robo clerk',
    )


@pytest.fixture
def email():
    return EMail.objects.create(
        to='test@localhost',
        subject='Test Mail',
        text='Hi!\nThis is just a nice test mail.\nThe robo clerk',
    )


@pytest.fixture
def sent_email():
    return EMail.objects.create(
        to='test@localhost',
        subject='Test Mail',
        text='Hi!\nThis is just a nice test mail.\nThe robo clerk',
        sent=now(),
    )


def account_helper(name, cat, **kwargs):
    def f():
        account = Account.objects.create(account_category=cat, **kwargs)
        yield account
        account.debits.all().delete()
        account.credits.all().delete()
        account.delete()
    f.__name__ = name
    return pytest.fixture(f)


fee_account = account_helper('fee_account', 'member_fees')

income_account = account_helper('income_account', AccountCategory.INCOME)
receivable_account = account_helper('receivable_account', AccountCategory.ASSET)
bank_account = account_helper('asset_account', AccountCategory.ASSET)
