import logging
from smtplib import SMTPRecipientsRefused, SMTPSenderRefused
from typing import Any, Dict, Union

from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.mail.backends.smtp import EmailBackend
from django.utils.translation import override
from i18nfield.strings import LazyI18nString

from byro.common.models import Configuration

logger = logging.getLogger(__name__)


class CustomSMTPBackend(EmailBackend):
    def test(self, from_addr):
        try:
            self.open()
            self.connection.ehlo_or_helo_if_needed()
            self.connection.rcpt("test@example.org")
            (code, resp) = self.connection.mail(from_addr, [])
            if code != 250:
                logger.warning(
                    "Error testing mail settings, code %d, resp: %s" % (code, resp)
                )
                raise SMTPSenderRefused(code, resp, from_addr)
            senderrs = {}
            (code, resp) = self.connection.rcpt("test@example.com")
            if (code != 250) and (code != 251):
                logger.warning(
                    "Error testing mail settings, code %d, resp: %s" % (code, resp)
                )
                raise SMTPRecipientsRefused(senderrs)
        finally:
            self.close()


class TolerantDict(dict):
    def __missing__(self, key):
        return key


class SendMailException(Exception):
    pass


def mail(
    email: str,
    subject: str,
    template: Union[str, LazyI18nString],
    context: Dict[str, Any] = None,
    locale: str = None,
    headers: dict = None,
):
    headers = headers or {}
    c = Configuration.get_solo()
    locale = locale or c.language

    with override(locale):
        body = str(template)
        if context:
            body = body.format_map(TolerantDict(context))

        sender = Configuration.get_solo().mail_from
        subject = str(subject)
        body_plain = body
        return mail_send_task.apply_async(
            args=([email], subject, body_plain, sender, headers)
        )


def mail_send_task(
    to: str,
    subject: str,
    body: str,
    sender: str,
    html: str = None,
    cc: list = None,
    bcc: list = None,
    headers: dict = None,
    attachments: list = None,
):
    email = EmailMultiAlternatives(
        subject, body, sender, to=to, cc=cc, bcc=bcc, headers=headers
    )
    if html is not None:
        email.attach_alternative(inline_css(html), "text/html")
    if attachments:
        from byro.documents.models import Document

        for attachment in attachments:
            email.attach_file(Document.objects.get(pk=attachment).document.path)
    backend = get_connection(fail_silently=False)

    try:
        backend.send_messages([email])
    except Exception:
        logger.exception("Error sending email")
        raise SendMailException("Failed to send an email to {}.".format(to))
