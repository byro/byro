"""The configuration of an installation is created by the historical migration
``common.0007``, long before the model default of the currency exists. That
bootstrap cannot be reproduced inside the already migrated test database, so
these tests run the real ``migrate`` command in a fresh interpreter against an
empty SQLite database."""

import os
import shutil
import sqlite3
import subprocess
import sys

import pytest
from django.db import connection, migrations
from django.db.migrations.loader import MigrationLoader

SRC_DIR = os.path.join(os.path.dirname(__file__), "..", "..")

BEFORE_BOOTSTRAP = ("common", "0006_auto_20180224_2114")
BOOTSTRAP = ("common", "0007_auto_20180224_2114")
SCHEMA_MIGRATION = ("common", "0023_configuration_currency_default")


def migrate(database, *target):
    config_file = database.with_suffix(".cfg")
    config_file.write_text(
        f"[filesystem]\ndata = {database.parent}\n\n"
        f"[database]\nengine = sqlite3\nname = {database}\n"
    )
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("BYRO_")
    }
    env.update(
        BYRO_CONFIG_FILE=str(config_file), DJANGO_SETTINGS_MODULE="byro.settings"
    )
    subprocess.run(
        [sys.executable, "manage.py", "migrate", *target, "--verbosity", "0"],
        env=env,
        cwd=SRC_DIR,
        capture_output=True,
        text=True,
        check=True,
    )


def query(database, sql, *parameters):
    with sqlite3.connect(database) as db:
        return db.execute(sql, parameters).fetchall()


@pytest.fixture(scope="module")
def database_before_bootstrap(tmp_path_factory):
    database = tmp_path_factory.mktemp("before_bootstrap") / "db.sqlite3"
    migrate(database, *BEFORE_BOOTSTRAP)
    return database


@pytest.fixture
def database(database_before_bootstrap, tmp_path):
    """An installation right before the configuration is created."""
    database = tmp_path / "db.sqlite3"
    shutil.copy(database_before_bootstrap, database)
    assert query(database, "SELECT COUNT(*) FROM common_configuration") == [(0,)]
    return database


def test_bootstrap_creates_configuration_with_euro(database):
    migrate(database, *BOOTSTRAP)

    assert query(database, "SELECT currency FROM common_configuration") == [("EUR",)]


def test_fresh_installation_starts_with_euro_and_its_symbol(database):
    migrate(database)

    assert query(
        database, "SELECT currency, currency_symbol FROM common_configuration"
    ) == [("EUR", "€")]


@pytest.mark.parametrize("currency", (None, "", "USD"))
def test_existing_configuration_keeps_its_currency(database, currency):
    # nothing but the currency is set: no property of the row may make it
    # look like a new installation
    query(
        database,
        "INSERT INTO common_configuration (currency, liability_interval)"
        " VALUES (?, 36)",
        currency,
    )

    migrate(database, *BOOTSTRAP)
    assert query(database, "SELECT currency FROM common_configuration") == [(currency,)]

    # ... and neither does any later migration up to the current state
    migrate(database)
    assert query(database, "SELECT currency FROM common_configuration") == [(currency,)]


@pytest.mark.django_db
def test_only_the_model_default_changes_after_the_bootstrap():
    loader = MigrationLoader(connection)
    (leaf,) = loader.graph.leaf_nodes("common")
    assert SCHEMA_MIGRATION in loader.graph.forwards_plan(leaf)

    (alter_field,) = loader.graph.nodes[SCHEMA_MIGRATION].operations
    assert isinstance(alter_field, migrations.AlterField)
    assert (alter_field.model_name, alter_field.name) == ("configuration", "currency")
    assert alter_field.field.default == "EUR"
    # still optional: nothing forces a currency onto existing installations
    assert alter_field.field.null and alter_field.field.blank
