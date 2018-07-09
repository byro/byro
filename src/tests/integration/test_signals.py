from collections import Counter

import pytest

from byro.bookkeeping.signals import process_transaction
from byro.bookkeeping.special_accounts import SpecialAccounts
from byro.members.models import Member


class connected_signal:
    """ connect a signal and make sure it is disconnected after use, so it doesn't leak into other tests. """

    def __init__(self, signal, receiver, uid='test-plugin'):
        self.signal = signal
        self.receiver = receiver
        self.dispatch_uid = uid

    def __enter__(self):
        self.signal.connect(self.receiver, dispatch_uid=self.dispatch_uid)

    def __exit__(self, exc_type, exc_value, tb):
        self.signal.disconnect(self.receiver, dispatch_uid=self.dispatch_uid)


@pytest.mark.django_db
def test_match_single_fee(member, partial_transaction):
    call_log = []

    def derive_test_transaction(sender, signal):
        call_log.append(True)
        if sender.is_read_only:
            return False
        if not sender.is_balanced:
            member = Member.objects.first()
            sender.credit(account=SpecialAccounts.fees_receivable, amount=10, member=member)
            return True
        return False

    with connected_signal(process_transaction, derive_test_transaction):
        assert partial_transaction.process_transaction() == 1

    assert len(call_log) == 2

    assert partial_transaction.is_balanced
    assert SpecialAccounts.fees_receivable.balances(end=None)['credit'] == partial_transaction.bookings.first().amount


@pytest.mark.django_db
def test_match_no_fee(member, partial_transaction):

    def derive_test_transaction(sender, signal):
        return False

    with pytest.raises(Exception) as excinfo:
        with connected_signal(process_transaction, derive_test_transaction):
            partial_transaction.process_transaction()

    assert 'No plugin tried to augment' in str(excinfo)

    assert not partial_transaction.is_balanced
    assert SpecialAccounts.fees_receivable.balances(end=None)['credit'] == 0


@pytest.mark.django_db
def test_match_multiple_fees(member, partial_transaction):
    call_log = Counter()

    def derive_test_transaction_donation(sender, signal):
        call_log['d'] += 1
        if sender.is_read_only:
            return False
        if not sender.is_balanced:
            member = Member.objects.first()
            sender.credit(account=SpecialAccounts.donations, amount=5, member=member)
            return True
        return False

    def derive_test_transaction_fee(sender, signal):
        call_log['f'] += 1
        if sender.is_read_only:
            return False
        if not sender.is_balanced:
            member = Member.objects.first()
            sender.credit(account=SpecialAccounts.fees_receivable, amount=5, member=member)
            return True
        return False

    with connected_signal(process_transaction, derive_test_transaction_donation, 'test-donation'):
        with connected_signal(process_transaction, derive_test_transaction_fee, 'test-fee'):
            partial_transaction.process_transaction()

    assert dict(call_log) == {'d': 2, 'f': 2}

    assert SpecialAccounts.fees_receivable.balances(end=None)['credit'] == 5
    assert SpecialAccounts.donations.balances(end=None)['credit'] == 5
