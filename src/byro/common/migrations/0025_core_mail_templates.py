from django.db import migrations

# The default templates as they were when this migration was written, in every
# language byro shipped then. They are frozen here on purpose: the runtime
# defaults in byro.mails.default may change later, an applied migration must
# not.
TEMPLATES = {
    "balance_reminder_template": {
        "subject": {
            "en": "Outstanding membership fees",
            "de": "Offene Mitgliedsbeiträge",
            "pt-br": "Outstanding membership fees",
        },
        "text": {
            "en": "Hello {name},\n\nwe wanted to let you know that within the time from {start}\nto {end} you incurred unpaid liabilities in the amount of\n\n   {amount}\n\nPlease settle this amount as soon as possible, or let us\nknow if you think this email is incorrect.",
            "de": "Hallo {name},\n\nwir wollten Dich wissen lassen, dass Du in der Zeit von {start}\nbis {end} versäumt hast, Mitgliedsbeiträge in Höhe von\n\n    {amount}\n\nzu zahlen. Bitte hole dies so bald wie möglich nach, oder lass\nuns wissen, wenn diese Erinnerung irrtümlich versandt wurde.",
            "pt-br": "Olá {name},\n\ngostaríamos de informar que dentro de {start}\npara {end} você incorreu em responsabilidades não pagas no valor de\n\n   {amount}\n\nPor favor, liquide este valor o mais rápido possível, ou deixe-nos\nsaber se você acha que este e-mail está incorreto.",
        },
    },
    "document_delivery_template": {
        "subject": {
            "en": "[{association}] Your document",
            "de": "[{association}] Dein Dokument",
            "pt-br": "[{association}] Seu documento",
        },
        "text": {
            "en": "Hi, {name},\n\nPlease find attached a document we wanted to send you/that you requested.\n\nThank you,\n{association}",
            "de": "Hi, {name},\n\nIm Anhang befindet sich ein Dokument für dich.\n\nDanke\n{association}",
            "pt-br": "Olá, {name},\n\nEm anexo encontra-se um documento que queríamos lhe enviar/que você solicitou.\n\nObrigado,\n{association}",
        },
    },
    "pgp_expiry_reminder_template": {
        "subject": {
            "en": "Your PGP key expires soon",
            "de": "Dein PGP-Schlüssel läuft bald ab",
            "pt-br": "Your PGP key expires soon",
        },
        "text": {
            "en": "Hello {name},\n\nthe PGP key stored for your membership expires on {date}. Please send us an updated public key before it expires.\n",
            "de": "Hallo {name},\n\nder für deine Mitgliedschaft gespeicherte PGP-Schlüssel läuft am {date} ab. Bitte sende uns vor Ablauf einen aktualisierten öffentlichen Schlüssel.\n",
            "pt-br": "Hello {name},\n\nthe PGP key stored for your membership expires on {date}. Please send us an updated public key before it expires.\n",
        },
    },
}


def init_templates(apps, schema_editor):
    MailTemplate = apps.get_model("mails", "MailTemplate")
    Configuration = apps.get_model("common", "Configuration")
    config, _ = Configuration.objects.get_or_create()
    for field, template in TEMPLATES.items():
        if getattr(config, f"{field}_id") is None:
            setattr(config, field, MailTemplate.objects.create(**template))
    config.save()


class Migration(migrations.Migration):
    dependencies = [("common", "0024_configuration_core_mail_templates")]

    operations = [migrations.RunPython(init_templates, migrations.RunPython.noop)]
