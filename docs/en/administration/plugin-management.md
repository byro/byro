# Plugin management

This page describes plugin management in a byroctl installation. The
installation pages cover the specifics of [byroctl](../installation/byroctl.md),
[Docker Compose](../installation/docker-compose.md) and
[bare metal](../installation/bare-metal.md).

## Installing plugins

byro finds plugins among the Python packages installed next to it. In a
container, byroctl builds a **derived image** from the release image and the
plugins listed in `plugins/plugins.txt`. `plugins/Dockerfile` is managed by
byroctl; the `compose/plugins.yml` add-on switches services to the image once
the list names at least one plugin.

Every change to the plugin set runs in two phases:

1. **Build and check** (reversible): the image is built and byro's
   configuration check runs inside it. If this fails, byroctl puts
   `plugins/plugins.txt`, `COMPOSE_FILE` and the image back to their previous
   state; the running containers were never touched.
2. **Migrate and start** (not reversible): a **pre-plugin safeguard** is
   written to `backups/` (database dump, previous `byro.conf`, previous
   `plugins.txt`, secret key), the database migrations run, and the services
   are recreated with the new image. Users see a short interruption.

If the migration or the following start fails, byroctl does **not** switch back
to the previous plugins on its own: the database may already carry the schema
of the new plugin set. To go back, restore the safeguard (database,
`byro.conf` and `plugins/plugins.txt`), then run `byroctl plugin rebuild` and
`byroctl start`. Alternatively, fix the cause and run the build again.

Plugins can be selected during installation with `--plugin NAME|SPEC`, or
managed afterwards with these commands:

```console
$ byroctl plugin list
$ byroctl plugin add finance-import-bank-files
$ byroctl plugin add 'byro-x==1.2.0'
$ byroctl plugin remove finance-import-bank-files
$ byroctl plugin update [finance-import-bank-files]
$ byroctl plugin rebuild [--no-cache]
```

Plugins can also be chosen during the installation: the installer asks for
catalog short names, and `byroctl install --plugin NAME|SPEC` (repeatable, also
through `install.sh`) takes names and requirements.

`add`, `remove`, `update` and `rebuild` run the two phases described above.
They exit with 1 on a build or check error (nothing changed), 2 on a migration
error, 3 when byro did not come back healthy, and 64 on a usage error.
`--skip-safeguard` skips the database dump before the migration.

## Two ways to name a plugin

**Catalog short names.** Every byro release ships a small plugin catalog
(`plugin-catalog.conf`; `byroctl plugin list` shows it). Adding a catalog
plugin resolves and pins its **current release**: on GitHub to the commit of
the current regular release tag (pre-releases are ignored), and on PyPI as
`package==<current version>`.

byroctl does not search for an older release that might fit the installed byro
version. If the current release needs a newer byro, install an older version as
an explicit requirement or update byro first.

**Explicit pip requirements.** Anything pip understands can be used, for
example `byro-mailman==1.0.1`,
`byro-finance-import-bank-files @ git+https://github.com/byro/byro-finance-import-bank-files.git@v1.2.0`
or `./my-plugin` for a checkout inside `plugins/`. Always pin a version or tag;
an unpinned requirement may install a different release on each rebuild.
`byroctl plugin update` leaves explicit requirements unchanged.

The GitHub topic [byro-plugin](https://github.com/topics/byro-plugin) lists
further community plugins. It is a place to look, nothing more: byroctl never
installs anything from it automatically.

## The plugin list and the plugins directory

`plugins/plugins.txt` is a plain pip requirements file: one requirement per
line, `#` starts a comment. Catalog entries carry a marker that byroctl writes
and reads:

```text
byro-finance-import-bank-files @ git+https://github.com/byro/byro-finance-import-bank-files.git@3f2a9c1e7b6d4a5f8c0e1d2b3a4f5e6d7c8b9a01  # byroctl:catalog=finance-import-bank-files version=v1.2.0
byro-mailman==1.0.1
./my-plugin
```

You may edit the file by hand, for example to add a local checkout: put the
plugin source into `plugins/my-plugin` and list it as `./my-plugin`. Then run
`byroctl plugin rebuild`. byroctl checks the file (`byroctl config check` does
too) and refuses lines that look like pip options or comments; the file is
trusted like `byro.conf`, so keep it under your control.

The `plugins/` directory is the Docker build context. `plugins/Dockerfile` is
replaced by byroctl on every byro update; do not edit it. Back up `plugins/`
together with `byro.conf`.

## What a byro update does with plugins

`byroctl update` keeps your pins and rebuilds the plugin image on the new byro
release before it stops anything. The pre-update safeguard contains the
previous `plugins.txt`. If the build fails, the running stack remains
untouched. Pass `--update-plugins` to move catalog plugins to their current
release in the same run; without it, run `byroctl plugin update` afterwards.

Release tags of plugins are treated as **immutable**. If a release tag you have
installed suddenly points to another commit, `byroctl plugin update` (and
`byroctl update --update-plugins`) stops with an integrity error, keeps your
pin and updates nothing else.

Removing a plugin removes its code from the image, not its database tables or
created documents. Remove tables before removing the plugin with
`byroctl manage migrate <app> zero`.

## Troubleshooting

* Read the output of the failed `docker compose build`; typical causes are a
  git ref that does not exist, a plugin that requires another Django or byro
  version (byroctl builds with the base image's packages as constraints, so pip
  reports a conflict instead of replacing Django), or a dependency without a
  wheel for your platform (the image has no compiler).
* `byroctl plugin rebuild --no-cache` builds from scratch.
* GitHub's API allows 60 anonymous requests per hour and address; byroctl
  needs two per GitHub plugin. Set `GITHUB_TOKEN` in the environment if you
  hit the limit.

`byroctl version` shows the plugins loaded by the running web service;
`byroctl plugin list` shows the configured list. If they differ, run
`byroctl plugin rebuild`. The previous byro release's image
`<project>-plugins:<version>` remains until you remove it with `docker image rm`.
