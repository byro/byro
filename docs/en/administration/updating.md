# Updating

This page collects what applies to a byro update regardless of the
installation path. The exact commands differ per path and live on the
respective installation page:

- [Updating with byroctl](../installation/byroctl.md#updates)
- [Updating with Docker Compose](../installation/docker-compose.md#updates)
- [Updating a bare metal installation](../installation/bare-metal.md#next-steps-updates)

## Before every update

1. Read the [release notes](https://github.com/byro/byro/releases) of the
   target version. byro flags releases with breaking changes or changes to
   files in `data/` explicitly; byroctl asks for confirmation in those cases
   before continuing.
2. Take a full backup (see [Backup and restore](backup-restore.md)), not just
   the automatic pre-update safeguard byroctl creates. A Docker Compose (by
   hand) or bare metal installation has no such automatic copy; back up
   yourself before updating there.
3. Update plugins following the same logic as byro itself and check their own
   release notes (see [Plugins](plugins.md#what-a-byro-update-does-with-plugins)).

## What happens during an update

All three paths follow the same order: download new artefacts (Compose
files, image, or package), check the configuration against new options, stop
byro, apply database migrations, start byro with the new version. byroctl
automates all of this including the safeguard copy; with Docker Compose by
hand and with bare metal you perform the steps yourself.

## Downgrade limits

**Downgrades are not supported.** byro's database migrations only run
forward; there are no tested, reversible migrations for a downgrade. To undo
a failed update, restore your backup from before the update instead
(database, `data/`, configuration) - see [Restore](backup-restore.md#restore).
That is also why a full, current backup before every update is mandatory,
not optional.

## When an update fails

If a migration fails, the byro services stay stopped. Fix the cause and
retry, or restore the safeguard copy (see [Restore](backup-restore.md#restore)).
Never combine an already-migrated database with the code of the previous
version: downgrading the code alone does not undo a failed update once the
migration has been (partially) applied.
