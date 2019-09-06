from annoying.fields import AutoOneToOneField
from django.db import models
from django.utils.translation import ugettext_lazy as _

from byro.common.models.auditable import Auditable


class MemberProfile(Auditable, models.Model):

    member = AutoOneToOneField(
        to="members.Member", related_name="profile_profile", on_delete=models.PROTECT
    )
    nick = models.CharField(
        verbose_name=_("Nick"), max_length=200, blank=True, null=True
    )
    birth_date = models.DateField(verbose_name=_("Birth date"), blank=True, null=True)
    phone_number = models.CharField(
        verbose_name=_("Phone number"), max_length=32, blank=True, null=True
    )

    form_title = _("General information")
