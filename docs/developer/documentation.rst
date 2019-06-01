Patching documentation
----------------------

You have found something to improve in our documentation? Great! We'll assume that you have
already forked and cloned byro as detailed in the
:doc:`contributing documentation </developer/contributing>`. For the following steps, you'll
need to have Python 3 installed on your system.

Start out in a shell in the repository. We'll start by generating a virtualenv and installing
the required Python packages::

  python3 -m venv .venv
  source venv/bin/activate
  pip install -Ur docs/requirements.txt


Writing documentation
=====================

Now go to the ``docs`` directory, find the file you want to adjust (or create), and make your
changes. You can look at the files by running ``make html`` in the ``docs`` directory and then
browsing the ``_build/html`` directory. For more convenience, you can run

::

  sphinx-autobuild . ./_build/html

Which starts an HTTP server and rebuilds the documentation upon any changes.


Translating documentation
=========================

Our documentation is multilingual. To update the translation files, run

::

  make gettext
  sphinx-intl update -p _build/gettext -l de

and then edit the generated ``.po`` files with an appropriate editor such as poedit.


Checking documentation
======================

In the future we want to use spell checking and style checking on our documentation.
