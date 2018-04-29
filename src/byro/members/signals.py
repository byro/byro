import django.dispatch

new_member_mail_information = django.dispatch.Signal()
"""
Receives the new member as signal. Response will be added to the email
welcoming the new member.
"""
new_member_office_mail_information = django.dispatch.Signal()
"""
Receives the new member as signal. Response will be added to the email
notifying the office about the new member.
"""
new_member = django.dispatch.Signal()
"""
Receives the new member as signal. If an exception is raised, the error
message will be displayed in the frontend as a warning.
"""
leave_member_mail_information = django.dispatch.Signal()
"""
Receives the leave of a member as signal. Response will be added to the email
confirming termination to the member.
"""
leave_member_office_mail_information = django.dispatch.Signal()
"""
Receives the leave of a member as signal. Response will be added to the email
notifying the office about the termination of the member.
"""
