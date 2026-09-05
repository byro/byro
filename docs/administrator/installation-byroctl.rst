Installation with byroctl (recommended)
=======================================

``byroctl`` installs byro as a set of Docker containers, keeps everything it
needs in one directory and installs updates with a single command. It is meant
for administrators of small and medium sized organizations who want a working
byro on a Linux server without assembling the pieces by hand.

What you get:

* the official byro container image, pinned to an exact release,
* a PostgreSQL database (or a connection to your own),
* optionally Caddy as a reverse proxy that obtains and renews TLS certificates,
* one configuration file, ``byro.conf``,
* ``byroctl update`` with a safeguard copy of the database before every update.

Everything byroctl starts is plain Docker Compose. You can always look at the
files in the installation directory and use ``docker compose`` directly.

Prerequisites
-------------

* A Linux server (Debian or Ubuntu are the tested platforms) with a DNS name
  that points to it.
* Docker Engine 24 or newer with the Compose plugin 2.20 or newer. Your user
  must be allowed to use Docker (member of the ``docker`` group). Note that
  membership in that group is equivalent to root access on the machine.
* ``bash`` 4 or newer and ``curl``. Both are present on every current
  distribution.
* Free ports 80 and 443 if Caddy should terminate TLS for you, otherwise a
  reverse proxy of your own that forwards to byro.
* An SMTP server to send mail. It can be configured later.
* Roughly 2 GB of free disk space for the images, plus room for your data.

The installer does not need root. If it should install into the default
directory ``/opt/byro``, create that directory once and hand it to your user::

    $ sudo mkdir -p /opt/byro && sudo chown "$(id -u):$(id -g)" /opt/byro

Alternatively choose a directory you own with ``--root ~/byro``.

Installation
------------

Run the bootstrap script. It downloads ``byroctl`` for the current stable
release, verifies it and starts the installation::

    $ bash -c "$(curl -fsSL https://raw.githubusercontent.com/byro/byro/stable/install.sh)"

Add ``-- --root /path`` to install somewhere else, or ``-- --dry-run`` to see
what the script would do without changing anything.

The installer asks a few questions, each with a sensible default:

* the public URL of your byro, for example ``https://byro.example.org``,
* whether byro should obtain TLS certificates itself (Caddy, ports 80 and 443
  must be free), whether you run your own reverse proxy, or whether byro is
  reached directly without HTTPS (only for tests),
* language and time zone,
* whether to use the built-in PostgreSQL or an external database,
* how to send mail: a mail server on the same machine, an external SMTP
  server, or later,
* user name, e-mail address and password of the first administrator.

Then it writes the configuration, downloads the images, creates the database
schema, creates the administrator account and starts byro. At the end it
prints the URL and the paths you need to know.

Unattended installation
~~~~~~~~~~~~~~~~~~~~~~~

Every answer can be given up front with ``--set KEY=VALUE``, passwords only
through environment variables so that they never appear in a process list or
shell history::

    $ export BYROCTL_ADMIN_PASSWORD='…'
    $ bash -c "$(curl -fsSL https://raw.githubusercontent.com/byro/byro/stable/install.sh)" -- \
        --non-interactive \
        --set BYRO_SITE_URL=https://byro.example.org \
        --set BYROCTL_PROXY=caddy \
        --set BYRO_LANGUAGE_CODE=de --set BYRO_TIME_ZONE=Europe/Berlin \
        --set BYROCTL_MAIL=smtp --set BYRO_MAIL_HOST=mail.example.org --set BYRO_MAIL_FROM=byro@example.org \
        --admin-user admin --admin-email admin@example.org

``BYROCTL_PROXY`` accepts ``caddy``, ``own`` or ``none``; ``BYROCTL_DB``
accepts ``internal`` or ``external``; ``BYROCTL_MAIL`` accepts ``host``,
``smtp`` or ``skip``. Passwords for an external database or an SMTP account
come from ``BYROCTL_DB_PASSWORD`` and ``BYROCTL_MAIL_PASSWORD``. ``byroctl
install --help`` lists all options.

If the installation stops halfway, for example because the administrator's
e-mail address was rejected, fix the input and run ``byroctl install`` again.
It continues where it stopped and does not ask the general questions again.

The installation directory
--------------------------

By default everything lives in ``/opt/byro``::

    /opt/byro/
    ├── byroctl                     the tool itself (linked into /usr/local/bin)
    ├── byro.conf                   your configuration - the only file you edit
    ├── .env -> byro.conf           lets plain "docker compose" read the same file
    ├── docker-compose.yml          byro services (do not edit, byroctl replaces it on update)
    ├── compose/postgres.yml        add-on: built-in PostgreSQL
    ├── compose/caddy.yml           add-on: Caddy reverse proxy
    ├── Caddyfile
    ├── data/                       documents, uploads, keys, the secret key, logs
    ├── db/                         PostgreSQL data
    ├── caddy/                      certificates (only with Caddy)
    ├── backups/                    safeguard copies made before updates
    └── .byroctl/                   internal state

