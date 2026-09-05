Plugins
=======

byro can be extended with plugins: Python packages that register themselves
with byro and add importers, member data, documents or whole features (see the
:doc:`developer documentation </developer/plugins/plugins>` for how they are
written). A plugin runs with the same privileges as byro itself and has full
access to your database, so install only plugins you trust.

This page describes plugins in a byroctl installation. The sections at the end
cover the manual Docker Compose setup and the plain installation.

How byroctl installs plugins
----------------------------

byro finds plugins among the Python packages installed next to it. In a
container that means the plugin has to be part of the image, so byroctl builds a
**derived image**: the pinned release image plus the plugins you listed. The
list lives in ``plugins/plugins.txt``, a pip requirements file in your
installation directory; ``plugins/Dockerfile`` (managed by byroctl) builds the
image, and the add-on ``compose/plugins.yml`` switches the byro services to it
while the list names at least one plugin.

Every change to the plugin set runs in two phases:

1. **Build and check** (reversible): the image is built and byro's
   configuration check runs inside it. If this fails, byroctl puts
   ``plugins/plugins.txt``, ``COMPOSE_FILE`` and the image back to their
   previous state; the running containers were never touched.
2. **Migrate and start** (not reversible): a **pre-plugin safeguard** is
   written to ``backups/`` (database dump, previous ``byro.conf``, previous
   ``plugins.txt``, secret key), the database migrations of the new plugin set
   run, and the byro services are recreated with the new image. Users see a
   short interruption.

If the migration or the following start fails, byroctl does **not** switch back
to the previous plugins on its own: the database may already carry the schema of
the new plugin set, and old code on a new schema would make things worse. The
files keep the attempted state and byroctl prints the way forward (fix the cause,
``byroctl plugin rebuild``) and the way back (restore the safeguard: database,
``byro.conf`` and ``plugins/plugins.txt``, then ``byroctl plugin rebuild`` and
``byroctl start``).

Two ways to name a plugin
-------------------------

**Catalog short names.** Every byro release ships a small catalog of plugins
(``plugin-catalog.conf`` in your installation directory; ``byroctl plugin
list`` shows it). The catalog carries metadata only: name, description, the
Python package and where it comes from. When you add a catalog plugin, byroctl
looks up its **current release** at that moment and pins it:

* a plugin on GitHub is installed from the commit its current regular release
  tag points to (pre-releases are ignored); the release tag is kept as the
  readable version,
* a plugin on PyPI is installed as ``package==<current version>``.

byroctl does not search for an older release that might fit your byro version
better. If the current release needs a newer byro, the build fails with pip's
message; install an older version as an explicit requirement then, or update
byro first.

**Explicit pip requirements.** Anything pip understands, for example
``byro-mailman==1.0.1``,
``byro-finance-import-bank-files @ git+https://github.com/byro/byro-finance-import-bank-files.git@v1.2.0``
or ``./my-plugin`` for a checkout inside ``plugins/``. Pin a version or a tag;
an unpinned requirement is accepted with a warning, but every rebuild may then
pick a different release. Explicit requirements are your responsibility:
``byroctl plugin update`` leaves them alone.

The GitHub topic `byro-plugin <https://github.com/topics/byro-plugin>`_ lists
further community plugins. It is a place to look, nothing more: byroctl never
installs anything from it automatically.

Commands
--------

::

    $ byroctl plugin list                                the catalog, what is installed, extra entries
    $ byroctl plugin add finance-import-bank-files       add a catalog plugin (current release)
    $ byroctl plugin add 'byro-x==1.2.0'                 add an explicit requirement
    $ byroctl plugin remove finance-import-bank-files    remove an entry (by name, requirement or package)
    $ byroctl plugin update --check                      which catalog plugins have a newer release
    $ byroctl plugin update [finance-import-bank-files]  move catalog plugins to their current release
    $ byroctl plugin rebuild [--no-cache]                rebuild the image from plugins/plugins.txt

Plugins can also be chosen during the installation: the installer asks for
catalog short names, and ``byroctl install --plugin NAME|SPEC`` (repeatable,
also through ``install.sh``) takes names and requirements.

