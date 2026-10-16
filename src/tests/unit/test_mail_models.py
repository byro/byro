import pytest

from byro.mails import default
from byro.mails.models import EMail, MailTemplate
from byro.mails.send import SendMailException


@pytest.mark.django_db
@pytest.mark.parametrize("skip_queue", (True, False))
def test_template_to_mail(mail_template, skip_queue):
    count = EMail.objects.count()
    mail_template.to_mail("test@localhost", skip_queue=skip_queue)
    assert EMail.objects.count() == count + 1
    obj = EMail.objects.last()
    assert obj.subject == mail_template.subject
    assert obj.text == mail_template.text
    assert obj.to == "test@localhost"
    assert (obj.sent is None) is not skip_queue
    assert str(mail_template) == mail_template.subject


@pytest.mark.django_db
def test_template_to_mail_fail(mail_template):
    mail_template.subject = "{incorrect_key}"
    count = EMail.objects.count()
    with pytest.raises(SendMailException):
        mail_template.to_mail("test@localhost")
    assert EMail.objects.count() == count


@pytest.mark.django_db
@pytest.mark.parametrize("text", ("{", "{0}", "{name.missing}", "{name:%Y}"))
def test_template_to_mail_fails_for_every_formatting_error(mail_template, text):
    mail_template.text = text
    count = EMail.objects.count()
    with pytest.raises(SendMailException):
        mail_template.to_mail("test@localhost", context={"name": "Jona"})
    assert EMail.objects.count() == count


@pytest.mark.django_db
def test_template_to_mail_uses_an_explicit_subject_without_rendering_the_template(
    mail_template,
):
    mail_template.subject = "{incorrect_key}"
    mail_template.text = "Hello {name}"
    mail_template.save()

    mail = mail_template.to_mail(
        "test@localhost", context={"name": "Jona"}, subject="Explicit {subject}"
    )

    mail.refresh_from_db()
    assert mail.subject == "Explicit {subject}"
    assert mail.text == "Hello Jona"
    assert mail.template == mail_template


@pytest.mark.django_db
def test_template_to_mail_uses_an_explicit_text_without_rendering_the_template(
    mail_template,
):
    mail_template.subject = "Hello {name}"
    mail_template.text = "{incorrect_key}"
    mail_template.save()

    mail = mail_template.to_mail(
        "test@localhost", context={"name": "Jona"}, text="Explicit {text}"
    )

    mail.refresh_from_db()
    assert mail.subject == "Hello Jona"
    assert mail.text == "Explicit {text}"


@pytest.mark.django_db
def test_unsaved_template_creates_a_mail_without_template(configuration):
    template = MailTemplate(subject="Hello {name}", text="Text for {name}")

    mail = template.to_mail("test@localhost", context={"name": "Jona"})

    mail.refresh_from_db()
    assert mail.template is None
    assert mail.subject == "Hello Jona"
    assert mail.text == "Text for Jona"


