from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PluginApp(AppConfig):
    name = "byro_testplugin"
    verbose_name = _("byroctl test plugin")

    class ByroPluginMeta:
        name = _("byroctl test plugin")
        author = "byro"
        description = _("Fixture plugin for the byroctl integration tests.")
        visible = True
        version = "0.0.1"
