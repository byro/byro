from django import template

from byro.common.models import Configuration

register = template.Library()


@register.filter
def format_with_currency(value, long_form=False):
    config = Configuration.get_solo()
    amount = str(value if config.display_cents else int(value))
    parts = [amount, config.currency if long_form else config.currency_symbol]
    return " ".join(parts if config.currency_postfix else reversed(parts))
