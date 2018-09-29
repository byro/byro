import django.dispatch

periodic_task = django.dispatch.Signal()
"""
This is a signal that we send out every time the periodic task cronjob runs.
This interval is not sharply defined, it can be everything between a minute and
a day. The actions you perform should be idempotent, i.e. it should not make a
difference if this is sent out more often than expected.
"""

unauthenticated_urls = django.dispatch.Signal()
"""
This signal is used to compile a list of URLs that should bypass the normal
authentication middleware.
The return value must be an iterable where each item is either a) a local
view name, or b) a callable with signature (request, resolver_match) that
should return True if authentication should be bypassed.
Note: in case a) only the local name must be provided, not with the
"plugins:$plugin_name:" namespace prefix, in case b) the callable will see
the request and resolver_match with the full name, including namespace prefix.
"""

log_formatters = django.dispatch.Signal()
"""
This signal is used to compile a list of log entry formatters.
The return value must be a mapping of action_type: callable(LogEntry) -> html_fragment: str
"""
