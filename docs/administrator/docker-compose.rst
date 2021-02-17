Installation via docker-compose
===============================

In the folder `production/` of the byro repository, you can find setup scripts
and a `docker-compose.yml`, which will help you set up a production deployment of byro using docker.

.. note:: There is also a `docker-compose` file inside the `src/` folder.
          This file is only intended for development!

Step 0: Prerequisites
---------------------

This guide assumes that you have installed and set up the following system services:

* Docker
* docker-compose
* An SMTP server to send out mails
* An HTTP reverse proxy, e.g. `nginx`_ or Apache to allow HTTPS connections

Step 1: Configuration
---------------------

Checkout the repository, and run the setup script::

    # git clone https://github.com/byro/byro
    # byro/production/setup.sh

This will create a folder `byro-data/` next to the byro folder, which will
contain all your data.
It will also copy an initial `byro.cfg` to the data folder.

Open this file in an editor, and configure the following aspects:

`[mail]`
    Enter connection settings to your SMTP server. The pre-filled IP represents the
    address the docker container can use to reach your host box. Change this if your
    SMTP server is not local to the server running byro.

`[site]`
    Change the URL to an URL your server is reachable on. If your server is not yet
    exposed to the world, you will need to enable `debug` to bypass Django URL security.

.. note:: Never expose your server to the world with `debug = True` enabled.
          This will allow users accessing the page to view potentially sensitive
          information.

Step 2: Deployment
------------------

After you have changed your configuration, run the setup script again::

    # byro/production/setup.sh

Your database will now be created, and you will be prompted to create a superuser.
After that, your deployment will be complete. You can use the `setup.sh` script
to perform further tasks, such as stopping your deployment, tailing the logs,
or installing byro plugins.

For more information, run::

    # byro/production/setup.sh help

Step 3: Install the FinTS plugin (optional)
-------------------------------------------

The following call will install the `byro-fints plugin`_::

  # byro/production/setup.sh fints


.. _nginx: https://botleg.com/stories/https-with-lets-encrypt-and-nginx/
.. _byro-fints plugin: https://github.com/henryk/byro-fints
