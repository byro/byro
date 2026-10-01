from django.conf import settings
from django.core.checks import Warning, register


@register()
def check_oidc_group_configuration(app_configs, **kwargs):
    """Warnings only: a broken OIDC configuration must never keep byro from
    starting, the password login (break-glass account) has to stay usable.
    An ambiguous configuration disables the OIDC login instead, see
    ``byro.common.oidc.get_configuration_error``."""
    warnings = []
    if settings.OIDC_GROUP_CONFLICT:
        warnings.append(
            Warning(
                "The OIDC options admin_group and staff_group are both set, "
                "but to different values. OIDC login is disabled until this "
                "is resolved; password login keeps working.",
                hint=(
                    "admin_group is the deprecated name of staff_group. Keep "
                    "staff_group only (BYRO_OIDC_STAFF_GROUP) and remove "
                    "admin_group (BYRO_OIDC_ADMIN_GROUP)."
                ),
                id="byro.common.W001",
            )
        )
    elif settings.OIDC_ADMIN_GROUP:
        warnings.append(
            Warning(
                "The OIDC option admin_group is deprecated and will be removed "
                "in a future release.",
                hint=(
                    "Rename it to staff_group (BYRO_OIDC_STAFF_GROUP). The "
                    "behavior stays the same."
                ),
                id="byro.common.W002",
            )
        )
    if settings.OIDC_SYNC_GROUPS and not (
        settings.OIDC_STAFF_GROUP
        or settings.OIDC_SUPERUSER_GROUP
        or settings.OIDC_GROUP_CONFLICT
    ):
        warnings.append(
            Warning(
                "The OIDC option sync_groups is enabled, but neither "
                "staff_group nor superuser_group is set. Nothing is "
                "synchronized.",
                hint="Set staff_group and/or superuser_group, or disable sync_groups.",
                id="byro.common.W003",
            )
        )
    return warnings
