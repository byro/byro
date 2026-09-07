# Users and login

This page describes who can sign in to the byro Office, how sign-in works,
and how you manage user accounts. For multi-factor authentication, see the
dedicated page [MFA](mfa.md); for server-side operation (TLS, the secret key,
container privileges) see [Security baseline](security-baseline.md).

!!! warning
    byro has **no tiered roles inside the Office**: any account that signs in
    successfully sees and operates the entire Office - members, finances,
    settings, other user accounts included. There is no read-only access and
    no restriction to individual areas. Weigh this before enabling OIDC
    auto-provisioning or creating accounts.

## First login

As long as **name**, **sender address** and **notification address**
(Settings → General, see [Settings](settings.md)) are not set, byro redirects
every signed-in account (except during the MFA flow) to the initial setup.
This also applies to an account just created through OIDC, not only to the
first administrator.

## Password login

The default: username and password, checked against the local account. An
account with no usable password (see "Disable password" below) cannot sign
in with a password - only with one of the other enabled methods.

## OIDC/SSO login

If `[oidc] issuer_url` is set (see
[Configuration](../configuration/index.md#the-oidc-section)), the login page
also shows an SSO button. The flow:

1. byro redirects to the OIDC provider (authorization code flow with `state`
   and `nonce`).
2. After a successful sign-in at the provider, byro validates the ID token
   (signature against the provider's JWKS, issuer, audience, expiry,
   `nonce`).
3. If `admin_group` is set, the `groups` claim must contain that value, or
   sign-in fails - **this is the only access check OIDC provides.** It only
   decides who may sign in, not what the account may do inside the Office
   afterwards (see the warning above).
4. byro looks for an existing account with the username from
   `username_field` (default `preferred_username`). If none is found and
   `auto_create_account` is enabled, it creates a new, **passwordless**
   account (`is_staff`/`is_superuser` stay `False`, see below). If
   `auto_create_account` is disabled, sign-in fails for unknown usernames.
5. If the found or created account has `is_active=False`, sign-in is
   rejected with an error message.

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

Under "Settings → Users" (`settings/users/`) you see every account, create
new ones and edit existing ones. Each account has:

- **Username**, **name**, **e-mail address**,
- **`is_staff`**: a prerequisite for REST API access (see
  [Development & API](../development/index.md)). Has **no** other effect on
  the Office itself.
- **`is_superuser`**: byro **never** evaluates this field itself (no Django
  admin site is wired in). It appears in the audit log but has no practical
  effect at runtime.

!!! note
    Since there are no roles (see the warning above), `is_staff` and
    `is_superuser` **do not** distinguish how much a user may do in the
    Office - only `is_staff` has any effect at all, and only for API access.

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
new accounts; an administrator creates every account themselves with an
initial password. If nobody is left signed in who could create a new
account, only server access helps, see
[Account recovery](troubleshooting.md#account-recovery).

## MFA requirement

Whether multi-factor authentication is optional or required for every
account is a global setting, not per account: see
[Requiring MFA for all administrators](mfa.md#requiring-mfa-for-all-administrators).

## Sign-in behavior

- The session cookie is named `byro_session`, the CSRF cookie
  `byro_csrftoken`; both are Django's default sessions with no fixed
  expiry beyond the browser session ending (no `SESSION_COOKIE_AGE` set).
- **No login lockout:** byro does not lock an account after wrong password
  attempts (neither temporarily nor permanently; that only applies to MFA
  codes, see [MFA](mfa.md#security-notes)). External protection (reverse
  proxy, Fail2ban) is up to you.
- **Failed password logins do not end up in the audit log** - only
  successful logins, logins on a deactivated account, and logouts are
  logged (see [Audit log](settings.md#audit-log)).
