# Security baseline

This page collects the operational security decisions that apply to every
byro installation, regardless of the installation path. Sign-in (OIDC,
password login) and user roles are covered under
[Users and login](users-and-login.md), the audit log under
[Settings](settings.md#audit-log),
[multi-factor authentication](mfa.md) on its own page.

## TLS and reverse proxy

**Never run byro without HTTPS**, except for testing. byro processes
personal and financial data of your members.

* With `BYROCTL_PROXY=caddy` (byroctl's default), Caddy automatically
  obtains and renews a Let's Encrypt certificate.
* With your own reverse proxy, it must terminate TLS and set the
  `X-Forwarded-Proto` header, and byro must have `[site] trust_proxy`
  (`BYRO_TRUST_PROXY=true`) set so it correctly treats forwarded requests as
  secure (absolute URLs, cookie security, OIDC redirects). **Never set
  `trust_proxy` when byro is reachable directly without such a proxy** -
  clients could forge the header and make byro trust them wrongly.
* Never serve `/media/` directly from the web server: byro only hands out
  documents after its own access check. A reverse proxy alias on the media
  directory exposes every uploaded document to anyone who knows the URL.

## Secrets and how to protect them

* **`data/.secret`** holds Django's `SECRET_KEY`, among other things used to
  derive the encryption of TOTP secrets. Losing it invalidates all sessions
  and all MFA devices; there is no way to list a previous key as a fallback
  (see [MFA](mfa.md#security-notes)). Back it up as described in
  [Backup and restore](backup-restore.md).
* **`byro.conf`/`byro.cfg`** holds database and mail passwords and, if
  configured, the OIDC client secret. Keep the file at `0600` (byroctl and
  the installation guides set this) and treat copies as equally
  confidential.
* **Never pass secrets on the command line.** `byroctl install`/`config set`
  only accept secrets from environment variables (`BYROCTL_ADMIN_PASSWORD`,
  `BYROCTL_DB_PASSWORD`, `BYROCTL_MAIL_PASSWORD`,
  `BYROCTL_OIDC_CLIENT_SECRET`), never as a `--set` value, so they never end
  up in a process list or shell history.

## Container privileges

The container images run unprivileged as user `byro` by default. The
entrypoint starts as root only to optionally apply `BYRO_UID`/`BYRO_GID`
(fail closed: only numeric, not-already-taken, non-root ids are accepted)
and to fix the ownership of the data directory, then drops privileges
permanently. Only change `BYRO_UID`/`BYRO_GID` if you need to share `data/`
with a specific host user.

## Account recovery

byro has no self-service password reset for office accounts. This is a
deliberate gap, not an oversight: the recovery path for a locked-out
administrator account goes through the command line
(`changepassword`/`createsuperuser`), see
[Account recovery](troubleshooting.md#account-recovery). Anyone with access
to the server's command line can therefore take over any account - protect
server access accordingly.

## Web security headers

byro sets a few headers unconditionally, with no configuration option:
`X-Frame-Options: DENY` (no embedding in a foreign `<iframe>`),
`X-Content-Type-Options: nosniff`, and its own cookie names for the session
(`byro_session`) and CSRF (`byro_csrftoken`). `CSRF_TRUSTED_ORIGINS` is
derived automatically from `[site] url`, you do not maintain it yourself.
There is **no HSTS setting in the code** - that is your reverse proxy's job
(the Caddy add-on does not set it automatically; add it yourself in a
Caddyfile snippet or your proxy configuration if you want it).

## What is deliberately not here

OpenID Connect login, user roles/`is_staff` and the audit log are security
relevant, but are the concern of administration *inside* byro, not of
self-hosting; they are covered under
[Users and login](users-and-login.md) and
[Settings](settings.md#audit-log). For context: the API documentation
(`/api/v1/docs/`) and the API schema (`/api/v1/schema/`) are reachable
without login, the API itself requires a token and `is_staff` (see
[Development & API](../development/overview.md)).
