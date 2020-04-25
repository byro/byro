import string
from urllib.parse import urljoin

from annoying.fields import AutoOneToOneField
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _

from byro.common.models.configuration import Configuration


def generate_default_token():
    return get_random_string(
        allowed_chars=string.ascii_lowercase + string.digits, length=32
    )


def get_default_consent():
    return {"fields": dict()}


class MemberpageProfile(models.Model):
    form_title = _("Memberpage settings")

    member = AutoOneToOneField(
        to="members.Member", on_delete=models.CASCADE, related_name="profile_memberpage"
    )
    secret_token = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        default=generate_default_token,
        unique=True,
    )
    is_visible_to_members = models.BooleanField(
        default=False, verbose_name=_("Consent: Visible to other members")
    )
    # publication_consent format: {"fields": {"profile_memberpage__secret_token": {"visibility": "share"}}}
    publication_consent = JSONField(default=get_default_consent, null=True, blank=True)

    def get_url(self):
        config = Configuration.get_solo()
        relative_url = reverse(
            "public:memberpage:member.dashboard",
            kwargs={"secret_token": self.secret_token},
        )
        if config.public_base_url:
            return urljoin(config.public_base_url, relative_url)
        else:
            return urljoin(settings.SITE_URL, relative_url)

    def get_public_data(self):
        result = []
        if not self.is_visible_to_members or not self.publication_consent:
            return result
        all_fields = self.member.get_fields()
        for key, value in self.publication_consent.get("fields", {}).items():
            if not value.get("visibility") == "share" or key not in all_fields:
                continue
            field = all_fields[key]
            result.append({"label": field.name, "value": field.getter(self.member)})
        return result
