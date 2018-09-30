from datetime import timedelta

from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from byro.bookkeeping.models import Transaction
from byro.bookkeeping.special_accounts import SpecialAccounts
from byro.common.models.configuration import Configuration
from byro.members.models import FeeIntervals, Member, Membership, MembershipType

SOURCE_TEST_DATA='Import of test data'

def make_date(delta, end=False):
    date = (now() - delta).date()
    date = date.replace(day=1)
    if end:
        date = date + relativedelta(month=1)
        return date - timedelta(days=1)
    return date


class Command(BaseCommand):
    help = "Introduce test data, including members and payments"
    leave_locale_alone = True

    def create_configs(self):
        config = Configuration.get_solo()
        config.name = 'Der Verein DER VEREIN'
        config.address = 'Erich-Weinert-Straße 53\n39104 Magdeburg'
        config.url = 'https://dervereindervere.in'
        config.language = 'de'
        config.currency = 'EUR'
        config.mail_from = 'verein@dervereindervere.in'
        config.backoffice_mail = 'vorstanz@dervereindervere.in'
        config.save()
        config.log(None, 'byro.settings.changed', source=SOURCE_TEST_DATA)

    def make_paid(self, member, vaguely=False, overly=False, donates=0, pays_for=None):
        member.update_liabilites()
        for index, liability in enumerate(member.bookings.filter(debit_account=SpecialAccounts.fees_receivable, transaction__value_datetime__lte=now()).all()):
            if vaguely and index % 2 == 0:
                continue

            pure_amount = liability.amount if not overly else liability.amount * 2

            text = _("Member fee for {number}").format(number=member.number)

            if pays_for:
                amount = pure_amount * 2
                text += ", " + _("and for {number}").format(number=pays_for.number)
            else:
                amount = pure_amount

            if donates:
                amount += donates
                text += ", " + _("EUR {amount} donation").format(amount=donates)

            t = Transaction.objects.create(
                value_datetime=liability.transaction.value_datetime
            )
            t.debit(
                memo=text,
                account=SpecialAccounts.bank, amount=amount
            )
            if donates:
                t.credit(account=SpecialAccounts.donations, member=member, amount=donates)
            t.credit(account=SpecialAccounts.fees_receivable, member=member, amount=pure_amount)
            if pays_for:
                t.credit(account=SpecialAccounts.fees_receivable, member=pays_for, amount=pure_amount)
            t.save()
            t.log(None, 'byro.bookkeeping.transaction.created', source=SOURCE_TEST_DATA)

    def create_membership_types(self):
        MembershipType.objects.create(name='Standard membership', amount=120)

    def create_members(self):
        has_left = Member.objects.create(
            number='1',
            name='Francis Foundingmember',
            address='Foo St 1\nSome Place',
            email='francis@group.org',
        )
        Membership.objects.create(
            member=has_left,
            start=make_date(relativedelta(years=2)),
            end=make_date(relativedelta(years=1), end=True),
            interval=FeeIntervals.MONTHLY,
            amount=10,
        )
        self.make_paid(has_left)
        has_left.log(None, 'byro.members.created', source=SOURCE_TEST_DATA)

        does_not_pay = Member.objects.create(
            number='2',
            name='Yohnny Yolo',
            address='Bar St 1\nSome Distant Place',
            email='yolo@group.org',
        )
        Membership.objects.create(
            member=does_not_pay,
            start=make_date(relativedelta(years=4)),
            interval=FeeIntervals.MONTHLY,
            amount=10,
        )
        does_not_pay.update_liabilites()
        does_not_pay.log(None, 'byro.members.created', source=SOURCE_TEST_DATA)

        pays_occasionally = Member.objects.create(
            number='3',
            name='Olga Occasional',
            address='Currently unknown',
            email='olga@group.org',
        )
        Membership.objects.create(
            member=pays_occasionally,
            start=make_date(relativedelta(years=4, months=6)),
            interval=FeeIntervals.MONTHLY,
            amount=10,
        )
        self.make_paid(pays_occasionally, vaguely=True)
        pays_occasionally.log(None, 'byro.members.created', source=SOURCE_TEST_DATA)

        pays_regularly = Member.objects.create(
            number='4',
            name='Dennis Diligent',
            address='Best St 3\nFoo Town\nMy Country\nEarth\nUniverse',
            email='dennis@group.org',
        )
        Membership.objects.create(
            member=pays_regularly,
            start=make_date(relativedelta(years=1, months=3)),
            interval=FeeIntervals.MONTHLY,
            amount=10,
        )
        self.make_paid(pays_regularly)
        pays_regularly.log(None, 'byro.members.created', source=SOURCE_TEST_DATA)

        pays_too_much = Member.objects.create(
            number='5',
            name='Omar Overachiever',
            address='SuperBest St 3\nSuperFoo Town',
            email='omar@group.org',
        )
        Membership.objects.create(
            member=pays_too_much,
            start=make_date(relativedelta(years=1)),
            interval=FeeIntervals.MONTHLY,
            amount=10,
        )
        self.make_paid(pays_too_much, overly=True)
        pays_too_much.log(None, 'byro.members.created', source=SOURCE_TEST_DATA)

        will_join = Member.objects.create(
            number='6',
            name='Francine Futuremember',
            address='Future St 3\nFuture Town',
            email='francine@group.org',
        )
        Membership.objects.create(
            member=will_join,
            start=make_date(relativedelta(months=-2)),
            interval=FeeIntervals.MONTHLY,
            amount=10,
        )
        will_join.log(None, 'byro.members.created', source=SOURCE_TEST_DATA)

        giver = Member.objects.create(
            number='7',
            name='George Giver',
            address='Generous St 3\nEnd-of-the-rainbow Hearth',
            email='george@group.org',
        )
        Membership.objects.create(
            member=giver,
            start=make_date(relativedelta(years=1)),
            interval=FeeIntervals.MONTHLY,
            amount=10,
        )
        self.make_paid(giver, donates=5)
        giver.log(None, 'byro.members.created', source=SOURCE_TEST_DATA)

        is_payed_for = Member.objects.create(
            number='8',
            name='Peter Partner',
            address='Commune St 3\nFamily Shire',
            email='peter@group.org',
        )
        Membership.objects.create(
            member=is_payed_for,
            start=make_date(relativedelta(months=3)),
            interval=FeeIntervals.MONTHLY,
            amount=10,
        )
        is_payed_for.update_liabilites()
        is_payed_for.log(None, 'byro.members.created', source=SOURCE_TEST_DATA)

        pays_other = Member.objects.create(
            number='9',
            name='Aaron Alsopayer',
            address='Commune St 3\nFamily Shire',
            email='aaron@group.org',
        )
        Membership.objects.create(
            member=pays_other,
            start=make_date(relativedelta(months=3)),
            interval=FeeIntervals.MONTHLY,
            amount=10,
        )
        self.make_paid(pays_other, pays_for=is_payed_for)
        pays_other.log(None, 'byro.members.created', source=SOURCE_TEST_DATA)

    def create_bank_chaff(self):
        "Create some dummy traffic, and a couple of unmatched transactions on the bank account"
        bank_account = SpecialAccounts.bank

        t = Transaction.objects.create(
            value_datetime=(now()-relativedelta(days=23)).date(),
        )
        t.debit(
            memo=_("Belated member fee payment for Olga"),
            account=bank_account, amount=20
        )
        t.save()
        t.log(None, 'byro.bookkeeping.transaction.created', source=SOURCE_TEST_DATA)

        t = Transaction.objects.create(
            value_datetime=(now()-relativedelta(days=17)).date(),
        )
        t.debit(
            memo=_("George lives to give, donation"),
            account=bank_account, amount=42.23
        )
        t.save()
        t.log(None, 'byro.bookkeeping.transaction.created', source=SOURCE_TEST_DATA)

        for i in range(1, 4):
            t = Transaction.objects.create(
                value_datetime=(now()-relativedelta(months=i)).date(),
            )
            t.credit(
                memo=_("Bank fees"),
                account=bank_account, amount=9.95
            )
            t.save()
            t.log(None, 'byro.bookkeeping.transaction.created', source=SOURCE_TEST_DATA)

        t = Transaction.objects.create(
            value_datetime=(now()-relativedelta(days=21)).date(),
        )
        t.credit(
            memo=_("ACME Inc. thanks you for your patronage, sale of one halo kite"),
            account=bank_account, amount=123
        )
        t.save()
        t.log(None, 'byro.bookkeeping.transaction.created', source=SOURCE_TEST_DATA)

        t = Transaction.objects.create(
            value_datetime=(now()-relativedelta(days=20)).date(),
        )
        t.credit(
            memo=_("ACME Inc. thanks you for your patronage, sale of one emergency medkit"),
            account=bank_account, amount=666
        )
        t.save()
        t.log(None, 'byro.bookkeeping.transaction.created', source=SOURCE_TEST_DATA)

    @transaction.atomic()
    def handle(self, *args, **options):
        self.create_configs()
        self.create_membership_types()
        self.create_members()
        self.create_bank_chaff()
