# Backup and restore

byro itself does not create its own backups (byroctl's pre-update and
pre-plugin safeguard copies are an exception, see below, but no substitute
for a regular backup). Backing up and restoring is an administration task,
independent of the installation path.

## What needs to be backed up

All three installation paths need the same three things:

1. **The database.** Holds all member, finance and configuration data.
2. **The data directory** (`data/` with byroctl and Docker Compose,
   `/var/byro/data` with bare metal). Holds uploaded documents, GnuPG keys
   and the `.secret` file with Django's `SECRET_KEY`.
3. **The configuration** (`byro.conf` or `byro.cfg`). Holds the database
   password, mail credentials and other secrets - treat the copy as
   confidential.

**Losing `.secret` alone already invalidates all sessions and all MFA
devices**, even if the database and configuration survive (see
[Multi-factor authentication](mfa.md#security-notes)). Back up `data/` just
as reliably as the database, not only occasionally.

A consistent database backup comes either from a stopped byro or from a
transactional dump (`pg_dump`); a filesystem snapshot of a running database's
data directory without filesystem or database support for that is not
consistent.

The exact commands per installation path are on the respective installation
page: [byroctl](../installation/byroctl.md#backups),
[Docker Compose](../installation/docker-compose.md#backups),
[bare metal](../installation/bare-metal.md#next-steps-updates).

!!! note
    The **pre-update safeguard** of `byroctl update` and the **pre-plugin
    safeguard** of `byroctl plugin add/remove/update` (both in `backups/`)
    contain the database, `byro.conf`, `plugins/plugins.txt` and `.secret` -
    **but not** the documents and other files in `data/`. They protect
    against a failed update, not against data loss in general.

## Restore

!!! warning
    A restore overwrites the current data. There is no `byroctl restore` -
    the following steps are manual. Check beforehand that the backup you are
    restoring is really the one you want (point in time, completeness).

### byroctl and Docker Compose

In the installation directory, with the byro services stopped but the
database running:

```console
$ byroctl stop            # or: docker compose stop web periodic
$ docker compose exec -T db pg_restore -U byro -d byro --clean --if-exists < byro.dump
$ rm -rf data && cp -a /path/to/backup/data ./data
$ byroctl start           # or: docker compose up -d
```

`--clean --if-exists` drops existing objects before restoring and works fine
against an already existing database; `byro.dump` is a dump in `pg_dump -Fc`
format (see the backup sections above). Also replace `byro.conf` if it has
since changed in a way you do not want to keep.

### Bare metal

As user `byro`, with `byro-web` and `byro-periodic.timer` stopped:

```console
# systemctl stop byro-web byro-periodic.timer
$ pg_restore -U byro -d byro --clean --if-exists -h localhost byro.dump
$ rm -rf /var/byro/data && cp -a /path/to/backup/data /var/byro/data
# cp /path/to/backup/byro.cfg /etc/byro/byro.cfg
# systemctl start byro-web byro-periodic.timer
```

For MySQL/MariaDB, replace the `pg_restore` call with restoring your
`mysqldump`/`mariadb-dump` export with the matching client.

After every restore, check the logs (see
[Monitoring, logging and troubleshooting](troubleshooting.md)) to make sure
byro starts cleanly with the restored state.

## Disaster recovery: moving to a new host

The procedure is a restore onto a fresh installation, not the installation
routine itself - `byroctl install` or the bare metal `python -m byro migrate`
step would otherwise create a **new, empty** database and a **new** secret
key.

For byroctl/Docker Compose:

1. Set up Docker and Docker Compose on the new host (see
   [Prerequisites](../installation/byroctl.md#prerequisites)), download
   byroctl and the Compose files of the same byro release you had installed
   (do not run `byroctl install`).
2. Place the backed-up `byro.conf` in the installation directory and link it
   as `.env`.
3. Start only the database (`docker compose up -d db`), wait until it is
   healthy, then restore the dump as described above under Restore.
4. Copy the backed-up `data/` to the same location.
5. Start the rest of the stack (`byroctl start` or `docker compose up -d`)
   and check `byroctl version` or `docker compose ps`.

For bare metal, correspondingly: set up system packages, the Python
environment and byro on the new host as in the
[bare metal installation](../installation/bare-metal.md), but replace step 5
(`python -m byro migrate`) with restoring the database dump, copy back
`data/` and `byro.cfg` from the backup, then continue with step 6 (starting
the services).

Afterwards, update your domain's DNS record to point to the new host and
check that `BYRO_SITE_URL` or `[site] url` still matches the address byro is
reachable under.
