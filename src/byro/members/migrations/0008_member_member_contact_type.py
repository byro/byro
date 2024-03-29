# Generated by Django 1.11.13 on 2018-05-11 16:14

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("members", "0007_member_membership_type")]

    operations = [
        migrations.AddField(
            model_name="member",
            name="member_contact_type",
            field=models.CharField(
                choices=[
                    ("organization", "organization"),
                    ("person", "person"),
                    ("role", "role"),
                ],
                default="person",
                max_length=12,
            ),
        )
    ]
