# Member page

Every member has their own, publicly reachable page - no login, no password,
no two-factor sign-in. This is not an Office account and should not be
confused with one (see
[Users and login](../administration/users-and-login.md) for actual Office
access with a password or OIDC).

## Access

The address contains a random, 32-character token (`/member/<token>/`) and is
the only access protection - anyone who knows the address can open the page.
A member gets their address:

* automatically as a link in the welcome mail, if a welcome template is
  configured (see [Creating a member](members.md#creating-a-member)),
* as an "Public profile" link on the member's dashboard in the Office.

!!! warning
    Anyone who knows the address can open the page and propose changes
    within the privacy settings below. Only share the link with the
    respective member, like a password.

## What the page shows

* membership duration (days/years since the first membership started),
  the current membership (fee, interval),
* the member's own bookings (fees, donations),
* dashboard tiles plugins explicitly expose for the public view (not the same
  tiles as the Office dashboard),
* only for **active** members, an additional link to the
  [member directory](#member-directory).

## Change proposals

On their page, a member can propose changes to part of their own data: name,
address, e-mail (core), plus nickname, birth date and phone number if the
`profile` plugin is installed, and bank details if the `sepa` plugin is
installed, and the PGP fingerprint.

**No proposal is applied automatically.** Every change lands as a proposal
that an Office user reviews and accepts or rejects in the "Data" tab of the
member view (see
[Reviewing change proposals](members.md#editing-member-data)). A member sees
on their page which proposals are still pending, including the currently
stored value for comparison.

## Privacy settings

On the same page, the member decides whether and what is visible to other
members:

* a checkbox "Yes, my data may be shown in the member list" - without it,
  the member does not appear there, regardless of the settings below,
* a separate share checkbox per field, deciding which data is then visible.

**Never shareable**, regardless of these settings: bank details, the access
token itself, the account balance, the active status and the internal
database id - the privacy page does not even offer these fields for sharing.

## Member directory

`/member/<token>/list` shows every **active** member who consented to
visibility, with the fields they individually shared. A member whose
membership ends disappears from the list, even if they had consented before.
The page additionally names the number of active members who have not (yet)
consented, without naming them.

A member with no active membership does not see this directory link on their
own page.
