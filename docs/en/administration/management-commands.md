# Management commands

byro is administered through management commands, the usual Django way of
running tasks that need no web interface. Invoke them like this:

```console
$ byroctl manage <command> [arguments]           # byroctl
$ docker compose run --rm manage <command> [arguments]   # Docker Compose by hand
$ python -m byro <command> [arguments]           # bare metal
```

The examples below show the byroctl form; substitute as needed.

## Setup and maintenance

* `migrate` - apply database migrations. Runs automatically when the web
  service starts with byroctl and Docker Compose (`BYRO_AUTO_MIGRATE`,
  default on); run manually after every update with bare metal.
* `rebuild` - compiles translations (including installed plugins'), collects
  static files (`collectstatic`) and compresses them (`compress`). Needed
  after every bare metal update and after every plugin change; the container
  images already ship the built result.
* `runperiodic` - runs byro's periodic tasks once (PGP refresh, expiry
  reminders, cleaning up unfinished MFA enrollments). With byroctl/Docker
  Compose the `periodic` service does this automatically every
  `BYRO_DEPLOY_PERIODIC_INTERVAL` seconds; with bare metal a systemd timer
  does (see
  [Bare metal installation](../installation/bare-metal.md#step-6-starting-byro-as-a-service)).
* `check --deploy` - Django's production checklist; also runs at container
  start (`python -m byro check`) and in CI.
* `make_testdata` - fills an empty installation with test data. For trying
  byro out and development only, not for an installation with real data.

## Account management

* `createsuperuser` - creates a new administrator account (Django built-in).
* `changepassword <username>` - resets the password of an existing account
  (Django built-in). byro has no self-service password reset; this is the
  way to recover a locked-out administrator account (see
  [Account recovery](troubleshooting.md#account-recovery)).
* `mfa_status <username or e-mail>` and `mfa_reset <username or e-mail>` -
  check MFA status, or remove all MFA devices of an account (see
  [Checking a user's MFA status](mfa.md#checking-a-users-mfa-status) and
  [Resetting the MFA of a user](mfa.md#resetting-the-mfa-of-a-user-break-glass-recovery)).

## Auditing and export

* `export_logchain` - exports the full hash chain as JSON (every entry with
  its hash and authenticated metadata); relevant for associations with audit
  obligations. All entries always appear; `-a`/`--data-include-actions` and
  `-A`/`--data-exclude-actions` (each a regex on `action_type`, `-a` defaults
  to matching everything) only control whether an entry's `data` field is
  included in the export, without changing the chain itself - useful for
  keeping sensitive payloads out of a shared export. See
  [Audit log](settings.md#audit-log) for the background.

## Reference

`<command> --help` shows all arguments of a command; `help` without an
argument lists every available command, including those added by plugins and
by Django/Django apps themselves (for example `dbshell`, `shell`), which are
not listed individually here.
