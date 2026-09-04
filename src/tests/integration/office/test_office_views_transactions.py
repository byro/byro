import pytest
from django.shortcuts import reverse
from django.utils.timezone import now

from byro.bookkeeping.models import Transaction
from byro.bookkeeping.special_accounts import SpecialAccounts

COUNTERPARTY_DATA = (
    {"counterparty_name": "Max Mustermann"},
    {"other_party": "Max Mustermann"},
)


def bank_booking(data):
    transaction = Transaction.objects.create(
        memo="NLL123 Jahresbeitrag", value_datetime=now(), user_or_context="test"
    )
    transaction.debit(
        account=SpecialAccounts.bank,
        amount=25,
        memo="NLL123 Jahresbeitrag",
        data=data,
        user_or_context="test",
    )
    return transaction


@pytest.mark.django_db
@pytest.mark.parametrize("data", COUNTERPARTY_DATA)
def test_transaction_detail_shows_counterparty(logged_in_client, configuration, data):
    transaction = bank_booking(data)
    response = logged_in_client.get(
        reverse("office:finance.transactions.detail", kwargs={"pk": transaction.pk})
    )
    assert response.status_code == 200
    assert "Max Mustermann" in response.content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize("data", COUNTERPARTY_DATA)
def test_account_detail_shows_counterparty(logged_in_client, configuration, data):
    bank_booking(data)
    response = logged_in_client.get(
        reverse(
            "office:finance.accounts.detail", kwargs={"pk": SpecialAccounts.bank.pk}
        )
    )
    assert response.status_code == 200
    assert "Max Mustermann" in response.content.decode()


@pytest.mark.django_db
def test_transaction_detail_without_counterparty(logged_in_client, configuration):
    transaction = bank_booking(None)
    response = logged_in_client.get(
        reverse("office:finance.transactions.detail", kwargs={"pk": transaction.pk})
    )
    assert response.status_code == 200
    assert "NLL123 Jahresbeitrag" in response.content.decode()
