# Configuration

You can configure byro in two different ways: using configuration files or
environment variables. You can combine those two options, and their precedence
is in this order:

1. Environment variables
2. Configuration files
    - Only the file named in the environment variable `BYRO_CONFIG_FILE` if
      that variable is set (byro refuses to start if the file does not exist),
      **or**:
    - The following three configuration files, where a later file overrides an
      earlier one:
        - `/etc/byro/byro.cfg`
        - `~/.byro.cfg` in the home of the executing user
        - `byro.cfg` in the current working directory of the byro process (for
          a development checkout that is the `src` directory, next to
          `byro.example.cfg`)
3. Sensible defaults

The container deployments ([byroctl](../installation/byroctl.md),
[Docker Compose](../installation/docker-compose.md)) use the environment
variables only, written as `KEY=VALUE` lines in `byro.conf`. The bare metal
installation uses the configuration file. Both forms describe the same options.

This page explains the options by configuration file section and notes the
corresponding environment variable next to it. A configuration file looks like
this:

```ini
--8<-- "src/byro.example.cfg"
```

!!! note
    This example file does not show every option in this reference (for
    example `[oidc]` and `[site] https`/`trust_proxy`/`secret` are missing) -
    it is a starting template, not a complete map of every possible key.
    Every option, including the ones not preset here, can be set as
    described below.

## The filesystem section

### `data`

- The `data` option describes the path that is the base for the media files
  directory, and where byro will save log files. Unless you have a compelling
  reason to keep those files apart, setting the `data` option is the easiest
  way to configure byro.
- **Environment variable:** `BYRO_DATA_DIR`
- **Default:** A directory called `data` next to byro's `manage.py`.

### `media`

- The `media` option sets the media directory that contains user generated
  files. It needs to be writable by the byro process.
- **Environment variable:** `BYRO_FILESYSTEM_MEDIA`
- **Default:** A directory called `media` in the `data` directory (see above).

### `logs`

- The `logs` option sets the log directory that contains logged data. It needs
  to be writable by the byro process.
- **Environment variable:** `BYRO_FILESYSTEM_LOGS`
- **Default:** A directory called `logs` in the `data` directory (see above).

### `static`

- The `static` option sets the directory that contains static files. It needs
  to be writable by the byro process. byro will put files there during the
  `collectstatic` command.
- **Environment variable:** `BYRO_FILESYSTEM_STATIC`
- **Default:** A directory called `static.dist` next to byro's `manage.py`.

## The site section

### `debug`

- Decides if byro runs in debug mode. Please use this mode for development and
  debugging, not for live usage.
- **Environment variable:** `BYRO_DEBUG`
- **Default:** `True` if you're executing `runserver`, `False` otherwise.
  **Never run a production server in debug mode.**

### `url`

- This value will appear wherever byro needs to render full URLs (for example
  in emails), and set the appropriate allowed hosts variables.
- **Environment variable:** `BYRO_SITE_URL`
- **Default:** `http://localhost`

### `https`

- Decides whether byro marks its session cookie `Secure`
  (`SESSION_COOKIE_SECURE`), sending it only over HTTPS connections. Set it to
  `True` as soon as byro is only reachable over HTTPS - directly or through a
  reverse proxy. Independent of `trust_proxy`: `https` only controls cookie
  security, not whether byro trusts an `X-Forwarded-Proto` header.
- **Environment variable:** `BYRO_HTTPS`
- **Default:** follows whether `url` starts with `https://`.

### `trust_proxy`

- Set this to `True` **only** if byro runs behind a reverse proxy (nginx,
  Apache, Caddy, …) that terminates TLS and sets the `X-Forwarded-Proto`
  header. byro then treats requests with `X-Forwarded-Proto: https` as secure,
  which is required for correct absolute URLs, for example the OpenID Connect
  redirect URI. Leave it at `False` when byro is reachable directly, because
  clients could otherwise forge the header. This setting is independent of
  `https`, which only controls cookie security.
- **Environment variable:** `BYRO_TRUST_PROXY`
- **Default:** `False`

### `secret`

- Every Django application has a secret that Django uses for cryptographic
  signing. You do not need to set this variable – byro will generate a secret
  key and save it in a local file if you do not set it manually.
- **Default:** None

## The oidc section

Optional single sign-on through OpenID Connect, in addition to the regular
password login (never as a replacement - an account with no password and no
matching OIDC claim could otherwise no longer sign in at all). If
`issuer_url` is empty, the login page shows no SSO button and the related
routes answer 404. For the flow, the group check and its security
consequences, see [Users and login](../administration/users-and-login.md).
The MFA policy itself is configured in *Settings → General*. Its OIDC-exception
variant trusts the identity provider to enforce MFA for OIDC sessions; see
[Multi-factor authentication](../administration/mfa.md) before selecting it.

### `issuer_url`

- Base URL of the OIDC provider. byro loads its
  `.well-known/openid-configuration` (discovery, cached for 4 hours) and
  derives every other endpoint from it. Leave empty to disable OIDC login.
