import collections
from contextlib import suppress

from django.conf import settings
from django.http import Http404
from django.urls import resolve

from byro.bookkeeping.models import Transaction
from byro.common.models import Configuration
from byro.mails.models import EMail
from byro.office.signals import nav_event


def byro_information(request):
    ctx = {
        'config': Configuration.get_solo(),
        'pending_mails': EMail.objects.filter(sent__isnull=True).count(),
        'pending_transactions': Transaction.objects.unbalanced_transactions().count(),
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


def sidebar_information(request):
    _nav_event = []
    for receiver, response in nav_event.send(request):
        if not response:
            continue
        if isinstance(response, collections.Mapping):
            _nav_event.append(response)
        else:
            _nav_event.extend(response)

    return {'nav_event': _nav_event}
