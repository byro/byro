# Memberships and fees

A member can have several **memberships** over time, for example because the
fee changes, or to document an earlier leave and rejoin. Each membership
carries its own fee - there is **no reusable "fee type"** you attach to
several memberships: amount and interval are set directly on each individual
membership (see [Editing member data](members.md#editing-member-data)).

## Fields of a membership

* **Start** and **end** (empty end = still running),
* **Fee**: the amount due each interval,
* **Interval**: monthly, quarterly, biannually or annually.

Only a membership with no end, or an end in the future, counts as active; a
member with no memberships, or only past ones, counts as inactive (see
[Member list](members.md#member-list)).

## How fees become due

byro calculates a membership's due dates from its start, interval and fee:
starting at the membership's start, the fee becomes due again every
`interval` months, until the membership ends or, with no end, until today.
There is no preview or editing function for individual due dates -
corrections go through [Account adjustment](members.md#account-adjustment)
on the member.

## Statute of limitations

How long a member's outstanding fees can still be claimed is set by the
**statute of limitations** (Settings → General, see
[Settings](../administration/settings.md#general)), organization-wide in
months, not per membership. The member's dashboard shows the amount already
past the limit, plus a preview of what will additionally pass the limit
within a year.

## Reconciling fees for many members

To generate balances over a time range for every active member at once, and
optionally prepare reminder mails for members below a balance threshold, see
[Bulk actions](members.md#bulk-actions).
