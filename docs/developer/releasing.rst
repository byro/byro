Releasing byro
==============

This page is for byro maintainers. It describes how a release is produced,
what the release pipeline does, and the two duties that come with the
deployment tooling: the ``stable`` pointer and the release flags in
``deploy/release.env``.

How a release is made
---------------------

1. `Release Drafter`_ keeps a draft release up to date on GitHub. Every merged
   pull request adds a line under the category of its label
   (``breaking-change``, ``enhancement``, ``bug``/``fix``, ``maintenance``,
   ``dependencies``, ``documentation``). The drafter also proposes the next
   tag, but with semantic-versioning rules: ``breaking-change`` bumps the first
   field, ``enhancement`` the second, everything else the third. byro's scheme
   is ``vYYYY.MINOR.PATCH``, so check the proposed tag and edit it by hand when
   needed: the first field is always the current year, the first release of a
   year is ``vYYYY.1.0``, and a ``breaking-change`` label must not bump the
   year.
2. Before publishing, edit the draft: write the introduction (the placeholder
   at the top) and go through the checklist at the end of this page.
3. Publish the release. GitHub creates the tag, and the tag starts the release
   pipeline (``.github/workflows/ci-cd.yml``, event ``release: published``):

   * style checks and the test matrix,
   * the Python package, uploaded to PyPI (environment ``pypi``),
   * the container image ``ghcr.io/byro/byro:vYYYY.M.P`` for ``linux/amd64`` and
     ``linux/arm64``, also tagged ``latest``,
   * and, only after both uploads succeeded, the ``stable`` pointer (see
     below).

   The run takes about half an hour; the multi-platform image build is the
   slow part. Watch it under *Actions*.

byro has not published pre-releases so far. If you mark a release as
*pre-release*, the pipeline still runs: package and image are published, and
the image also receives the ``latest`` tag, which the deprecated
``production/`` setup pulls unpinned. Only the ``stable`` pointer is not moved.
Turning the pre-release into a release later does not run the pipeline again
(GitHub sends ``released``, not ``published``); move ``stable`` by hand with
the *Stable pointer* workflow in that case.

The stable pointer
------------------

The byroctl bootstrap (:doc:`/administrator/installation-byroctl`) starts
with::

    bash -c "$(curl -fsSL https://raw.githubusercontent.com/byro/byro/stable/install.sh)"

and ``byroctl update --check`` asks the same place which release is current.
``stable`` is a branch of this repository with exactly three files, written by
CI and by nothing else:

* ``stable.env`` with one line ``BYRO_RELEASE_VERSION=vYYYY.M.P``,
* ``install.sh``, a byte-identical copy of ``deploy/install.sh`` from that
  release tag,
* a ``README.md`` that explains the branch.

Everything else (byroctl, the Compose files, the image) is fetched from the
immutable release tag, so the branch only says *which* release is current. The
job *Point stable at the release* runs as the last step of the pipeline and
calls ``.github/scripts/update-stable-branch.sh`` through the workflow
``.github/workflows/stable.yml``. The script

* refuses anything that is not a ``vYYYY.M.P`` tag,
* checks that the tag contains ``deploy/install.sh`` matching its
  ``SHA256SUMS`` and that the image exists in the registry,
* compares versions numerically and never moves the pointer to an older
  release on its own (the job then ends green with a notice),
* appends a commit to the branch history and pushes it as a fast-forward;
  the branch is never force-pushed.

``raw.githubusercontent.com`` caches files for a few minutes, so installers
may still see the previous release for up to about five minutes after the
pointer moved.

Moving the pointer by hand
~~~~~~~~~~~~~~~~~~~~~~~~~~

Do not edit or push the ``stable`` branch directly. If a release turns out to
be broken, point ``stable`` back at the previous release: *Actions* → *Stable
pointer* → *Run workflow*, enter the tag and tick *force* (moving to an older
release is refused otherwise). Then fix the problem and publish a new release;
the pipeline moves the pointer forward again. Consider yanking the broken
version on PyPI as well. The image tag stays available, because byroctl
installations pin the release they installed. byroctl does not downgrade:
while ``stable`` names an older release than the installed one,
``byroctl update`` and ``byroctl update --check`` on the broken release exit
with an error that names both versions. Those installations wait for the fixed
release and update to it (``byroctl update --to vX.Y.Z`` until ``stable`` has
moved there).

The workflow pushes with the repository's ``GITHUB_TOKEN``. If ``stable`` is
covered by a branch protection rule or a ruleset, that automation actor needs
push or bypass permission for the branch. People do not need it: changes to
the pointer go through the workflow, never through a direct push.

Release flags
-------------

``deploy/release.env`` carries two flags that ``byroctl update`` reads from
the *target* release before it changes anything:

``BYRO_RELEASE_BREAKING=1``
    Administrators must read the release notes and confirm the update
    explicitly (``byroctl update`` asks, ``--yes`` confirms). Use it only when
    an administrator has to act or decide before updating: a configuration
    that must change, a service that goes away, a manual step. It is not a
    synonym for the ``breaking-change`` label, which also covers code and
    plugin API changes that need no action from administrators.