Local additions, for example extra labels for a reverse proxy, belong in a
``docker-compose.override.yml`` next to these files; byroctl never touches it.

Configuration
-------------

``byro.conf`` holds the settings of byro itself (``BYRO_*``, see
:doc:`configuration` for every option), the deployment settings
(``BYRO_DEPLOY_*``) and the list of Compose files (``COMPOSE_FILE``). Read and
change it with byroctl::

    $ byroctl config get BYRO_SITE_URL
    $ byroctl config set BYRO_MAIL_HOST mail.example.org --apply
    $ byroctl config edit
    $ byroctl config check

``--apply`` validates the file and recreates only the containers whose
settings changed. Passwords are set from the environment instead of the
command line::

    $ BYROCTL_VALUE='…' byroctl config set BYRO_MAIL_PASSWORD --apply

If you edit the file by hand: put values that contain ``$``, ``#``, spaces,
quotes or backslashes in single quotes. Compose interpolates ``$`` inside
double quotes and unquoted values, and an unquoted ``#`` after a space starts a
comment. ``byroctl config check`` reports such mistakes.

Everyday commands
-----------------

::

    $ byroctl start                  start the stack and wait until byro is healthy
    $ byroctl stop                   stop the containers, keep all data
    $ byroctl restart                recreate the byro services (not the database)
    $ byroctl logs [-f] [web]        show (or follow) logs
    $ byroctl manage <command>       run a byro management command, e.g. createsuperuser
    $ byroctl version                installed release, image digest and running version

Updates
-------

::

    $ byroctl update --check
    $ byroctl update

``update --check`` compares the installed release with the current stable one
and shows the link to the release notes. ``update`` then

1. switches to the byroctl that belongs to the new release,
2. writes a **pre-update safeguard** to ``backups/``: a dump of the database,
   your ``byro.conf`` and the secret key file,
3. adds new configuration options with their defaults to ``byro.conf`` (nothing
   is removed or reordered),
4. replaces the Compose files, pulls the new image and pins its digest,
5. stops byro, applies the database migrations and starts the new release.

If a release is flagged as breaking, byroctl asks you to read the release
notes and confirm (``--yes``). If a release changes files in ``data/``,
byroctl refuses to continue until you confirm with ``--data-safeguard-done``
that you have a full backup of that directory. Downgrades are not supported.

Should a migration fail, the byro services stay stopped and byroctl prints
the way back to the previous release, including the location of the safeguard.

.. note:: The pre-update safeguard is **not a backup**. It contains the
          database, ``byro.conf`` and the secret key, but none of the documents
          and other files in ``data/``.

Backups
-------

Back up these three things regularly, ideally while byro is stopped or with a
consistent database dump:

* ``data/`` - documents, uploads, GnuPG keys and ``.secret``. Losing
  ``.secret`` invalidates all sessions and all MFA devices.
* the database - ``db/`` while the stack is stopped, or a dump::

      $ cd /opt/byro && docker compose exec -T db pg_dump -Fc -U byro byro > byro.dump

* ``byro.conf`` - it contains your passwords, keep the copy private.

Reverse proxy
-------------

With ``BYROCTL_PROXY=caddy`` byro ships its own reverse proxy. Caddy listens on
ports 80 and 443, obtains a certificate from Let's Encrypt for the host in
``BYRO_SITE_URL`` and forwards requests to byro.

With your own reverse proxy (``BYROCTL_PROXY=own``) byro listens on
``127.0.0.1:8345`` (``BYRO_DEPLOY_BIND`` and ``BYRO_DEPLOY_PORT``). Forward
HTTPS traffic there, pass the ``Host`` header through and set
``X-Forwarded-Proto``. byroctl sets ``BYRO_TRUST_PROXY=true`` in this mode so
that byro treats forwarded requests as secure. Never set it when byro is
reachable directly, because clients could forge the header.

Troubleshooting
---------------

* ``byroctl config check`` validates ``byro.conf`` and the Compose files.
* ``byroctl logs web`` shows what the web service is doing; ``byroctl logs db``
  the database.
* ``docker compose ps`` in the installation directory shows the containers and
  their health.
* A port in use during installation means another service listens there:
  choose the ``own`` proxy mode or another ``BYRO_DEPLOY_PORT``.
* ``byroctl self-update`` re-fetches byroctl for the installed release if the
  script was damaged.
