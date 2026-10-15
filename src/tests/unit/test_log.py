import pytest
from django.db import transaction
from django.utils.timezone import now

from byro.bookkeeping.models import Transaction
from byro.bookkeeping.special_accounts import SpecialAccounts
from byro.common.models import LogEntry


@pytest.mark.django_db
def test_log_create(member):
    a = LogEntry.objects.create(
        content_object=member,
        action_type="test.test_log_create",
        data={"source": "test"},
    )

    assert a
    assert a.pk
    assert LogEntry.objects.get(pk=a.pk)
    assert LogEntry.objects.filter(action_type="test.test_log_create").count() == 1


@pytest.mark.django_db
def test_log_filter_content_object(member):
    LogEntry.objects.create(
        content_object=member,
        action_type="test.test_log_filter_content_object",
        data={"source": "test"},
    )

    assert (
        LogEntry.objects.filter(
            content_object=member, action_type="test.test_log_filter_content_object"
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_log_immutable(member):
    LogEntry.objects.create(
        content_object=member,
        action_type="test.test_log_immutable",
        data={"source": "test"},
    )

    a = LogEntry.objects.get(action_type="test.test_log_immutable")

    with pytest.raises(TypeError):
        a.action_type = "Fnord"
        a.save()

    with pytest.raises(TypeError):
        a.delete()


@pytest.mark.django_db
def test_log_immutable_2(member):
    LogEntry.objects.create(
        content_object=member,
        action_type="test.test_log_immutable_2",
        data={"source": "test"},
    )

    a = LogEntry.objects.get(action_type="test.test_log_immutable_2")

    def monkey_patched_save(*args, **kwargs):
        return super(LogEntry, a).save(*args, **kwargs)

    def monkey_patched_delete(*args, **kwargs):
        return super(LogEntry, a).delete(*args, **kwargs)

    a.save = monkey_patched_save
    a.delete = monkey_patched_delete

    with pytest.raises(TypeError):
        a.action_type = "Fnord"
        with transaction.atomic():
            a.save()

    with pytest.raises(TypeError):
        with transaction.atomic():
            a.delete()


@pytest.mark.django_db
def test_log_user(user, member):
    a = LogEntry.objects.create(
        user=user, content_object=member, action_type="test.test_log_user"
    )

    assert a in LogEntry.objects.filter(user=user)

    with pytest.raises(ValueError):
        LogEntry.objects.create(content_object=member, action_type="test.test_log_user")

    assert LogEntry.objects.filter(user=user).first().data["source"] == str(user)


@pytest.mark.django_db
def test_log_call_keeps_source_kwarg_apart_from_actor(real_transaction_source):
    t = Transaction.objects.create(
        value_datetime=now(), user_or_context="internal: test"
    )
    t.debit(
        account=SpecialAccounts.bank,
        amount=1,
        source=real_transaction_source,
        user_or_context="internal: test",
    )

    entry = LogEntry.objects.get(
        action_type="byro.bookkeeping.transaction.debit.created"
    )
    assert entry.data["source"] == "internal: test"
    assert entry.data["_source"]["ref"] == [
        "bookkeeping",
        "realtransactionsource",
        real_transaction_source.pk,
    ]
    assert entry.verify()
