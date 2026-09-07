# Administration

This section covers the administration of a running byro instance: the
features that administrators configure inside byro and the maintenance tasks
around it.

- [Users and login](users-and-login.md): creating and editing accounts,
  password and OIDC/SSO login, what `is_staff`/`is_superuser` actually mean.
- [Multi-factor authentication (MFA)](mfa.md): TOTP for backend users, the
  policy for administrators, recovery and the management commands.
- [PGP email encryption](pgp.md): signing outgoing mail and encrypting mail to
  members with OpenPGP.
- [Settings](settings.md): association configuration, registration form, API
  token, about byro and the audit log.
- [Plugins](plugins.md): how plugins are installed and maintained in a byroctl,
  Docker Compose or bare metal installation (managing them itself happens at
  the deployment layer, not through a page inside the Office).
- [Updating](updating.md): what applies to a byro update across installation
  paths, and the limits of downgrades.
- [Backup and restore](backup-restore.md): what needs to be backed up,
  restoring, and moving to a new host.
- [Management commands](management-commands.md): reference of the
  command-line commands for setup, maintenance and account management.
- [Monitoring, logging and troubleshooting](troubleshooting.md): health
  checks, log locations, resources/scaling and common problems.
- [Security baseline](security-baseline.md): TLS, secrets, container
  privileges and account recovery at a glance.

The exact updating and backup commands per installation path are still on the
installation pages ([byroctl](../installation/byroctl.md#updates),
[Docker Compose](../installation/docker-compose.md#updates),
[bare metal](../installation/bare-metal.md#next-steps-updates)).
