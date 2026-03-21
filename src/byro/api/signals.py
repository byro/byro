from django.dispatch import receiver

from byro.common.signals import unauthenticated_urls


@receiver(unauthenticated_urls)
def api_docs_unauthenticated_urls(sender, **kwargs):
    return ("api:schema", "api:swagger-ui")
