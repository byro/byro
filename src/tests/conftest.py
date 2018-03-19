import decimal

import pytest
from django.utils.timezone import now

from byro.bookkeeping.models import RealTransaction, TransactionChannel
from byro.mails.models import EMail, MailTemplate
from byro.members.models import Member


@pytest.fixture
def member():
    member = Member.objects.create(email='joe@hacker.space')
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
