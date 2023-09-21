# Generated by Django 2.1.1 on 2018-09-29 13:17

from django.db import migrations


def init_templates(apps, schema_editor):
    from byro.mails import default

    MailTemplate = apps.get_model("mails", "MailTemplate")
    Configuration = apps.get_model("common", "Configuration")
    config, _ = Configuration.objects.get_or_create()
    if not config.record_disclosure_template:
        template = MailTemplate.objects.create(
            subject=default.RECORD_DISCLOSURE_SUBJECT,
            text=default.RECORD_DISCLOSURE_TEXT,
        )
        config.record_disclosure_template = template
    config.save()


class Migration(migrations.Migration):
    dependencies = [("common", "0011_configuration_record_disclosure_template")]

    operations = [migrations.RunPython(init_templates, migrations.RunPython.noop)]
