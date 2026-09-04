from django import template

from byro.mfa import services

register = template.Library()


@register.filter
def mfa_enabled(user):
    return services.user_has_mfa(user)
