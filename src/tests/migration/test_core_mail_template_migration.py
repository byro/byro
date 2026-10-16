"""The default templates of the balance reminder, the document delivery and the
PGP expiry reminder are created by ``common.0025`` with the values frozen in
that migration."""

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

DATA_MIGRATION = ("common", "0025_core_mail_templates")
NEW_FIELDS = (
    "balance_reminder_template",
    "document_delivery_template",
    "pgp_expiry_reminder_template",
)
EXISTING_FIELDS = (
    "welcome_member_template",
    "welcome_office_template",
    "leave_member_template",
    "leave_office_template",
    "record_disclosure_template",
)

data_migration = importlib.import_module(
    "byro.common.migrations.0025_core_mail_templates"
)


@pytest.fixture
def historical_apps():
    return MigrationLoader(connection).project_state(DATA_MIGRATION).apps


@pytest.mark.django_db
def test_existing_installation_gets_the_three_templates_once(historical_apps):
    MailTemplate = historical_apps.get_model("mails", "MailTemplate")
    Configuration = historical_apps.get_model("common", "Configuration")
    config = Configuration.objects.get()
    for field in NEW_FIELDS:
        setattr(config, field, None)
    config.save()
    existing = {
        template.pk: (template.subject, template.text)
        for template in MailTemplate.objects.all()
    }
    assignments = {field: getattr(config, f"{field}_id") for field in EXISTING_FIELDS}

    data_migration.init_templates(historical_apps, None)

    config.refresh_from_db()
    new = MailTemplate.objects.exclude(pk__in=existing)
    assert sorted(new.values_list("pk", flat=True)) == sorted(
        getattr(config, f"{field}_id") for field in NEW_FIELDS
    )
    assert {
        template.pk: (template.subject, template.text)
        for template in MailTemplate.objects.filter(pk__in=existing)
    } == existing
    assert {
        field: getattr(config, f"{field}_id") for field in EXISTING_FIELDS
    } == assignments

    # running it again, as with a faked migration, creates no duplicates
    data_migration.init_templates(historical_apps, None)

    assert MailTemplate.objects.count() == len(existing) + 3


@pytest.mark.django_db
def test_migration_does_not_depend_on_the_runtime_defaults(
    historical_apps, monkeypatch
):
    Configuration = historical_apps.get_model("common", "Configuration")
    config = Configuration.objects.get()
    config.pgp_expiry_reminder_template = None
    config.save()
    monkeypatch.setitem(
        sys.modules, "byro.mails.default", types.ModuleType("byro.mails.default")
    )
    # ``from byro.mails import default`` would now find the empty module
    monkeypatch.delattr("byro.mails.default", raising=False)

    data_migration.init_templates(historical_apps, None)

    config.refresh_from_db()
    template = config.pgp_expiry_reminder_template
    assert template.subject.data == {
        "en": "Your PGP key expires soon",
        "de": "Dein PGP-Schlüssel läuft bald ab",
        "pt-br": "Your PGP key expires soon",
    }


def migrate(database):
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
        [sys.executable, "manage.py", "migrate", "--verbosity", "0"],
        env=env,
        cwd=SRC_DIR,
        capture_output=True,
        text=True,
        check=True,
    )


def test_fresh_installation_has_every_core_mail_template(tmp_path):
    database = tmp_path / "db.sqlite3"
    migrate(database)

    columns = ", ".join(f"{field}_id" for field in EXISTING_FIELDS + NEW_FIELDS)
    with sqlite3.connect(database) as db:
        (assigned,) = db.execute(f"SELECT {columns} FROM common_configuration")
        templates = dict(db.execute("SELECT id, subject FROM mails_mailtemplate"))
        (balance_text,) = db.execute(
            "SELECT text FROM mails_mailtemplate WHERE id = ?",
            (assigned[len(EXISTING_FIELDS)],),
        ).fetchone()

    # the currency is part of the amount, the text does not name one
    assert all(
        "{amount}" in text and "EUR" not in text
        for text in json.loads(balance_text).values()
    )
    assert None not in assigned
    assert sorted(assigned) == sorted(templates)
    pgp_subject = json.loads(templates[assigned[-1]])
    assert pgp_subject["en"] == "Your PGP key expires soon"
    assert pgp_subject["de"] == "Dein PGP-Schlüssel läuft bald ab"
