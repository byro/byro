import decimal

import pytest
from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.utils.timezone import now

from byro.bookkeeping.models import RealTransaction, TransactionChannel
from byro.mails.models import EMail, MailTemplate
from byro.members.models import FeeIntervals, Member, Membership


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
    member.transactions.all().delete()
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
    member.transactions.all().delete()
    member.delete()


@pytest.fixture
def real_transaction():
    return RealTransaction.objects.create(
        channel=TransactionChannel.BANK,
        booking_datetime=now(),
        value_datetime=now(),
        amount=decimal.Decimal('20.00'),
        purpose='Erm, this is my fees for today',
        originator='Jane Doe',
    )


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
