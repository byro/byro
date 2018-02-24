from contextlib import suppress

from django.conf import settings
from django.http import Http404
from django.urls import resolve

from byro.common.models import Configuration
from byro.mails.models import EMail


def byro_information(request):
    ctx = {
        'config': Configuration.get_solo(),
        'pending_mails': EMail.objects.filter(sent__isnull=True).count(),
    }

    try:
        ctx['url_name'] = resolve(request.path_info).url_name
    except Http404:
        ctx['url_name'] = ''

    if settings.DEBUG:
        ctx['development_warning'] = True
        with suppress(Exception):
            import subprocess
            ctx['byro_version'] = subprocess.check_output(['git', 'describe', '--always'])

    return ctx
