# Deprecated: the `production/` Docker setup

The files in this directory (`docker-compose.yml`, `setup.sh`, `nginx.conf`,
`byro.example.cfg`) are the original, experimental Docker deployment of byro.
They are **deprecated**. They keep working with the current byro image, but they
receive no new features and will be removed in a later release.

## What replaces it

* **byroctl** (recommended): one command installs and updates a byro deployment
  based on Docker Compose.
  https://byro.readthedocs.io/en/latest/administrator/installation-byroctl.html
* **Docker Compose by hand** with the files in `deploy/`:
  https://byro.readthedocs.io/en/latest/administrator/installation-compose.html

The new deployment uses the same image (`ghcr.io/byro/byro`), but a dedicated
unprivileged user, a health check, a `periodic` service for byro's periodic
tasks, an optional Caddy reverse proxy and one configuration file
(`byro.conf`) instead of a mounted `byro.cfg`. Media files are no longer served
by nginx: documents are delivered by byro itself after authentication.

## Known problems of this setup that will not be fixed

* `setup.sh` runs `compress` before `collectstatic`. On a fresh installation the
  static files manifest does not exist yet, and every page answers with an
  error 500 (`OfflineGenerationError`). Run `manage collectstatic` before
  `manage compress`, or run `manage rebuild` once.
* `setup.sh plugin` cannot work: no service in `docker-compose.yml` has a
  `build:` section.
* `nginx.conf` serves `/media/` without authentication.
* `docker-compose.yml` uses the `latest` tag, so every release changes the
  running image without notice.

## Moving an existing installation to byroctl

Your data lives in `../byro-data/` next to the byro checkout: `data/`
(documents, uploads, `.secret`, GnuPG home) and `db/` (PostgreSQL 14 data
directory), plus `byro.cfg`.

1. Stop the old stack: `byro/production/setup.sh stop` (note: this runs
   `docker compose down -v`; your data is in bind mounts and is kept).
2. Install byro with byroctl into a new directory, for example `/opt/byro`,
   answering the questions with the values from your `byro.cfg`
   (`[site] url`, mail settings). Choose the built-in database.
3. Stop the new stack (`byroctl stop`), then move your data over:
   * copy `byro-data/data/` to `/opt/byro/data/` (keep `.secret`!),
   * either copy `byro-data/db/` to `/opt/byro/db/` and set
     `BYRO_DEPLOY_POSTGRES_MAJOR=14` in `byro.conf` (same PostgreSQL major as
     before; a later major upgrade is done with dump and restore),
   * or restore a dump made with the old stack into the new database with
     `docker compose exec -T db psql -U byro byro < byro.sql`.
4. `byroctl start`, log in, check the documents and settings.
5. Remove the old checkout and `byro-data/` when you no longer need them.

Copying `data/` including `.secret` keeps sessions and MFA devices valid.
