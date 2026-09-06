# Signal list

This page lists the signals and hooks that are available in byro. The
[plugin guides](plugins/index.md) give examples on how to use these signals.

## Member management

::: byro.members.signals
    options:
      members:
        - new_member
        - new_member_mail_information
        - new_member_office_mail_information
        - leave_member
        - leave_member_mail_information
        - leave_member_office_mail_information
        - update_member

## Payment

::: byro.bookkeeping.signals
    options:
      members:
        - process_transaction
        - bank_transaction_importers
        - process_csv_upload

`process_csv_upload` is the legacy signal, see
[Bank transaction importers](plugins/bank-transaction-importers.md#legacy-api).
Bank transaction importers are registered via `bank_transaction_importers`
(see [Bank transaction importers](plugins/bank-transaction-importers.md)).

## Display and import

::: byro.office.signals
    options:
      members:
        - nav_event
        - member_view
        - member_dashboard_tile
        - member_list_importers

## General

!!! info "Not generated"
    `byro.common`, unlike every other byro app, has no `__init__.py`
    (see `src/byro/common/`). mkdocstrings/Griffe therefore cannot statically
    collect `byro.common.signals`; the descriptions below are copied from its
    source by hand. This is reported as a product finding, not fixed here (the
    documentation does not change product code).

Module `byro.common.signals`:

`unauthenticated_urls`
:   Sent to determine whether a URL should be reachable without
    authentication. Plugins connect a receiver to mark their own views public;
    the MFA and permission middleware exempt matching URLs.

`log_formatters`
:   Sent to collect formatters for audit log entries, so plugins can render
    their own log actions in the office UI.

`periodic_task`
:   Sent by `byroctl manage runperiodic` / `python -m byro runperiodic`.
    Connect a receiver to run recurring work, for example the built-in PGP key
    refresh and expiry reminders.
