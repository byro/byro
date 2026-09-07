# Installation

byro is free software, which means you can run it yourself on your own server
(or your own Raspberry Pi, …). But while this offers you great freedom, it also
comes with great responsibility:

!!! warning
    Hosting byro means taking responsibility for your members' personal and
    financial data. Please make sure that your installation and servers are
    secure and will be maintained in the future. If you don't feel comfortable
    with this, consider contacting us for information, or choosing an offline
    installation.

There are three ways to install byro:

1. **byroctl** (recommended): a small command line tool that sets up byro with
   Docker Compose, keeps the configuration in one file and installs updates for
   you. Start here unless you have a reason not to: [Installation with byroctl](byroctl.md).
2. **Docker Compose by hand**: the same container image and Compose files as
   byroctl, managed with plain `docker compose` commands. For administrators
   who run their own Docker environment: [Installation with Docker Compose](docker-compose.md).
3. **Bare metal**: byro from PyPI in a Python environment with a PostgreSQL
   server, gunicorn, systemd and your own reverse proxy. For classic or
   individual deployments: [Bare metal installation](bare-metal.md).

All three share the same configuration options ([Configuration](../configuration/index.md)),
the same way to add plugins ([Plugins](../administration/plugins.md)),
the same maintenance tasks (see [Administration](../administration/operations.md))
and the same advice: run byro behind HTTPS only, and back up your data.

The following pages document a straightforward setup without going into
details on administrative basics like securing your server, or performing
backups. Updating, backup and restore, monitoring and the security baseline
are covered under [Administration](../administration/operations.md) once
byro is running.

The deprecated `production/` setup is described on its own page:
[Legacy setup with the production/ files](legacy-production.md).
