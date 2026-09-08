Configuration
=============

You can configure byro in two different ways: using configuration files or
environment variables. You can combine those two options, and their precedence
is in this order:

1. Environment variables
2. Configuration files
    - Only the file named in the environment variable ``BYRO_CONFIG_FILE`` if that variable is set
      (byro refuses to start if the file does not exist), **or**:
    - The following three configuration files, where a later file overrides an earlier one:
       - ``/etc/byro/byro.cfg``
       - ``~/.byro.cfg`` in the home of the executing user
       - ``byro.cfg`` in the current working directory of the byro process (for a development checkout
         that is the ``src`` directory, next to ``byro.example.cfg``)
3. Sensible defaults

The container deployments (:doc:`installation-byroctl`, :doc:`installation-compose`) use the
environment variables only, written as ``KEY=VALUE`` lines in ``byro.conf``. The plain installation
uses the configuration file. Both forms describe the same options.

This page explains the options by configuration file section and notes the corresponding environment
variable next to it. A configuration file looks like this:

.. literalinclude:: ../../src/byro.example.cfg
   :language: ini

The filesystem section
----------------------

``data``
~~~~~~~~

- The ``data`` option describes the path that is the base for the media files
  directory, and where byro will save log files. Unless you have a
  compelling reason to keep those files apart, setting the ``data`` option is
  the easiest way to configure byro.
- **Environment variable:** ``BYRO_DATA_DIR``
- **Default:** A directory called ``data`` next to byro's ``manage.py``.

``media``
~~~~~~~~~

- The ``media`` option sets the media directory that contains user generated files. It needs to
  be writable by the byro process.
- **Environment variable:** ``BYRO_FILESYSTEM_MEDIA``
- **Default:** A directory called ``media`` in the ``data`` directory (see above).

``logs``
~~~~~~~~

- The ``logs`` option sets the log directory that contains logged data. It needs to
  be writable by the byro process.
- **Environment variable:** ``BYRO_FILESYSTEM_LOGS``
- **Default:** A directory called ``logs`` in the ``data`` directory (see above).

``static``
~~~~~~~~~~

- The ``statics`` option sets the directory that contains static files. It needs to
  be writable by the byro process. byro will put files there during the
  ``collectstatic`` command.
- **Environment variable:** ``BYRO_FILESYSTEM_STATIC``
- **Default:** A directory called ``static.dist`` next to byro's ``manage.py``.

The site section
----------------

``debug``
~~~~~~~~~

- Decides if byro runs in debug mode. Please use this mode for development and debugging, not
  for live usage.
- **Environment variable:** ``BYRO_DEBUG``
- **Default:** ``True`` if you're executing ``runserver``, ``False`` otherwise. **Never run a
  production server in debug mode.**

``url``
~~~~~~~

- This value will appear wherever byro needs to render full URLs (for example in emails and),
  and set the appropriate allowed hosts variables.
- **Environment variable:** ``BYRO_SITE_URL``
- **Default:** ``http://localhost``

``trust_proxy``
~~~~~~~~~~~~~~~

- Set this to ``True`` **only** if byro runs behind a reverse proxy (nginx, Apache, Caddy, …)
  that terminates TLS and sets the ``X-Forwarded-Proto`` header. byro then treats requests
  with ``X-Forwarded-Proto: https`` as secure, which is required for correct absolute URLs,
  for example the OpenID Connect redirect URI. Leave it at ``False`` when byro is reachable
  directly, because clients could otherwise forge the header. This setting is independent of
  ``https``, which only controls cookie security.
- **Environment variable:** ``BYRO_TRUST_PROXY``
- **Default:** ``False``

``secret``
~~~~~~~~~~

- Every Django application has a secret that Django uses for cryptographic signing.
  You do not need to set this variable – byro will generate a secret key and save it in a local file if
  you do not set it manually.
- **Default:** None


The database section
--------------------

``name``
~~~~~~~~

- The database's name.
- **Environment variable:** ``BYRO_DB_NAME``
- **Default:** ``''``

``user``
~~~~~~~~

- The database user.
- **Environment variable:** ``BYRO_DB_USER``
- **Default:** ``''``

