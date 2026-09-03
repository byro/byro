from contextlib import suppress
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.utils import timezone

from byro.bookkeeping.bank_import import (
    BankTransactionImporter,
    BankTransactionImportService,
    ImportedBankTransaction,
    ImporterError,
    InvalidBankTransaction,
    InvalidImportFile,
    UnknownImporter,
    UnsupportedCurrency,
    get_bank_transaction_importer,
    get_bank_transaction_importers,
    identity,
)
from byro.bookkeeping.models import Booking, RealTransactionSource, Transaction
from byro.bookkeeping.models.real_transaction import SourceState
from byro.bookkeeping.signals import (
    bank_transaction_importers,
    process_csv_upload,
    process_transaction,
)
from byro.bookkeeping.special_accounts import SpecialAccounts


class connected_signal:
    """Connect a receiver for the duration of a ``with`` block."""

    def __init__(self, signal, receiver, uid="test-bank-import"):
        self.signal = signal
        self.receiver = receiver
        self.uid = uid

    def __enter__(self):
        self.signal.connect(self.receiver, dispatch_uid=self.uid)
        return self.receiver

    def __exit__(self, *exc):
        self.signal.disconnect(self.receiver, dispatch_uid=self.uid)


class ListImporter(BankTransactionImporter):
    """Test importer yielding a predefined list of transactions."""

    identifier = "test.list"
    label = "Test list importer"

    def __init__(self, transactions=(), identifier=None, label=None):
        self.transactions = list(transactions)
        if identifier:
            self.identifier = identifier
        if label:
            self.label = label
        self.parsed_sources = []

    def parse(self, source):
        self.parsed_sources.append(source)
        yield from self.transactions


def registered(importer, uid="test-importer"):
    return connected_signal(
        bank_transaction_importers, lambda sender, **kwargs: importer, uid
    )


def make_source(importer=None):
    return RealTransactionSource.objects.create(
        source_file=SimpleUploadedFile("statement.txt", b"irrelevant"),
        importer=importer,
    )


def tx(amount="25.00", **kwargs):
    if isinstance(amount, str):
        with suppress(InvalidOperation):
            amount = Decimal(amount)
    defaults = dict(
        booking_date=date(2026, 9, 1),
        amount=amount,
        memo="NLL123 Jahresbeitrag",
        counterparty_name="Max Mustermann",
        counterparty_iban="DE12 3456 7890 1234 5678 90",
    )
    defaults.update(kwargs)
    return ImportedBankTransaction(**defaults)


# -- registry --------------------------------------------------------------


def test_registry_lists_registered_importer():
    importer = ListImporter()
    with registered(importer):
        importers = get_bank_transaction_importers()
    assert importers == {"test.list": importer}
    assert get_bank_transaction_importers() == {}


def test_registry_resolves_by_identifier():
    importer = ListImporter()
    with registered(importer):
        assert get_bank_transaction_importer("test.list") is importer


def test_registry_unknown_identifier():
    with pytest.raises(UnknownImporter) as excinfo:
        get_bank_transaction_importer("does.not.exist")
    assert excinfo.value.identifier == "does.not.exist"
    assert "not available" in str(excinfo.value)


def test_registry_accepts_lists_and_sorts_by_label():
    a = ListImporter(identifier="test.a", label="Zebra")
    b = ListImporter(identifier="test.b", label="Alpha")
    with registered([a, b]):
        assert list(get_bank_transaction_importers()) == ["test.b", "test.a"]


def test_registry_skips_invalid_and_duplicate_importers(caplog):
    class Broken:
        identifier = ""
        label = "Broken"

    first = ListImporter(identifier="test.dup", label="First")
    second = ListImporter(identifier="test.dup", label="Second")
    with registered([Broken(), first, None], "one"), registered(second, "two"):
        importers = get_bank_transaction_importers()
    assert importers == {"test.dup": first}


def test_registry_survives_failing_receiver(caplog):
    def broken(sender, **kwargs):
        raise RuntimeError("plugin is broken")

    with connected_signal(bank_transaction_importers, broken, "broken"), registered(
        ListImporter()
    ):
        assert list(get_bank_transaction_importers()) == ["test.list"]
    assert "registration failed" in caplog.text


# -- data model ------------------------------------------------------------