``add``, ``remove``, ``update`` and ``rebuild`` all end with the two phases
described above and exit with 1 when the build or check failed (nothing was
changed), 2 when the migration failed and 3 when byro did not come back
healthy (see the recovery hint in both cases); 64 is a usage error.
``--skip-safeguard`` skips the database dump before the migration.

Removing a plugin removes its code from the image, not its database tables or
the documents it created. If you want the tables gone, run
``byroctl manage migrate <app> zero`` *before* removing the plugin.

The plugin list and the plugins directory
-----------------------------------------

``plugins/plugins.txt`` is a plain pip requirements file: one requirement per
line, ``#`` starts a comment. Catalog entries carry a marker that byroctl
writes and reads::

    byro-finance-import-bank-files @ git+https://github.com/byro/byro-finance-import-bank-files.git@3f2a9c1e7b6d4a5f8c0e1d2b3a4f5e6d7c8b9a01  # byroctl:catalog=finance-import-bank-files version=v1.2.0
    byro-mailman==1.0.1
    ./my-plugin

You may edit the file by hand, for example to add a local checkout: put the
plugin's source into ``plugins/my-plugin`` and list it as ``./my-plugin``. Then
run ``byroctl plugin rebuild``. byroctl checks the file (``byroctl config
check`` does too) and refuses lines that look like pip options or comments; the
file is trusted like ``byro.conf``, so keep it under your control.

The ``plugins/`` directory is the Docker build context. ``plugins/Dockerfile``
is replaced by byroctl on every byro update; do not edit it. Back up
``plugins/`` together with ``byro.conf``.

What a byro update does with plugins
------------------------------------

``byroctl update`` keeps your pins and rebuilds the plugin image on top of the
new byro release before it stops anything. The pre-update safeguard contains
the previous ``plugins.txt``. If the build fails, the running stack is not
touched and byroctl prints the way back. Pass ``--update-plugins`` to move
catalog plugins to their current release in the same run; without it, run
``byroctl plugin update`` afterwards.

Release tags of plugins are treated as **immutable**. If a release tag you have
installed suddenly points to another commit, ``byroctl plugin update`` (and
``byroctl update --update-plugins``) stops with an integrity error, keeps your
pin and updates nothing else. Ask the plugin's maintainer to publish a new
release for changed code.

Troubleshooting
---------------

* Read the output of the failed ``docker compose build``; typical causes are a
  git ref that does not exist, a plugin that requires another Django or byro
  version (byroctl builds with the base image's packages as constraints, so pip
  reports a conflict instead of replacing Django), or a dependency without a
  wheel for your platform (the image has no compiler).
* ``byroctl plugin rebuild --no-cache`` builds from scratch.
* GitHub's API allows 60 anonymous requests per hour and address; byroctl
  needs two per GitHub plugin. Set ``GITHUB_TOKEN`` in the environment if you
  hit the limit.
* ``byroctl version`` shows which plugins the running web service loaded;
  ``byroctl plugin list`` what is configured. If they differ, run
  ``byroctl plugin rebuild``.
* The image ``<project>-plugins:<version>`` of the previous byro release stays
  until you remove it with ``docker image rm``.

Docker Compose by hand
----------------------

The same mechanism works without byroctl. In your installation directory:

1. Create ``plugins/``, download ``plugins/Dockerfile`` from the release you
   run (``deploy/plugins/Dockerfile`` in the repository) and write
   ``plugins/plugins.txt`` with pinned requirements.
2. Add ``compose/plugins.yml`` (``deploy/compose/plugins.yml`` of the release)
   to ``COMPOSE_FILE`` in ``byro.conf``.
3. Build, migrate and restart::

       $ docker compose build web
       $ docker compose run --rm manage migrate
       $ docker compose up -d

Repeat the build after every change to ``plugins.txt`` and after every byro
update (the base image changed).

Plain installation
------------------

Install the plugin into the same Python environment as byro, migrate, rebuild
the assets (``rebuild`` compiles the plugin's translations too) and restart::

    $ pip install --user 'byro-finance-import-bank-files @ git+https://github.com/byro/byro-finance-import-bank-files.git@v1.2.0'
    $ python -m byro migrate
    $ python -m byro rebuild
    # systemctl restart byro-web