``password``
~~~~~~~~~~~~

- The database password.
- **Environment variable:** ``BYRO_DB_PASS``
- **Default:** ``''``

``host``
~~~~~~~~

- The database host, or the socket location, as needed.
- **Environment variable:** ``BYRO_DB_HOST``
- **Default:** ``''``

``port``
~~~~~~~~

- The database port.
- **Environment variable:** ``BYRO_DB_PORT``
- **Default:** ``''``

``engine``
~~~~~~~~~~

- The database engine.
- **Environment variable:** ``BYRO_DB_ENGINE``
- **Default:** ``'postgresql'`` – by default it falls back to the PostgreSQL backend
- **Possible values:** ``postgresql``, ``mysql``, ``sqlite3``, ``oracle``

The mail section
----------------

``from``
~~~~~~~~

- The fall-back sender address, e.g. for when byro sends event independent emails.
- **Environment variable:** ``BYRO_MAIL_FROM``
- **Default:** ``admin@localhost``

``host``
~~~~~~~~

- The email server host address.
- **Environment variable:** ``BYRO_MAIL_HOST``
- **Default:** ``localhost``

``port``
~~~~~~~~

- The email server port.
- **Environment variable:** ``BYRO_MAIL_PORT``
- **Default:** ``25``

``user``
~~~~~~~~

- The user account for mail server authentication, if needed.
- **Environment variable:** ``BYRO_MAIL_USER``
- **Default:** ``''``

``password``
~~~~~~~~~~~~

- The password for mail server authentication, if needed.
- **Environment variable:** ``BYRO_MAIL_PASSWORD``
- **Default:** ``''``

``tls``
~~~~~~~

- Should byro use TLS when sending mail? Please choose either TLS or SSL.
- **Environment variable:** ``BYRO_MAIL_TLS``
- **Default:** ``False``

``ssl``
~~~~~~~

- Should byro use SSL when sending mail? Please choose either TLS or SSL.
- **Environment variable:** ``BYRO_MAIL_SSL``
- **Default:** ``False``

The PGP section
---------------

``backend``
~~~~~~~~~~~

- Python import path of the PGP backend used for signing, encryption, and key
  imports.
- **Environment variable:** ``BYRO_PGP_BACKEND``
- **Default:** ``byro.mails.gnupg_backend.GnuPGBackend``

``home``
~~~~~~~~

- GnuPG home directory used by byro. This directory stores public keys imported
  by byro and is also where GnuPG looks for the organization's private signing
  key. It should only be readable and writable by the user running byro.
- **Environment variable:** ``BYRO_PGP_HOME``
- **Default:** ``''`` – GnuPG uses its normal default for the executing user.

The logging section
-------------------

``email``
~~~~~~~~~

- The email address (or addresses, comma separated) to send system logs to.
- **Environment variable:** ``BYRO_LOGGING_EMAIL``
- **Default:** ``''``

``email_level``
~~~~~~~~~~~~~~~

- The log level to start sending emails at. Any of ``[DEBUG, INFO, WARNING, ERROR, CRITICAL]``.
- **Environment variable:** ``BYRO_LOGGING_EMAIL_LEVEL``
- **Default:** ``'ERROR'``

The locale section
------------------

``language_code``
~~~~~~~~~~~~~~~~~

- The system's default locale.
- **Environment variable:** ``BYRO_LANGUAGE_CODE``
- **Default:** ``'de'``

``time_zone``
~~~~~~~~~~~~~

- The system's default time zone as a ``pytz`` name.
- **Environment variable:** ``BYRO_TIME_ZONE``
- **Default:** ``'UTC'``

The OIDC section
-----------------

This section configures optional single sign-on login via OpenID Connect. Leave
``issuer_url`` empty (the default) to disable it entirely; the password login form
is unaffected either way. Only accounts with the ``is_staff`` flag can log in to
the backend, via password or OIDC.

``issuer_url``
~~~~~~~~~~~~~~

- The identity provider's issuer URL. byro discovers the rest of the OIDC
  endpoints from ``<issuer_url>/.well-known/openid-configuration``.
