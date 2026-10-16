"""Editing the footer of mails to members in the general settings."""

import html
import re

import pytest
from django.conf import settings
from django.shortcuts import reverse

from byro.common.models import Configuration, LogEntry
from byro.mails.models import EMail

SETTINGS_POST_DATA = {
    "Configuration-currency_symbol": "€",
    "Configuration-currency_postfix": "on",
    "Configuration-display_cents": "on",
    "Configuration-liability_interval": "36",
    "Configuration-default_order_name": "last",
    "Configuration-default_direct_address_name": "first",
    "PGPConfiguration-missing_key_policy": "send_plain",
    "PGPConfiguration-invalid_key_policy": "block",
    "PGPConfiguration-unverified_key_policy": "block",
    "PGPConfiguration-expired_key_policy": "block",
    "PGPConfiguration-key_refresh_interval_days": "1",
    "PGPConfiguration-keyserver_timeout_seconds": "30",
    "PGPConfiguration-expiry_reminder_days": "30",
    "MFAConfiguration-policy": "optional",
    "MFAConfiguration-account_label": "{association} - {username}",
}
MIGRATED = {
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


def footer_input(language):
    """The name of the text area of ``language``: i18nfield numbers them by
    their position in ``settings.LANGUAGES``."""
    codes = [code for code, _name in settings.LANGUAGES]
    return f"Configuration-member_mail_footer_{codes.index(language)}"


def use_language(language, footer="unchanged"):
    config = Configuration.get_solo()
    config.language = language
    if footer != "unchanged":
        config.member_mail_footer = footer
    config.save()
    return config


def shown_footer(client, language):
    content = client.get(reverse("office:settings.base")).content.decode()
    match = re.search(
        r'<textarea[^>]*name="%s"[^>]*>(.*?)</textarea>' % footer_input(language),
        content,
        re.DOTALL,
    )
    assert match, "no footer text area for " + language
    # Django puts a line break after the opening tag, browsers drop it
    return html.unescape(match.group(1)).removeprefix("\n")


def post_settings(client, footer, language, **changes):
    config = Configuration.get_solo()
    data = {
        **SETTINGS_POST_DATA,
        "Configuration-name": config.name,
        "Configuration-mail_from": config.mail_from,
        "Configuration-backoffice_mail": config.backoffice_mail,
        "Configuration-language": language,
        footer_input(language): footer,
        **changes,
    }
    return client.post(reverse("office:settings.base"), data)


def settings_log_entry():
    config = Configuration.get_solo()
    entries = LogEntry.objects.filter(action_type="byro.settings.changed")
    return [
        entry for entry in entries.order_by("pk") if entry.content_object == config
    ][-1]


def stored_footer():
    return Configuration.get_solo().member_mail_footer.data


@pytest.mark.django_db
@pytest.mark.parametrize("language", ("en", "de"))
def test_settings_show_the_footer_in_the_language_of_the_organization(
    configuration, superuser_client, language
):
    use_language(language)

    content = superuser_client.get(reverse("office:settings.base")).content.decode()

    assert shown_footer(superuser_client, language) == MIGRATED[language]
    other = "de" if language == "en" else "en"
    assert f'name="{footer_input(other)}"' not in content
    assert "{member_page_url}" in content  # the help text names the placeholders


@pytest.mark.django_db
def test_settings_show_the_built_in_default_for_null(configuration, superuser_client):
    use_language("de", footer=None)

    assert shown_footer(superuser_client, "de") == MIGRATED["de"]


@pytest.mark.django_db
@pytest.mark.parametrize("stored", ("migrated", "null", "custom"))
def test_saving_other_settings_keeps_the_footer(
    configuration, superuser_client, stored
):
    footers = {"migrated": "unchanged", "null": None, "custom": {"de": "Ciao"}}
    use_language("de", footer=footers[stored])
    before = stored_footer()
    # posted as a browser does: the text that was shown, with CRLF line breaks
    shown = shown_footer(superuser_client, "de").replace("\n", "\r\n")

    response = post_settings(
        superuser_client, shown, "de", **{"Configuration-currency_symbol": "EUR"}
    )

    assert response.status_code == 302
    config = Configuration.get_solo()
    assert config.currency_symbol == "EUR"
    assert config.member_mail_footer.data == before
    entry = settings_log_entry()
    assert "member_mail_footer" not in entry.data["changes"]


@pytest.mark.django_db
def test_editing_one_language_keeps_the_other_languages(
    configuration, superuser_client
):
    use_language("de")

    response = post_settings(superuser_client, "Tschüss\r\n{association_name}", "de")

    assert response.status_code == 302
    assert stored_footer() == {
        **MIGRATED,
        "de": "Tschüss\n{association_name}",
    }
    entry = settings_log_entry()
    assert entry.data["changes"]["member_mail_footer"] == [
        MIGRATED,
        {**MIGRATED, "de": "Tschüss\n{association_name}"},
    ]


@pytest.mark.django_db
def test_editing_the_built_in_default_keeps_it_for_the_other_languages(
    configuration, superuser_client
):
    use_language("de", footer=None)

    response = post_settings(superuser_client, "Tschüss", "de")

    assert response.status_code == 302
    assert stored_footer() == {**MIGRATED, "de": "Tschüss"}
    changes = settings_log_entry().data["changes"]
    # the log stores None as text, as for every other setting
    assert changes["member_mail_footer"] == ["None", {**MIGRATED, "de": "Tschüss"}]


@pytest.mark.django_db
@pytest.mark.parametrize("stored", ("migrated", "null"))
def test_emptying_the_footer_turns_it_off_in_every_language(
    configuration, superuser_client, member, mailoutbox, stored
):
    use_language("de", footer=None if stored == "null" else "unchanged")

    response = post_settings(superuser_client, "  \r\n ", "de")

    assert response.status_code == 302
    assert stored_footer() == {}
    use_language("en")
    mail = EMail.for_member(member, subject="Test", text="Text")
    mail.save()
    mail.send()
    assert mailoutbox[0].body == "Text"
    assert shown_footer(superuser_client, "en") == ""


@pytest.mark.django_db
@pytest.mark.parametrize(
    "footer,message",
    (
        ("Hi {nmae}", "Unknown placeholder: {nmae}. Available placeholders:"),
        ("{association.name}", "Unknown placeholder: {association}."),
        ("Hi {", "The text contains an invalid placeholder."),
        ("{association_name:%d}", "The text contains an invalid placeholder."),
    ),
)
def test_invalid_footer_is_refused(configuration, superuser_client, footer, message):
    use_language("en")
    before = stored_footer()

    response = post_settings(superuser_client, footer, "en")

    assert response.status_code == 200
    content = html.unescape(response.content.decode())
    assert message in content
    assert (
        "{association_name}, {association_address}, {association_url}, "
        "{member_page_url}" in content
    )
    assert stored_footer() == before


@pytest.mark.django_db
def test_outbox_reports_an_invalid_footer(
    configuration, member, logged_in_client, mailoutbox
):
    use_language("en", footer={"en": "{nmae}"})
    mail = EMail.for_member(member, subject="Test", text="Text")
    mail.save()

    response = logged_in_client.get(reverse("office:mails.outbox.send"), follow=True)

    assert response.status_code == 200
    messages = [str(message) for message in response.context["messages"]]
    assert any("footer of mails to members" in message for message in messages)
    assert mailoutbox == []
    mail.refresh_from_db()
    assert mail.sent is None


@pytest.mark.django_db
def test_office_sends_the_footer_in_the_language_of_the_organization(
    configuration, member, logged_in_client, mailoutbox, settings
):
    settings.DEFAULT_LANGUAGE = "en"
    use_language("de")
    mail = EMail.for_member(member, subject="Test", text="Text")
    mail.save()

    response = logged_in_client.get(
        reverse("office:mails.mail.send", kwargs={"pk": mail.pk})
    )

    assert response.status_code == 302
    assert mailoutbox[0].body == (
        "Text\n\nViele Grüße\nDeine Mitgliedsverwaltung\n\n-- \nAssociation Name"
    )
