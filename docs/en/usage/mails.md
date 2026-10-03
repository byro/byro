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
* a specific member (only members and external contacts with a stored e-mail
  address are offered; nobody is preselected, a member always has to be
  chosen explicitly),
* **every member with an active membership and an e-mail address**.

There is no way to pick a freely chosen group of members - that's what the
member list's bulk actions are for (see [Members](members.md#bulk-actions)).

### Members and addresses

byro tells a mail **to a member** from a mail **to an address**:

* A mail to a member, or to every member, knows which member it is for. The
  address is only looked up from the member at the moment of sending. Such a
  mail gets the signature with the link to the member page of exactly this
  member, is encrypted with this member's PGP key if PGP encryption is
  enabled, and shows up in this member's mail history. The mail byro generates for a member (welcome,
  leave, disclosure, reminder, PGP key expiry, documents) is of this kind.
* A mail to a specific address is just that. byro never looks for a member
  behind an address, even if the address is stored for a member: such a mail
  has no member signature, is not encrypted and does not appear in any
  member's mail history. To write to a member, pick "Member".

Several members may share one address, for example a family. Each of them
still receives their own mail with their own member page link, and a mail to
every member is delivered once per member, not once per address.

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
  retry - only the ones still pending. Members are remembered as members
  here, not by their address: if two members share an address and only one
  delivery succeeded, the retry reaches the other member.
* Once a mail has been delivered to at least one recipient, its recipients
  can no longer be changed: the mail is the record of who received it. A
  retry reaches the remaining recipients; to write to somebody else, use
  "Copy to new mail", which creates a draft without any deliveries.
* **Delete** discards the draft unsent, with no confirmation beyond the
  single action itself.

!!! warning "Drafts created by older versions"
    Older byro versions stored only the address in the mail they generated
    for a member. Such drafts that are still in the outbox after an update
    are mails to an address: they are sent without the member signature and
    **without PGP encryption**. Send the outbox before updating, or open the
    draft afterwards and select the member as recipient. Reminder mail from
    the fee reconciliation and drafts written to a member or to every member
    via "Compose" are converted automatically, as long as nothing of them
    has been delivered yet.

    Older versions did not record which member a mail was delivered to. A
    draft to a member or to every member that was already delivered partly,
    or that is linked to other members, is therefore not converted: the
    outbox lists it as "Review required" and refuses to send it, instead of
    guessing who received it. Open it and select the recipient again; if it
    was delivered partly, copy it to a new mail (everybody then receives it
    again) or delete it.

## Sent

"Mails → Sent" is a read-only view of already sent mail, ordered by the time
it was sent. A mail to a member shows the address it was actually delivered
to, even if the member has changed their address since.

## Attachments

A document only ends up as a mail attachment when an automated function adds
it there (see
[Documents](documents.md#sending-as-a-mail-attachment)); the compose form
itself offers no attachment picker.

## PGP

If member encryption is enabled, byro encrypts every mail to a member with
the key stored for this member, regardless of whether it came from a
template, "Compose", or was generated automatically. Mail to a specific
address and copies to CC or BCC addresses are not encrypted. Details:
[PGP email encryption](../administration/pgp.md).
