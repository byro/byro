# Development setup

To contribute to byro, it's useful to run byro locally on your device so you
can test your changes. First of all, you need install some packages on your
operating system:

If you want to install byro on a server for actual usage, go to the
[installation documentation](../installation/index.md) instead.

Please make sure you have the following dependencies installed:

| Tool                             | Debian package   |
|----------------------------------|------------------|
| Python 3.12 or newer             |                  |
| pip for Python 3                 | `python3-pip`    |
| `python-dev` for Python 3        | `python3-dev`    |
| `python-venv`, if not included   | `python3-venv`   |
| libffi                           | `libffi-dev`     |
| gettext                          | `gettext`        |
| git                              | `git`            |
| libmagic                         |                  |
| libjpeg                          |                  |

libjpeg can be replaced by any other library supported in
[pillow](https://pillow.readthedocs.io/en/latest/installation/basic-installation.html#basic-installation)
(for [qrcode](https://pypi.org/project/qrcode/)).

Some Python dependencies might also need a compiler during installation, the
Debian package `build-essential` or something similar should suffice.

## Get a copy of the source code

You can clone our git repository:

```console
$ git clone https://github.com/byro/byro.git
$ cd byro/
```

## Your local python environment

Please execute `python -V` or `python3 -V` to make sure you have Python 3.x
installed. Also make sure you have pip for Python 3 installed, you can execute
`pip3 -V` to check. Then use Python's internal tools (Ubuntu package:
`python3-venv`) to create a virtual environment and activate it for your
current session:

```console
$ python3 -m venv env  # or virtualenv -p /usr/bin/python3 env, or ...
$ source env/bin/activate
```

You should now see a `(env)` prepended to your shell prompt. You have to do
this in every shell you use to work with byro (or configure your shell to do so
automatically). If you are working on Ubuntu or Debian, we strongly recommend
upgrading your `pip` and `setuptools` installation inside the virtual
environment, otherwise some of the dependencies might fail:

```console
(env)$ pip3 install -U pip setuptools wheel
```

## Working with the code

The first thing you need are all the main application's dependencies:

```console
(env)$ cd src/
(env)$ pip3 install -e .
```

To be able to run the code checks and unit tests you need to install the
development dependencies as well:

```console
(env)$ pip3 install -e ".[dev]"
```

!!! note
    Under Windows, if you get the error message
    `failed to find libmagic.  Check your installation` error, do
    `pip install python-magic-bin` in the virtual environment to install the
    necessary magic library for Windows.

!!! note
    Under macOS, if you get the error message
    `failed to find libmagic.  Check your installation`, do
    `brew install libmagic` to install the necessary magic library.

Create a file called `byro.cfg` with this content:

```ini
[database]
engine = sqlite3
```

If you have custom database settings or other settings you need, you can
provide them like this instead:

```ini
[database]
name = byro
user = byro
password = byro
host = localhost
port = 5432
```

The default -- and recommended -- production installation uses PostgreSQL, but
for local development, you can use SQLite instead.

Then, create the local database:

```console
(env)$ python manage.py migrate
```

To be able to log in, you should also create an admin user:

```console
(env)$ python manage.py createsuperuser
```

If you want to see byro in a different language than English, you have to
compile our language files:

```console
(env)$ python manage.py compilemessages
```

### Run the development server

To run the local development server, execute:

```console
(env)$ python manage.py runserver
```

Now point your browser to <http://localhost:8000/> – You should be able to log
in and play around! You can use the following command to generate example data:

```console
(env)$ python manage.py make_testdata
```

### Code checks and unit tests

Before you check in your code into git, always run the static checkers and unit
tests:

```console
(env)$ isort .
(env)$ black .
(env)$ flake8 .
(env)$ djhtml byro/
(env)$ python manage.py check --deploy
(env)$ python -m pytest tests
```

CI runs the same checks, but without auto-formatting: `isort -c .` and
`black --check .` (check only, never write), and the test run is
parallelized with automatic reruns for flaky tests:
`python -m pytest --reruns=3 -nauto -p no:sugar --maxfail=100 tests`. Read
`.github/workflows/ci-cd.yml` if you need the exact CI commands.

!!! note
    If you have more than one CPU core and want to speed up the test suite,
    run `python -m pytest -n auto tests` (`pytest-xdist` is already part of
    the development dependencies).

It's a good idea to put the style checks into your git hook
`.git/hooks/pre-commit`, for example:

```sh
#!/bin/sh
set -e
cd $GIT_DIR/../src
source ../env/bin/activate
isort .
black .
flake8 .
djhtml byro/
```

### Working with translations

If you want to translate new strings that are not yet known to the translation
system, you can use the following command to scan the source code for strings
we want to translate and update the `*.po` files accordingly:

```console
(env)$ python manage.py makemessages
```

To actually see byro in your language, you have to compile the `*.po` files to
their optimized binary `*.mo` counterparts:

```console
(env)$ python manage.py compilemessages
```

### Next steps

To contribute to byro, please read the
[contributing documentation](contributing.md).

Head over to [Working on the documentation](documentation.md) if you want to
improve the documentation.

If you want to work on plugins, please go to the
[plugin guides](plugins/index.md).
