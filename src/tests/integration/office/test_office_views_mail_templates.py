"""Editing mail templates refuses placeholders they cannot be rendered with."""

import html

import pytest
from django.conf import settings
from django.db import models
from django.shortcuts import reverse
from django.utils.translation import override

from byro.common.models import Configuration
from byro.mails import default
from byro.mails.models import MailTemplate
from byro.mails.placeholders import CORE_TEMPLATE_CONTEXTS, check_template_text

DEFAULT_TEXTS = {
    "welcome_member_template": ("WELCOME_MEMBER_SUBJECT", "WELCOME_MEMBER_TEXT"),
    "welcome_office_template": ("WELCOME_OFFICE_SUBJECT", "WELCOME_OFFICE_TEXT"),
    "leave_member_template": ("LEAVE_MEMBER_SUBJECT", "LEAVE_MEMBER_TEXT"),
    "leave_office_template": (
        "LEAVE_MEMBER_OFFICE_SUBJECT",
        "LEAVE_MEMBER_OFFICE_TEXT",
    ),
    "record_disclosure_template": (
        "RECORD_DISCLOSURE_SUBJECT",
        "RECORD_DISCLOSURE_TEXT",
    ),
    "balance_reminder_template": ("BALANCE_REMINDER_SUBJECT", "BALANCE_REMINDER_TEXT"),
    "document_delivery_template": (
        "DOCUMENT_DELIVERY_SUBJECT",
        "DOCUMENT_DELIVERY_TEXT",
    ),
    "pgp_expiry_reminder_template": (
        "PGP_EXPIRY_REMINDER_SUBJECT",
        "PGP_EXPIRY_REMINDER_TEXT",
    ),
}


def field_input(field):
    """i18nfield numbers the inputs by the position of the language in
    ``settings.LANGUAGES``, and the form shows only the office language."""
    codes = [code for code, _name in settings.LANGUAGES]
    return f"{field}_{codes.index(Configuration.get_solo().language)}"


def post_template(client, template, subject, text):
    url = (
        reverse("office:mails.templates.view", kwargs={"pk": template.pk})
        if template
        else reverse("office:mails.templates.add")
    )
    return client.post(
        url, {field_input("subject"): subject, field_input("text"): text}
    )


def use_template(field, template):
    config = Configuration.get_solo()
    config.language = "en"
    setattr(config, field, template)
    config.save()


def test_every_configured_template_has_its_placeholders():
    fields = {
        field.name
        for field in Configuration._meta.get_fields()
        if isinstance(field, models.ForeignKey) and field.related_model is MailTemplate
    }
    assert fields == set(CORE_TEMPLATE_CONTEXTS)


@pytest.mark.parametrize("field", sorted(DEFAULT_TEXTS))
@pytest.mark.parametrize("language", [code for code, _name in settings.LANGUAGES])
def test_default_texts_pass_the_check(field, language):
    with override(language):
        for name in DEFAULT_TEXTS[field]:
            check_template_text(
                str(getattr(default, name)), CORE_TEMPLATE_CONTEXTS[field]
            )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "text,message",
    (
        ("Dear {nmae}", "Unknown placeholder: {nmae}. Available placeholders:"),
        ("Dear {name.first}", "The text contains an invalid placeholder."),
        ("Dear {name", "The text contains an invalid placeholder."),
        ("Pay {amount:%d}", "The text contains an invalid placeholder."),
    ),
)
def test_invalid_placeholders_are_refused(
    configuration, superuser_client, mail_template, text, message
):
    use_template("balance_reminder_template", mail_template)

    response = post_template(superuser_client, mail_template, "Please pay", text)

    assert response.status_code == 200
    content = html.unescape(response.content.decode())
    assert message in content
    assert "{name}, {start}, {end}, {amount}" in content
    mail_template.refresh_from_db()
    assert str(mail_template.text) == "Hi!\nThis is just a test mail.\nThe robo clerk"


@pytest.mark.django_db
def test_the_subject_is_checked_too(configuration, superuser_client, mail_template):
    use_template("pgp_expiry_reminder_template", mail_template)

    response = post_template(superuser_client, mail_template, "For {nmae}", "Hi")

    assert response.status_code == 200
    content = html.unescape(response.content.decode())
    assert "Unknown placeholder: {nmae}. Available placeholders: {name}, {date}" in (
        content
    )


@pytest.mark.django_db
def test_the_balance_reminder_subject_is_sent_as_written(
    configuration, superuser_client, mail_template
):
    use_template("balance_reminder_template", mail_template)

    response = post_template(superuser_client, mail_template, "Fees {2026", "Hi")

    assert response.status_code == 302
    mail_template.refresh_from_db()
    assert str(mail_template.subject) == "Fees {2026"


@pytest.mark.django_db
def test_format_specifications_of_the_context_are_allowed(
    configuration, superuser_client, mail_template
):
    use_template("leave_member_template", mail_template)
    text = "Dear {member_name}, your membership ends on {end:%d.%m.%Y}. {{braces}}"

    response = post_template(superuser_client, mail_template, "Bye {name}", text)

    assert response.status_code == 302
    mail_template.refresh_from_db()
    assert str(mail_template.text) == text


@pytest.mark.django_db
def test_a_template_in_two_settings_needs_the_placeholders_of_both(
    configuration, superuser_client, mail_template
):
    use_template("welcome_member_template", mail_template)
    use_template("welcome_office_template", mail_template)

    response = post_template(superuser_client, mail_template, "New", "No. {number}")

    assert response.status_code == 200
    content = html.unescape(response.content.decode())
    assert "Unknown placeholder: {number}." in content


@pytest.mark.django_db
@pytest.mark.parametrize("existing", (True, False))
def test_other_templates_only_need_valid_syntax(
    configuration, superuser_client, mail_template, existing
):
    use_template("balance_reminder_template", None)
    template = mail_template if existing else None

    accepted = post_template(superuser_client, template, "Hi", "Dear {anyone}")
    refused = post_template(superuser_client, template, "Hi", "Dear {anyone")

    assert accepted.status_code == 302
    assert refused.status_code == 200
    assert "The text contains an invalid placeholder." in html.unescape(
        refused.content.decode()
    )
