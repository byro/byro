# Configuration

This section covers what you set up *inside* a running byro installation,
through the Office - regardless of how or where byro is hosted.

- [Users and login](users-and-login.md): creating and editing accounts,
  password and OIDC/SSO login, what `is_staff`/`is_superuser` actually mean.
- [Multi-factor authentication (MFA)](mfa.md): requiring the policy for all
  accounts, checking status, recovery and the management commands (personal
  setup is in the [user guide](../usage/mfa.md)).
- [PGP email encryption](pgp.md): signing outgoing mail and encrypting mail to
  members with OpenPGP.
- [Settings](settings.md): association configuration, registration form,
  about byro and the audit log.
- [Configuration reference](../configuration/index.md): every option from
  `byro.cfg`/the `BYRO_*` environment variables.

Your own profile, your personal MFA setup and your API token are reachable
from your user menu, not from this page - see
[My account](../usage/account.md) in the user guide. Server operation,
updating, backup and restore, monitoring and the security baseline belong to
technical self-hosting and live under [Administration](operations.md); which
plugins exist and how they are installed is under
[Plugins & integrations](plugins.md).
