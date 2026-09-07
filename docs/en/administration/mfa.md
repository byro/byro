# Multi-factor authentication (MFA)

This page covers MFA **policy and administration** for administrators and
server access. How an individual account sets up MFA, signs in with it, or
uses recovery codes is in the user guide:
[Multi-factor authentication](../usage/mfa.md).

byro supports multi-factor authentication for all users of the backend
("office") based on time-based one-time passwords (TOTP,
[RFC 6238](https://www.rfc-editor.org/rfc/rfc6238)). Any common authenticator
app works, for example Aegis, Google Authenticator, Microsoft Authenticator,
1Password or Bitwarden.

MFA is **optional by default**: every backend user can enable it for their own
account. Administrators can additionally **require MFA for all
administrators**, i.e. for every user who can log in to the backend.

MFA only concerns the interactive backend login. It does not change

- the member pages: members keep using their personal links, no login or
  second factor is needed there,
- the REST API: API tokens keep working, regardless of the MFA state of the
  token's user or of the global policy. API requests are never redirected to
  an MFA page.

!!! note
    byro grants access to the complete backend to every active user account;
    there are no tiered roles for the office (see
    [Users and login](users-and-login.md)). The `is_staff` field exists, but
    only gates REST API access, not the office itself. The MFA policy
    therefore applies to *every* user who can log in to the office,
    regardless of `is_staff`.

## Requiring MFA for all administrators

Under *Settings → General* you find the card *Multi-factor authentication*
with the option **Require MFA for all administrators** (off by default).
Enabling it has the following effects:

- Users who already use MFA are not affected; they can no longer disable it,
  though.
- Users without MFA are sent to the MFA setup right after entering their
  password. Until the setup is complete, they cannot use any other page of the
  backend (only the setup itself and logout).
- Sessions that were already logged in without MFA are treated the same way:
  the next request is redirected to the setup.
- The setting applies to logins via single sign-on (OIDC) as well. byro does
  not evaluate MFA information from the identity provider; OIDC users have to
  complete the byro TOTP step, too.
- Enabling the option does not require that everybody has set up MFA already.
  Nobody is locked out – but every user has to enroll at their next login.

Changing the option is recorded in the audit log.

## Display in authenticator apps

Entries created from byro's QR code always show **BYRO** as the service name.
The second line, the account name, is configurable in the same settings card
(*Account name in authenticator apps*). The default is
`{association} - {username}`, i.e. the association name from the general
settings followed by the username. Available placeholders: `{username}`,
`{email}`, `{name}` (the user's name) and `{association}`, for example
`{name} ({email})`.

Colons are not allowed: the `otpauth` format used by authenticator apps
separates the service name from the account with a colon.

The setting only affects newly set up authenticators; existing entries in the
users' apps keep the name they had when they were created.

## Checking a user's MFA status

The user list marks users with MFA with a shield icon. On the server:

```console
$ python manage.py mfa_status <username or e-mail>
```

prints something like:

```text
User: admin (admin@example.org)
Active: yes
MFA enabled: yes
TOTP device: configured (since Sept. 1, 2026, 10:00 a.m., last used Sept. 4, 2026, 9:12 a.m.)
Recovery codes remaining: 6
MFA required by policy: no
```

Secrets and recovery codes are never displayed.

## Resetting the MFA of a user (break-glass recovery)

If a user lost their authenticator and has no recovery codes left (or is
locked out for any other reason), reset their MFA on the server:

```console
$ python manage.py mfa_reset <username or e-mail>
```

The command shows a warning and asks you to type the username to confirm. It
then

1. removes the authenticator (TOTP secret) and all recovery codes,
2. terminates all existing sessions of that user,
3. writes an audit log entry (`byro.mfa.reset`).

For scripted recovery, `--force` skips the confirmation prompt.

!!! warning
    A reset is a recovery mechanism, not a way around the policy. **If MFA is
    required for all administrators, the reset only allows the user to enroll
    again**: after the next password login they are sent to the MFA setup and
    have to configure a new authenticator before they can use the backend. The
    global policy is not changed by the command.

Sessions can only be terminated automatically with the default
database-backed session storage (`SESSION_ENGINE` ending in `.db`); the
command tells you if that is not the case.

## Security notes

- **TOTP secrets are stored encrypted.** The encryption key is derived from
  Django's `SECRET_KEY` (see [Configuration](../configuration/reference.md)). Keep
  the secret key stable and back it up together with the database (see
  [Backup and restore](backup-restore.md)): if it is lost, no user can pass
  the MFA step any more and every account has to be reset with `mfa_reset`.
  byro offers **no configuration option to list a previous secret key as a
  fallback**; changing the secret key is therefore equivalent to losing all
  existing sessions and MFA devices, not a seamless rotation.
- **Recovery codes are stored as password hashes** and are single use.
- **Brute force protection:** after every failed code, the account's MFA is
  locked for an exponentially growing time (1, 2, 4, 8, … seconds), for
  authenticator codes and recovery codes alike. Each TOTP code is accepted
  only once. byro itself does not rate limit the password login; as before, we
  recommend rate limiting on the reverse proxy (for example nginx `limit_req`
  for `/login/`) or fail2ban on the web server logs.
- **Audit log:** enabling (`byro.mfa.enabled`), disabling
  (`byro.mfa.disabled`) and resetting (`byro.mfa.reset`) MFA, generating new
  recovery codes (`byro.mfa.recovery_codes.regenerated`) and signing in with a
  recovery code (`byro.mfa.recovery_code.used`) are recorded in the audit log.
  Secrets, codes and QR codes are never logged; failed attempts are written to
  the application log only.
- **System time:** TOTP depends on a correct clock on the server (and on the
  user's phone). Run an NTP client on the server.

## Notes for plugin developers

Every URL that requires a login is automatically covered by the MFA
enforcement, plugin views included. URLs that a plugin marks as public via the
`unauthenticated_urls` signal are exempt from MFA as well. In views,
`request.user.is_verified()` tells whether the current session has passed the
MFA step (it is always `True` for users who do not need MFA once they are past
the middleware).
