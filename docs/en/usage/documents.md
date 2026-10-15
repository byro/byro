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
* **Through the REST API**: for a member, for example when importing the
  files of another system (see
  [Member documents](../development/api.md#member-documents)).

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

PDF files and images in PNG, JPEG, GIF or WebP format open in the browser, and
the detail page shows them as a preview. All other files are only offered as a
download. byro decides this by the content of the file, not by its name.

A downloaded file is named after the title of the document, with the
extension of the uploaded file: `scan0042.pdf` with the title "Membership
application Jona Than" becomes `Membership application Jona Than.pdf`.
Without a title, byro uses the name of the category, and without either, the
name of the uploaded file. Mail attachments get the same name.

byro stores every file under a key of its own, independent of its name, so
uploading a file with the same name never replaces another document's file.
The name of the uploaded file is kept with the document.

## Sending as a mail attachment

A document can be attached programmatically to a new mail placed in the
outbox; plugins that automatically deliver a requested document use this, for
example. **The Office itself has no button for this** - neither the compose
form nor the member view offer "send this document by mail". A document only
ends up as a mail attachment when an automated function (for example a
plugin) adds it there.
