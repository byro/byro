# Signal list

This page lists the signals and hooks that are available in byro. The
[plugin guides](plugins/index.md) give examples on how to use these signals.

!!! info "Generated reference"
    In the Sphinx documentation the descriptions on this page were generated
    from the docstrings in the source code. The generated reference is being
    set up with mkdocstrings (documentation work package AP05). Until then the
    docstrings in the modules named below are authoritative.

## Member management

Module `byro.members.signals`:

- `new_member`
- `new_member_mail_information`
- `new_member_office_mail_information`
- `leave_member`
- `leave_member_mail_information`
- `leave_member_office_mail_information`
- `update_member`

## Payment

Module `byro.bookkeeping.signals`:

- `process_transaction`
- `bank_transaction_importers`
- `process_csv_upload` (legacy, see
  [Bank transaction importers](plugins/bank-transaction-importers.md#legacy-api))

## Display

Module `byro.office.signals`:

- `nav_event`
- `member_view`
- `member_dashboard_tile`

Module `byro.common.signals`:

- `unauthenticated_urls`
- `log_formatters`

## Import

Module `byro.office.signals`:

- `member_list_importers`

Bank transaction importers are registered via
`byro.bookkeeping.signals.bank_transaction_importers` (see Payment above and
[Bank transaction importers](plugins/bank-transaction-importers.md)).

## General

Module `byro.common.signals`:

- `periodic_task`