``BYRO_RELEASE_DATA_MIGRATION=1``
    The release changes files outside the database (documents, uploads,
    GnuPG home). The regular pre-update safeguard does not cover them, so
    ``byroctl update`` refuses to continue until the administrator confirms a
    full backup of ``data/`` with ``--data-safeguard-done``.

Both flags are ``0`` on ``main``. For a release that needs one:

1. In the pull request that prepares the release, set the flag to ``1``, run
   ``.github/scripts/deploy-checksums.sh --write`` (``release.env`` is on the
   checksum list that CI enforces) and write the release-notes section that
   explains what administrators must do.
2. Publish the release. The flag is part of the tag, and byroctl reads it
   there.
3. Right afterwards, open a pull request that resets the flag to ``0``, again
   with a regenerated ``SHA256SUMS``.

The CI check *[Deploy] release flags* (workflow ``release-flags.yml``, every
push to ``main`` and every pull request) enforces the format of the file (each
flag exactly once, only ``0`` or ``1``, nothing else) and reminds you of step
3: on ``main`` it fails as long as a flag is ``1``, the latest release tag
shipped it at ``1`` and no commit since that release changed the flag's line;
in pull requests it only warns. This red phase between publishing and the
reset pull request is intended.

byroctl reads the flags of the release it updates *to*, nothing else. An
installation that skips a flagged release (from ``v2026.2.0`` straight to
``v2026.4.0`` when ``v2026.3.0`` carried ``BYRO_RELEASE_DATA_MIGRATION=1``) is
not stopped by that flag, although the migration still runs. When you set a
flag, tell administrators in the release notes of the following releases what
those who skipped the flagged release must do. Do not tag a hotfix from
``main`` while a flag is still ``1`` unless the hotfix needs it too.

Plugin catalog
--------------

``deploy/plugin-catalog.conf`` is the list of plugins that ``byroctl plugin add
<shortname>`` knows. It is a release artifact like the Compose files: versioned
with the release, listed in ``deploy/SHA256SUMS``, downloaded and verified by
byroctl. It carries **metadata only**, no versions:

.. code-block:: ini

    [finance-import-bank-files]
    name=Bank file importers
    description=Imports file-based bank statements
    package=byro-finance-import-bank-files
    source=github
    repo=https://github.com/byro/byro-finance-import-bank-files

byroctl resolves the version when an administrator adds or updates the plugin:
for ``source=github`` the current regular GitHub release of ``repo``, installed
by the commit its tag points to; for ``source=pypi`` the current release on
PyPI. A new plugin release therefore needs no change in this repository.
Whether a plugin release works with a byro release is declared by the plugin
itself (``dependencies = ["byro>=2026.3"]`` in its ``pyproject.toml``); the
image build checks it against the installed byro.

To add a plugin:

1. The plugin must have a ``byro.plugin`` entry point, an ``apps.py`` with
   ``ByroPluginMeta`` and at least one regular GitHub release (or a release on
   PyPI). Without a release ``byroctl plugin add`` fails with a clear message.
2. Add a section with the five keys above. Section names are lower-case
   letters, digits and hyphens; ``repo`` is ``https://github.com/<owner>/<repo>``
   for GitHub plugins.
3. Run ``.github/scripts/check-plugin-catalog.sh`` and
   ``.github/scripts/deploy-checksums.sh --write``; both are enforced by CI
   (job *[Deploy] shellcheck, checksums, bats*).

Only plugins that work with the current byro release belong in the catalog.
Candidates that still need work are tracked as issues, not as commented-out
entries.

Notes for administrators
------------------------

The pipeline publishes the release, but only you can tell administrators what
to do. Check before publishing:

* Does the release change configuration options, the Compose files or the
  behavior of the image? Describe the steps for byroctl users
  (``byroctl update`` takes care of new options and Compose files), for
  ``docker compose`` users and for plain installations (``pip install -U
  byro``, ``migrate``, ``rebuild``, restart).
* Users of the deprecated ``production/`` setup pull
  ``ghcr.io/byro/byro:latest`` and get the new image without pinning. Mention
  anything that affects them and point to ``production/DEPRECATED.md``.

The first release that ships ``deploy/`` deserves an explicit section for
``production/`` users, because it is the first time the published image
changes its default behavior. It does not need ``BYRO_RELEASE_BREAKING=1``:
no byroctl installation exists yet that could read the flag.

Checklist
---------

Before publishing:

* the draft is reviewed, the introduction is written, the categories are
  complete,
* ``deploy/release.env`` has the flags this release needs, and the release
  notes explain them,
* the release notes tell administrators what to do,
* ``deploy/plugin-catalog.conf`` lists only plugins that work with this release
  and the catalog lint is green,
* ``main`` is green; if *[Deploy] release flags* is red, the previous flag has
  not been reset yet, do that first.

After publishing:

* the pipeline run is green, including *Point stable at the release*,
* ``stable`` names the new release (``stable.env`` on the branch),
* a flag that was set is reset to ``0`` in a follow-up pull request.

.. _Release Drafter: https://github.com/release-drafter/release-drafter
