from django.contrib.auth import get_user_model
from django.db import models


class ReminderGroup(models.Model):
    created = models.DateTimeField(auto_now=True)
    started_by = models.ForeignKey(
        to=get_user_model(),
        on_delete=models.PROTECT,
        related_name='+',  # no related lookup
        null=True,
    )
    interval_start = models.DateTimeField(null=True, blank=True)
    interval_end = models.DateTimeField()
    minimum_amount = models.DecimalField(max_digits=8, decimal_places=2)
    template = models.ForeignKey(
        to='mails.MailTemplate', on_delete=models.CASCADE, related_name='+'
    )


class Reminder(models.Model):
    reminder_group = models.ForeignKey(
        to=ReminderGroup, on_delete=models.CASCADE, related_name='reminders'
    )
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    member = models.ForeignKey(
        to='members.Member',
        related_name='reminders',
        on_delete=models.PROTECT,
        null=True,
    )
    email = models.ForeignKey(to='mails.EMail', on_delete=models.CASCADE)
