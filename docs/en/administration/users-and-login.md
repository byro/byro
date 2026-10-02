# Users and login

This page describes who can sign in to the byro Office, how sign-in works,
and how you manage user accounts. For multi-factor authentication, see the
dedicated page [MFA](mfa.md); for server-side operation (TLS, the secret key,
container privileges) see [Security baseline](security-baseline.md).

## Permission model

byro distinguishes three kinds of accounts through the two flags `is_staff`
and `is_superuser`:

| `is_staff` | `is_superuser` | Office and API | Settings, registration form, users, log |
|---|---|---|---|
| no | no | no | no |
| yes | no | yes | no |
| no | yes | yes | yes |
| yes | yes | yes | yes |

- **No flag:** the account can neither sign in to the Office nor use the
  authenticated API.
- **Staff (`is_staff`):** regular access to the Office - members, finances,
  documents, mails, the own profile - and to the API.
- **Superuser (`is_superuser`):** everything staff may do, plus the
  administrative functions, marked **superuser only** in this documentation:
  the [initial setup](settings.md#initial-setup), the
  [general settings](settings.md#general), the
  [registration form](settings.md#registration-form), the
  [audit log](settings.md#audit-log) and
  [user management](#managing-user-accounts). A superuser can always sign in,
  even without `is_staff`, so an inconsistent combination of flags cannot
  lock a superuser out.

These rules are enforced on the server, not only by hiding menu entries. A
staff account that opens a superuser-only page directly gets an error page
(HTTP 403). An account that loses both flags while it is signed in is signed
out with its next request to a protected page. Pages that need no login
(the login page, member pages, `/log/info`) do not end the session; an API
token of the account stops working immediately.

!!! warning
    The model is deliberately small. There are **no finer-grained roles**: no
    read-only access and no restriction to individual areas such as finances
    or member management. Every staff account sees and edits all members,
    finances and mails. Weigh this before enabling OIDC auto-provisioning or
    creating accounts.

!!! note "Plugins"
    Plugins that add pages to the "Settings" menu have to restrict them to
    superusers themselves. byro hides those menu entries from staff, but it
    cannot protect the pages of a plugin that has not been adapted yet: such
    a page stays reachable for staff through its direct address. See
    [Settings entries are superuser only](../development/signals.md#settings-entries-are-superuser-only).

### Existing installations

Before this permission model was introduced, every account had unrestricted
access to the whole Office, including settings and user management. To keep
exactly that access, the update sets `is_staff` and `is_superuser` for
**every existing account**, including accounts created through OIDC. Nobody
loses access through the update.

After updating, review "Settings → Users" and remove the superuser status
from the accounts that should only have regular access. The migration itself
does not write an audit log entry, and migrating backwards does not restore
the previous flag values.

### Keep a local break-glass superuser

Inside the Office, a superuser cannot remove their own superuser status, and
only superusers manage accounts, so at least one superuser always remains.
This guarantee ends at the Office: an account can still be changed on the
server (shell, database), and with OIDC group synchronization the identity
provider can remove the superuser status of every account that signs in
through OIDC (see
[Synchronizing permissions](#synchronizing-permissions-on-every-login)).

Keep at least one local superuser account with a password that does not
depend on OIDC, for example the account created during installation with
`createsuperuser`. If no superuser is left, see
[Account recovery](troubleshooting.md#account-recovery).

## First login

**Superuser only.** As long as **name**, **sender address** and
**notification address** (Settings → General, see [Settings](settings.md))
are not set, byro redirects every signed-in account (except during the MFA
flow) to the initial setup. Only a superuser can complete it; a staff
account, for example one just created through OIDC, sees an error page
telling it that a superuser has to finish the setup first. Logging out and
signing in with another account (password or OIDC) stays possible while the
setup is incomplete.

## Password login

The default: username and password, checked against the local account. An
account with no usable password (see "Disable password" below) cannot sign
in with a password - only with one of the other enabled methods.

## OIDC/SSO login

If `[oidc] issuer_url` is set (see
[Configuration](../configuration/reference.md#the-oidc-section)), the login page
also shows an SSO button. The flow:

1. byro redirects to the OIDC provider (authorization code flow with `state`
   and `nonce`).
2. After a successful sign-in at the provider, byro validates the ID token
   (signature against the provider's JWKS, issuer, audience, expiry,
   `nonce`).
3. If `staff_group` or `superuser_group` is set, byro reads the groups of
   the user: from the `groups` claim of the ID token if the token has one,
   otherwise from the userinfo endpoint. A claim that is present but empty
   is a valid answer (member of no group) and userinfo is not asked. Only if
   the claim is missing in both places, the user counts as a member of no
   group.
4. byro looks for an existing account with the username from
   `username_field` (default `preferred_username`). If none is found, the
   user passes the group check from step 6 and `auto_create_account` is
   enabled, it creates a new, **passwordless** account with the permissions
   described under [OIDC groups and permissions](#oidc-groups-and-permissions).
   If `auto_create_account` is disabled, sign-in fails for unknown usernames.
5. If `sync_groups` is enabled, the permissions of an existing, active
   account are updated from the groups and saved.
6. Group check: if `staff_group` is set, the user has to be a member of
   `staff_group` or of the configured `superuser_group`, or sign-in fails.
   This happens after step 5, so permissions that were just removed stay
   removed although the sign-in is rejected.
7. If the account has `is_active=False`, sign-in is rejected with an error
   message. A deactivated account is never changed by step 5.
8. If the account is neither staff nor superuser, sign-in is rejected with an
   error message and recorded in the audit log.

### OIDC groups and permissions

Two options map groups of the identity provider to the two flags of the
[permission model](#permission-model):

- `staff_group`: members get `is_staff`. It also limits who may sign in
  through OIDC at all (step 6). If it is empty, every user of the identity
  provider may sign in.
- `superuser_group`: members get `is_superuser`. If it is empty, OIDC never
  grants or removes superuser status.

The two flags stay independent: membership in `superuser_group` never sets
`is_staff` by itself. Whether a member of `superuser_group` is also staff is
decided by the staff side alone:

- If `staff_group` is configured, `is_staff` follows that group. A user who
  is only in `superuser_group` then gets `is_superuser` without `is_staff`,
  as a new account or through `sync_groups`, and can still sign in, because
  a superuser always has access.
- If no `staff_group` is configured, a new account becomes staff by default
  (see the table below), also when it is in `superuser_group`. For an
  existing account `is_staff` is left as it is.

So an account with `is_superuser` but without `is_staff` only comes about
when the staff side says so: through a configured `staff_group`, or because
the flag is already set that way locally.

A **new account** (`auto_create_account`) gets its permissions once:

| `staff_group` set | `superuser_group` set | `is_staff` | `is_superuser` |
|---|---|---|---|
| no | no | yes | no |
| yes | no | yes (membership is required to sign in) | no |
| no | yes | yes | if member of `superuser_group` |
| yes | yes | if member of `staff_group` | if member of `superuser_group` |

So the simplest setup, `auto_create_account` without any group, still makes
every new OIDC user a regular staff account and never a superuser.

For an **existing account** it depends on `sync_groups`:

- `sync_groups = false` (default): an OIDC login never changes the flags.
  The group check decides whether the user may sign in through OIDC, the
  local flags decide what the account may do. Being added to a group later
  grants nothing: a superuser sets the flags under "Settings → Users".
- `sync_groups = true`: see the next section.

Group names with spaces only work if the provider sends the `groups` claim
as a list; a claim sent as one string is split at spaces. A claim in any
other form, for example a list that contains something other than group
names, makes the sign-in fail. byro then creates no account and changes no
permissions.

### Synchronizing permissions on every login

With `sync_groups = true` the identity provider is the **source of truth**
for the configured groups. On every successful OIDC login of an existing
account:

- if `staff_group` is set, `is_staff` is set to "member of `staff_group`",
- if `superuser_group` is set, `is_superuser` is set to "member of
  `superuser_group`",
- a flag whose group is not configured is left exactly as it is.

byro reads the account again under a lock right before it compares and
writes, and only writes a flag that is mapped and actually differs. A flag
whose group is not configured is therefore never written, even if somebody
changes it in the Office at the same moment.

A change is saved before the group check and the permission model are
evaluated and is recorded in the audit log with the old and new flags. A
user who was removed from `staff_group` loses `is_staff` with the next OIDC
login; if the account is neither staff nor superuser afterwards, that login
is rejected.

!!! warning
    - Removing users from a synchronized group at the identity provider
      removes their permission in byro, without any safeguard. This can
      remove **every** superuser that signs in through OIDC. Keep a
      [local break-glass superuser](#keep-a-local-break-glass-superuser)
      with a password.
    - Synchronization only happens **during an OIDC login of that
      account**. Until then nothing changes: sessions, password sign-in and
      API tokens of the account keep working. byro never changes accounts
      that do not sign in through OIDC.
    - `staff_group` alone does not manage superusers. After the update to
      the permission model, every existing account is a superuser (see
      [Existing installations](#existing-installations)). Such an account
      loses `is_staff` and its OIDC sign-in when it leaves `staff_group`,
      but keeps `is_superuser`, and with it password sign-in and its API
      token, until you also set `superuser_group` or remove the flag by
      hand.
    - If the provider stops sending the `groups` claim, for example after a
      changed scope or mapper, every user counts as a member of no group
      and loses the synchronized permissions with the next login.

### The deprecated `admin_group`

`admin_group` is the old name of `staff_group` and is still read. On its
own it behaves as before: only members may sign in through OIDC, and new
accounts become staff. Two things are new: together with `superuser_group`,
membership in **either** group is enough to sign in, and with `sync_groups`
it also controls `is_staff` like `staff_group` does.

Rename it to `staff_group` when convenient. If both options are set to
different values, byro does not guess which one is meant: the SSO button
disappears and OIDC logins are refused until the configuration is fixed.
Password sign-in keeps working. `manage.py check` reports the problem and
`byroctl config check` refuses to apply such a configuration.

**Error cases** (an expired code, an invalid `state`, rejection by the
provider, a network error talking to the provider) all end up as an error
message on the login page; there is no dedicated error page and no fallback
to password login within the same attempt.

!!! warning
    "Disable password" (see below) only blocks password sign-in for that
    account. If OIDC is configured and the username matches, the account can
    still sign in through OIDC. To lock an account out completely, it must
    be removed or disabled at the OIDC provider itself (leaving the
    configured groups is enough for the OIDC sign-in), or `is_active` must be
    false.

## Managing user accounts

**Superuser only.** Under "Settings → Users" (`settings/users/`) you see
every account, create new ones and edit existing ones. Staff accounts cannot
open this area; they can only edit their own profile through the user menu
(see [My account](../usage/account.md)), and that form does not contain the
two permission fields. Each account has:

- **Username**, **name**, **e-mail address**,
- **Backend access (staff)** (`is_staff`): allows the account to sign in to
  the Office and to use the REST API (see [API](../development/api.md)).
  Preselected when you create an account; switch it off if the account
  should not have access (yet).
- **Superuser** (`is_superuser`): additionally grants access to the
  superuser-only functions (see [Permission model](#permission-model)). Not
  preselected.

**No self-demotion:** in your own profile only the superuser field is locked.
You cannot remove your own superuser status; another superuser has to do
that. Your own `is_staff` stays editable: you can switch it on or off
yourself, which changes nothing as long as you are a superuser.

**Password when editing:** the edit form requires a new password on **every**
save - even if you only change the name or `is_staff`. There is no way to
change other fields without also setting a new password at the same time.
Tell the affected person the new password afterwards, or use `changepassword`
instead (see [Management commands](management-commands.md#account-management))
if you only want to set a known password without opening the edit form.

**Disabling a password** (`settings/users/<pk>/disable-password`) sets an
unusable password; the account can no longer sign in with a password
afterwards (see the OIDC warning above about the interaction). It cannot be
applied to your own account. To re-enable password sign-in, save the edit
form with a new password.

**Revoking an API token** (`settings/users/<pk>/revoke-api-token`): the page
of another account shows whether that account has an
[API token](../usage/account.md#api-token), never the token itself. "Revoke
API token" deletes it. The token stops working immediately (the API answers
with `401`) and no replacement is issued. Nothing else about the account
changes: password, OIDC sign-in, MFA, sessions and permissions stay as they
are. It cannot be applied to your own account; use your own API token page
for that.

Revoking is **not an API lock**. It invalidates the token issued so far, for
example because it may have leaked. The owner of the account gets a new
token the next time they open their API token page. To keep an account away
from the API, remove `is_staff` and `is_superuser` (see
[Permission model](#permission-model)).

Every revocation is recorded in the audit log, without the token. If that
entry cannot be written, the token stays revoked nevertheless: you see a
warning instead of the confirmation, and the error is written to the
application log.

**There is no way to delete or deactivate an account** (set
`is_active=False`) through the Office UI. "Disable password" only blocks
password sign-in, and "Revoke API token" only invalidates the token issued
so far. To take away the access of an account, remove both `is_staff` and
`is_superuser`.

There is **no self-service password reset** and no invitation workflow for
new accounts; a superuser creates every account themselves with an
initial password. If no superuser is left who could create a new account,
only server access helps, see
[Account recovery](troubleshooting.md#account-recovery).

## MFA requirement

Whether multi-factor authentication is optional or required for every
account is a global setting, not per account: see
[Choosing an MFA policy](mfa.md#choosing-an-mfa-policy).

## Sign-in behavior

- The session cookie is named `byro_session`, the CSRF cookie
  `byro_csrftoken`; both are Django's default sessions with no fixed
  expiry beyond the browser session ending (no `SESSION_COOKIE_AGE` set).
- **No login lockout:** byro does not lock an account after wrong password
  attempts (neither temporarily nor permanently; that only applies to MFA
  codes, see [MFA](mfa.md#security-notes)). External protection (reverse
  proxy, Fail2ban) is up to you.
- **Failed password logins do not end up in the audit log** - only
  successful logins, logins on a deactivated account, logins rejected
  because the account has no backend access, and logouts are logged (see
  [Audit log](settings.md#audit-log)). Ending the session of an account that
  lost its backend access is logged as a logout. Permissions changed by the
  OIDC group synchronization are logged with the old and new flags; the
  entry contains no claims or group names.
- **API tokens:** creating, regenerating and revoking an API token is
  logged with the affected account and the account that did it. The entries
  never contain a token.
