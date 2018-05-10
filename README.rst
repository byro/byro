byro
====

.. image:: https://travis-ci.org/byro/byro.svg?branch=master
   :target: https://travis-ci.org/byro/byro
   :alt: Travis build status

.. image:: https://codecov.io/gh/byro/byro/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/byro/byro
   :alt: Code coverage

.. image:: https://readthedocs.org/projects/byro/badge/?version=latest
   :target: http://byro.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation

byro is currently very very much work in progress. It will be a membership administration tool
for small and medium sized clubs/NGOs/associations of all kinds, with a focus on the DACH region.

Development Setup
-----------------

using Docker
^^^^^^^^^^^^

- add ``local_settings.py`` in the ``src/byro/`` folder with this contents:

.. code:: python

  DATABASES = {
      'default': {
          'ENGINE': 'django.db.backends.postgresql_psycopg2',
          'NAME': 'byro',
          'USER': 'postgres',
          'PASSWORD': '',
          'HOST': 'db',
      }
  }

- create database

.. code:: shell

  docker-compose run --rm web reset_db

- run Django on port 8020:

.. code:: shell

  docker-compose up -d

- run the database-migrations

.. code:: shell

  docker-compose run --rm web migrate

- create the superuser

.. code:: shell

  docker-compose run --rm web createsuperuser

- run tests

.. code:: shell

   docker-compose exec web py.test -sx

- execute arbitrary django commands like so:

.. code:: shell

  docker-compose run --rm web makemigrate

Not using Docker
^^^^^^^^^^^^^^^^

.. code:: shell

    [postgres@localhost ~]$ createdb byro
    [postgres@localhost ~]$ createuser byro -P
    Enter password for new role:
    Enter it again:
    [postgres@ronja ~]$ psql
    psql (10.1)
    Type "help" for help.

    postgres=# GRANT ALL PRIVILEGES ON DATABASE byro TO byro;
    GRANT


Features
--------


Planned features
----------------


Official Plugins
----------------

byro provides a rich API for plugins. See our `developer documentation`_ if you want to write a
plugin. If you want your plugin to be officially recognized or listed here, please open an issue
or a pull request.

.. _developer documentation: http://byro.readthedocs.io/en/latest/