@pytest.mark.django_db
def test_import_incoming_payment_debits_bank_account():
    source = make_source()
    importer = ListImporter([tx("25.00", external_id="REF-1")])
    result = BankTransactionImportService().import_transactions(
        source, importer.parse(source), importer
    )

    assert result.imported_count == 1
    assert result.duplicate_count == 0
    assert result.read_count == 1
    [t] = result.transactions
    booking = t.bookings.get()
    assert booking.debit_account == SpecialAccounts.bank
    assert booking.credit_account is None
    assert booking.amount == Decimal("25.00")
    assert booking.memo == "NLL123 Jahresbeitrag"
    assert t.memo == "NLL123 Jahresbeitrag"
    assert booking.source == source
    assert booking.importer == "test.list"
    assert booking.import_identity
    assert t.value_datetime.date() == date(2026, 9, 1)
    assert t.booking_datetime.date() == date(2026, 9, 1)
    assert timezone.is_aware(t.value_datetime)
    assert source.transactions.get() == t


@pytest.mark.django_db
def test_import_outgoing_payment_credits_bank_account():
    source = make_source()
    importer = ListImporter([tx("-80.00", memo="Invoice 4711")])
    result = BankTransactionImportService().import_transactions(
        source, importer.parse(source), importer
    )
    booking = result.transactions[0].bookings.get()
    assert booking.credit_account == SpecialAccounts.bank
    assert booking.debit_account is None
    assert booking.amount == Decimal("80.00")


@pytest.mark.django_db
def test_import_stores_normalized_metadata_without_interpreting_it():
    source = make_source()
    importer = ListImporter(
        [
            tx(
                value_date=date(2026, 9, 2),
                counterparty_bic="COBA DEFF",
                end_to_end_id="E2E-1",
                mandate_id="MANDATE-1",
                creditor_id="DE98ZZZ09999999999",
                bank_reference="BANKREF",
                transaction_code="NTRF",
                external_id="ACCT-SVCR-REF",
                data={"entry_reference": "42", "counterparty_iban": "overridden"},
            )
        ]
    )
    [t] = (
        BankTransactionImportService()
        .import_transactions(source, importer.parse(source), importer)
        .transactions
    )
    booking = t.bookings.get()
    assert booking.data == {
        "entry_reference": "42",
        "counterparty_name": "Max Mustermann",
        "counterparty_iban": "DE12345678901234567890",
        "counterparty_bic": "COBADEFF",
        "external_id": "ACCT-SVCR-REF",
        "end_to_end_id": "E2E-1",
        "mandate_id": "MANDATE-1",
        "creditor_id": "DE98ZZZ09999999999",
        "bank_reference": "BANKREF",
        "transaction_code": "NTRF",
    }
    assert t.value_datetime.date() == date(2026, 9, 2)
    assert t.booking_datetime.date() == date(2026, 9, 1)


@pytest.mark.django_db
def test_import_accepts_aware_datetimes_and_lowercase_currency():
    source = make_source()
    when = timezone.make_aware(datetime(2026, 9, 1, 14, 30))
    importer = ListImporter([tx(booking_date=when, currency="eur")])
    [t] = (
        BankTransactionImportService()
        .import_transactions(source, importer.parse(source), importer)
        .transactions
    )
    assert t.value_datetime == when


# -- validation ------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "amount", [Decimal("0"), Decimal("1.005"), 25.0, Decimal("1000000.00"), "abc"]
)
def test_import_rejects_invalid_amounts(amount):
    source = make_source()
    importer = ListImporter([tx(), tx(amount=amount)])
    with pytest.raises(InvalidBankTransaction) as excinfo:
        BankTransactionImportService().import_transactions(
            source, importer.parse(source), importer
        )
    assert excinfo.value.position == 2
    assert Booking.objects.filter(source=source).count() == 0


@pytest.mark.django_db
def test_import_rejects_unsupported_currency_explicitly():
    source = make_source()
    importer = ListImporter([tx(currency="USD")])
    with pytest.raises(UnsupportedCurrency) as excinfo:
        BankTransactionImportService().import_transactions(
            source, importer.parse(source), importer
        )
    assert excinfo.value.currency == "USD"
    assert "USD" in str(excinfo.value)
    assert isinstance(excinfo.value, InvalidBankTransaction)
    assert Booking.objects.filter(source=source).count() == 0


