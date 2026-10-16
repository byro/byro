"""``common.0027`` gives the eight core mail templates their reworked default
texts, as long as nobody changed them."""

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

from byro.mails import default

SRC_DIR = os.path.join(os.path.dirname(__file__), "..", "..")

DATA_MIGRATION = ("common", "0027_core_mail_default_texts")
DEFAULTS = {
    "welcome_member_template": "WELCOME_MEMBER",
    "welcome_office_template": "WELCOME_OFFICE",
    "leave_member_template": "LEAVE_MEMBER",
    "leave_office_template": "LEAVE_MEMBER_OFFICE",
    "record_disclosure_template": "RECORD_DISCLOSURE",
    "balance_reminder_template": "BALANCE_REMINDER",
    "document_delivery_template": "DOCUMENT_DELIVERY",
    "pgp_expiry_reminder_template": "PGP_EXPIRY_REMINDER",
}

data_migration = importlib.import_module(
    "byro.common.migrations.0027_core_mail_default_texts"
)
TEMPLATES = data_migration.TEMPLATES

OLD_WELCOME_OFFICE = {
    "subject": {
        "en": "[byro] New member",
        "de": "[byr] Neues Mitglied",
        "pt-br": "[byro] Nova pessoa associada",
    },
    "text": {
        "en": "Hi,\n\nwe have a new member: {member_name}\n\n"
        "{additional_information}\n\nThanks,\nthe robo clerk",
        "de": "Hi,\n\nwir haben ein neues Mitglied: {member_name}\n\n"
        "{additional_information}\n\nDanke\nDas Helferlein",
        "pt-br": "Olá,\n\ntemos uma nova pessoa associada: {member_name}\n\n"
        "{additional_information}\n\nObrigado,\no robo escriturário",
    },
}
NEW_WELCOME_OFFICE_EN = {
    "subject": "[byro] New member: {member_name}",
    "text": "A new member has been added: {member_name}\n\n{additional_information}",
}
NEW_WELCOME_OFFICE = {
    "subject": {
        "en": NEW_WELCOME_OFFICE_EN["subject"],
        "de": "[byro] Neues Mitglied: {member_name}",
        "pt-br": NEW_WELCOME_OFFICE_EN["subject"],
    },
    "text": {
        "en": NEW_WELCOME_OFFICE_EN["text"],
        "de": "Ein neues Mitglied wurde angelegt: {member_name}\n\n"
        "{additional_information}",
        "pt-br": NEW_WELCOME_OFFICE_EN["text"],
    },
}


@pytest.fixture
def historical_apps():
    return MigrationLoader(connection).project_state(DATA_MIGRATION).apps


def assigned(apps, field):
    Configuration = apps.get_model("common", "Configuration")
    MailTemplate = apps.get_model("mails", "MailTemplate")
    config = Configuration.objects.get()
    return MailTemplate.objects.get(pk=getattr(config, f"{field}_id"))


def store(template, subject, text):
    template.subject = subject
    template.text = text
    template.save()


def texts(template):
    template.refresh_from_db()
    return {"subject": template.subject.data, "text": template.text.data}


@pytest.mark.django_db
def test_unchanged_template_gets_the_new_texts(historical_apps):
    template = assigned(historical_apps, "welcome_office_template")
    store(template, **OLD_WELCOME_OFFICE)

    data_migration.update_templates(historical_apps, None)

    assert texts(template) == NEW_WELCOME_OFFICE


@pytest.mark.django_db
@pytest.mark.parametrize("field", DEFAULTS)
def test_every_unchanged_core_template_gets_the_new_texts(historical_apps, field):
    template = assigned(historical_apps, field)
    store(template, **TEMPLATES[field]["old"])

    data_migration.update_templates(historical_apps, None)

    new = TEMPLATES[field]["new"]
    assert texts(template) == new
    # Portuguese has no translation of the new texts and uses the English ones
    assert new["subject"]["pt-br"] == new["subject"]["en"]
    assert new["text"]["pt-br"] == new["text"]["en"]


@pytest.mark.django_db
def test_changed_portuguese_text_is_kept(historical_apps):
    template = assigned(historical_apps, "welcome_office_template")
    text = dict(OLD_WELCOME_OFFICE["text"], **{"pt-br": "Nova pessoa: {member_name}"})
    store(template, OLD_WELCOME_OFFICE["subject"], text)

    data_migration.update_templates(historical_apps, None)

    result = texts(template)
    assert result["subject"]["pt-br"] == "[byro] Nova pessoa associada"
    assert result["text"]["pt-br"] == "Nova pessoa: {member_name}"
    for language in ("en", "de"):
        assert result["subject"][language] == NEW_WELCOME_OFFICE["subject"][language]
        assert result["text"][language] == NEW_WELCOME_OFFICE["text"][language]


