Configuration
=============

You can configure byro in two different ways: using configuration files or
environment variables. You can combine those two options, and their precedence
is in this order:

1. Environment variables
2. Configuration files
    - The configuration file in the environment variable ``BYRO_CONFIG_FILE`` if present, **or**:
    - The following three configuration files in this order:
       - The configuration file ``byro.cfg`` in the ``src`` directory, next to the ``byro.example.cfg`` file.
       - The configuration file ``~/.byro.cfg`` in the home of the executing user.
       - The configuration file ``/etc/byro/byro.cfg``
3. Sensible defaults

This page explains the options by configuration file section and notes the corresponding environment
variable next to it. A configuration file looks like this:

.. literalinclude:: ../../src/byro.example.cfg
   :language: ini

The filesystem section
----------------------

``data``
~~~~~~~~

- The ``data`` option describes the path that is the base for the media files
  directory, and where byro will save log files. Unless you have a
  compelling reason to keep those files apart, setting the ``data`` option is
  the easiest way to configure byro.
- **Environment variable:** ``BYRO_DATA_DIR``
- **Default:** A directory called ``data`` next to byro's ``manage.py``.

``media``
~~~~~~~~~

- The ``media`` option sets the media directory that contains user generated files. It needs to
  be writeable by the byro process.
- **Environment variable:** ``BYRO_FILESYSTEM_MEDIA``
- **Default:** A directory called ``media`` in the ``data`` directory (see above).

``logs``
~~~~~~~~

- The ``logs`` option sets the log directory that contains logged data. It needs to
  be writeable by the byro process.
- **Environment variable:** ``BYRO_FILESYSTEM_LOGS``
- **Default:** A directory called ``logs`` in the ``data`` directory (see above).

``static``
~~~~~~~~~~

- The ``statics`` option sets the directory that contains static files. It needs to
  be writeable by the byro process. byro will put files there during the
  ``collectstatic`` command.
- **Environment variable:** ``BYRO_FILESYSTEM_STATIC``
- **Default:** A directory called ``static.dist`` next to byro's ``manage.py``.

The site section
----------------

``debug``
~~~~~~~~~

- Decides if byro runs in debug mode. Please use this mode for development and debugging, not
  for live usage.
- **Environment variable:** ``BYRO_DEBUG``
- **Default:** ``True`` if you're executing ``runserver``, ``False`` otherwise. **Never run a
  production server in debug mode.**

``url``
~~~~~~~

- This value will appear wherever byro needs to render full URLs (for example in emails and),
  and set the appropriate allowed hosts variables.
- **Environment variable:** ``BYRO_SITE_URL``
- **Default:** ``http://localhost``

``secret``
~~~~~~~~~~

- Every Django application has a secret that Django uses for cryptographic signing.
  You do not need to set this variable – byro will generate a secret key and save it in a local file if
  you do not set it manually.
- **Default:** None


The database section
--------------------

``name``
~~~~~~~~

- The database's name.
- **Environment variable:** ``BYRO_DB_NAME``
- **Default:** ``''``

``user``
~~~~~~~~

- The database user.
- **Environment variable:** ``BYRO_DB_USER``
- **Default:** ``''``

``password``
~~~~~~~~~~~~

- The database password.
- **Environment variable:** ``BYRO_DB_PASS``
- **Default:** ``''``

``host``
~~~~~~~~

- The database host, or the socket location, as needed.
- **Environment variable:** ``BYRO_DB_HOST``
- **Default:** ``''``

``port``
~~~~~~~~

- The database port.
- **Environment variable:** ``BYRO_DB_PORT``
- **Default:** ``''``

The mail section
----------------

``from``
~~~~~~~~

- The fall-back sender address, e.g. for when byro sends event independent emails.
- **Environment variable:** ``BYRO_MAIL_FROM``
- **Default:** ``admin@localhost``

``host``
~~~~~~~~

- The email server host address.
- **Environment variable:** ``BYRO_MAIL_HOST``
- **Default:** ``localhost``

``port``
~~~~~~~~

- The email server port.
- **Environment variable:** ``BYRO_MAIL_PORT``
- **Default:** ``25``

``user``
~~~~~~~~

- The user account for mail server authentication, if needed.
- **Environment variable:** ``BYRO_MAIL_USER``
- **Default:** ``''``

``password``
~~~~~~~~~~~~

- The password for mail server authentication, if needed.
- **Environment variable:** ``BYRO_MAIL_PASSWORD``
- **Default:** ``''``

``tls``
~~~~~~~

- Should byro use TLS when sending mail? Please choose either TLS or SSL.
- **Environment variable:** ``BYRO_MAIL_TLS``
- **Default:** ``False``

``ssl``
~~~~~~~

- Should byro use SSL when sending mail? Please choose either TLS or SSL.
- **Environment variable:** ``BYRO_MAIL_SSL``
- **Default:** ``False``

The logging section
-------------------

``email``
~~~~~~~~~

- The email address (or addresses, comma separated) to send system logs to.
- **Environment variable:** ``BYRO_LOGGING_EMAIL``
- **Default:** ``''``

``email_level``
~~~~~~~~~~~~~~~

- The log level to start sending emails at. Any of ``[DEBUG, INFO, WARNING, ERROR, CRITICAL]``.
- **Environment variable:** ``BYRO_LOGGING_EMAIL_LEVEL``
- **Default:** ``'ERROR'``

The locale section
------------------

``language_code``
~~~~~~~~~~~~~~~~~

- The system's default locale.
- **Environment variable:** ``BYRO_LANGUAGE_CODE``
- **Default:** ``'de'``

``time_zone``
~~~~~~~~~~~~~

- The system's default time zone as a ``pytz`` name.
- **Environment variable:** ``BYRO_TIME_ZONE``
- **Default:** ``'UTC'``
