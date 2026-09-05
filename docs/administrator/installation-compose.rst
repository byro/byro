Installation with Docker Compose
================================

This page describes the same deployment that :doc:`installation-byroctl` sets
up, but managed by hand with ``docker compose``. Use it if you run your own
Docker environment and prefer to control the files yourself. The Compose
files, the image and the configuration format are identical, so you can adopt
byroctl later.

Prerequisites
-------------

* Docker Engine 24 or newer with the Compose plugin 2.20 or newer.
* A reverse proxy that terminates TLS, or ports 80 and 443 free for the Caddy
  add-on.
* An SMTP server to send mail.

Files
-----

The deployment consists of a base file with the byro services and optional,
purely additive add-on files. They live in the ``deploy/`` directory of the
byro repository and are versioned with every release; always take the files of
the release you install.

The base file starts the web service, the periodic task runner and defines the
``manage`` service for one-off commands:

.. literalinclude:: ../../deploy/docker-compose.yml
   :language: yaml

The built-in PostgreSQL is an add-on. Leave it out to use an external
database:

.. literalinclude:: ../../deploy/compose/postgres.yml
   :language: yaml

Caddy as a reverse proxy with automatic HTTPS is the second add-on:

.. literalinclude:: ../../deploy/compose/caddy.yml
   :language: yaml

All values come from one file, ``byro.conf``, which Docker Compose reads as
``.env`` for interpolation and passes to the containers as ``env_file``:

.. literalinclude:: ../../deploy/byro.conf.example
   :language: bash

Set up
------

Create a directory, download the files of the release you want (replace the
tag), and link the configuration as ``.env``::

    $ sudo mkdir -p /opt/byro && sudo chown "$(id -u):$(id -g)" /opt/byro && cd /opt/byro
    $ T=v2026.3.0
    $ R="https://raw.githubusercontent.com/byro/byro/$T/deploy"
    $ curl -fsSLO "$R/docker-compose.yml"
    $ mkdir -p compose && curl -fsSL -o compose/postgres.yml "$R/compose/postgres.yml"
    $ curl -fsSL -o compose/caddy.yml "$R/compose/caddy.yml" && curl -fsSLO "$R/Caddyfile"
    $ curl -fsSL -o byro.conf "$R/byro.conf.example" && chmod 600 byro.conf && ln -s byro.conf .env

Edit ``byro.conf``:

* ``BYRO_DEPLOY_VERSION``: the tag you downloaded, e.g. ``v2026.3.0``. The
  image ``ghcr.io/byro/byro:<tag>`` is pulled from GitHub's container
  registry.
* ``COMPOSE_FILE``: ``docker-compose.yml:compose/postgres.yml`` for the
  built-in database, append ``:compose/caddy.yml`` for Caddy. For an external
  database leave ``compose/postgres.yml`` out and fill in ``BYRO_DB_HOST`` and
  the other ``BYRO_DB_*`` values.
* ``BYRO_DB_PASS``: a long random password for the built-in database. The
  stack refuses to start while it is empty.
* ``BYRO_SITE_URL``, ``BYRO_HTTPS``, language, time zone, mail settings.
* ``BYRO_TRUST_PROXY=true`` if your own reverse proxy terminates TLS. The
  Caddy add-on sets it for you.

Put values that contain ``$``, ``#``, spaces, quotes or backslashes in single
quotes; Compose interpolates ``$`` in double quotes and unquoted values.

Then start the stack and create the first administrator::

    $ docker compose pull
    $ docker compose up -d
    $ docker compose run --rm manage createsuperuser

The web service runs the database migrations when it starts; the ``periodic``
service waits until the web service is healthy and then runs byro's periodic
tasks every ten minutes. byro listens on ``127.0.0.1:8345`` unless you change
``BYRO_DEPLOY_BIND`` and ``BYRO_DEPLOY_PORT``.

Everyday operations
-------------------

::

    $ docker compose ps
    $ docker compose logs -f web
    $ docker compose run --rm manage <byro command>
    $ docker compose up -d                 apply configuration changes
    $ docker compose stop

Updates
-------

Read the release notes of the new version first. Then, in the installation
directory:

1. Dump the database and copy the secret key::

       $ docker compose exec -T db pg_dump -Fc -U byro byro > pre-update.dump
       $ cp data/.secret byro.conf /somewhere/safe/

2. Download the Compose files of the new release as above (they may have
   changed) and set ``BYRO_DEPLOY_VERSION`` to the new tag. Clear
   ``BYRO_DEPLOY_IMAGE_DIGEST`` if you had pinned a digest.
3. Compare ``byro.conf.example`` of the new release with your ``byro.conf``
   and add new options you need.
4. Pull and restart; the web service applies the migrations::

       $ docker compose pull
       $ docker compose up -d

Downgrades are not supported: restore the dump and the previous files instead.

Backups
-------

Back up ``data/`` (documents, uploads, keys and ``.secret``), the database
(``db/`` while stopped, or a ``pg_dump``) and ``byro.conf``. Losing
``data/.secret`` invalidates all sessions and MFA devices.

Custom Compose settings
-----------------------

Keep local changes in a ``docker-compose.override.yml`` in the same directory
and add it to ``COMPOSE_FILE``. Do not edit the downloaded files, so that you
can replace them on the next update.
