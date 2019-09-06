"""byro URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
import importlib.util
from contextlib import suppress

from django.apps import apps
from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static

raw_plugin_patterns = []
for app in apps.get_app_configs():
    if hasattr(app, "ByroPluginMeta"):
        if importlib.util.find_spec(app.name + ".urls"):
            urlmod = importlib.import_module(app.name + ".urls")
            single_plugin_patterns = []
            if hasattr(urlmod, "urlpatterns"):
                single_plugin_patterns += urlmod.urlpatterns
            raw_plugin_patterns.append(
                url(r"", include((single_plugin_patterns, app.label)))
            )

urlpatterns = [
    url(r"", include((raw_plugin_patterns, "plugins"))),
    url(r"", include("byro.common.urls", namespace="common")),
    url(r"", include("byro.office.urls", namespace="office")),
    url(r"^p/", include("byro.public.urls", namespace="public")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    with suppress(ImportError):
        import debug_toolbar

        urlpatterns.insert(0, url(r"^__debug__/", include(debug_toolbar.urls)))