@pytest.mark.django_db
def test_import_rejects_invalid_date_and_metadata():
    source = make_source()
    importer = ListImporter([tx(booking_date="2026-09-01")])
    with pytest.raises(InvalidBankTransaction):
        BankTransactionImportService().import_transactions(
            source, importer.parse(source), importer
        )
    importer = ListImporter([tx(data={"amount": Decimal("1")})])
    with pytest.raises(InvalidBankTransaction):
        BankTransactionImportService().import_transactions(
            source, importer.parse(source), importer
        )
    importer = ListImporter([object()])
    with pytest.raises(InvalidBankTransaction):
        BankTransactionImportService().import_transactions(
            source, importer.parse(source), importer
        )


@pytest.mark.django_db
def test_import_error_messages_do_not_leak_bank_data():
    source = make_source()
    importer = ListImporter([tx(amount=Decimal("0"), memo="SECRET MEMO")])
    with pytest.raises(InvalidBankTransaction) as excinfo:
        BankTransactionImportService().import_transactions(
            source, importer.parse(source), importer
        )
    assert "SECRET" not in str(excinfo.value)
    assert "Mustermann" not in str(excinfo.value)


# -- duplicate detection ---------------------------------------------------


def run_import(transactions, source=None):
    source = source or make_source()
    importer = ListImporter(transactions)
    return BankTransactionImportService().import_transactions(
        source, importer.parse(source), importer
    )


@pytest.mark.django_db
def test_same_external_id_is_duplicate():
    run_import([tx(external_id="REF-1")])
    result = run_import([tx(external_id="REF-1", memo="changed memo")])
    assert (result.imported_count, result.duplicate_count) == (0, 1)
    assert Booking.objects.filter(import_identity__isnull=False).count() == 1


@pytest.mark.django_db
def test_different_external_id_same_amount_is_not_duplicate():
    run_import([tx(external_id="REF-1")])
    result = run_import([tx(external_id="REF-2")])
    assert (result.imported_count, result.duplicate_count) == (1, 0)


@pytest.mark.django_db
def test_same_fingerprint_without_external_id_is_duplicate():
    run_import([tx()])
    result = run_import([tx(counterparty_iban="de12345678901234567890")])
    assert (result.imported_count, result.duplicate_count) == (0, 1)


@pytest.mark.django_db
def test_same_amount_and_date_different_counterparty_is_not_duplicate():
    run_import([tx()])
    result = run_import(
        [tx(counterparty_iban="DE00 0000 0000 0000 0000 01", counterparty_name="Erika")]
    )
    assert (result.imported_count, result.duplicate_count) == (1, 0)


@pytest.mark.django_db
def test_same_amount_and_date_different_memo_is_not_duplicate():
    run_import([tx(memo="Beitrag Max")])
    result = run_import([tx(memo="Beitrag Erika")])
    assert (result.imported_count, result.duplicate_count) == (1, 0)


@pytest.mark.django_db
def test_identical_transactions_within_one_file_are_all_imported():
    result = run_import([tx(), tx()])
    assert (result.imported_count, result.duplicate_count) == (2, 0)
    identities = set(Booking.objects.values_list("import_identity", flat=True))
    assert len(identities) == 2

    result = run_import([tx(), tx()])
    assert (result.imported_count, result.duplicate_count) == (0, 2)
    result = run_import([tx(), tx(), tx()])
    assert (result.imported_count, result.duplicate_count) == (1, 2)


@pytest.mark.django_db
def test_repeated_external_id_within_one_file_is_duplicate():
    result = run_import([tx(external_id="REF-1"), tx(external_id="REF-1")])
    assert (result.imported_count, result.duplicate_count) == (1, 1)


@pytest.mark.django_db
def test_overlapping_imports_only_add_new_transactions():
    a, b, c, d = (
        tx(booking_date=date(2026, m, 1), memo=f"payment {m}") for m in (1, 2, 3, 4)
    )
    first = run_import([a, b, c])
    assert (first.imported_count, first.duplicate_count) == (3, 0)

    second = run_import([a, b, c, d])
    assert (second.imported_count, second.duplicate_count) == (1, 3)
    assert Transaction.objects.filter(bookings__source__isnull=False).count() == 4
    assert second.transactions[0].memo == "payment 4"


