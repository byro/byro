import string
from urllib.parse import urljoin

from annoying.fields import AutoOneToOneField
from django.db import models
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _

from byro.common.models.configuration import Configuration


def generate_default_token():
    return get_random_string(allowed_chars=string.ascii_lowercase + string.digits, length=32)


class MemberpageProfile(models.Model):
    form_title = _("Memberpage settings")

    member = AutoOneToOneField(
        to='members.Member',
        on_delete=models.CASCADE,
        related_name='profile_memberpage',
    )
    secret_token = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        default=generate_default_token,
    )
    is_visible_to_members = models.BooleanField(
        default=False,
        verbose_name=_('Consent: Visible to other members'),
    )

    def get_url(self):
        config = Configuration.get_solo()
        relative_url = reverse(
            'plugins:byro_memberpage:unprotected:memberpage.dashboard',
            kwargs={'secret_token': self.secret_token}
        )
        if config.public_base_url:
            return urljoin(config.public_base_url, relative_url)
        else:
            return relative_url
