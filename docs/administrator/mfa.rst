.. _mfa:

Multi-factor authentication (MFA)
=================================

byro supports multi-factor authentication for all users of the backend
("office") based on time-based one-time passwords (TOTP, :rfc:`6238`). Any
common authenticator app works, for example Aegis, Google Authenticator,
Microsoft Authenticator, 1Password or Bitwarden.

MFA is **optional by default**: every backend user can enable it for their
own account. Administrators can additionally **require MFA for all
administrators**, i.e. for every user who can log in to the backend.

MFA only concerns the interactive backend login. It does not change

- the member pages: members keep using their personal links, no login or
  second factor is needed there,
- the REST API: API tokens keep working, regardless of the MFA state of the
  token's user or of the global policy. API requests are never redirected to
  an MFA page.

.. note:: byro grants access to the complete backend to every active user
   account, there are no separate roles or a "staff" flag for the office.
   The MFA policy therefore applies to *every* user who can log in.

For backend users
-----------------

Setting up MFA
~~~~~~~~~~~~~~

1. Open the user menu (your username in the top right corner) and choose
   *Multi-factor authentication* (also reachable from the *Multi-factor
   authentication* button on your own profile page).
2. Click *Set up MFA*.
3. Scan the QR code with your authenticator app. If you cannot scan it,
   enter the key shown below the QR code manually (type: time-based / TOTP,
   6 digits, 30 seconds, SHA-1).
4. Enter the six-digit code your app shows and click *Verify and enable*.
   MFA is only activated once a code has been verified successfully – simply
   opening the setup page does not change anything.
5. byro now shows **ten recovery codes**. Store them in a safe place (for
   example a password manager). They are shown only once.

From now on, every login asks for a code from your authenticator app after
the password. There is no way to skip this step for an account with MFA
enabled.

Signing in
~~~~~~~~~~

Enter username and password as before. On the next page, enter the current
six-digit code from your authenticator app. Codes are valid for a short
time only and every code can be used only once.

Using a recovery code
~~~~~~~~~~~~~~~~~~~~~

If you do not have access to your authenticator app, click *Use a recovery
code* on the code page and enter one of your recovery codes
(``XXXX-XXXX-XXXX``, dashes and case do not matter). Every recovery code
works exactly once. After signing in, byro tells you how many codes are
left; generate new codes if you are running low.

Generating new recovery codes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*User menu → Multi-factor authentication → Generate new recovery codes*.
You have to confirm with a current code from your authenticator app. All
previous recovery codes stop working immediately.

Disabling MFA
~~~~~~~~~~~~~

*User menu → Multi-factor authentication → Disable MFA*, confirmed with a
current authenticator code. This removes the authenticator and all recovery
codes; afterwards the account is protected by the password only.

If MFA is required for all administrators, this option is not available.

Lost authenticator and no recovery codes left
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Ask an administrator with shell access to the byro server to reset your MFA
with the management command described below. It is not possible to reset
another user's MFA from the web interface.

For administrators
------------------

Requiring MFA for all administrators
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Under *Settings → General* you find the card *Multi-factor authentication*
with the option **Require MFA for all administrators** (off by default).
Enabling it has the following effects:

- Users who already use MFA are not affected; they can no longer disable
  it, though.
- Users without MFA are sent to the MFA setup right after entering their
  password. Until the setup is complete, they cannot use any other page of
  the backend (only the setup itself and logout).
- Sessions that were already logged in without MFA are treated the same
  way: the next request is redirected to the setup.
- The setting applies to logins via single sign-on (OIDC) as well. byro does
  not evaluate MFA information from the identity provider; OIDC users have
  to complete the byro TOTP step, too.
- Enabling the option does not require that everybody has set up MFA
  already. Nobody is locked out – but every user has to enroll at their
  next login.

Changing the option is recorded in the audit log.

Display in authenticator apps
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Entries created from byro's QR code always show **BYRO** as the service
name. The second line, the account name, is configurable in the same
settings card (*Account name in authenticator apps*). The default is
``{association} - {username}``, i.e. the association name from the general
settings followed by the username. Available placeholders: ``{username}``,
``{email}``, ``{name}`` (the user's name) and ``{association}``, for example
``{name} ({email})``.

Colons are not allowed: the ``otpauth`` format used by authenticator apps
separates the service name from the account with a colon.

The setting only affects newly set up authenticators; existing entries in the
users' apps keep the name they had when they were created.

Checking a user's MFA status
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The user list marks users with MFA with a shield icon. On the server::

    python manage.py mfa_status <username or e-mail>

prints something like::

    User: admin (admin@example.org)
    Active: yes
    MFA enabled: yes
    TOTP device: configured (since Sept. 1, 2026, 10:00 a.m., last used Sept. 4, 2026, 9:12 a.m.)
    Recovery codes remaining: 6
    MFA required by policy: no

Secrets and recovery codes are never displayed.

Resetting the MFA of a user (break-glass recovery)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If a user lost their authenticator and has no recovery codes left (or is
locked out for any other reason), reset their MFA on the server::

    python manage.py mfa_reset <username or e-mail>

The command shows a warning and asks you to type the username to confirm.
It then

1. removes the authenticator (TOTP secret) and all recovery codes,
2. terminates all existing sessions of that user,
3. writes an audit log entry (``byro.mfa.reset``).

For scripted recovery, ``--force`` skips the confirmation prompt.

.. warning:: A reset is a recovery mechanism, not a way around the policy.
   **If MFA is required for all administrators, the reset only allows the
   user to enroll again**: after the next password login they are sent to
   the MFA setup and have to configure a new authenticator before they can
   use the backend. The global policy is not changed by the command.

Sessions can only be terminated automatically with the default
database-backed session storage (``SESSION_ENGINE`` ending in ``.db``); the
command tells you if that is not the case.

Security notes
~~~~~~~~~~~~~~

- **TOTP secrets are stored encrypted.** The encryption key is derived from
  Django's ``SECRET_KEY`` (see :doc:`configuration`). Keep the secret key
  stable and back it up together with the database: if it is lost, no user
  can pass the MFA step any more and every account has to be reset with
  ``mfa_reset``. When rotating the key, list the previous key in
  ``SECRET_KEY_FALLBACKS`` so existing devices keep working.
- **Recovery codes are stored as password hashes** and are single use.
- **Brute force protection:** after every failed code, the account's MFA is
  locked for an exponentially growing time (1, 2, 4, 8, … seconds), for
  authenticator codes and recovery codes alike. Each TOTP code is accepted
  only once. byro itself does not rate limit the password login; as before,
  we recommend rate limiting on the reverse proxy (for example nginx
  ``limit_req`` for ``/login/``) or fail2ban on the web server logs.
- **Audit log:** enabling (``byro.mfa.enabled``), disabling
  (``byro.mfa.disabled``) and resetting (``byro.mfa.reset``) MFA, generating
  new recovery codes (``byro.mfa.recovery_codes.regenerated``) and signing
  in with a recovery code (``byro.mfa.recovery_code.used``) are recorded in
  the audit log. Secrets, codes and QR codes are never logged; failed
  attempts are written to the application log only.
- **System time:** TOTP depends on a correct clock on the server (and on
  the user's phone). Run an NTP client on the server.

Notes for plugin developers
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Every URL that requires a login is automatically covered by the MFA
enforcement, plugin views included. URLs that a plugin marks as public via
the ``unauthenticated_urls`` signal are exempt from MFA as well. In views,
``request.user.is_verified()`` tells whether the current session has passed
the MFA step (it is always ``True`` for users who do not need MFA once they
are past the middleware).
