from datetime import date
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from byro.bookkeeping.bank_import import (
    BankTransactionImporter,
    ImportedBankTransaction,
    InvalidImportFile,
)
from byro.bookkeeping.models import Booking, RealTransactionSource
from byro.bookkeeping.models.real_transaction import SourceState
from byro.bookkeeping.signals import bank_transaction_importers, process_csv_upload
from byro.office.views.upload import LEGACY_IMPORTER_CHOICE

pytestmark = pytest.mark.usefixtures("configuration")


class LineImporter(BankTransactionImporter):
    """Imports one transaction per line: ``<amount>;<memo>[;<external id>]``."""

    identifier = "test.lines"
    label = "Line importer"

    def parse(self, source):
        content = source.source_file.read().decode("utf-8")
        for lineno, line in enumerate(content.splitlines(), start=1):
            parts = line.split(";")
            if len(parts) < 2:
                raise InvalidImportFile()
            yield ImportedBankTransaction(
                booking_date=date(2026, 9, 1),
                amount=Decimal(parts[0]),
                memo=parts[1],
                external_id=parts[2] if len(parts) > 2 else None,
            )


@pytest.fixture
def line_importer():
    importer = LineImporter()

    def register(sender, **kwargs):
        return importer

    bank_transaction_importers.connect(register, dispatch_uid="test-lines")
    yield importer
    bank_transaction_importers.disconnect(register, dispatch_uid="test-lines")


@pytest.fixture
def legacy_receiver():
    calls = []

    def legacy(sender, **kwargs):
        calls.append(sender)
        return []

    process_csv_upload.connect(legacy, dispatch_uid="test-legacy")
    yield calls
    process_csv_upload.disconnect(legacy, dispatch_uid="test-legacy")


def upload(client, importer, content, name="statement.csv"):
    return client.post(
        reverse("office:finance.uploads.add"),
        {"importer": importer, "source_file": SimpleUploadedFile(name, content)},
        follow=True,
    )


@pytest.mark.django_db
def test_import_page_lists_importers(logged_in_client, line_importer):
    response = logged_in_client.get(reverse("office:finance.uploads.add"))
    content = response.content.decode()
    assert response.status_code == 200
    assert "Import bank transactions" in content
    assert 'value="test.lines"' in content
    assert "Line importer" in content
    assert "Legacy bank importer" not in content
    assert "No bank transaction importer is installed" not in content


@pytest.mark.django_db
def test_import_page_without_importers_shows_warning(logged_in_client):
    response = logged_in_client.get(reverse("office:finance.uploads.add"))
    content = response.content.decode()
    assert "No bank transaction importer is installed" in content
    assert "disabled" in content


@pytest.mark.django_db
def test_import_page_offers_legacy_importer_when_receiver_exists(
    logged_in_client, legacy_receiver
):
    response = logged_in_client.get(reverse("office:finance.uploads.add"))
    assert f'value="{LEGACY_IMPORTER_CHOICE}"' in response.content.decode()


@pytest.mark.django_db
def test_upload_with_importer_imports_and_reports_counts(
    logged_in_client, line_importer, legacy_receiver
):
    response = upload(
        logged_in_client, "test.lines", b"25.00;Fee Max;REF-1\n-80.00;Invoice;REF-2\n"
    )
    content = response.content.decode()
    assert response.status_code == 200, content
    assert "Import successful" in content
    assert "2 transactions read" in content
    assert "2 newly imported" in content
    assert "0 already known" in content

    source = RealTransactionSource.objects.get()
    assert source.importer == "test.lines"
    assert source.state == SourceState.PROCESSED
    assert source.imported_count == 2
    assert source.duplicate_count == 0
    assert Booking.objects.filter(source=source).count() == 2
    assert legacy_receiver == []

    response = upload(
        logged_in_client, "test.lines", b"25.00;Fee Max;REF-1\n10.00;Donation;REF-3\n"
    )
    content = response.content.decode()
    assert "1 newly imported" in content
    assert "1 already known" in content
    assert Booking.objects.filter(source__isnull=False).count() == 3


@pytest.mark.django_db
def test_upload_with_invalid_file_reports_error_and_failed_state(
    logged_in_client, line_importer
):
    response = upload(logged_in_client, "test.lines", b"garbage\n")
    content = response.content.decode()
    assert "could not be imported" in content
    assert "could not be processed by the selected bank transaction importer" in content
    source = RealTransactionSource.objects.get()
    assert source.state == SourceState.FAILED
    assert Booking.objects.filter(source=source).count() == 0


@pytest.mark.django_db
def test_upload_with_unsupported_currency_reports_error(logged_in_client):
    class UsdImporter(LineImporter):
        identifier = "test.usd"

        def parse(self, source):
            yield ImportedBankTransaction(
                booking_date=date(2026, 9, 1), amount=Decimal("1"), currency="USD"
            )

    register = lambda sender, **kwargs: UsdImporter()  # noqa: E731
    bank_transaction_importers.connect(register, dispatch_uid="test-usd")
    try:
        response = upload(logged_in_client, "test.usd", b"x")
    finally:
        bank_transaction_importers.disconnect(register, dispatch_uid="test-usd")
    assert "unsupported currency USD" in response.content.decode()
    assert Booking.objects.filter(source__isnull=False).count() == 0


@pytest.mark.django_db
def test_upload_with_legacy_choice_uses_legacy_signal(
    logged_in_client, line_importer, legacy_receiver
):
    response = upload(logged_in_client, LEGACY_IMPORTER_CHOICE, b"whatever")
    assert "processed successfully" in response.content.decode()
    source = RealTransactionSource.objects.get()
    assert source.importer is None
    assert legacy_receiver == [source]
    assert source.state == SourceState.PROCESSED


@pytest.mark.django_db
def test_upload_rejects_unknown_importer_choice(logged_in_client, line_importer):
    response = upload(logged_in_client, "evil.importer", b"x")
    assert response.status_code == 200
    assert RealTransactionSource.objects.count() == 0
    assert "valid choice" in response.content.decode()


@pytest.mark.django_db
@override_settings(BANK_TRANSACTION_IMPORT_MAX_FILE_SIZE=16)
def test_upload_rejects_oversized_files(logged_in_client, line_importer):
    response = upload(logged_in_client, "test.lines", b"25.00;" + b"x" * 100)
    assert "larger than the allowed maximum" in response.content.decode()
    assert RealTransactionSource.objects.count() == 0


@pytest.mark.django_db
def test_upload_list_shows_importer_and_counts(logged_in_client, line_importer):
    upload(logged_in_client, "test.lines", b"25.00;Fee;REF-1\n25.00;Fee;REF-1\n")
    response = logged_in_client.get(reverse("office:finance.uploads.list"))
    content = response.content.decode()
    assert response.status_code == 200
    assert "Line importer" in content
    assert "statement" in content
    assert '<td class="text-right">1</td>' in content


@pytest.mark.django_db
def test_reprocess_view_reports_duplicates(logged_in_client, line_importer):
    upload(logged_in_client, "test.lines", b"25.00;Fee;REF-1\n")
    source = RealTransactionSource.objects.get()
    response = logged_in_client.post(
        reverse("office:finance.uploads.process", kwargs={"pk": source.pk}),
        follow=True,
    )
    content = response.content.decode()
    assert "0 newly imported" in content
    assert "1 already known" in content
    assert Booking.objects.filter(source=source).count() == 1
