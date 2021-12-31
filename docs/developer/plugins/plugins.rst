.. _`pluginsetup`:

Creating a plugin
=================

You can, and probably need to, extend byro with custom Python code using the
official plugin API. You'll have to think of every plugin as an independent
Django 'app' living in its own python package installed like any other python
module.

The communication between byro and the plugins happens primarily using Django's
`signal dispatcher`_ feature. The core modules of byro expose signals for
different purposes. You can find their documentation on the next pages. We also
provide guides for common plugin use cases, such as tracking custom member
data, or importing and matching payments.

To create a new plugin, create a new python package which must be a valid `Django app`_
and must contain plugin metadata, as described below.
You will need some boilerplate code for every plugin to get started. To save
your time, we created a `cookiecutter`_ template that you can use like this::

   (env)$ pip install cookiecutter
   (env)$ cookiecutter https://github.com/byro/byro-plugin-cookiecutter

This will ask you some questions and then create a project folder for your plugin.

The following pages go into detail about the different types of plugins byro
supports. While these instructions don't assume that you know a lot about byro,
they do assume that you have prior knowledge about Django (e.g. its view layer,
how its ORM works, etc.).

Plugin metadata
---------------

The plugin metadata lives inside a ``ByroPluginMeta`` class inside your app's
configuration class. The metadata class must define the following attributes:

.. rst-class:: rest-resource-table

================== ==================== ===========================================================
Attribute          Type                 Description
================== ==================== ===========================================================
name               string               The human-readable name of your plugin
author             string               Your name
version            string               A human-readable version code of your plugin
description        string               A more verbose description of what your plugin does.
================== ==================== ===========================================================

A working example would be::

    from django.apps import AppConfig
    from django.utils.translation import ugettext_lazy as _


    class IRCApp(AppConfig):
        name = 'byro_irc'
        verbose_name = _("IRC")

        class ByroPluginMeta:
            name = _("IRC")
            author = _("irclover")
            version = '1.0.0'
            visible = True
            description = _("This plugin sends notifications via IRC.")


    default_app_config = 'byro_irc.IRCApp'

Plugin registration
-------------------

Somehow, byro needs to know that your plugin exists at all. For this purpose, we
make use of the `entry point`_ feature of setuptools. To register a plugin that lives
in a separate python package, your ``setup.py`` should contain something like this::

    setup(
        args...,
        entry_points="""
    [byro.plugin]
    byro_irc=byro_irc:ByroPluginMeta
    """
    )


This will automatically make byro discover this plugin as soon as you have
installed it, e.g.  through ``pip``. During development, you can run ``python
setup.py develop`` inside your plugin source directory to make it discoverable.

Signals
-------

byro defines different signals which your plugin can listen for. We will
go into the details of the different signals in the following pages. We suggest
that you put your signal receivers into a ``signals`` submodule of your plugin.
You should extend your ``AppConfig`` (see above) by the following method to
make your receivers available::

    class IRCApp(AppConfig):
        …

        def ready(self):
            from . import signals  # noqa


Views
-----

Your plugin may define custom views. If you put an ``urls`` submodule into your
plugin module, byro will automatically import it and include it into the root
URL configuration with the namespace ``plugins:<label>:``, where ``<label>`` is
your Django app label.

.. WARNING:: If you define custom URLs and views, you are on your own
   with checking that the user has appropriate permissions. byro ensures that
   you are dealing with an authenticated user, but nothing else.

.. _Django app: https://docs.djangoproject.com/en/dev/ref/applications/
.. _signal dispatcher: https://docs.djangoproject.com/en/dev/topics/signals/
.. _namespace packages: http://legacy.python.org/dev/peps/pep-0420/
.. _entry point: https://setuptools.pypa.io/en/latest/pkg_resources.html#locating-plugins
.. _cookiecutter: https://cookiecutter.readthedocs.io/en/latest/
