# Signal list

This page lists the signals and hooks that are available in byro. The
[plugin guides](plugins/overview.md) give examples on how to use these signals.

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

### Settings entries are superuser only

The "Settings" submenu of the sidebar is only shown to superusers (see
[Permission model](../administration/users-and-login.md#permission-model)).
A `nav_event` entry with `section` set to `settings` therefore marks an
**administrative function that is meant for superusers only**.

Hiding the navigation entry is not an access control. byro cannot tell which
views belong to a navigation entry and does not try to block plugin URLs on
its own. A plugin has to protect every view behind such an entry itself, on
the server:

```python
from django.views.generic import FormView

from byro.common.permissions import SuperuserRequiredMixin, superuser_required


class NewsletterSettingsView(SuperuserRequiredMixin, FormView):
    ...


@superuser_required
def newsletter_settings_export(request):
    ...
```

Both checks are self-contained: they require an authenticated, active
superuser and do not depend on byro's middleware. Anonymous visitors are
redirected to the login page, every other account gets byro's "Permission
denied" page (HTTP 403). In templates, use `request.user.is_superuser` to
decide whether to show a link to such a page.
`byro.common.permissions.has_backend_access(user)` is the central definition
of who may use the Office at all (staff or superuser).

Configuration models that inherit from `ByroConfiguration` need no extra
work: they are part of the general settings page, which is restricted to
superusers already. Entries with `section` set to `finance`, or without a
section, stay visible to every account with access to the Office.

!!! warning "Migration note for existing plugins"
    Before the permission model was introduced, every account could open
    every page, so existing plugins usually contain no such check. Their
    "Settings" entries are hidden from staff now, but the pages behind them
    **stay reachable for staff through their direct address** until the
    plugin protects them as shown above. This is a compatibility limit for
    existing third-party plugins, not the intended permission behavior.

    If you maintain a plugin with entries in the "Settings" section: add the
    mixin or the decorator to every view behind those entries, including
    views that only handle form submissions or exports.
    `byro.common.permissions` is available from the byro release that
    introduces the permission model; a plugin that also has to run on older
    releases can check `request.user.is_superuser` itself and raise
    `django.core.exceptions.PermissionDenied`.

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
