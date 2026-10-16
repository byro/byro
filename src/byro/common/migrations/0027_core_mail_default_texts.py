from django.db import migrations

# The default texts of the eight mail templates byro uses for the mails it
# generates, before and after they were reworked. They are frozen here on
# purpose, like in 0025: byro.mails.default may change later, an applied
# migration must not. Portuguese has no translation of the new texts yet and
# uses the English ones, as gettext does for a new installation.
TEMPLATES = {
    "welcome_member_template": {
        "old": {
            "subject": {
                "en": "Welcome, latest member!",
                "de": "Willkommen, neustes Mitglied!",
                "pt-br": "Boas-vindas, última associada!",
            },
            "text": {
                "en": "Hi,\n\nwelcome to {name}! You're now officially our latest member. Your member ID\nis {number}. If you have any questions relating to your member fees or\nyou want to update your member data, please contact us at {contact}.\n\n{additional_information}\n\nThanks,\nthe robo clerk",
                "de": "Hi,\n\nWillkommen bei uns im {name}! Du bist unser neustes Mitglied. Deine\nMitgliedsnummer ist {number}. Wenn du Fragen zu deinem Beitrag hast\noder deine Kontaktdaten sich ändern, melde dich bitte unter {contact}.\n\n{additional_information}\n\nDanke\nDas Helferlein",
                "pt-br": "Oi,\n\nboas-vindas a {name}! Agora você é oficialmente nossa pessoa associada mais recente.\nSeu ID de associação é {number}. Se você tiver alguma dúvida sobre as taxas de associação ou\nvocê deseja atualizar seus dados de associada entre em contato conosco em {contact}.\n\n{additional_information}\n\nObrigado,\no robo escriturário",
            },
        },
        "new": {
            "subject": {
                "en": "Welcome to {name}",
                "de": "Willkommen bei {name}",
                "pt-br": "Welcome to {name}",
            },
            "text": {
                "en": "Hello {member_name},\n\nWelcome to {name}! Your member number is {number}.\n\nIf you have questions about your membership fees or want to update your details, please contact us at {contact}.\n\n{additional_information}",
                "de": "Hallo {member_name},\n\nwillkommen bei {name}! Deine Mitgliedsnummer ist {number}.\n\nWenn du Fragen zu deinen Mitgliedsbeiträgen hast oder sich deine Daten ändern, schreib uns bitte an {contact}.\n\n{additional_information}",
                "pt-br": "Hello {member_name},\n\nWelcome to {name}! Your member number is {number}.\n\nIf you have questions about your membership fees or want to update your details, please contact us at {contact}.\n\n{additional_information}",
            },
        },
    },
    "welcome_office_template": {
        "old": {
            "subject": {
                "en": "[byro] New member",
                "de": "[byr] Neues Mitglied",
                "pt-br": "[byro] Nova pessoa associada",
            },
            "text": {
                "en": "Hi,\n\nwe have a new member: {member_name}\n\n{additional_information}\n\nThanks,\nthe robo clerk",
                "de": "Hi,\n\nwir haben ein neues Mitglied: {member_name}\n\n{additional_information}\n\nDanke\nDas Helferlein",
                "pt-br": "Olá,\n\ntemos uma nova pessoa associada: {member_name}\n\n{additional_information}\n\nObrigado,\no robo escriturário",
            },
        },
        "new": {
            "subject": {
                "en": "[byro] New member: {member_name}",
                "de": "[byro] Neues Mitglied: {member_name}",
                "pt-br": "[byro] New member: {member_name}",
            },
            "text": {
                "en": "A new member has been added: {member_name}\n\n{additional_information}",
                "de": "Ein neues Mitglied wurde angelegt: {member_name}\n\n{additional_information}",
                "pt-br": "A new member has been added: {member_name}\n\n{additional_information}",
            },
        },
    },
    "leave_member_template": {
        "old": {
            "subject": {
                "en": "Goodbye!",
                "de": "Tschüß!",
                "pt-br": "Até logo!",
            },
            "text": {
                "en": "Hi,\n\nwe are sorry that you will leave us at {end}.\n\n{additional_information}\n\nThanks,\nthe robo clerk",
                "de": "Hi,\n\nschade, dass du uns zu {end} verlässt.\n\n{additional_information}\n\nDanke\nDas Helferlein",
                "pt-br": "Olá,\n\nlamentamos que você nos deixe em {end}.\n\n{additional_information}\n\nObrigado,\no robo escriturário",
            },
        },
        "new": {
            "subject": {
                "en": "End of your membership",
                "de": "Ende deiner Mitgliedschaft",
                "pt-br": "End of your membership",
            },
            "text": {
                "en": "Hello {member_name},\n\nYour membership in {name} ends on {end}.\n\n{additional_information}",
                "de": "Hallo {member_name},\n\ndeine Mitgliedschaft bei {name} endet am {end}.\n\n{additional_information}",
                "pt-br": "Hello {member_name},\n\nYour membership in {name} ends on {end}.\n\n{additional_information}",
            },
        },
    },
    "leave_office_template": {
        "old": {
            "subject": {
                "en": "[byro] Membership termination",
                "de": "[byro] Austritt",
                "pt-br": "[byro] Encerramento de associação",
            },
            "text": {
                "en": "Hi,\n\n{member_name} will leave us at {end}.\n\n{additional_information}\n\nThanks,\nthe robo clerk",
                "de": "Hi,\n\n{member_name} wird uns zu {end} verlassen.\n\n{additional_information}\n\nDanke\nDas Helferlein",
                "pt-br": "Olá,\n\n{member_name} nos deixará em {end}.\n\n{additional_information}\n\nObrigado,\no robo escriturário",
            },
        },
        "new": {
            "subject": {
                "en": "[byro] End of membership: {member_name}",
                "de": "[byro] Ende der Mitgliedschaft: {member_name}",
                "pt-br": "[byro] End of membership: {member_name}",
            },
            "text": {
                "en": "The membership of {member_name} ends on {end}.\n\n{additional_information}",
                "de": "Die Mitgliedschaft von {member_name} endet am {end}.\n\n{additional_information}",
                "pt-br": "The membership of {member_name} ends on {end}.\n\n{additional_information}",
            },
        },
    },
    "record_disclosure_template": {
        "old": {
            "subject": {
                "en": "Your {association_name} data record (#{number})",
                "de": "Dein {association_name} Datenbestand (#{number})",
                "pt-br": "Seu registro de dados para {association_name} (#{number})",
            },
            "text": {
                "en": "Hi,\n\nWe're writing you to let you know about the data we have currently stored about\nyourself and your membership.\n\nYour current balance is {balance}.\n\n{data}\n\nIf these records are outdated or incorrect, please let us know as a response to\nthis email.\n\nThanks,\nthe robo clerk",
                "de": "Hi,\n\nwir schreiben dir, um dir den aktuellen Datenbestand über dich in unserer\nMitgliederdatenbank mitzuteilen.\n\nDein Guthaben (Rückstand falls negativ): {balance}\n\n{data}\n\n\nWenn diese Daten veraltet oder falsch sind, lass es uns bitte als Antwort\nauf diese Mail wissen.\n\nDanke,\nDas Helferlein",
                "pt-br": "Olá,\n\nEstamos escrevendo para informá-lo sobre os dados que armazenamos atualmente sobre\nvocê e sua associação.\n\nSeu saldo atual é {balance}.\n\n{data}\n\nSe esses registros estiverem desatualizados ou incorretos, informe-nos em resposta a\neste e-mail.\n\nObrigado,\no robo escriturário",
            },
        },
        "new": {
            "subject": {
                "en": "Your data at {association_name} (member number {number})",
                "de": "Deine Daten bei {association_name} (Mitgliedsnummer {number})",
                "pt-br": "Your data at {association_name} (member number {number})",
            },
            "text": {
                "en": "Hello,\n\nThis is an overview of the data {association_name} currently stores about you and your membership.\n\nYour current balance is {balance}. A negative balance means that fees are outstanding.\n\n{data}\n\nIf anything is outdated or incorrect, please reply to this email and let us know.",
                "de": "Hallo,\n\nhier ist eine Übersicht der Daten, die {association_name} aktuell über dich und deine Mitgliedschaft gespeichert hat.\n\nDein aktueller Kontostand beträgt {balance}. Ein negativer Betrag bedeutet, dass Beiträge offen sind.\n\n{data}\n\nWenn etwas veraltet oder falsch ist, antworte bitte einfach auf diese E-Mail.",
                "pt-br": "Hello,\n\nThis is an overview of the data {association_name} currently stores about you and your membership.\n\nYour current balance is {balance}. A negative balance means that fees are outstanding.\n\n{data}\n\nIf anything is outdated or incorrect, please reply to this email and let us know.",
            },
        },
    },
    "balance_reminder_template": {
        "old": {
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
        "new": {
            "subject": {
                "en": "Outstanding membership fees",
                "de": "Offene Mitgliedsbeiträge",
                "pt-br": "Outstanding membership fees",
            },
            "text": {
                "en": "Hello {name},\n\nAccording to our records, membership fees for the period from {start} to {end} are still outstanding:\n\n    {amount}\n\nPlease pay this amount as soon as possible. If you think this is a mistake, please reply to this email.",
                "de": "Hallo {name},\n\nlaut unseren Unterlagen sind für den Zeitraum vom {start} bis {end} noch Mitgliedsbeiträge offen:\n\n    {amount}\n\nBitte zahle den Betrag so bald wie möglich. Falls du denkst, dass hier ein Fehler vorliegt, antworte bitte auf diese E-Mail.",
                "pt-br": "Hello {name},\n\nAccording to our records, membership fees for the period from {start} to {end} are still outstanding:\n\n    {amount}\n\nPlease pay this amount as soon as possible. If you think this is a mistake, please reply to this email.",
            },
        },
    },
    "document_delivery_template": {
        "old": {
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
        "new": {
            "subject": {
                "en": "Your document from {association}",
                "de": "Dein Dokument von {association}",
                "pt-br": "Your document from {association}",
            },
            "text": {
                "en": "Hello,\n\nA document from {association} is attached to this email.",
                "de": "Hallo,\n\nim Anhang dieser E-Mail findest du ein Dokument von {association}.",
                "pt-br": "Hello,\n\nA document from {association} is attached to this email.",
            },
        },
    },
    "pgp_expiry_reminder_template": {
        "old": {
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
        "new": {
            "subject": {
                "en": "Your PGP key expires soon",
                "de": "Dein PGP-Schlüssel läuft bald ab",
                "pt-br": "Your PGP key expires soon",
            },
            "text": {
                "en": "Hello {name},\n\nThe PGP key stored for your membership expires on {date}. Please send us an updated public key before it expires.",
                "de": "Hallo {name},\n\nder für deine Mitgliedschaft gespeicherte PGP-Schlüssel läuft am {date} ab. Bitte sende uns vor Ablauf einen aktualisierten öffentlichen Schlüssel.",
                "pt-br": "Hello {name},\n\nThe PGP key stored for your membership expires on {date}. Please send us an updated public key before it expires.",
            },
        },
    },
}

LANGUAGES = ("en", "de", "pt-br")


def _value(data, language):
    """The text of one language: a value stored as plain text is the text of
    every language."""
    if isinstance(data, dict):
        return data.get(language)
    return data


def _replace(data, language, value):
    if isinstance(data, dict):
        return {**data, language: value}
    return value


def _normalize(value):
    # texts saved through a browser form have CRLF line breaks
    return value.replace("\r\n", "\n") if isinstance(value, str) else value


def update_templates(apps, schema_editor):
    """Give the assigned templates the new default texts.

    A language is only changed where subject and text both still are the
    old default of that language. Templates someone changed keep their texts.
    """
    MailTemplate = apps.get_model("mails", "MailTemplate")
    Configuration = apps.get_model("common", "Configuration")
    config = Configuration.objects.first()
    if config is None:
        return
    for field, texts in TEMPLATES.items():
        template_id = getattr(config, f"{field}_id")
        if template_id is None:
            continue
        template = MailTemplate.objects.get(pk=template_id)
        subject = template.subject.data
        text = template.text.data
        changed = False
        for language in LANGUAGES:
            if (
                _normalize(_value(subject, language))
                == texts["old"]["subject"][language]
                and _normalize(_value(text, language)) == texts["old"]["text"][language]
            ):
                subject = _replace(subject, language, texts["new"]["subject"][language])
                text = _replace(text, language, texts["new"]["text"][language])
                changed = True
        if changed:
            template.subject = subject
            template.text = text
            template.save(update_fields=["subject", "text"])


class Migration(migrations.Migration):
    dependencies = [("common", "0026_configuration_member_mail_footer")]

    operations = [migrations.RunPython(update_templates, migrations.RunPython.noop)]
