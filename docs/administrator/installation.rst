Installation
============

This guide will help you to install byro on a Linux distribution, as long as
the prerequisites are present.

Note: there is also an experimental deployment available via `docker-compose`_.

Step 0: Prerequisites
---------------------

Please set up the following systems beforehand, we'll not explain them here (but see these links for
external installation guides):

* **Python 3.7+** and ``pip`` for Python 3. You can use ``python -V`` and ``pip3 -V`` to check.
* An SMTP server to send out mails
* An HTTP reverse proxy, e.g. `nginx`_ or Apache to allow HTTPS connections
* A database server: `MySQL`_ 5.7+ or MariaDB 10.2+ or `PostgreSQL`_ 9.6+.
  You can use SQLite, but we strongly recommend not to run SQLite in
  production. Given the choice, we'd recommend to use PostgreSQL.

We also recommend that you use a firewall, although this is not a byro-specific recommendation.
If you're new to Linux and firewalls, we recommend that you start with `ufw`_.

.. note:: Please do not run byro without HTTPS encryption. You'll handle sensitive data and thanks
          to `Let's Encrypt`_, SSL certificates are free these days. We also *do not* provide
          support for HTTP-exclusive installations except for evaluation purposes.

Step 1: Unix user
-----------------

As we do not want to run byro as root, we first create a new unprivileged user::

    # adduser byro --disabled-password --home /var/byro

In this guide, all code lines prepended with a ``#`` symbol are commands that
you need to execute on your server as ``root`` user (e.g. using ``sudo``); you
should run all lines prepended with a ``$`` symbol as the unprivileged user.


Step 2: Database setup
----------------------

Having the database server installed, we still need a database and a database
user. We recommend using PostgreSQL. byro also works (and runs tests
against) MariaDB and SQLite. If you do not use PostgreSQL, please refer to the
appropriate documentation on how to set up a database. For PostgreSQL, run
these commands::

  postgres $ createuser byro -P
  postgres $ createdb -O byro byro

When using MySQL, make sure you set the character set of the database to ``utf8mb4``, e.g. like this::

    mysql > CREATE DATABASE byro DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci

Step 3: Package dependencies
----------------------------

To build and run byro, you will need the following Debian packages beyond the dependencies
mentioned above::

    # apt-get install git build-essential libssl-dev gettext

Replace all further "pip" commands with "pip3" if your system does not have
Python 3 as default Python version.


Step 4: Configuration
---------------------

We now create a configuration directory and configuration file for byro::

    # mkdir /etc/byro
    # touch /etc/byro/byro.cfg
    # chown -R byro:byro /etc/byro/
    # chmod 0600 /etc/byro/byro.cfg

Fill the configuration file ``/etc/byro/byro.cfg`` with the following content (adjusted to your environment):

.. literalinclude:: ../../src/byro.example.cfg
   :language: ini

Step 5: Installation
--------------------

Now we will install byro itself. Please execute the following steps as the ``byro`` user. We will
update all relevant Python packages in the user's Python environment, so that your global Python
installation will not know of them::

    $ pip install --user -U pip setuptools wheel gunicorn psycopg2-binary

Next, we will install byro – you can either install the latest PyPI release, or install a specific
branch or commit::

    $ pip install --user -U byro  # OR, alternatively
    $ pip install --user -U "git+git://github.com/byro/byro.git@master#egg=byro&subdirectory=src"

We also need to create a data directory::

    $ mkdir -p /var/byro/data/media

We compile static files and translation data and create the database structure::

    $ python -m byro migrate
    $ python -m byro compilemessages
    $ python -m byro collectstatic
    $ python -m byro compress

Now, create an administrator user by running::

    $ python -m byro createsuperuser

If you just want to play around with byro, you can load test data::

    $ python -m byro make_testdata

Step 6: Starting byro as a service
----------------------------------

We recommend starting byro using systemd to make sure it starts up after a
reboot. Create a file named ``/etc/systemd/system/byro-web.service`` with the
following content (replacing the local paths with ones appropriate for your
system, especially the local Python version's)::

    [Unit]
    Description=byro web service
    After=network.target

    [Service]
    User=byro
    Group=byro
    WorkingDirectory=/var/byro/.local/lib/python3.8/site-packages/byro
    ExecStart=/var/byro/.local/bin/gunicorn byro.wsgi \
                          --name byro --workers 4 \
                          --max-requests 1200  --max-requests-jitter 50 \
                          --log-level=info --bind=127.0.0.1:8345
    Restart=on-failure

    [Install]
    WantedBy=multi-user.target


You can now run the following commands to enable and start the services::

    # systemctl daemon-reload
    # systemctl enable byro-web
    # systemctl start byro-web

Step 7: SSL
-----------

The following snippet is an example on how to configure a nginx proxy for byro::

    server {
        listen 80 default_server;
        listen [::]:80 ipv6only=on default_server;
        server_name byro.mydomain.com;
    }
    server {
        listen 443 default_server;
        listen [::]:443 ipv6only=on default_server;
        server_name byro.mydomain.com;

        ssl on;
        ssl_certificate /path/to/cert.chain.pem;
        ssl_certificate_key /path/to/key.pem;

        add_header Referrer-Options same-origin;
        add_header X-Content-Type-Options nosniff;

        location / {
            proxy_pass http://localhost:8345/;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto https;
            proxy_set_header Host $http_host;
        }

        location /media/ {
            alias /var/byro/data/media/;
            add_header Content-Disposition 'attachment; filename="$1"';
            expires 7d;
            access_log off;
        }

        location /static/ {
            alias /path/to/static.dist/;
            access_log off;
            expires 365d;
            add_header Cache-Control "public";
        }
    }

We recommend reading about setting `strong encryption settings`_ for your web server.

You've made it! You should now be able to reach byro at
https://byro.yourdomain.com/ and log in as the administrator you configured
above. byro will take you through the remaining configuration steps.

Step 8: Check the installation
-------------------------------

You can make sure the web interface is up and look for any issues with::

    # journalctl -u byro-web

In the start-up output, byro also lists its logging directory, which is also
a good place to look for the reason for issues.


Next Steps: Updates
-------------------

.. warning:: While we try hard not to issue breaking updates, **please perform a backup before every upgrade**.

To upgrade byro, please first read through our changelog and if
available our release blog post to check for relevant update notes. Also, make
sure you have a current backup.

Next, please execute the following commands in the same environment (probably
your virtualenv) to first update the byro source, then update the database
if necessary, then rebuild changed static files, and then restart the byro
service. Please note that you will run into an entertaining amount of errors
if you forget to restart the services.

If you want to upgrade byro to a specific release, you can substitute
``byro`` with ``byro==1.2.3`` in the first line::

    $ pip3 install -U byro gunicorn
    $ python -m byro migrate
    $ python -m byro compilemessages
    $ python -m byro collectstatic
    $ python -m byro compress
    # systemctl restart byro-web


.. _nginx: https://botleg.com/stories/https-with-lets-encrypt-and-nginx/
.. _Let's Encrypt: https://letsencrypt.org/
.. _PostgreSQL: https://www.digitalocean.com/community/tutorials/how-to-install-and-use-postgresql-9-4-on-debian-8
.. _ufw: https://en.wikipedia.org/wiki/Uncomplicated_Firewall
.. _strong encryption settings: https://mozilla.github.io/server-side-tls/ssl-config-generator/
.. _docker-compose: https://byro.readthedocs.io/en/latest/administrator/docker-compose.html
