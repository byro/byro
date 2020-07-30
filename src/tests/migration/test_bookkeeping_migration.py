import pytest
from django.db.models import Q
from helper import TestMigrations


class TestWithShackdataBase(TestMigrations):
    app = "bookkeeping"
    migrate_fixtures = ["tests/fixtures/test_shackspace_transactions.json"]
    migrate_from = "0012_auto_20180617_1926"


@pytest.mark.xfail
@pytest.mark.django_db
class TestBookkeepingMigrationsFirst(TestWithShackdataBase):
    migrate_to = "0013_new_data_model"

    def setUpBeforeMigration(self, apps):
        RealTransaction = apps.get_model("bookkeeping", "RealTransaction")
        VirtualTransaction = apps.get_model("bookkeeping", "VirtualTransaction")

        # For test comparison
        self.real_transaction_count = RealTransaction.objects.count()
        self.virtual_transaction_w_src_count = VirtualTransaction.objects.filter(
            source_account__isnull=False
        ).count()
        self.virtual_transaction_w_dst_count = VirtualTransaction.objects.filter(
            destination_account__isnull=False
        ).count()
        self.virtual_transaction_member_fees_count = VirtualTransaction.objects.filter(
            Q(
                source_account__isnull=True,
                destination_account__account_category="member_fees",
                real_transaction__isnull=True,
            )
            | Q(
                destination_account__isnull=True,
                source_account__account_category="member_fees",
                real_transaction__isnull=True,
            )
        ).count()
        self.orphan_virtual_transaction_count = VirtualTransaction.objects.filter(
            real_transaction=None
        ).count()

        self.reversed_transactions = {
            rt: rt.reverses
            for rt in RealTransaction.objects.filter(reverses__isnull=False).all()
        }

    def test_accounts_migrated(self):
        from byro.bookkeeping.models import Account

        assert Account.objects.filter(tags__name="bank").count() == 1
        assert Account.objects.filter(tags__name="fees").count() == 1
        assert Account.objects.filter(tags__name="fees_receivable").count() == 1

    def test_transactions_migrated(self):
        from byro.bookkeeping.models import Booking, Transaction

        # All RealTransaction lead to one Transaction, as do VirtualTransaction with no RealTransaction
        assert (
            Transaction.objects.count()
            == self.real_transaction_count + self.orphan_virtual_transaction_count
        )

        # All VirtualTransaction lead to one Booking per direction, as does each RealTransaction
        #  VirtualTransaction referencing 'member_fees' have an additional implicit direction
        assert (
            Booking.objects.count()
            == self.virtual_transaction_w_src_count
            + self.virtual_transaction_w_dst_count
            + self.real_transaction_count
            + self.virtual_transaction_member_fees_count
        )

    def test_reverses_migrated(self):
        assert len(self.reversed_transactions) > 0

        from byro.bookkeeping.models import Transaction

        for rt, rt_reverses in self.reversed_transactions.items():
            t = Transaction.objects.filter(
                Q(memo=rt.purpose) | Q(bookings__memo=rt.purpose)
            ).first()
            t_reverses = Transaction.objects.filter(
                Q(memo=rt_reverses.purpose) | Q(bookings__memo=rt_reverses.purpose)
            ).first()

            assert t
            assert t_reverses
            assert t.reverses == t_reverses

    def test_amounts_migrated(self):
        from byro.bookkeeping.models import Booking

        assert Booking.objects.filter(amount__lt=0).count() == 0


@pytest.mark.xfail
@pytest.mark.django_db
class TestBookkeepingMigrationsFinal(TestWithShackdataBase):
    migrate_to = "0014_auto_20180707_1410"

    def test_accounts_migrated_fully(self):
        from byro.bookkeeping.models import Account, AccountCategory

        assert (
            Account.objects.exclude(
                account_category__in=[
                    AccountCategory.ASSET,
                    AccountCategory.LIABILITY,
                    AccountCategory.INCOME,
                    AccountCategory.EXPENSE,
                    AccountCategory.EQUITY,
                ]
            ).count()
            == 0
        )
