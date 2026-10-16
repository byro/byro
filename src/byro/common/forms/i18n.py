from django.conf import settings
from i18nfield.forms import I18nModelForm


class RestrictedLanguagesI18nModelForm(I18nModelForm):
    """Shows the translatable fields only in the language of the
    organization, in which mail texts are written and sent."""

    def __init__(self, *args, **kwargs):
        if "locales" not in kwargs:
            from byro.common.models import Configuration

            config = Configuration.get_solo()
            kwargs["locales"] = [config.language or settings.LANGUAGE_CODE]
        return super().__init__(*args, **kwargs)
