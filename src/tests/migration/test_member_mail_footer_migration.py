"""The footer of mails to members is set by ``common.0026`` with the texts
frozen in that migration."""

import importlib
import json
import os
import sqlite3
import subprocess
import sys
import types

import pytest
from django.db import connection
from django.db.migrations.loader import MigrationLoader

SRC_DIR = os.path.join(os.path.dirname(__file__), "..", "..")

DATA_MIGRATION = ("common", "0026_configuration_member_mail_footer")
FROZEN = {
    "en": (
        "Best regards\nYour membership team\n\n-- \n"
        "{association_name}\n{association_address}\n{association_url}"
    ),
    "de": (
        "Viele Grüße\nDeine Mitgliedsverwaltung\n\n-- \n"
        "{association_name}\n{association_address}\n{association_url}"
    ),
    "pt-br": (
        "Atenciosamente\nEquipe de gestão de associados\n\n-- \n"
        "{association_name}\n{association_address}\n{association_url}"
    ),
}

data_migration = importlib.import_module(
    "byro.common.migrations.0026_configuration_member_mail_footer"
)


@pytest.fixture
def historical_apps():
    return MigrationLoader(connection).project_state(DATA_MIGRATION).apps


def mail_templates(apps):
    MailTemplate = apps.get_model("mails", "MailTemplate")
    return {
        template.pk: (template.subject.data, template.text.data)
        for template in MailTemplate.objects.all()
    }


@pytest.mark.django_db
def test_existing_installation_gets_the_frozen_footer(historical_apps):
    Configuration = historical_apps.get_model("common", "Configuration")
    config = Configuration.objects.get()
    config.member_mail_footer = None
    config.save()
    templates = mail_templates(historical_apps)

    data_migration.init_member_mail_footer(historical_apps, None)

    config.refresh_from_db()
    assert config.member_mail_footer.data == FROZEN
    assert mail_templates(historical_apps) == templates


@pytest.mark.django_db
@pytest.mark.parametrize("footer", ({}, {"de": "Ciao"}), ids=("off", "custom"))
def test_a_set_footer_is_kept(historical_apps, footer):
    Configuration = historical_apps.get_model("common", "Configuration")
    config = Configuration.objects.get()
    config.member_mail_footer = footer
    config.save()

    # as when the migration is run again, for example faked
    data_migration.init_member_mail_footer(historical_apps, None)

    config.refresh_from_db()
    assert config.member_mail_footer.data == footer


@pytest.mark.django_db
def test_migration_does_not_depend_on_the_runtime_default(historical_apps, monkeypatch):
    Configuration = historical_apps.get_model("common", "Configuration")
    config = Configuration.objects.get()
    config.member_mail_footer = None
    config.save()
    monkeypatch.setitem(
        sys.modules, "byro.mails.default", types.ModuleType("byro.mails.default")
    )
    monkeypatch.delattr("byro.mails.default", raising=False)

    data_migration.init_member_mail_footer(historical_apps, None)

    config.refresh_from_db()
    assert config.member_mail_footer.data == FROZEN


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
        BYRO_CONFIG_FILE=str(config_file),
        DJANGO_SETTINGS_MODULE="byro.common.settings.core_test_settings",
    )
    subprocess.run(
        [sys.executable, "manage.py", "migrate", *target, "--verbosity", "0"],
        env=env,
        cwd=SRC_DIR,
        capture_output=True,
        text=True,
        check=True,
    )


def stored_footer(database):
    with sqlite3.connect(database) as db:
        (footer,) = db.execute(
            "SELECT member_mail_footer FROM common_configuration"
        ).fetchone()
    return footer


def test_fresh_installation_has_the_default_footer(tmp_path):
    database = tmp_path / "db.sqlite3"
    migrate(database)

    assert json.loads(stored_footer(database)) == FROZEN


def test_migration_can_be_unapplied(tmp_path):
    database = tmp_path / "db.sqlite3"
    migrate(database)

    migrate(database, "common", "0025")

    with sqlite3.connect(database) as db:
        columns = [
            row[1] for row in db.execute("PRAGMA table_info(common_configuration)")
        ]
    assert "member_mail_footer" not in columns

    migrate(database)
    assert json.loads(stored_footer(database)) == FROZEN
