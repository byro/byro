import subprocess
import sys
import os
import pytest

SRC_DIR = os.path.join(os.path.dirname(__file__), "..", "..")

def run_test_script(script):
    env = os.environ.copy()
    env["BYRO_DB_ENGINE"] = "sqlite3"
    result = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        cwd=SRC_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()

def test_test_settings_removes_debug_toolbar():
    script = """
import sys
from types import ModuleType

# Simulate debug_toolbar being importable so byro.settings adds it
sys.modules["debug_toolbar"] = ModuleType("debug_toolbar")

from byro.common.settings import test_settings

print("debug_toolbar" in test_settings.INSTALLED_APPS)
print("debug_toolbar.middleware.DebugToolbarMiddleware" in test_settings.MIDDLEWARE)
"""
    output = run_test_script(script).splitlines()
    assert output == ["False", "False"]

def test_test_settings_independent_removal():
    script = """
import sys
from types import ModuleType

sys.modules["debug_toolbar"] = ModuleType("debug_toolbar")

import byro.settings
# Remove the app entry manually so only the middleware is present
byro.settings.INSTALLED_APPS.remove("debug_toolbar")

from byro.common.settings import test_settings

print("debug_toolbar" in test_settings.INSTALLED_APPS)
print("debug_toolbar.middleware.DebugToolbarMiddleware" in test_settings.MIDDLEWARE)
"""
    output = run_test_script(script).splitlines()
    assert output == ["False", "False"]
