from django import forms
from django.utils.translation import gettext_lazy as _

PGP_REGISTRATION_FIELD = "pgp__fingerprint"


def build_pgp_fingerprint_field():
    return forms.CharField(
        label=_("PGP fingerprint"),
        max_length=100,
        required=False,
        help_text=_("Full OpenPGP fingerprint used to import the member's public key."),
    )


def get_member_pgp_fingerprint(member):
    key = (
        member.pgp_keys.filter(is_active=True)
        .order_by("-verified_at", "-last_checked_at", "fingerprint")
        .first()
    )
    return key.fingerprint if key else ""
