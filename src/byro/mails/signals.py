from datetime import timedelta

from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from byro.common.signals import periodic_task
from byro.mails.models import MemberPGPKey, PGPConfiguration, PGPKeySource, PGPKeyStatus
from byro.mails.pgp import import_member_key


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

    from byro.mails.models import EMail

    for key in keys:
        if not key.member.email:
            continue
        EMail.objects.create(
            to=key.member.email,
            subject=_("Your PGP key expires soon"),
            text=_(
                "Hello {name},\n\n"
                "the PGP key stored for your membership expires on {date}. "
                "Please send us an updated public key before it expires.\n"
            ).format(name=key.member.name, date=key.expires_at.date()),
        )
        key.last_reminder_at = now
        key.save(update_fields=["last_reminder_at"])