@pytest.mark.django_db
def test_duplicates_are_detected_across_importers():
    source = make_source()
    camt = ListImporter([tx(external_id="REF-1")], identifier="test.camt")
    BankTransactionImportService().import_transactions(source, camt.parse(source), camt)
    other = ListImporter([tx(external_id="REF-1")], identifier="test.other")
    result = BankTransactionImportService().import_transactions(
        make_source(), other.parse(source), other
    )
    assert (result.imported_count, result.duplicate_count) == (0, 1)


def test_identity_is_independent_of_source_and_importer_but_not_of_account():
    a = identity.fingerprint_identity("1", tx())
    assert a == identity.fingerprint_identity("1", tx())
    assert a != identity.fingerprint_identity("2", tx())
    assert a != identity.fingerprint_identity("1", tx(), occurrence=1)
    assert identity.external_identity("1", "X") != identity.fingerprint_identity(
        "1", tx()
    )
    assert identity.normalize_iban(" de12 34 ") == "DE1234"
    assert identity.normalize_amount(Decimal("25")) == "25.00"


# -- source processing -----------------------------------------------------


@pytest.mark.django_db
def test_source_process_with_importer_runs_new_pipeline_and_matching():
    matched = []

    def matcher(sender, **kwargs):
        matched.append(sender)
        return False

    legacy_calls = []

    def legacy(sender, **kwargs):
        legacy_calls.append(sender)
        return []

    importer = ListImporter([tx(external_id="REF-1"), tx(external_id="REF-2")])
    source = make_source(importer="test.list")
    with registered(importer), connected_signal(
        process_transaction, matcher, "matcher"
    ), connected_signal(process_csv_upload, legacy, "legacy"):
        result = source.process()

    source.refresh_from_db()
    assert result.imported_count == 2
    assert source.state == SourceState.PROCESSED
    assert source.processed_at is not None
    assert source.imported_count == 2
    assert source.duplicate_count == 0
    assert importer.parsed_sources == [source]
    assert set(matched) == set(result.transactions)
    assert legacy_calls == []
    assert (
        source.log_entries()
        .filter(action_type="byro.bookkeeping.real_transaction_source.processed")
        .exists()
    )


@pytest.mark.django_db
def test_source_reprocess_is_idempotent():
    importer = ListImporter([tx(), tx(memo="other")])
    source = make_source(importer="test.list")
    with registered(importer):
        assert source.process().imported_count == 2
        result = source.process()
    assert (result.imported_count, result.duplicate_count) == (0, 2)
    assert source.transactions.count() == 2
    source.refresh_from_db()
    assert source.state == SourceState.PROCESSED
    assert (source.imported_count, source.duplicate_count) == (0, 2)


@pytest.mark.django_db
def test_source_process_is_atomic_and_marks_failure():
    importer = ListImporter([tx(external_id="1"), tx(external_id="2"), tx("0")])
    source = make_source(importer="test.list")
    with registered(importer), pytest.raises(InvalidBankTransaction):
        source.process()

    source.refresh_from_db()
    assert source.state == SourceState.FAILED
    assert source.processed_at is not None
    assert source.imported_count is None
    assert Booking.objects.filter(source=source).count() == 0
    assert Transaction.objects.filter(memo="NLL123 Jahresbeitrag").count() == 0


@pytest.mark.django_db
def test_source_process_unknown_importer_fails_cleanly():
    source = make_source(importer="gone.importer")
    with pytest.raises(UnknownImporter):
        source.process()
    source.refresh_from_db()
    assert source.state == SourceState.FAILED


@pytest.mark.django_db
def test_source_process_wraps_importer_exceptions(caplog):
    class Exploding(ListImporter):
        def parse(self, source):
            yield tx(external_id="1")
            raise KeyError("column missing")

    source = make_source(importer="test.list")
    with registered(Exploding()), pytest.raises(ImporterError) as excinfo:
        source.process()
    assert isinstance(excinfo.value.__cause__, KeyError)
    assert "column missing" not in str(excinfo.value)
    assert "column missing" in caplog.text
    assert Booking.objects.filter(source=source).count() == 0


@pytest.mark.django_db
def test_source_process_passes_invalid_file_error_through():
    class Rejecting(ListImporter):
        def parse(self, source):
            raise InvalidImportFile("Not a statement file.")
            yield  # pragma: no cover

    source = make_source(importer="test.list")
    with registered(Rejecting()), pytest.raises(InvalidImportFile) as excinfo:
        source.process()
    assert str(excinfo.value) == "Not a statement file."
    source.refresh_from_db()
    assert source.state == SourceState.FAILED


