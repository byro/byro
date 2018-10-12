import logging
from smtplib import SMTPRecipientsRefused, SMTPSenderRefused
from typing import Any, Dict, Union

from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.mail.backends.smtp import EmailBackend
from django.utils.translation import override
from i18nfield.strings import LazyI18nString

from byro.common.models import Configuration
from django.http import HttpResponse
import gpg
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from django.core.mail import SafeMIMEMultipart
from email.mime.nonmultipart import MIMENonMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import make_msgid
from email.encoders import encode_noop
from email.charset import Charset, QP


import smtplib
from django.conf import settings

logger = logging.getLogger(__name__)


class CustomSMTPBackend(EmailBackend):

    def test(self, from_addr):
        try:
            self.open()
            self.connection.ehlo_or_helo_if_needed()
            self.connection.rcpt("test@example.org")
            (code, resp) = self.connection.mail(from_addr, [])
            if code != 250:
                logger.warning('Error testing mail settings, code %d, resp: %s' % (code, resp))
                raise SMTPSenderRefused(code, resp, from_addr)
            senderrs = {}
            (code, resp) = self.connection.rcpt('test@example.com')
            if (code != 250) and (code != 251):
                logger.warning('Error testing mail settings, code %d, resp: %s' % (code, resp))
                raise SMTPRecipientsRefused(senderrs)
        finally:
            self.close()


class TolerantDict(dict):

    def __missing__(self, key):
        return key


class SendMailException(Exception):
    pass


def mail(email: str, subject: str, template: Union[str, LazyI18nString],
         context: Dict[str, Any] = None, locale: str = None,
         headers: dict = None):
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
        return mail_send_task.apply_async(args=([email], subject, body_plain, sender, headers))


def mail_send_task(
        to: str, subject: str, body: str, sender: str, cc: list = None,
        bcc: list = None, headers: dict = None, attachments: list = None,
):
    email = EmailMultiAlternatives(
        subject, body, sender,
        to=to, cc=cc, bcc=bcc, headers=headers,
    )
    if attachments:
        from byro.documents.models import Document
        for attachment in attachments:
            email.attach_file(Document.objects.get(pk=attachment).document.path)
    backend = get_connection(fail_silently=False)

    try:
        backend.send_messages([email])
    except Exception:
        logger.exception('Error sending email')
        raise SendMailException('Failed to send an email to {}.'.format(to))


def send_pgp_mime_email(subject, sender, recipients, text, html, cc=None, bcc=None, attachments=None, sign_key_id=None,
                        enc_key_ids=None, passphrase_callback=None):
    """
    Sends an encrypted and signed MIME email. It depends on the recipient's MUA if the text or html body is shown, but
    the html body is preferred.

    :param subject: String to be used as subject of email
    :param sender: String of the senders' email address
    :param recipients: List of recipient email addresses as string
    :param cc: List of recipients in copy
    :param bcc: List of recipients in blind copy
    :param text: Text body as string
    :param html: HTML body as string
    :param sign_key_id: Key ID or fingerprint of the key to use for signing. The private key has to be in the local
    keyring and its password might have to be provided.
    :param enc_key_ids: List of key IDs to encrypt the email to. Will be fetched from the keyserver configured in gpg.
    It is recommended to include the sign_key_id also in the list of the enc_key_ids so the sender is able to decrypt
    and read their own email as well, for example inside a sent folder.
    :param attachments: List of attachments as MIMEBase objects.
    :param passphrase_callback: A func(hint, desc, prev_bad) which returns the signing key password.
    :raises gpg.errors.KeyNotFound: The key id format of sign_key_id or enc_key_id is wrong or the key cannot be found.
    In case of the sign_key_id the secret key might be missing from the local keyring.
    :raises gpg.errors.GPGMEError: A general gpg error from the gpgme backend.
    :raises gpg.errors.InvalidRecipients: Some of the keys referenced through enc_key_id are not suitable to encrypt
    with. Maybe the key has been revoked or is expired.
    :raises gpg.errors.InvalidSigners: The key referenced by sign_key_id is not suitable for signing. Maybe the key has
    been revoked or is expired.
    :raises SMTPHeloError: The server didn't reply properly to the helo greeting.
    :raises SMTPRecipientsRefused: The server rejected ALL recipients (no mail was sent).
    :raises SMTPSenderRefused: The server didn't accept the from_addr.
    :raises SMTPDataError: The server replied with an unexpected error code (other than a refusal of a recipient).
    :raises SMTPNotSupportedError: The mail_options parameter includes 'SMTPUTF8' but the SMTPUTF8 extension is not
    supported by the server.
    """

    class MIMEUTF8QP(MIMENonMultipart):
        def __init__(self, payload, _subtype, charset='utf-8'):
            MIMENonMultipart.__init__(self, 'text', _subtype, charset=charset)

            utf8qp = Charset(charset)
            utf8qp.body_encoding = QP
            self.set_payload(payload, charset=utf8qp)

    msg_alt = MIMEMultipart(_subtype='alternative')
    msg_alt.attach(MIMEUTF8QP(text, 'plain'))
    msg_alt.attach(MIMEUTF8QP(html, 'html'))

    msg_att = MIMEMultipart()
    msg_att.attach(msg_alt)
    for attachment in attachments:
        msg_att.attach(attachment)

    msg_final = wrap_mime_in_gpg(mime_object=msg_att, sign_key_id=sign_key_id, enc_key_ids=enc_key_ids,
                                 passphrase_callback=passphrase_callback)

    msg_final['Subject'] = subject
    msg_final['From'] = sender
    msg_final['To'] = ', '.join(recipients)
    if cc:
        msg_final['CC'] = ', '.join(cc)
    if bcc:
        msg_final['BCC'] = ', '.join(bcc)
    msg_final['Message-ID'] = make_msgid(domain=sender.split('@')[-1])

    with smtplib.SMTP() as s:
        s.connect(host=settings.EMAIL_HOST, port=settings.EMAIL_PORT)
        if settings.EMAIL_USE_TLS:
            s.starttls()
        s.login(user=settings.EMAIL_HOST_USER, password=settings.EMAIL_HOST_PASSWORD)
        s.send_message(msg=msg_final, from_addr=sender, to_addrs=recipients)


