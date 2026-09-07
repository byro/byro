# Administration

What applies across installation paths for the day-to-day operation of a
byro installation - regardless of whether it was set up with byroctl, Docker
Compose or bare metal (see [Installation](../installation/overview.md)). What
you set up *inside* byro afterwards (user accounts, login, MFA, settings) is
under [Configuration](overview.md).

- [Updating](updating.md): what applies to an update, and the limits of
  downgrades.
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
