from django.dispatch import receiver

from byro.common.signals import unauthenticated_urls


def _is_api_request(request, url):
    return url.namespace == "api"


@receiver(unauthenticated_urls)
def api_unauthenticated_urls(sender, **kwargs):
    return [_is_api_request]
