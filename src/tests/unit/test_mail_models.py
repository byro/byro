import pytest

from byro.mails.models import EMail
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
def test_mail_cannot_send_sent_mail(sent_email):
    with pytest.raises(Exception):
        sent_email.send()


@pytest.mark.django_db
def test_mail_can_copy_to_draft(sent_email):
    count = EMail.objects.count()
    assert sent_email.sent is not None
    new_mail = sent_email.copy_to_draft()
    assert new_mail.subject == sent_email.subject
    assert new_mail.to == sent_email.to
    assert new_mail.sent is None
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
