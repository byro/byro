import pytest
from django.utils.timezone import now


@pytest.mark.django_db
def test_account_model_str(fee_account):
    assert str(fee_account) == 'member_fees account #{}'.format(fee_account.id)
    fee_account.name = 'foo'
    assert str(fee_account) == 'foo'


@pytest.mark.django_db
def test_account_methods(fee_account):
    assert not fee_account.transactions
    assert fee_account.total_in(start=now()) == 0
    assert fee_account.total_out(start=now()) == 0
