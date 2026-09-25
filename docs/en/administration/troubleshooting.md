# Monitoring, logging and troubleshooting

## Health check

byro answers unauthenticated `GET /healthz` with `200 {"status": "ok"}` when
the database connection works, `503` otherwise. The endpoint deliberately
checks only that and nothing else (no version, no configuration). For your
own monitoring, an HTTP check against this path with the correct `Host`
header (your `BYRO_SITE_URL` or `[site] url`) is enough, since byro's
`ALLOWED_HOSTS` check applies here too.

* **byroctl/Docker Compose:** the container health check already queries
  `/healthz` internally; `docker compose ps` shows the status
  (`healthy`/`unhealthy`/`starting`), and `byroctl start`, `update` and
  `config set --apply` wait for it (timeout via `BYROCTL_WEB_HEALTH_TIMEOUT`,
  see [byroctl](../installation/byroctl.md#environment-variables)). External
  monitoring can query the same path through your configured reverse proxy.
* **Bare metal:** no built-in health check process; set up an external HTTP
  check against `https://your-domain/healthz` or query gunicorn locally.

## Logging

* **byroctl/Docker Compose:** `byroctl logs [-f] [SERVICE...]` or
  `docker compose logs [-f] [SERVICE...]` show the container logs (byro
  writes to stdout/stderr, not to files inside the container). byro also
  writes log files into `BYRO_FILESYSTEM_LOGS` inside the data directory
  (see [Configuration](../configuration/reference.md#the-filesystem-section)).
* **Bare metal:** `journalctl -u byro-web` and `journalctl -u byro-periodic`
  show the systemd logs; the log directory from `[filesystem] logs` also
  holds byro's own log files. byro's startup output names this directory.
* **Errors by mail:** the `[logging]` section (`BYRO_LOGGING_EMAIL`,
  `BYRO_LOGGING_EMAIL_LEVEL`) mails log messages from a configurable severity
  onward, regardless of the installation path (see
  [Configuration](../configuration/reference.md#the-logging-section)). Useful to
  learn about server errors without actively watching the logs.

## Resources and scaling

byro scales within one server through the number of gunicorn workers
(`BYRO_DEPLOY_WEB_WORKERS` with Docker/byroctl, `--workers` in the systemd
unit with bare metal). There is **no built-in horizontal scaling across
hosts**: the secret key lives locally in `data/.secret`, there is no
distributed job queue for periodic tasks (exactly one `periodic` process
should run, otherwise tasks run twice), and uploads land in the local data
directory. Multiple `web` processes on different hosts in front of the same
database are possible if they share `data/` (in particular `.secret` and
media) and exactly one `periodic` process; byroctl does not support this out
of the box.

## Account recovery

byro has **no self-service password reset** for office accounts. If an
administrator is locked out, set a new password with a management command
(see [Management commands](management-commands.md#account-management)):

```console
$ byroctl manage changepassword <username>
$ docker compose run --rm manage changepassword <username>
$ python -m byro changepassword <username>
```

If no administrator account is left at all, create a new one the same way
with `createsuperuser`. For an MFA-related lockout (lost device), see
`mfa_reset` in
[Resetting the MFA of a user](mfa.md#resetting-the-mfa-of-a-user-break-glass-recovery).

## Common problems

* **`byroctl config check` reports an error in `byro.conf`.** Usually a value
  containing `$`, `#`, a space or a backslash that is not in single quotes
  (see [byroctl](../installation/byroctl.md#configuration)).
* **A port is already in use during installation.** Another service is
  listening there; choose your own reverse proxy mode or a different
  `BYRO_DEPLOY_PORT`.
* **byro does not become healthy (`wait_healthy`/container `unhealthy`).**
  Check the web service's logs: usually a failed database connection, a
  missing required variable (an empty `BYRO_DB_PASS` prevents the stack from
  starting at all) or a failed migration.
* **Absolute URLs are `http://` instead of `https://`, or OIDC redirects
  fail.** `[site] trust_proxy` (`BYRO_TRUST_PROXY`) is not set even though a
  reverse proxy terminates TLS (see
  [Security baseline](security-baseline.md#tls-and-reverse-proxy)).
* **A plugin build fails.** See
  [Plugin troubleshooting](plugin-management.md#troubleshooting).
