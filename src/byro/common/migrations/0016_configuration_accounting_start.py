# Generated by Django 2.2.12 on 2020-07-30 23:57

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("common", "0015_auto_20200421_2336"),
    ]

    operations = [
        migrations.AddField(
            model_name="configuration",
            name="accounting_start",
            field=models.DateField(
                blank=True,
                help_text="This field is especially useful if the organization was later migrated to byro and the membership fees of members from the past are not to be billed. Leave the field empty if you do not have this requirement and you want to invoice all members from the beginning of their membership.",
                null=True,
                verbose_name="Start accounting Membership Fees from",
            ),
        ),
    ]
