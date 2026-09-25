# Documents

Documents are uploaded files with a title, date, category and direction
(incoming, outgoing or other), optionally linked to a member.

## Where documents are uploaded

* **On a member**: in the "Documents" tab of the member view (see
  [Members](members.md#documents)) - the document is linked to that member
  from the start.
* **On a transaction**: on the transaction page (see
  [Finances](finances.md#attaching-a-receipt)) - in addition to a member
  link, this connects a receipt to the specific booking.
* **General, unrelated** (`Documents → Add`): for documents that belong to
  no member and no transaction.

## Categories

Categories come from the core and from installed apps/plugins, not from a
fixed list. The core itself knows:

* Miscellaneous document, Registration form (documents app),
* Receipt, Invoice, Statement (bookkeeping).

An installed plugin can contribute further categories; which ones exist in
a given installation depends on which plugins are installed.

## Downloading

Every document can be downloaded from its detail page; byro only serves the
file after its own access check (see
[Security baseline](../administration/security-baseline.md#tls-and-reverse-proxy)
for why `/media/` must never be served directly by the web server).

## Sending as a mail attachment

A document can be attached programmatically to a new mail placed in the
outbox; plugins that automatically deliver a requested document use this, for
example. **The Office itself has no button for this** - neither the compose
form nor the member view offer "send this document by mail". A document only
ends up as a mail attachment when an automated function (for example a
plugin) adds it there.
