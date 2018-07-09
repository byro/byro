from django import template

register = template.Library()


@register.filter
def extract_property(value, argument):
    return [getattr(v, argument, None) for v in value]
