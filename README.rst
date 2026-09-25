|byro|
======

.. image:: https://img.shields.io/github/v/release/byro/byro
   :target: https://github.com/byro/byro/releases/latest
   :alt: Latest GitHub release

.. image:: https://img.shields.io/pypi/v/byro
   :target: https://pypi.org/project/byro/
   :alt: PyPI version

.. image:: https://img.shields.io/badge/license-AGPL--3.0--only-blue.svg
   :target: https://github.com/byro/byro/blob/main/LICENSE
   :alt: AGPL-3.0-only license

.. image:: https://github.com/byro/byro/actions/workflows/ci-cd.yml/badge.svg?branch=main
   :target: https://github.com/byro/byro/actions/workflows/ci-cd.yml?query=branch%3Amain
   :alt: CI/CD status

.. image:: https://codecov.io/gh/byro/byro/branch/main/graph/badge.svg
   :target: https://codecov.io/gh/byro/byro
   :alt: Code coverage
.. image:: https://readthedocs.org/projects/byro/badge/?version=latest
   :target: https://byro.readthedocs.io/en/latest/
   :alt: Documentation status

byro_ is a simple, self-hosted membership administration tool for small and
medium-sized clubs, NGOs and associations, with a focus on the DACH region. It
is stable, in active use in several communities and actively developed.

byro is plugin-based so that organizations can adapt it to their own processes
and local requirements. It is not a complete bookkeeping, event or ticketing
system, and it does not offer a hosted default instance.

Getting started
---------------

* **Run byro for an organization:** The `installation guide`_ covers byroctl
  (recommended), Docker Compose and bare-metal installations.
* **Use an existing installation:** The `user guide`_ covers members, fees,
  finances, documents and communication.
* **Extend or improve byro:** Start with the `API and plugin documentation`_ or
  `contributing`_.

.. image:: https://raw.githubusercontent.com/byro/byro/main/docs/en/img/screenshots/office_dashboard.png
   :alt: byro Office dashboard
   :width: 800px

Features
--------

* Manage members, memberships and recurring fees.
* Record and match payments; the official bank-file importer supports CAMT.053
  and MT940.
* Create documents, review and send mail, and keep member balances transparent.
* Let members manage selected data and interact through the member area.
* Protect Office accounts with multi-factor authentication.
* Adapt byro through plugins and use its REST API for integrations.

Plugins
-------

Plugins are Python packages that extend byro with importers, member data,
documents or whole features. Administrators can install the compatible official
plugins listed in the `plugin catalog`_; see `plugin management`_ for their
installation and maintenance. The `plugin development documentation`_ explains
how to build one.

The GitHub `byro-plugin topic`_ is a place to discover community plugins, not
an endorsement; byroctl never installs entries from it automatically.

Contributing
------------

Contributions to byro, its documentation and its plugins are welcome. See the
`contributor documentation`_ for the development setup and contribution
workflow.

License
-------

byro is licensed under the GNU Affero General Public License, version 3.0 only
(``AGPL-3.0-only``). Older versions of byro were released under the Apache
License 2.0. The documentation in ``docs/`` is licensed under the Creative
Commons Attribution-ShareAlike 4.0 International License (``CC-BY-SA-4.0``).
See the `LICENSE`_ file for details, including the licensing history and the
licenses of bundled third-party components.

.. |byro| image:: https://raw.githubusercontent.com/byro/byro/main/docs/en/img/logo/byro_128.png
   :alt: byro
.. _byro: https://byro.cloud
.. _installation guide: https://byro.readthedocs.io/en/latest/installation/overview/
.. _user guide: https://byro.readthedocs.io/en/latest/usage/overview/
.. _API and plugin documentation: https://byro.readthedocs.io/en/latest/administration/plugins/
.. _contributing: https://byro.readthedocs.io/en/latest/development/overview/
.. _plugin catalog: https://github.com/byro/byro/blob/main/deploy/plugin-catalog.conf
.. _plugin management: https://byro.readthedocs.io/en/latest/administration/plugin-management/
.. _plugin development documentation: https://byro.readthedocs.io/en/latest/development/plugins/overview/
.. _byro-plugin topic: https://github.com/topics/byro-plugin
.. _contributor documentation: https://byro.readthedocs.io/en/latest/development/contributing/
.. _LICENSE: https://github.com/byro/byro/blob/main/LICENSE
