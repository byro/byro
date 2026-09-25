# Members

This page describes day-to-day work with member records: searching,
creating, editing, joining and leaving, documents, and export/import and
bulk actions for many members at once. Fees and payment intervals have their
own page: [Memberships and fees](memberships-and-fees.md).

!!! note
    Some fields that look like core fields at first glance come from the
    bundled plugins `byro.plugins.profile` (nickname, birth date, phone
    number) and `byro.plugins.sepa` (bank details for SEPA direct debit).
    They show up like core fields in forms and exports, but are plugins - if
    one is disabled, the fields disappear.

## Member list

"Members → List" shows every member with search and filters:

* **Search** looks through name, nickname (from the profile plugin) and the
  membership number.
* **Filters**: Active (default), Inactive, Negative balance, Pending change
  proposals, All. "Active" means: at least one membership that started in
  the past and either has no end or an end in the future - a computed
  property, not a field you set manually.

The same search is available as autocomplete elsewhere in the Office, for
example to match a payment to a member during bank import (see the Finances
page once it exists).

## Creating a member

"Members → Add" shows exactly the fields configured under
[Settings → Registration form](../administration/settings.md#registration-form)
- core fields, membership fields, profile plugin fields and optionally the
PGP fingerprint, in the order set there. Required fields from that
configuration cannot be skipped; the membership number is pre-filled with the
next free numeric value, but you can replace it with any text.

On save:

1. The member and their first membership (start, interval, fee) are created.
2. If a welcome template is configured (see
   [Settings → General](../administration/settings.md#general)) and the
   member has an e-mail address, a welcome mail is placed in the outbox -
   including an automatically inserted link to their personal
   [member page](member-page.md#access).
3. If an internal welcome template is configured, a matching mail goes to
   the notification address.
4. If a PGP fingerprint was given when creating the member, byro immediately
   tries to import the matching key from the configured keyservers (see
   [PGP email encryption](../administration/pgp.md#member-application-fingerprints)).

Mail always lands in the outbox for review, it is never sent directly.

## The member view

Opening a member shows several tabs:

| Tab | Content |
|---|---|
| Dashboard | membership duration, current membership, statute-of-limitations status, tiles from plugins (e.g. PGP warnings) |
| Data | core fields, every membership, adding a new membership, profile plugin fields, change proposals |
| Timeline | a merged history of finance, mail, operations and document events |
| Finance | this member's bookings (see the Finances page once it exists) |
| Operations | leaving, account adjustment (see below) |
| Mails | mail sent to this member (see the Communication page once it exists) |
| PGP | managing this member's PGP keys (see [PGP email encryption](../administration/pgp.md#member-keys)) |
| Documents | uploading and downloading this member's documents (see below) |
| Log | audit log entries for this member |
| Disclosure | a single data disclosure (see below) |

### Editing member data

In the "Data" tab, each section (core data, each existing membership, adding
a new membership, each profile plugin) is its own form; only changed forms
are applied on save.

**Reviewing change proposals:** if the member proposed changes to their own
data through the [member page](member-page.md), they show up here to accept
or reject. Nothing is applied automatically. Accepting a PGP fingerprint
proposal immediately triggers a keyserver import; an invalid fingerprint is
rejected with an error instead of being applied.

### Joining and leaving

In the "Operations" tab, every currently running membership has an "End
membership" form (only the end date is editable). After saving:

* the membership gets the given end date,
* outstanding fees are recalculated,
* if a leave template (member or internal) is configured, a matching mail
  is placed in the outbox.

There is no function to undo ending a membership other than clearing the end
date again.

### Account adjustment

Also in the "Operations" tab: the account correction for this member, with
two reasons:

* **Initial balance**: for migrating into byro, when a member already
  brings a balance from before byro.
* **Fees waived**: reduces an existing debt; the amount must decrease the
  debt (negative in relative mode, smaller than the current balance in
  absolute mode), otherwise byro rejects the input.

Amounts can be entered relatively (add/subtract) or absolutely (target
balance). Details on the account model behind this are on the Finances page
once it exists.

### Documents

The "Documents" tab uploads files directly for this member (title, date,
category - categories come from the core and installed apps and plugins -,
direction incoming/outgoing/other) and lists the existing ones. More on the
general document system (sending as a mail attachment, categories in detail)
on the Documents page once it exists.

### Data disclosure

"Disclosure" generates a single disclosure mail for this member (content: all
stored data) and places it in the outbox. For many members at once, see
"Bulk actions" below.

## Export

"Members → List → Export" exports the currently filtered members (same
filters as the list, plus "All") as CSV, either comma-separated (default) or
semicolon-separated (for German Windows Excel versions: decimal comma
instead of a period). You choose individually which fields to export -
preselected are the fields that also appear in the registration form. No
XLSX export.

## Import

"Members → List → Import" reads a CSV file (the same two formats as the
export) and matches columns to fields automatically by their **header**
(the exact text of the field's label); if a column matches no field, the
import aborts with an error before anything is written.

* A column for the internal database ID **updates an existing** member
  instead of creating a new one.
* Columns for balance and last fee timestamp create an initial balance for
  **new** members (both columns must be present together).
* New members with no membership columns are created without a membership.

## Bulk actions

* **Generate balances** (`Members → List → Balances`): creates a balance
  over a chosen time range for every member with an active membership, and
  optionally places reminder mails in the outbox for members below a
  configurable balance threshold. Runs synchronously when the form is
  submitted.
* **Disclosure for all** (`Members → List → Disclosure`): generates a
  disclosure mail in the outbox for **every currently filtered** member -
  check the active filter first.
* **Balance refresh** (button on the member list): recalculates every
  member's balance in the background; only one run at a time, a second
  click while it runs just reports that.

## Reference: contact type

Every member has a contact type (person, organization, role) with no further
effect on forms or permissions - purely informational, unless it is exposed
through the registration form.
