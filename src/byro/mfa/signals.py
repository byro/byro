from django.dispatch import receiver

from byro.common.signals import periodic_task


@receiver(periodic_task)
def mfa_cleanup_pending_devices(sender, **kwargs):
    from byro.mfa.services import cleanup_pending_devices

    cleanup_pending_devices()
