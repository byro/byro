import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.shortcuts import reverse
from django.utils.timezone import now

from byro.bookkeeping.models import DocumentTransactionLink, Transaction
from byro.bookkeeping.special_accounts import SpecialAccounts
from byro.documents.models import Document

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


def transaction_detail_url(transaction):
    return reverse("office:finance.transactions.detail", kwargs={"pk": transaction.pk})


def credit_fees(amount):
    return {"account": SpecialAccounts.fees_receivable.pk, "credit_value": amount}


@pytest.mark.django_db
def test_transaction_post_without_in_account(logged_in_client, configuration):
    transaction = bank_booking(None)
    response = logged_in_client.post(
        transaction_detail_url(transaction), credit_fees("10")
    )
    assert response.status_code == 302
    assert response["Location"] == transaction_detail_url(transaction)
    assert transaction.bookings.count() == 2


@pytest.mark.django_db
def test_transaction_post_keeps_in_account_while_unbalanced(
    logged_in_client, configuration
):
    transaction = bank_booking(None)
    account = SpecialAccounts.bank
    response = logged_in_client.post(
        transaction_detail_url(transaction) + f"?in_account={account.pk}",
        credit_fees("10"),
    )
    assert response.status_code == 302
    assert response["Location"] == (
        transaction_detail_url(transaction) + f"?in_account={account.pk}"
    )
    assert transaction.bookings.count() == 2


@pytest.mark.django_db
def test_transaction_post_balanced_returns_to_unbalanced_in_account(
    logged_in_client, configuration
):
    transaction = bank_booking(None)
    bank_booking(None)
    account = SpecialAccounts.bank
    response = logged_in_client.post(
        transaction_detail_url(transaction) + f"?in_account={account.pk}",
        credit_fees("25"),
    )
    assert response.status_code == 302
    assert response["Location"] == (
        reverse("office:finance.accounts.detail", kwargs={"pk": account.pk})
        + "?filter=unbalanced"
    )


@pytest.mark.django_db
def test_transaction_post_balanced_returns_to_account_list(
    logged_in_client, configuration
):
    transaction = bank_booking(None)
    response = logged_in_client.post(
        transaction_detail_url(transaction) + f"?in_account={SpecialAccounts.bank.pk}",
        credit_fees("25"),
    )
    assert response.status_code == 302
    assert response["Location"] == reverse("office:finance.accounts.list")


@pytest.mark.django_db
def test_transaction_post_redirect_uses_account_pk_not_raw_value(
    logged_in_client, configuration
):
    transaction = bank_booking(None)
    account = SpecialAccounts.bank
    response = logged_in_client.post(
        transaction_detail_url(transaction),
        credit_fees("10"),
        query_params={
            "in_account": f"0{account.pk}",
            "next": "https://evil.example/",
        },
    )
    assert response.status_code == 302
    assert response["Location"] == (
        transaction_detail_url(transaction) + f"?in_account={account.pk}"
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "in_account",
    (
        "",
        "abc",
        "999999",
        "//evil.example/",
        "https://evil.example/",
        "1&next=//evil.example/",
        "1\r\nLocation: https://evil.example/",
    ),
)
@pytest.mark.parametrize("amount", ("10", "25"))
def test_transaction_post_with_invalid_in_account(
    logged_in_client, configuration, in_account, amount
):
    transaction = bank_booking(None)
    response = logged_in_client.post(
        transaction_detail_url(transaction),
        credit_fees(amount),
        query_params={"in_account": in_account},
    )
    assert response.status_code == 404
    assert "Location" not in response
    assert transaction.bookings.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("in_account", ("abc", "999999"))
def test_transaction_upload_with_invalid_in_account(
    logged_in_client, configuration, in_account
):
    transaction = bank_booking(None)
    response = logged_in_client.post(
        transaction_detail_url(transaction),
        {
            "upload_form-document": SimpleUploadedFile("receipt.txt", b"a receipt"),
            "upload_form-date": str(now().date()),
            "upload_form-category": "byro.bookkeeping.receipt",
            "upload_form-direction": "incoming",
        },
        query_params={"in_account": in_account},
    )
    assert response.status_code == 404
    assert "Location" not in response
    assert not Document.objects.exists()
    assert not DocumentTransactionLink.objects.exists()
    assert transaction.bookings.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("in_account", ("abc", "999999"))
def test_transaction_post_with_invalid_form_and_invalid_in_account(
    logged_in_client, configuration, in_account
):
    transaction = bank_booking(None)
    response = logged_in_client.post(
        transaction_detail_url(transaction),
        {"credit_value": "10"},
        query_params={"in_account": in_account},
    )
    assert response.status_code == 404
    assert "Location" not in response
    assert transaction.bookings.count() == 1
    assert not Document.objects.exists()
    assert not DocumentTransactionLink.objects.exists()
