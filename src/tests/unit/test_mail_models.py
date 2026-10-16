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


# Behaviour preservation: the runtime defaults keep the texts these mails had
# before they became templates. Only the balance reminder no longer names a
# currency, the amount brings the configured one.
@pytest.mark.parametrize(
    "value,expected",
    (
        (default.BALANCE_REMINDER_SUBJECT, "Outstanding membership fees"),
        (
            default.BALANCE_REMINDER_TEXT,
            """Hello {name},

we wanted to let you know that within the time from {start}
to {end} you incurred unpaid liabilities in the amount of

   {amount}

Please settle this amount as soon as possible, or let us
know if you think this email is incorrect.""",
        ),
        (default.DOCUMENT_DELIVERY_SUBJECT, "[{association}] Your document"),
        (
            default.DOCUMENT_DELIVERY_TEXT,
            """Hi, {name},

Please find attached a document we wanted to send you/that you requested.

Thank you,
{association}""",
        ),
        (default.PGP_EXPIRY_REMINDER_SUBJECT, "Your PGP key expires soon"),
        (
            default.PGP_EXPIRY_REMINDER_TEXT,
            "Hello {name},\n\n"
            "the PGP key stored for your membership expires on {date}. "
            "Please send us an updated public key before it expires.\n",
        ),
    ),
)
def test_default_mail_texts_keep_their_english_wording(value, expected):
    assert value.localize("en") == expected


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