DEFAULT_TEXTS = (
    (
        "WELCOME_MEMBER_SUBJECT",
        "Welcome to {name}",
        "Willkommen bei {name}",
    ),
    (
        "WELCOME_MEMBER_TEXT",
        "Hello {member_name},\n\n"
        "Welcome to {name}! Your member number is {number}.\n\n"
        "If you have questions about your membership fees or want to update your "
        "details, please contact us at {contact}.\n\n"
        "{additional_information}",
        "Hallo {member_name},\n\n"
        "willkommen bei {name}! Deine Mitgliedsnummer ist {number}.\n\n"
        "Wenn du Fragen zu deinen Mitgliedsbeiträgen hast oder sich deine Daten "
        "ändern, schreib uns bitte an {contact}.\n\n"
        "{additional_information}",
    ),
    (
        "WELCOME_OFFICE_SUBJECT",
        "[byro] New member: {member_name}",
        "[byro] Neues Mitglied: {member_name}",
    ),
    (
        "WELCOME_OFFICE_TEXT",
        "A new member has been added: {member_name}\n\n{additional_information}",
        "Ein neues Mitglied wurde angelegt: {member_name}\n\n{additional_information}",
    ),
    (
        "LEAVE_MEMBER_SUBJECT",
        "End of your membership",
        "Ende deiner Mitgliedschaft",
    ),
    (
        "LEAVE_MEMBER_TEXT",
        "Hello {member_name},\n\n"
        "Your membership in {name} ends on {end}.\n\n"
        "{additional_information}",
        "Hallo {member_name},\n\n"
        "deine Mitgliedschaft bei {name} endet am {end}.\n\n"
        "{additional_information}",
    ),
    (
        "LEAVE_MEMBER_OFFICE_SUBJECT",
        "[byro] End of membership: {member_name}",
        "[byro] Ende der Mitgliedschaft: {member_name}",
    ),
    (
        "LEAVE_MEMBER_OFFICE_TEXT",
        "The membership of {member_name} ends on {end}.\n\n{additional_information}",
        "Die Mitgliedschaft von {member_name} endet am {end}.\n\n"
        "{additional_information}",
    ),
    (
        "RECORD_DISCLOSURE_SUBJECT",
        "Your data at {association_name} (member number {number})",
        "Deine Daten bei {association_name} (Mitgliedsnummer {number})",
    ),
    (
        "RECORD_DISCLOSURE_TEXT",
        "Hello,\n\n"
        "This is an overview of the data {association_name} currently stores about "
        "you and your membership.\n\n"
        "Your current balance is {balance}. A negative balance means that fees are "
        "outstanding.\n\n"
        "{data}\n\n"
        "If anything is outdated or incorrect, please reply to this email and let us "
        "know.",
        "Hallo,\n\n"
        "hier ist eine Übersicht der Daten, die {association_name} aktuell über dich "
        "und deine Mitgliedschaft gespeichert hat.\n\n"
        "Dein aktueller Kontostand beträgt {balance}. Ein negativer Betrag bedeutet, "
        "dass Beiträge offen sind.\n\n"
        "{data}\n\n"
        "Wenn etwas veraltet oder falsch ist, antworte bitte einfach auf diese E-Mail.",
    ),
    (
        "BALANCE_REMINDER_SUBJECT",
        "Outstanding membership fees",
        "Offene Mitgliedsbeiträge",
    ),
    (
        "BALANCE_REMINDER_TEXT",
        "Hello {name},\n\n"
        "According to our records, membership fees for the period from {start} to "
        "{end} are still outstanding:\n\n"
        "    {amount}\n\n"
        "Please pay this amount as soon as possible. If you think this is a mistake, "
        "please reply to this email.",
        "Hallo {name},\n\n"
        "laut unseren Unterlagen sind für den Zeitraum vom {start} bis {end} noch "
        "Mitgliedsbeiträge offen:\n\n"
        "    {amount}\n\n"
        "Bitte zahle den Betrag so bald wie möglich. Falls du denkst, dass hier ein "
        "Fehler vorliegt, antworte bitte auf diese E-Mail.",
    ),
    (
        "DOCUMENT_DELIVERY_SUBJECT",
        "Your document from {association}",
        "Dein Dokument von {association}",
    ),
    (
        "DOCUMENT_DELIVERY_TEXT",
        "Hello,\n\nA document from {association} is attached to this email.",
        "Hallo,\n\nim Anhang dieser E-Mail findest du ein Dokument von {association}.",
    ),
    (
        "PGP_EXPIRY_REMINDER_SUBJECT",
        "Your PGP key expires soon",
        "Dein PGP-Schlüssel läuft bald ab",
    ),
    (
        "PGP_EXPIRY_REMINDER_TEXT",
        "Hello {name},\n\n"
        "The PGP key stored for your membership expires on {date}. "
        "Please send us an updated public key before it expires.",
        "Hallo {name},\n\n"
        "der für deine Mitgliedschaft gespeicherte PGP-Schlüssel läuft am {date} ab. "
        "Bitte sende uns vor Ablauf einen aktualisierten öffentlichen Schlüssel.",
    ),
)


# The member mails end without a greeting, the footer adds it. Portuguese has
# no translation of these texts yet and uses the English ones.
@pytest.mark.parametrize("name,en,de", DEFAULT_TEXTS, ids=[t[0] for t in DEFAULT_TEXTS])
def test_default_mail_texts(name, en, de):
    value = getattr(default, name)
    assert value.localize("en") == en
    assert value.localize("de") == de
    assert value.localize("pt-br") == en


@pytest.mark.django_db
def test_mail_cannot_send_sent_mail(sent_email):
    with pytest.raises(TypeError):
        sent_email.send()


@pytest.mark.django_db
def test_mail_can_copy_to_draft(sent_email):
    count = EMail.objects.count()
    assert sent_email.sent is not None
    new_mail = sent_email.copy_to_draft()
    assert new_mail.subject == sent_email.subject
    assert new_mail.to == sent_email.to
    assert new_mail.sent is None
    assert new_mail.delivered_to == []
    assert new_mail.delivered_to_members == {}
    assert new_mail.pk != sent_email.pk
    assert EMail.objects.count() == count + 1


@pytest.mark.django_db
def test_mail_can_send_regular_mail(email):
    assert email.sent is None
    email.send()
    email.refresh_from_db()
    assert email.sent is not None


@pytest.mark.django_db
def test_attachment_ids(email):
    assert email.attachment_ids == []
