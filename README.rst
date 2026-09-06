|byro|
======

.. image:: https://img.shields.io/github/v/release/byro/byro
   :target: https://github.com/byro/byro/releases/latest
   :alt: GitHub release (with filter)

.. image:: https://img.shields.io/pypi/v/byro
   :target: https://pypi.org/project/byro/
   :alt: PyPI - Version

.. image:: https://github.com/byro/byro/actions/workflows/ci-cd.yml/badge.svg?branch=main
   :target: https://github.com/byro/byro/actions/workflows/ci-cd.yml?query=branch%3Amain
   :alt: CI/CD

.. image:: https://codecov.io/gh/byro/byro/branch/main/graph/badge.svg
   :target: https://codecov.io/gh/byro/byro
   :alt: Code coverage

.. image:: https://img.shields.io/codeclimate/maintainability/byro/byro.svg
   :target: https://codeclimate.com/github/byro/byro
   :alt: Code maintainability

.. image:: https://readthedocs.org/projects/byro/badge/?version=latest
   :target: http://byro.readthedocs.io/
   :alt: Documentation



byro_ is a membership administration tool for small and medium sized
clubs/NGOs/associations of all kinds, with a focus on the DACH region. While it
is still a work in progress, it is already usable and in active use.

.. image:: https://raw.githubusercontent.com/byro/byro/main/docs/img/screenshots/office_dashboard.png

Development and Production Setup
--------------------------------

Please refer to the `development`_ or the `production documentation`_. The
recommended way to run byro is `byroctl`_, which installs and updates a
Docker based deployment with one command; Docker Compose by hand and a plain
installation from PyPI are documented as well.

Features
--------


Planned features
----------------


Plugins
-------

byro provides a rich API for plugins. See our `developer documentation`_ if you want to write a
plugin.

Plugins that work with the current byro release are listed in the `plugin catalog`_ that ships
with every release; administrators install them with ``byroctl plugin add <name>`` (see the
`plugin documentation`_). To get a plugin listed, publish a GitHub release and open a pull request
against the catalog.

- `byro-finance-import-bank-files`_ imports file-based bank statements, currently CAMT.053.
- `byro-mailman`_ (mailing list integration) and `byro-gemeinnuetzigkeit`_ (receipts for German
  non-profits) exist, but are not yet compatible with byro 2026.x.

Community plugins are encouraged to add the `byro-plugin` tag if they are on GitHub. You can see
all byro plugins on GitHub `here`_; byroctl never installs anything from that list on its own.
`byro-shackspace`_ is an example for how a group can extend or modify byro to fit their purpose,
e.g. add custom mechanisms and save additional data.

License
-------

byro is licensed under the GNU Affero General Public License, version 3.0 only
(``AGPL-3.0-only``). Older versions of byro were released under the Apache
License 2.0. The documentation in ``docs/`` is licensed under the Creative
Commons Attribution-ShareAlike 4.0 International License (``CC-BY-SA-4.0``).
See the `LICENSE`_ file for details, including the licensing history and the
licenses of bundled third-party components.

.. |byro| image:: https://raw.githubusercontent.com/byro/byro/main/docs/img/logo/byro_128.png
   :alt: byro
.. _developer documentation: http://byro.readthedocs.io/en/latest/
.. _development: https://byro.readthedocs.io/en/latest/developer/setup.html
.. _byro: https://byro.cloud
.. _here: https://github.com/topics/byro-plugin
.. _plugin catalog: https://github.com/byro/byro/blob/main/deploy/plugin-catalog.conf
.. _plugin documentation: https://byro.readthedocs.io/en/latest/administrator/plugins.html
.. _byro-finance-import-bank-files: https://github.com/byro/byro-finance-import-bank-files
.. _byro-mailman: https://github.com/byro/byro-mailman
.. _byro-gemeinnuetzigkeit: https://github.com/byro/byro-gemeinnuetzigkeit
.. _byro-shackspace: https://github.com/byro/byro-shackspace
.. _production documentation: https://byro.readthedocs.io/en/latest/administrator/
.. _byroctl: https://byro.readthedocs.io/en/latest/administrator/installation-byroctl.html
.. _LICENSE: https://github.com/byro/byro/blob/main/LICENSE
