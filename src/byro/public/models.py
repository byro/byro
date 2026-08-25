import string
from urllib.parse import urljoin

from annoying.fields import AutoOneToOneField
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _

from byro.common.models.configuration import Configuration
from byro.members.models import Field, Member


def get_proposable_fields(member):
    """Return a dict {field_id: Field} of the fields a member may propose changes
    to. Which fields are editable is declared by each contributing model (core or
    plugin) via its ``member_editable_fields`` attribute and surfaced on the byro
    Field as ``editable_by_member`` in Member.get_fields()."""
    return {
        field_id: field
        for field_id, field in member.get_fields().items()
        if getattr(field, "editable_by_member", False)
    }


def model_field_for(member, field):
    """Resolve the concrete Django model field a byro Field points at, so we can
    reuse its form field for validation and its value coercion."""
    target, prop = Field._follow_path(member, field.path)
    return target._meta.get_field(prop)


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
    publication_consent = models.JSONField(
        default=get_default_consent, null=True, blank=True
    )

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
            result.append(
                {"label": field.base_name, "value": field.getter(self.member)}
            )
        return result


class MemberChangeProposal(models.Model):
    """A change to a single member data field, proposed by the member via their
    (token-secured) member page. Proposals never modify data directly; an admin
    accepts or rejects them in the office backend."""

    member = models.ForeignKey(
        to=Member,
        on_delete=models.CASCADE,
        related_name="change_proposals",
    )
    field_id = models.CharField(max_length=200)
    new_value = models.TextField(null=True, blank=True)
    created = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("member", "field_id")
        ordering = ("field_id",)

    def get_field(self):
        """Return the byro Field this proposal targets, or None if it is no
        longer available (e.g. a removed profile plugin)."""
        return self.member.get_fields().get(self.field_id)

    @property
    def label(self):
        field = self.get_field()
        return field.name if field else self.field_id

    @property
    def current_value(self):
        field = self.get_field()
        return field.getter(self.member) if field else None
