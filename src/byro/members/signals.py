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
Receives the leaving member as signal. Response will be added to the email
confirming termination to the member.
"""
leave_member_office_mail_information = django.dispatch.Signal()
"""
Receives the leaving member as signal. Response will be added to the email
notifying the office about the termination of the member.
"""
leave_member = django.dispatch.Signal()
"""
Receives the new member as signal. If an exception is raised, the error
message will be displayed in the frontend as a warning.
"""
update_member = django.dispatch.Signal()
"""
If a member is updated via the office form collection at members/view/{id}/data.
The signal receives the request, and the form_list as parameters. The changes
will already have been saved at this point.
"""
