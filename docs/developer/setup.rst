Development setup
=================

To contribute to byro, it's useful to run byro locally on your device so you can test your
changes. First of all, you need install some packages on your operating system:

If you want to install byro on a server for actual usage, go to the :ref:`administrator documentation <administrator-setup>` instead.

* git
* Python 3.x
* A recent version of pip (Ubuntu package: ``python3-pip``)
* gettext (Debian package: ``gettext``)
* libjpeg or any other library supported in pillow_ (for qrcode_)
* libmagic
* A PostgreSQL server

Some Python dependencies might also need a compiler during installation, the Debian package
``build-essential`` or something similar should suffice.


Get a copy of the source code
-----------------------------
You can clone our git repository::

    git clone https://github.com/byro/byro.git
    cd byro/


Database setup
--------------

Having the database server installed, we still need a database and a database user::

  sudo -u postgres -i
  postgres $ createuser <yourusername>
  postgres $ createdb byro -O <yourusername>

Substitute your system username for ``<yourusername>``.


Your local python environment
-----------------------------

Please execute ``python -V`` or ``python3 -V`` to make sure you have Python 3.x
installed. Also make sure you have pip for Python 3 installed, you can execute ``pip3 -V`` to check.
Then use Python's internal tools (Ubuntu package: ``python3-venv``) to create a virtual environment and activate it for your current
session::

    python3 -m venv env  # or virtualenv -p /usr/bin/python3 env, or ...
    source env/bin/activate

You should now see a ``(env)`` prepended to your shell prompt. You have to do this in every shell
you use to work with byro (or configure your shell to do so automatically). If you are working on
Ubuntu or Debian, we strongly recommend upgrading your pip and setuptools installation inside the
virtual environment, otherwise some of the dependencies might fail::

    (env)$ pip3 install -U pip setuptools wheel


Working with the code
---------------------
The first thing you need are all the main application's dependencies::

    (env)$ cd src/
    (env)$ pip3 install -e .

.. note:: (Windows only) If you get the error message ``failed to find libmagic.  Check your installation`` error, do ``pip install python-magic-bin`` in the virtual environment to install the necessary magic library for Windows.

Next, if you have custom database settings or other settings you need, make a new
file ``byro/local_settings.py`` with contents like these::

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'byro',
            'USER': 'byro',
            'PASSWORD': 'byro',
            'HOST': 'localhost',
        }
    }

(The default -- and recommended -- installation uses PostgreSQL "Peer Authentication", in which the
Unix user is mapped to the Postgres database user. This works only for local connections, and only
on Linux, most BSDs, OS X, and Solaris, but provides the highest level of security and the least
amount of configuration. In this mode the keys ``USER``, ``PASSWORD``, and ``HOST`` MUST NOT be set.)

Then, create the local database::

    (env)$ python manage.py migrate

To be able to log in, you should also create an admin user::

    (env)$ python manage.py createsuperuser

If you want to see byro in a different language than English, you have to compile our language
files::

    (env)$ python manage.py compilemessages


Run the development server
^^^^^^^^^^^^^^^^^^^^^^^^^^
To run the local development server, execute::

    (env)$ python manage.py runserver

Now point your browser to http://localhost:8000/ – You should be able to log in and play
around! You can use the following command to generate example data::

    (env)$ python manage.py make_testdata

.. _`checksandtests`:

Code checks and unit tests
^^^^^^^^^^^^^^^^^^^^^^^^^^
Before you check in your code into git, always run the static checkers and unit tests::

    (env)$ isort -c -rc .
    (env)$ black -S --exclude "/(\.eggs|\.git|\.mypy_cache|\.nox|\.tox|\.venv|_build|build|static|static.dist|dist|migrations)/|urls.py" .
    (env)$ python manage.py check
    (env)$ py.test tests

.. note:: If you have more than one CPU core and want to speed up the test suite, you can run
          ``py.test -n NUM`` with ``NUM`` being the number of threads you want to use.

It's a good idea to put the style checks into your git hook ``.git/hooks/pre-commit``,
for example::

    #!/bin/sh
    set -e
    cd $GIT_DIR/../src
    source ../env/bin/activate
    isort -c -rc .
    black -S --exclude "/(\.eggs|\.git|\.mypy_cache|\.nox|\.tox|\.venv|_build|build|static|static.dist|dist|migrations)/|urls.py" .


Working with translations
^^^^^^^^^^^^^^^^^^^^^^^^^
If you want to translate new strings that are not yet known to the translation system, you can use
the following command to scan the source code for strings we want to translate and update the
``*.po`` files accordingly::

    (env)$ python manage.py makemessages

To actually see byro in your language, you have to compile the ``*.po`` files to their optimized
binary ``*.mo`` counterparts::

    (env)$ python manage.py compilemessages


Next steps
^^^^^^^^^^
To contribute to byro, please read the :doc:`contributing documentation </developer/contributing>`.

Head over to the :doc:`documentation patching section </developer/documentation>` if you want to improve the documentation.

If you want to work on plugins, please go to the :doc:`plugin guides </developer/plugins/index>`.

.. _qrcode: https://pypi.org/project/qrcode/
.. _pillow: https://pillow.readthedocs.io/en/latest/installation.html#external-libraries