def wrap_mime_in_gpg(mime_object, sign_key_id=None, enc_key_ids=None, passphrase_callback=None):
    """
    Wraps a MIME message in an OpenPGP encrypted wrapper.

    :param mime_object: Instance of email.mime.base.MIMEBase containing the message to be encrypted
    :param sign_key_id: Key ID of the secret key to use for signing the message.
    :param enc_key_ids: List of the key IDs of the public keys to use to encrypt the message.
    :param passphrase_callback: A func(hint, desc, prev_bad) which returns the signing key password.
    :return:
    :raises gpg.errors.KeyNotFound: The key id format of sign_key_id or enc_key_id is wrong or the key cannot be found.
    In case of the sign_key_id the secret key might be missing from the local keyring.
    :raises gpg.errors.GPGMEError: A general gpg error from the gpgme backend.
    :raises gpg.errors.InvalidRecipients: Some of the keys referenced through enc_key_id are not suitable to encrypt
    with. Maybe the key has been revoked or is expired.
    :raises gpg.errors.InvalidSigners: The key referenced by sign_key_id is not suitable for signing. Maybe the key has
    been revoked or is expired.
    """

    if not isinstance(mime_object, MIMEBase):
        raise ValueError('mimeobject must be an object of a type derived from email.mime.base.MIMEBase')

    if not sign_key_id and not enc_key_ids:
        return mime_object

    with gpg.Context(armor=True, pinentry_mode=gpg.constants.PINENTRY_MODE_LOOPBACK) as c:
        # Set the gpg homedir where the keyring is being stored
        c.set_engine_info(gpg.constants.protocol.OpenPGP, home_dir=settings.GPG_HOME_DIR)

        if sign_key_id:
            if not passphrase_callback:
                raise ValueError('passphrase_callback is needed when signing the email (a sign_key_id is given)')
            # Get password for secret keys through this method
            c.set_passphrase_cb(passphrase_callback)

            # Get signing key from keyring, should be private key
            sign_key = c.get_key(sign_key_id)
            c.signers = [sign_key]

            def _normalize(original):
                return "\r\n".join(str(original).splitlines()[1:]) + "\r\n"

            if not enc_key_ids:
                msg = SafeMIMEMultipart(_subtype='signed', micalg='pgp-sha512', protocol='application/pgp-signature')
                msg.preamble = 'This is an OpenPGP/MIME signed message (RFC 4880 and 3156)'
                msg.attach(mime_object)

                # ToDo: Why is this header line missing from the output of mime_object.as_string()?
                # This header shouldn't be created here because it will be different for other mime objects.
                to_be_signed = 'Content-Type: multipart/mixed; boundary="{}"\n'.format(mime_object.get_boundary())
                to_be_signed += mime_object.as_string()
                # RFC 3156 requires the newlines to be CR+LF
                # Although RFC 3156 requires the signature *not* to not cover the last newline, verification fails if
                # it's not included
                to_be_signed = "\r\n".join(str(to_be_signed).splitlines()[1:]) + "\r\n"

                data = gpg.Data(string=to_be_signed)
                signature, sign_result = c.sign(data=data, mode=gpg.constants.SIG_MODE_DETACH)

                mime_signature = MIMEApplication(_subtype='pgp-signature', _encoder=encode_noop, name='signature.asc',
                                                 _data=signature.decode('utf-8'))
                mime_signature.add_header('Content-Description', 'OpenPGP digital signature')
                mime_signature.add_header('Content-Disposition', 'attachment', filename='signature.asc')
                del mime_signature['MIME-Version']

                msg.attach(mime_signature)

                return msg

        if enc_key_ids:
            # Get public keys from the keyservers
            c.set_keylist_mode(gpg.constants.keylist.mode.EXTERN)
            enc_keys = [c.get_key(k) for k in enc_key_ids]

            # Important: If downloaded keys are not imported to the context they are not usable
            c.op_import_keys(enc_keys)

            # Encrypt
            msg_string, result, sign_result = c.encrypt(
                mime_object.as_bytes(),
                recipients=enc_keys,
                sign=bool(sign_key_id), always_trust=True)

        # Create OpenPGP MIME object
        msg_version = MIMENonMultipart(_maintype='application', _subtype='pgp-encrypted')
        msg_version.add_header('Content-Description', 'PGP/MIME version identification')
        msg_version.set_payload('Version: 1\r\n')

        msg_encrypted = MIMENonMultipart(_maintype='application', _subtype='octet-stream', name='encrypted.asc')
        msg_encrypted.add_header('Content-Description', 'OpenPGP encrypted message')
        msg_encrypted.add_header('Content-Disposition', 'inline', filename='encrypted.asc')
        msg_encrypted.set_payload(msg_string)

        msg = MIMEMultipart(_subtype='encrypted', protocol='application/pgp-encrypted')
        msg.preamble = 'This is an OpenPGP/MIME encrypted message (RFC 4880 and 3156)'
        msg.attach(msg_version)
        msg.attach(msg_encrypted)

        return msg