@pytest.mark.django_db
def test_changed_language_is_kept_and_the_others_get_the_new_texts(
    historical_apps,
):
    template = assigned(historical_apps, "welcome_office_template")
    text = dict(OLD_WELCOME_OFFICE["text"], de="Neu: {member_name}", fr="Nouveau")
    store(template, OLD_WELCOME_OFFICE["subject"], text)

    data_migration.update_templates(historical_apps, None)

    result = texts(template)
    assert result["subject"]["de"] == "[byr] Neues Mitglied"
    assert result["text"]["de"] == "Neu: {member_name}"
    assert result["text"]["fr"] == "Nouveau"
    for language in ("en", "pt-br"):
        assert result["subject"][language] == NEW_WELCOME_OFFICE["subject"][language]
        assert result["text"][language] == NEW_WELCOME_OFFICE["text"][language]


@pytest.mark.django_db
def test_changed_subject_keeps_the_text_of_that_language(historical_apps):
    template = assigned(historical_apps, "welcome_office_template")
    subject = dict(OLD_WELCOME_OFFICE["subject"], en="New member!")
    store(template, subject, OLD_WELCOME_OFFICE["text"])

    data_migration.update_templates(historical_apps, None)

    result = texts(template)
    assert result["subject"]["en"] == "New member!"
    assert result["text"]["en"] == OLD_WELCOME_OFFICE["text"]["en"]
    assert result["text"]["de"] == NEW_WELCOME_OFFICE["text"]["de"]


@pytest.mark.django_db
def test_text_saved_with_crlf_line_breaks_gets_the_new_text(historical_apps):
    template = assigned(historical_apps, "welcome_office_template")
    text = {
        language: value.replace("\n", "\r\n")
        for language, value in OLD_WELCOME_OFFICE["text"].items()
    }
    store(template, OLD_WELCOME_OFFICE["subject"], text)

    data_migration.update_templates(historical_apps, None)

    assert texts(template) == NEW_WELCOME_OFFICE


@pytest.mark.django_db
def test_value_stored_as_plain_text_gets_the_new_text_of_its_language(
    historical_apps,
):
    template = assigned(historical_apps, "welcome_office_template")
    store(
        template,
        OLD_WELCOME_OFFICE["subject"]["de"],
        OLD_WELCOME_OFFICE["text"]["de"],
    )

    data_migration.update_templates(historical_apps, None)

    assert texts(template) == {
        "subject": NEW_WELCOME_OFFICE["subject"]["de"],
        "text": NEW_WELCOME_OFFICE["text"]["de"],
    }


@pytest.mark.django_db
def test_templates_that_are_not_assigned_are_not_changed(historical_apps):
    MailTemplate = historical_apps.get_model("mails", "MailTemplate")
    Configuration = historical_apps.get_model("common", "Configuration")
    other = MailTemplate.objects.create(**OLD_WELCOME_OFFICE)
    config = Configuration.objects.get()
    unassigned = config.welcome_office_template
    store(unassigned, **OLD_WELCOME_OFFICE)
    config.welcome_office_template = None
    config.save()

    data_migration.update_templates(historical_apps, None)

    assert texts(other) == OLD_WELCOME_OFFICE
    assert texts(unassigned) == OLD_WELCOME_OFFICE


@pytest.mark.django_db
def test_second_run_changes_nothing(historical_apps):
    template = assigned(historical_apps, "welcome_office_template")
    text = dict(OLD_WELCOME_OFFICE["text"], de="Neu: {member_name}")
    store(template, OLD_WELCOME_OFFICE["subject"], text)
    data_migration.update_templates(historical_apps, None)
    first = texts(template)

    data_migration.update_templates(historical_apps, None)

    assert texts(template) == first


@pytest.mark.django_db
def test_migration_does_not_depend_on_the_runtime_defaults(
    historical_apps, monkeypatch
):
    template = assigned(historical_apps, "welcome_office_template")
    store(template, **OLD_WELCOME_OFFICE)
    monkeypatch.setitem(
        sys.modules, "byro.mails.default", types.ModuleType("byro.mails.default")
    )
    # ``from byro.mails import default`` would now find the empty module
    monkeypatch.delattr("byro.mails.default", raising=False)

    data_migration.update_templates(historical_apps, None)

    assert texts(template) == NEW_WELCOME_OFFICE


# The frozen texts are the defaults byro ships with this migration. A later
# change of the defaults needs a migration of its own.
@pytest.mark.parametrize("field", DEFAULTS)
def test_frozen_new_texts_are_the_runtime_defaults(field):
    for part in ("subject", "text"):
        value = getattr(default, f"{DEFAULTS[field]}_{part.upper()}")
        frozen = TEMPLATES[field]["new"][part]
        assert value.localize("en") == frozen["en"]
        assert value.localize("de") == frozen["de"]
        assert value.localize("pt-br") == frozen["pt-br"]


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


def test_fresh_installation_has_the_new_default_texts(tmp_path):
    database = tmp_path / "db.sqlite3"
    migrate(database)

    columns = ", ".join(f"{field}_id" for field in DEFAULTS)
    with sqlite3.connect(database) as db:
        (ids,) = db.execute(f"SELECT {columns} FROM common_configuration")
        stored = {
            pk: {"subject": json.loads(subject), "text": json.loads(text)}
            for pk, subject, text in db.execute(
                "SELECT id, subject, text FROM mails_mailtemplate"
            )
        }

    for field, pk in zip(DEFAULTS, ids):
        assert stored[pk] == TEMPLATES[field]["new"], field