# -- legacy compatibility --------------------------------------------------


@pytest.mark.django_db
def test_legacy_receiver_still_processes_sources_without_importer():
    def legacy_importer(sender, **kwargs):
        t = Transaction.objects.create(
            memo="legacy", value_datetime=timezone.now(), user_or_context="legacy"
        )
        t.debit(
            account=SpecialAccounts.bank,
            amount=10,
            source=sender,
            importer="legacy.plugin",
            user_or_context="legacy",
        )
        return [t]

    matched = []

    def matcher(sender, **kwargs):
        matched.append(sender)
        return False

    source = make_source()
    with connected_signal(process_csv_upload, legacy_importer, "legacy"):
        with connected_signal(process_transaction, matcher, "matcher"):
            response = source.process()

    assert len(response) == 1
    assert source.transactions.get() == response[0]
    assert matched == response
    source.refresh_from_db()
    assert source.state == SourceState.PROCESSED
    assert source.importer is None


@pytest.mark.django_db
def test_legacy_processing_without_receiver_fails():
    source = make_source()
    with pytest.raises(Exception, match="No plugin tried to process"):
        source.process()
    source.refresh_from_db()
    assert source.state == SourceState.FAILED


@pytest.mark.django_db
def test_legacy_processing_with_multiple_receivers_fails():
    source = make_source()
    receiver = lambda sender, **kwargs: []  # noqa: E731
    with connected_signal(process_csv_upload, receiver, "one"), connected_signal(
        process_csv_upload, lambda sender, **kwargs: [], "two"
    ), pytest.raises(Exception, match="More than one plugin"):
        source.process()


@pytest.mark.django_db
def test_legacy_receiver_exception_marks_source_failed():
    def legacy_importer(sender, **kwargs):
        raise ValueError("bad csv")

    source = make_source()
    with connected_signal(process_csv_upload, legacy_importer, "legacy"):
        with pytest.raises(ValueError):
            source.process()
    source.refresh_from_db()
    assert source.state == SourceState.FAILED


# -- concurrency and atomicity of the service itself -----------------------


@pytest.mark.django_db
def test_import_identity_is_unique(partial_transaction):
    booking = partial_transaction.bookings.get()
    booking.import_identity = "a" * 64
    booking.save()
    t = Transaction.objects.create(value_datetime=timezone.now(), user_or_context="t")
    with pytest.raises(IntegrityError), transaction.atomic():
        t.debit(
            account=SpecialAccounts.bank,
            amount=1,
            import_identity="a" * 64,
            user_or_context="t",
        )


@pytest.mark.django_db
def test_concurrently_imported_transaction_is_counted_as_duplicate(monkeypatch):
    """Simulate a race: the identity check sees nothing, but the row exists by
    the time we insert."""
    run_import([tx(external_id="REF-1")])
    monkeypatch.setattr(
        BankTransactionImportService, "_existing_identities", lambda self, ids: set()
    )
    result = run_import([tx(external_id="REF-1"), tx(external_id="REF-2")])
    assert (result.imported_count, result.duplicate_count) == (1, 1)
    assert result.transactions[0].bookings.get().data["external_id"] == "REF-2"
    assert Booking.objects.filter(import_identity__isnull=False).count() == 2


@pytest.mark.django_db
def test_service_import_is_atomic_without_caller_transaction(monkeypatch):
    original = BankTransactionImportService._persist
    calls = []

    def failing_persist(self, entry, *args, **kwargs):
        calls.append(entry.position)
        if len(calls) == 2:
            raise RuntimeError("database gone")
        return original(self, entry, *args, **kwargs)

    monkeypatch.setattr(BankTransactionImportService, "_persist", failing_persist)
    source = make_source()
    importer = ListImporter([tx(external_id="1"), tx(external_id="2")])
    with pytest.raises(RuntimeError):
        BankTransactionImportService().import_transactions(
            source, importer.parse(source), importer
        )
    assert calls == [1, 2]
    assert Booking.objects.filter(source=source).count() == 0
    assert Transaction.objects.filter(bookings__source=source).count() == 0
