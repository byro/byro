# Finances

byro keeps double-entry books for fees and payments, but is **not a complete
bookkeeping tool** – there is no balance sheet or profit-and-loss reporting,
no tax or year-end closing functions, and no separate export or reporting
area beyond what this page describes.

## Accounts

"Finances → Accounts" shows every account with its category (asset,
liability, income, expense, equity) and its balance. byro automatically
creates six accounts as needed:

| Account | Category | Purpose |
|---|---|---|
| Bank | Asset | counter-account of every imported bank booking |
| Member fees receivable | Asset | outstanding fee claims |
| Opening balance | Asset | counter-account for initial balances during migration |
| Member fees | Income | collected fees |
| Donations | Income | donation bookings |
| Lost income | Expense | waived fees |

You can create additional accounts of your own ("Finances → Accounts →
Add"), for example for a cash box or other income types. Opening an account
shows its bookings, with a filter for **unbalanced** transactions (see
below).

There is no function to delete an account; no such link exists in the
interface.

## Transactions and bookings

A **transaction** consists of one or more **bookings**, each a debit or
credit on exactly one account, optionally linked to a member. A transaction
counts as **balanced** once its debit and credit sums match; only balanced
transactions count as complete.

**Bookings cannot be deleted or changed directly.** To undo a transaction,
reverse it ("Reverse" on the transaction page): byro creates a new
transaction with exactly opposite bookings and links it to the original.
Both stay visible.

### Manually balancing an unbalanced transaction

After a bank import (see below), a transaction can stay unbalanced if no
automatic match was possible. On the transaction page you then enter a
counter-account by hand (optionally with a member) and a debit or credit
amount - pre-filled with exactly the amount still missing to balance it. If
you arrived here from an account's list of unbalanced bookings, byro takes
you straight to the next unbalanced transaction after saving.

### Attaching a receipt

The same transaction page lets you upload a document and link it to the
transaction (preselected category "Receipt"). More on documents and
categories: [Documents](documents.md).

## Bank import

"Finances → Bank import → Add" uploads a file (default limit 25 MiB) and
processes it immediately with the chosen import format.

* If no import format is offered, no matching plugin is installed - byro
  itself ships no bank importer (see [Plugins](../administration/plugins.md)
  for installation, for example of the official plugin for CAMT.053 and MT940
  files).
* After processing, byro reports how many bookings were read, newly
  imported, and skipped as already known. Re-importing the same or
  overlapping files creates **no** duplicate bookings.
* Right after import, byro automatically tries to match every new booking
  to a member (depending on installed matching plugins). Bookings that
  could not be matched stay unbalanced (see above) and can be balanced
  manually later, or matched again automatically via "Match" in the upload
  list - for example after installing or updating a matching plugin.
* If processing fails (an unreadable file, an unsupported currency, an
  invalid amount or date in the file), byro reports that with an
  understandable error message; **nothing is written**, the import is
  all-or-nothing. The upload itself is kept and can be retried via "Process"
  in the upload list, for example after a corrected file.
* byro only accepts amounts in euros.

Technical details on duplicate detection, the exact error classes, and how a
bank importer plugin works: the developer documentation
[Bank transaction importers](../development/plugins/bank-transaction-importers.md).

## Reference: payment status

A member's balance (see [Memberships and fees](memberships-and-fees.md)) is
the sum of their bookings on the fee accounts; a negative balance means
outstanding claims. There is no separate "payment status" beyond the
computed balance.
