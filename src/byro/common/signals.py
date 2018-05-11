import django.dispatch

periodic_task = django.dispatch.Signal()
"""
This is a signal that we send out every time the periodic task cronjob runs.
This interval is not sharply defined, it can be everything between a minute and
a day. The actions you perform should be idempotent, i.e. it should not make a
difference if this is sent out more often than expected.
"""