- **Environment variable:** ``BYRO_OIDC_ISSUER_URL``
- **Default:** ``''`` – OIDC login is disabled.

``client_id`` / ``client_secret``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- The OAuth2 client credentials registered with the identity provider for byro.
- **Environment variables:** ``BYRO_OIDC_CLIENT_ID``, ``BYRO_OIDC_CLIENT_SECRET``
- **Default:** ``''``

``admin_group``
~~~~~~~~~~~~~~~

- Restricts OIDC login to members of this group, as reported by the identity
  provider's ``groups`` claim (or the userinfo endpoint). Leave empty to allow
  any authenticated OIDC user through.
- A local account that does not exist yet is auto-created (if
  ``auto_create_account`` is enabled) with ``is_staff`` set, since reaching this
  point already proved office access is intended.
- **Environment variable:** ``BYRO_OIDC_ADMIN_GROUP``
- **Default:** ``''``

``superuser_group``
~~~~~~~~~~~~~~~~~~~

- If set, members of this group are granted superuser rights: a newly
  auto-created account is created as a superuser, and – only if
  ``sync_groups`` is enabled – an existing account's superuser status is kept
  in sync with current membership on every login.
- Leave empty to never grant or change superuser status via OIDC; existing
  accounts then keep whatever superuser status was set locally, and new
  accounts are never created as superusers.
- **Environment variable:** ``BYRO_OIDC_SUPERUSER_GROUP``
- **Default:** ``''``

``auto_create_account``
~~~~~~~~~~~~~~~~~~~~~~~~

- Set to true to automatically create a local account the first time someone
  passes the ``admin_group`` check via OIDC. If false, only users who already
  have a local account can log in via OIDC.
- **Environment variable:** ``BYRO_OIDC_AUTO_CREATE_ACCOUNT``
- **Default:** ``false``

``sync_groups``
~~~~~~~~~~~~~~~

- Set to true to re-evaluate ``admin_group``/``superuser_group`` membership on
  *every* OIDC login of an *existing* account, updating its ``is_staff`` and
  ``is_superuser`` flags to match. With this off (the default), group
  membership only matters when an account is first auto-created; an existing
  account's local flags are never touched again by OIDC login afterwards.
- **Environment variable:** ``BYRO_OIDC_SYNC_GROUPS``
- **Default:** ``false``

.. warning:: Enabling ``sync_groups`` together with ``superuser_group`` ties
   byro's superuser status directly to the identity provider's group
   membership. If that group is ever deleted, renamed, or misconfigured at
   the identity provider so that nobody is a member any more, **every**
   account loses superuser status the next time it logs in via OIDC – there
   is no built-in protection against ending up with zero superusers this
   way (unlike removing your own superuser status by hand in byro's user
   management, which is blocked). The same applies to ``admin_group`` and
   ``is_staff``: if it is ever emptied out at the identity provider, every
   synced account can lose backend access entirely. Recovering from this
   requires direct database access (or a Django management shell) to set
   ``is_staff``/``is_superuser`` back on at least one account – there is no
   recovery path through byro's own interface once nobody can log in. Test
   group changes carefully, and keep at least one break-glass account (a
   local superuser with a usable password, not managed via OIDC at all) for
   this scenario.

``mfa_exempt``
~~~~~~~~~~~~~~

- Set to true to skip byro's own MFA challenge (and any policy-driven MFA
  enrollment, see :doc:`mfa`) for sessions established via OIDC login, on the
  assumption that the identity provider already enforces its own MFA. Only
  applies to the session that was actually authenticated via OIDC; logging in
  with a password is always subject to byro's MFA policy, regardless of this
  setting.
- **Environment variable:** ``BYRO_OIDC_MFA_EXEMPT``
- **Default:** ``false``

``username_field``
~~~~~~~~~~~~~~~~~~~

- The OIDC claim used as the Django username. Existing accounts are matched
  against this claim on every login, so changing it after accounts already
  exist will make byro treat those logins as new users.
- **Environment variable:** ``BYRO_OIDC_USERNAME_FIELD``
- **Default:** ``'preferred_username'``
