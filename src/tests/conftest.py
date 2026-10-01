import os.path

import pytest
from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.shortcuts import reverse
from django.utils.timezone import now

from byro.bookkeeping.models import (
    Account,
    AccountCategory,
    RealTransactionSource,
    Transaction,
)
from byro.bookkeeping.special_accounts import SpecialAccounts
from byro.common import oidc
from byro.common import views as common_views
from byro.common.models.configuration import Configuration
from byro.mails.models import EMail, MailTemplate
from byro.members.models import FeeIntervals, Member, Membership
from byro.plugins.sepa.models import MemberSepa


@pytest.fixture
def configuration():
    config = Configuration.get_solo()
    config.name = "Association Name"
    config.backoffice_mail = "associationname@example.com"
    config.mail_from = "associationname@example.com"
    config.save()
    return config


@pytest.fixture
def full_testdata(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command("loaddata", "tests/fixtures/test_full_testdata.json")


@pytest.fixture
def login_user():
    def do_login(client, user):
        client.post(
            reverse("common:login"),
            {"username": user.username, "password": "test_password"},
        )

    return do_login


@pytest.fixture
def user(login_user):
    user = get_user_model().objects.create(username="regular_user", is_staff=True)
    user.set_password("test_password")
    user.save()
    yield user
    user.delete()


@pytest.fixture
def create_user():
    """Create accounts with any combination of ``is_staff``/``is_superuser``
    and the password ``login_user`` expects."""

    def create(username, is_staff=False, is_superuser=False, **kwargs):
        user = get_user_model().objects.create(
            username=username, is_staff=is_staff, is_superuser=is_superuser, **kwargs
        )
        user.set_password("test_password")
        user.save()
        return user

    return create


@pytest.fixture
def superuser(create_user):
    return create_user("super_user", is_staff=True, is_superuser=True)


@pytest.fixture
def logged_in_client(login_user, client, user):
    login_user(client, user)
    return client


@pytest.fixture
def superuser_client(login_user, client, superuser):
    login_user(client, superuser)
    return client


@pytest.fixture
def oidc_provider(settings, monkeypatch):
    """An OIDC login through the real callback view. Only the communication
    with the identity provider is replaced; the callback, account lookup,
    provisioning and group synchronization run unchanged.

    Returns a callable ``(client, claims)`` that performs the callback with
    the given ID token claims."""
    settings.OIDC_ISSUER_URL = "https://idp.example.org"
    settings.OIDC_CLIENT_ID = "byro"
    settings.OIDC_USERNAME_FIELD = "preferred_username"
    settings.OIDC_STAFF_GROUP = ""
    settings.OIDC_SUPERUSER_GROUP = ""
    settings.OIDC_SYNC_GROUPS = False
    settings.OIDC_GROUP_CONFLICT = False
    settings.OIDC_AUTO_CREATE_ACCOUNT = True
    monkeypatch.setattr(
        common_views,
        "build_auth_url",
        lambda redirect_uri, state, nonce: "https://idp.example.org/auth",
    )
    monkeypatch.setattr(
        common_views,
        "exchange_code",
        lambda code, redirect_uri: {"id_token": "id", "access_token": "at"},
    )

    def no_userinfo(access_token):
        raise AssertionError("unexpected userinfo request")

    monkeypatch.setattr(oidc, "get_userinfo", no_userinfo)

    def callback(client, claims):
        monkeypatch.setattr(
            common_views, "validate_id_token", lambda id_token, nonce: claims
        )
        session = client.session
        session["oidc_state"] = "state123"
        session["oidc_nonce"] = "nonce123"
        session.save()
        return client.get(reverse("common:oidc-callback") + "?state=state123&code=abc")

    return callback


@pytest.fixture
def member():
    member = Member.objects.create(
        email="joe@hacker.space", number="1", name="Jona Than"
    )
    yield member

    [profile.delete() for profile in member.profiles]
    [
        (t.bookings.all().delete(), t.delete())
        for t in Transaction.objects.filter(bookings__member=member).all()
    ]
    member.delete()


@pytest.fixture
def member_with_sepa_profile(member):
    MemberSepa.objects.create(
        member=member,
        iban="DE89370400440532013000",
        bic="COBADEFFXXX",
        issue_date=now().date(),
        fullname=member.name,
        address="Somewhere",
        mandate_reference="'tis a reference",
    )
    return member


@pytest.fixture
def membership(member):
    today = now()
    begin_last_month = today.replace(day=1) - relativedelta(months=+1)
    end_this_month = today.replace(day=1) + relativedelta(months=+1, days=-1)
    if end_this_month == today:
        end_this_month += relativedelta(months=1)
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
    member = Member.objects.create(email="joe@ex-hacker.space", name="Inactive Joe")
    today = now()
    begin = today.replace(day=1) - relativedelta(months=3)
    end = today.replace(day=1) - relativedelta(months=1, days=-1)
    Membership.objects.create(
        member=member, start=begin, end=end, amount=20, interval=FeeIntervals.MONTHLY
    )
    yield member
    [profile.delete() for profile in member.profiles]
    [
        (t.bookings.all().delete(), t.delete())
        for t in Transaction.objects.filter(bookings__member=member).all()
    ]
    member.delete()


@pytest.fixture
def partial_transaction():
    t = Transaction.objects.create(value_datetime=now(), user_or_context="test")
    t.debit(
        account=SpecialAccounts.bank, amount=10, memo="Fee ID 3", user_or_context="test"
    )
    yield t
    t.bookings.all().delete()
    t.delete()


@pytest.fixture
def mail_template():
    return MailTemplate.objects.create(
        subject="Test Mail", text="Hi!\nThis is just a test mail.\nThe robo clerk"
    )


@pytest.fixture
def email():
    return EMail.objects.create(
        to="test@localhost",
        subject="Test Mail",
        text="Hi!\nThis is just a nice test mail.\nThe robo clerk",
    )


@pytest.fixture
def sent_email():
    return EMail.objects.create(
        to="test@localhost",
        subject="Test Mail",
        text="Hi!\nThis is just a nice test mail.\nThe robo clerk",
        sent=now(),
    )


@pytest.fixture
def real_transaction_source():
    csv = open(
        os.path.join(os.path.dirname(__file__), "fixtures/transactions.csv")
    ).read()
    f = SimpleUploadedFile("testresource.csv", csv.encode())
    return RealTransactionSource.objects.create(source_file=f)


def account_helper(name, cat, **kwargs):
    def f():
        account = Account.objects.create(account_category=cat, **kwargs)
        yield account
        account.debits.all().delete()
        account.credits.all().delete()
        account.delete()

    f.__name__ = name
    return pytest.fixture(f)


fee_account = account_helper("fee_account", "member_fees")
income_account = account_helper("income_account", AccountCategory.INCOME)
receivable_account = account_helper("receivable_account", AccountCategory.ASSET)
bank_account = account_helper("asset_account", AccountCategory.ASSET)
