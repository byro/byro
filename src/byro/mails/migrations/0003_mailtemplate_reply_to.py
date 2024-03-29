# Generated by Django 1.11.8 on 2018-02-24 20:16

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("mails", "0002_email_attachments")]

    operations = [
        migrations.AddField(
            model_name="mailtemplate",
            name="reply_to",
            field=models.EmailField(
                blank=True,
                help_text="Change the Reply-To address if you do not want to use the default orga address",
                max_length=200,
                null=True,
                verbose_name="Reply-To",
            ),
        )
    ]