- **Environment variable:** `BYRO_OIDC_ISSUER_URL`
- **Default:** `''`

### `client_id`

- Client id byro is registered as with the OIDC provider.
- **Environment variable:** `BYRO_OIDC_CLIENT_ID`
- **Default:** `''`

### `client_secret`

- The matching client secret. Like any secret, never pass it on the command
  line; `byroctl install`/`config set` read it from
  `BYROCTL_OIDC_CLIENT_SECRET` (see
  [byroctl](../installation/byroctl.md#environment-variables)).
- **Environment variable:** `BYRO_OIDC_CLIENT_SECRET`
- **Default:** `''`

### `admin_group`

- When set, the `groups` claim (a string or a list) in the ID token or
  userinfo response must contain this value, or sign-in fails. **This only
  controls who may sign in at all - not what the account can do inside the
  Office afterwards** (see the security consequences under
  [Users and login](../administration/users-and-login.md)).
- **Environment variable:** `BYRO_OIDC_ADMIN_GROUP`
- **Default:** `''` (no group check, every successful OIDC login is accepted)

### `auto_create_account`

- Automatically creates a new, passwordless byro account when the OIDC
  username (see `username_field`) does not match an existing account yet. If
  `False`, sign-in fails for unknown usernames even if `admin_group` is
  satisfied.
- **Environment variable:** `BYRO_OIDC_AUTO_CREATE_ACCOUNT`
- **Default:** `False`

### `username_field`

- Name of the claim (in the ID token, or in the userinfo response if not
  present there) used as the byro username. Must stay stable across logins.
- **Environment variable:** `BYRO_OIDC_USERNAME_FIELD`
- **Default:** `'preferred_username'`

## The database section

### `name`

- The database's name.
- **Environment variable:** `BYRO_DB_NAME`
- **Default:** `''`

### `user`

- The database user.
- **Environment variable:** `BYRO_DB_USER`
- **Default:** `''`

### `password`

- The database password.
- **Environment variable:** `BYRO_DB_PASS`
- **Default:** `''`

### `host`

- The database host, or the socket location, as needed.
- **Environment variable:** `BYRO_DB_HOST`
- **Default:** `''`

### `port`

- The database port.
- **Environment variable:** `BYRO_DB_PORT`
- **Default:** `''`

### `engine`

- The database engine.
- **Environment variable:** `BYRO_DB_ENGINE`
- **Default:** `'postgresql'` – by default it falls back to the PostgreSQL
  backend
- **Possible values:** `postgresql`, `mysql`, `sqlite3`, `oracle`

## The mail section

### `from`

- The fall-back sender address, e.g. for when byro sends event independent
  emails.
- **Environment variable:** `BYRO_MAIL_FROM`
- **Default:** `admin@localhost`

### `host`

- The email server host address.
- **Environment variable:** `BYRO_MAIL_HOST`
- **Default:** `localhost`

### `port`

- The email server port.
- **Environment variable:** `BYRO_MAIL_PORT`
- **Default:** `25`

### `user`

- The user account for mail server authentication, if needed.
- **Environment variable:** `BYRO_MAIL_USER`
- **Default:** `''`

### `password`

- The password for mail server authentication, if needed.
- **Environment variable:** `BYRO_MAIL_PASSWORD`
- **Default:** `''`

### `tls`

- Should byro use TLS when sending mail? Please choose either TLS or SSL.
- **Environment variable:** `BYRO_MAIL_TLS`
- **Default:** `False`

### `ssl`

- Should byro use SSL when sending mail? Please choose either TLS or SSL.
- **Environment variable:** `BYRO_MAIL_SSL`
- **Default:** `False`

## The PGP section

### `backend`

- Python import path of the PGP backend used for signing, encryption, and key
  imports.
- **Environment variable:** `BYRO_PGP_BACKEND`
- **Default:** `byro.mails.gnupg_backend.GnuPGBackend`

### `home`

- GnuPG home directory used by byro. This directory stores public keys imported
  by byro and is also where GnuPG looks for the organization's private signing
  key. It should only be readable and writable by the user running byro.
- **Environment variable:** `BYRO_PGP_HOME`
- **Default:** `''` – GnuPG uses its normal default for the executing user.

## The logging section

### `email`

- The email address (or addresses, comma separated) to send system logs to.
- **Environment variable:** `BYRO_LOGGING_EMAIL`
- **Default:** `''`

### `email_level`

- The log level to start sending emails at. Any of
  `[DEBUG, INFO, WARNING, ERROR, CRITICAL]`.
- **Environment variable:** `BYRO_LOGGING_EMAIL_LEVEL`
- **Default:** `'ERROR'`

## The locale section

### `language_code`

- The system's default locale.
- **Environment variable:** `BYRO_LANGUAGE_CODE`
- **Default:** `'en'`. Set it explicitly to `de` if your members expect
  German; the container installations already do this in their bundled
  `byro.conf.example`.

### `time_zone`

- The system's default time zone as a `pytz` name.
- **Environment variable:** `BYRO_TIME_ZONE`
- **Default:** `'UTC'`
