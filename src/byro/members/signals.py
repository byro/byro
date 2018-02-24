import django.dispatch

new_member_mail_information = django.dispatch.Signal()
new_member_office_mail_information = django.dispatch.Signal()
new_member = django.dispatch.Signal()
""" All signals receive the new member as sender. """
