# Settings

This page describes the application-internal settings under "Settings" in
the Office. User accounts and login have their own page:
[Users and login](users-and-login.md).

## Initial setup

Right after installation (and for every account, as long as the required
fields are missing, see [First login](users-and-login.md#first-login)), byro
asks for three things:

- **Association name**,
- **sender address** for mail byro sends on the association's behalf,
- **notification address** byro sends administrative notices to.

Only then does byro move on to the registration form setup (see below) and
the rest of the Office becomes usable.

## General

The general settings (`settings/`) combine several forms on one page: the
association configuration itself plus, where installed, PGP (see
[PGP email encryption](pgp.md)) and configuration models plugins contribute
through `ByroConfiguration` (see
[Custom member data](../development/plugins/member-data.md)) - each plugin
can add its own section to this page this way.

The association configuration itself covers:

- **Association name, address, URL**,
- **Statute of limitations** (`liability_interval`, in months): up to what
  age a member's outstanding fees can still be claimed,
- **Accounting start** (`accounting_start`): an optional date fees are
  billed from retroactively - useful when an organization was migrated to
  byro later and older, unpaid fees should not become due retroactively,
- **Language** and **currency** (code, symbol, symbol before/after the
  amount, cent display),
- **External base URL** (`public_base_url`): only needed if public member
  pages should be reachable under a different base URL than the rest of
  byro; otherwise leave it empty.
- **Sender and notification address** (the same fields as in the initial
  setup, changeable here),
- **Default sort order** and **default form of address** for members (first
  or last name part first), with an action to apply them retroactively to
  every existing member,
- **Default mail templates** for welcome and leave mail (to the member and
  to the office) and for record disclosure.

Every saved change is recorded in the audit log with the changed fields
(before/after) (see below); forms can exclude individual fields (for example
secrets) from this logging.

## Registration form

Under "Settings → Registration form" you decide which fields are asked for
when a new member is created: member and membership fields, every field
installed profile plugins contribute (for example `byro.plugins.profile`),
plus the PGP fingerprint entry. For each field you can set:

- its **position** in the form (empty = not shown, unless it is a required
  field),
- a **default value** (for date fields a relative default such as
  "beginning of the current month", for boolean fields true/false/no
  default),
- whether it is **required**. Fields the database would not leave empty
  anyway (`NOT NULL` with no default) automatically show up as required and
  cannot be removed from the form.

With no saved configuration, byro shows a sensible default (member number,
name, address, e-mail, fee start, interval, amount).

## API token

Every account has its own REST API token under "Settings → API token" (see
[Development & API](../development/index.md)); "Regenerate" deletes the old
one and creates a new one. The token only works while the account is
`is_staff` (see
[Managing user accounts](users-and-login.md#managing-user-accounts)); without
`is_staff` the token can still be displayed, but the API rejects it.

## About byro

Shows the installed byro version and the loaded plugins with their metadata
(name, version, description).

## Audit log

"Settings → Log" shows the most recent audit log entries: who changed what,
when (member changes, settings, logins, plugin events, …). Every entry is
part of a **cryptographically chained hash chain** (each entry references
the previous one through a hash); entries can neither be deleted nor
modified afterwards through the application. `/log/info` shows the current
chain head without requiring a login - an external party can use it to check
whether a copy of the chain they hold still matches the current state,
without signing in.

For a full, machine-readable export see the `export_logchain` management
command under
[Management commands](management-commands.md#auditing-and-export).

!!! note
    Failed password logins do **not** appear in the audit log (see
    [Sign-in behavior](users-and-login.md#sign-in-behavior)); it is not a
    tool for detecting login attempts, but a record of changes actually made
    and logins actually completed.
