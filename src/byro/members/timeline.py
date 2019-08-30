from contextlib import suppress
from datetime import datetime

from django.utils.timezone import now
from more_itertools import peekable

from byro.bookkeeping.models import Booking
from byro.bookkeeping.special_accounts import SpecialAccounts


def _date_compare_key(d):
    # Returns datetime as is, Converts date to datetime at end of day local timezone
    if isinstance(d, datetime):
        return d
    else:
        return now().replace(d.year, d.month, d.day, 23, 59, 59, 999999)


def sorted_merge(*args):
    initer = [iter(e) for e in args]
    nextin = [None] * len(initer)

    for i, e in enumerate(initer):
        with suppress(StopIteration):
            nextin[i] = next(e)

    while any(e is not None for e in nextin):
        available = [i for (i, e) in enumerate(nextin) if e is not None]
        if len(available) > 1:
            minindex = max(
                *available, key=lambda a: _date_compare_key(nextin[a]["date"])
            )
        else:
            minindex = available[0]
        yield nextin[minindex]
        nextin[minindex] = None
        with suppress(StopIteration):
            nextin[minindex] = next(initer[minindex])


def get_mail_timeline(member):
    for instance in member.emails.filter(sent__isnull=False).order_by("-sent").all():
        yield {
            "type": "mail",
            "subtype": "mail-out",
            "date": instance.sent,
            "icon": "envelope",
            "instance": instance,
        }


def get_base_finance_timeline(member):
    last_transaction_pk = None
    for instance in (
        Booking.objects.with_transaction_data()
        .filter(member=member, transaction__reverses__isnull=True)
        .order_by("-transaction__value_datetime", "-transaction__pk")
    ):
        if instance.transaction.pk == last_transaction_pk:
            continue
        last_transaction_pk = instance.transaction.pk
        base_data = {
            "type": "finance",
            "date": instance.transaction.value_datetime,
            "icon": "money",
            "instance": instance,
            "deleted": instance.transaction.reversed_by.first(),
        }
        b = list(instance.transaction.bookings.all())
        if any(
            e.member == member and e.debit_account == SpecialAccounts.fees_receivable
            for e in b
        ) and any(
            e.member == member and e.credit_account == SpecialAccounts.fees for e in b
        ):
            yield dict(subtype="membership-due", value=instance.amount, **base_data)
        elif any(
            e.member == member and e.credit_account == SpecialAccounts.fees_receivable
            for e in b
        ):
            yield dict(subtype="membership-paid", value=instance.amount, **base_data)
        else:
            yield dict(subtype="other-transaction", value=instance.amount, **base_data)


def get_misc_finance_timeline(member):
    for entry in member.log_entries().filter(
        action_type__startswith="byro.members.finance."
    ):
        base_data = {
            "type": "finance",
            "icon": "money",
            "instance": entry,
            "date": entry.datetime,
        }
        if (
            entry.action_type
            == "byro.members.finance.sepadd.mandate_reference_assigned"
        ):
            yield dict(
                base_data, subtype="sepadd-mandate-reference-assigned", icon="info"
            )
        else:
            yield dict(base_data, subtype="other")


def get_finance_timeline(member):
    return sorted_merge(
        get_base_finance_timeline(member), get_misc_finance_timeline(member)
    )


def get_misc_ops_timeline(member):
    for entry in member.log_entries().exclude(
        action_type__startswith="byro.members.finance."
    ):
        base_data = {
            "type": "ops",
            "icon": "user",
            "instance": entry,
            "date": entry.datetime,
        }
        if entry.action_type == "byro.members.created":
            yield dict(base_data, subtype="member-created", icon="user-plus")
        elif entry.action_type == "byro.members.updated":
            yield dict(base_data, subtype="member-updated", icon="pencil")
        elif entry.action_type == "byro.members.document.created":
            yield dict(base_data, subtype="document-created", icon="file")
        else:
            yield dict(base_data, subtype="other")


def get_ops_timeline(member):
    membership_ops = []
    for membership in member.memberships.all():
        base_data = {"type": "ops", "icon": "user", "instance": membership}
        if membership.start:
            membership_ops.append(
                dict(subtype="membership-begin", date=membership.start, **base_data)
            )
        if membership.end:
            membership_ops.append(
                dict(subtype="membership-end", date=membership.end, **base_data)
            )

    return sorted_merge(
        sorted(membership_ops, reverse=True, key=lambda a: a["date"]),
        get_misc_ops_timeline(member),
    )


def get_file_icon(document):
    return {"application/pdf": "file-pdf-o"}.get(document.mime_type_guessed, "file-o")


def get_document_timeline(member):
    for document in member.documents.order_by("-date", "-id").all():
        base_data = {
            "type": "document",
            "icon": get_file_icon(document),
            "instance": document,
            "date": document.date,
        }
        if document.category == "byro.documents.registration_form":
            yield dict(base_data, subtype="registration_form")
        else:
            yield dict(base_data, subtype="misc_document")


def add_dummy_entries(entries):
    entries = peekable(entries)
    prev_entry = next(entries)
    yield prev_entry
    output_month, output_year = prev_entry["date"].month, prev_entry["date"].year

    while entries:
        entry = next(entries)
        while output_month != entry["date"].month or output_year != entry["date"].year:
            output_month = output_month - 1
            if output_month < 1:
                output_month = 12
                output_year = output_year - 1
            if output_month != entry["date"].month or output_year != entry["date"].year:
                yield {
                    "type": "dummy",
                    "subtype": "dummy",
                    "instance": None,
                    "date": datetime(year=output_year, month=output_month, day=1),
                }
        yield entry


def augment_timeline(entries):
    last_year = None
    last_month = None

    entries = peekable(add_dummy_entries(entries))

    while entries:
        entry = next(entries)
        nentry = entries.peek(None)
        tl = {
            "year_first": False,
            "year_last": False,
            "month_first": False,
            "month_last": False,
            "entry_id": "{}:{}:{}".format(
                entry["type"], entry["subtype"], entry["instance"].pk
            )
            if entry["instance"]
            else None,
        }
        if last_year != entry["date"].year:
            tl["year_first"] = True
        if last_month != entry["date"].month:
            tl["month_first"] = True
        if not nentry or nentry["date"].year != entry["date"].year:
            tl["year_last"] = True
        if not nentry or nentry["date"].month != entry["date"].month:
            tl["month_last"] = True
        yield dict(entry, tl=tl)
        last_year = entry["date"].year
        last_month = entry["date"].month
