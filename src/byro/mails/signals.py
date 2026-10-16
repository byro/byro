import logging
from datetime import timedelta

from django.dispatch import receiver
from django.utils import timezone

from byro.common.signals import periodic_task
from byro.mails import default
from byro.mails.models import (
    MailTemplate,
    MemberPGPKey,
    PGPConfiguration,
    PGPKeySource,
    PGPKeyStatus,
)
from byro.mails.pgp import import_member_key
from byro.mails.send import SendMailException

logger = logging.getLogger(__name__)


@receiver(periodic_task)
def refresh_pgp_keys(sender, **kwargs):
    config = PGPConfiguration.get_solo()
    if not config.refresh_keys_automatically:
        return

    cutoff = timezone.now() - timedelta(days=config.key_refresh_interval_days)
    keys = MemberPGPKey.objects.filter(source=PGPKeySource.KEYSERVER).filter(
        last_checked_at__isnull=True
    ) | MemberPGPKey.objects.filter(
        source=PGPKeySource.KEYSERVER,
        last_checked_at__lt=cutoff,
    )
    for key in keys:
        import_member_key(key.member, key.fingerprint, key.source)


@receiver(periodic_task)
def send_pgp_expiry_reminders(sender, **kwargs):
    config = PGPConfiguration.get_solo()
    if not config.send_expiry_reminders:
        return

    now = timezone.now()
    reminder_cutoff = now + timedelta(days=config.expiry_reminder_days)
    keys = MemberPGPKey.objects.filter(
        is_active=True,
        status=PGPKeyStatus.VALID,
        expires_at__isnull=False,
        expires_at__lte=reminder_cutoff,
    ).exclude(last_reminder_at__gte=now - timedelta(days=7))

    from byro.common.models import Configuration

    template = Configuration.get_solo().pgp_expiry_reminder_template or MailTemplate(
        subject=default.PGP_EXPIRY_REMINDER_SUBJECT,
        text=default.PGP_EXPIRY_REMINDER_TEXT,
    )
    for key in keys:
        if not key.member.email:
            continue
        try:
            template.to_mail(
                member=key.member,
                context={"name": key.member.name, "date": key.expires_at.date()},
            )
        except SendMailException:
            # The template can be edited, so it may use an unknown variable.
            # That must not stop the reminders for the other keys or the
            # other periodic tasks; this key is reminded on the next run.
            logger.warning(
                "The PGP expiry reminder for key %s could not be created.", key.pk
            )
            continue
        key.last_reminder_at = now
        key.save(update_fields=["last_reminder_at"])
