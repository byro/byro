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
out with its next request.

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
server (shell, database), and byro cannot see what happens at an external
identity provider. Accounts created through OIDC are never superusers by
themselves.

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
telling it that a superuser has to finish the setup first.

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
3. If `admin_group` is set, the `groups` claim must contain that value, or
   sign-in fails - **this is the only access check OIDC provides.** It only
   decides who may sign in through OIDC, not what the account may do inside
   the Office afterwards; that is decided by the flags of the local account
   (see [Permission model](#permission-model)).
4. byro looks for an existing account with the username from
   `username_field` (default `preferred_username`). If none is found and
   `auto_create_account` is enabled, it creates a new, **passwordless**
   account with `is_staff=True` and `is_superuser=False`, so the person can
   work in the Office right away but has no administrative access. If
   `auto_create_account` is disabled, sign-in fails for unknown usernames.
5. If the found or created account has `is_active=False`, sign-in is
   rejected with an error message.
6. If the account is neither staff nor superuser, sign-in is rejected with an
   error message and recorded in the audit log.

The flags are set **once, when the account is created**. byro does not
synchronize `is_staff` or `is_superuser` from OIDC groups: an OIDC login
never changes the flags of an existing account, and a superuser grants or
removes them under "Settings → Users".

**Error cases** (an expired code, an invalid `state`, rejection by the
provider, a network error talking to the provider) all end up as an error
message on the login page; there is no dedicated error page and no fallback
to password login within the same attempt.

!!! warning
    "Disable password" (see below) only blocks password sign-in for that
    account. If OIDC is configured and the username matches, the account can
    still sign in through OIDC. To lock an account out completely, it must
    be removed or disabled at the OIDC provider itself (leaving
    `admin_group`, if configured, is enough), or `is_active` must be false.

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

**No self-demotion:** in your own profile the superuser field is locked. You
cannot remove your own superuser status; another superuser has to do that.
You can switch off your own `is_staff`, which changes nothing as long as you
are a superuser.

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

**There is no way to delete or deactivate an account** (set
`is_active=False`) through the Office UI. "Disable password" is the only
built-in way to restrict an account, and as described above only blocks
password sign-in.

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
  lost its backend access is logged as a logout.
