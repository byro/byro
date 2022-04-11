import importlib
import os
from contextlib import suppress

import pytest
from django.conf import settings
from django.dispatch import Signal

here = os.path.dirname(__file__)
doc_dir = os.path.join(here, "../../../docs")
base_dir = os.path.join(here, "../../byro")

with open(os.path.join(doc_dir, "developer/plugins/general.rst")) as doc_file:
    plugin_docs = doc_file.read()


@pytest.mark.parametrize(
    "app", [app for app in settings.INSTALLED_APPS if app.startswith("byro.")]
)
def test_documentation_includes_signals(app):
    app = "byro." + app.split(".")[1]
    with suppress(ImportError):
        module = importlib.import_module(app + ".signals")
        for key in dir(module):
            attrib = getattr(module, key)
            if isinstance(attrib, Signal):
                assert (
                    key in plugin_docs
                ), "Signal {app}.signals.{key} is not documented!".format(
                    app=app, key=key
                )
