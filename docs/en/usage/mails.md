# Communication

Every mail byro sends - whether triggered automatically or written by hand -
first lands as a **draft in the outbox** and is never sent without your
action.

## Where mail comes from

* **Generated automatically**: welcome and leave mail (see
  [Creating a member](members.md#creating-a-member) and
  [Joining and leaving](members.md#joining-and-leaving)), data disclosures
  (single or as a bulk action, see
  [Members](members.md#data-disclosure)), reminder mail from the fee
  reconciliation (see [Bulk actions](members.md#bulk-actions)).
* **Written by hand**: "Mails → Compose" (see below).

## Templates

"Mails → Templates" manages reusable templates (subject, text, a different
reply-to address, BCC addresses). Text and subject are only maintained in
the organization's configured language (see
[Settings](../administration/settings.md#general)), not per recipient in
multiple languages. Which templates are used automatically where (welcome,
leave, disclosure) is set under
[Settings → General](../administration/settings.md#general).

!!! note
    There is no function to delete a template; no such link exists in the
    interface.

## Composing a mail

"Mails → Compose" creates a new mail with exactly one recipient type:

* a specific address,
* a specific member (only members with a stored e-mail address are offered),
* **every member with an active membership and an e-mail address**.

There is no way to pick a freely chosen group of members - that's what the
member list's bulk actions are for (see [Members](members.md#bulk-actions)).

"Save" stores the mail as a draft, "Save and send" sends it immediately. A
mail that has already been sent can no longer be edited; "Copy" creates a
new, editable draft from it.

## Outbox

"Mails → Outbox" lists every mail not yet sent. **Send** and **Delete** are
available individually or for the whole list.

* Sending to "every member" resolves the recipient list only at the moment
  of actually sending (the current membership status at that time, not at
  the time of composing).
* If delivery to individual recipients fails, that does not abort the rest
  of the send: byro reports who was delivered to successfully and who had
  errors. Recipients already delivered to are **not** mailed again on a
  retry - only the ones still pending.
* **Delete** discards the draft unsent, with no confirmation beyond the
  single action itself.

## Sent

"Mails → Sent" is a read-only view of already sent mail, ordered by the time
it was sent.

## Attachments

A document only ends up as a mail attachment when an automated function adds
it there (see
[Documents](documents.md#sending-as-a-mail-attachment)); the compose form
itself offers no attachment picker.

## PGP

If member encryption is enabled, byro encrypts every mail individually per
recipient with their stored key, regardless of whether it came from a
template, "Compose", or was generated automatically. Details:
[PGP email encryption](../administration/pgp.md).
