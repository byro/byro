from django.db import migrations, models


def migrate_require_mfa(apps, schema_editor):
    MFAConfiguration = apps.get_model("mfa", "MFAConfiguration")
    MFAConfiguration.objects.filter(require_mfa=True).update(policy="required")


class Migration(migrations.Migration):

    dependencies = [
        ("mfa", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="mfaconfiguration",
            name="policy",
            field=models.CharField(
                choices=[
                    ("optional", "Optional"),
                    ("required", "Required for all administrators"),
                    (
                        "required_except_oidc",
                        "Required for all administrators except OIDC logins",
                    ),
                ],
                default="optional",
                help_text=(
                    "Choose whether MFA is optional, required for every backend login, or "
                    "required except for sessions authenticated through OIDC. An authenticator "
                    "that a user set up themselves is always required."
                ),
                max_length=32,
                verbose_name="MFA policy",
            ),
        ),
        migrations.RunPython(migrate_require_mfa, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="mfaconfiguration",
            name="require_mfa",
        ),
    ]
