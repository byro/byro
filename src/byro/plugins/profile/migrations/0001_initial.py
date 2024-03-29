# Generated by Django 1.11.4 on 2017-08-12 16:05

import byro.common.models.auditable
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [("members", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="MemberProfile",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("member_identifier", models.CharField(max_length=50, null=True)),
                ("birth_date", models.DateField(null=True)),
                ("address", models.CharField(max_length=500, null=True)),
                ("nick", models.CharField(max_length=200, null=True)),
                ("name", models.CharField(max_length=200, null=True)),
                (
                    "member",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="profile_profile",
                        to="members.Member",
                    ),
                ),
            ],
            bases=(byro.common.models.auditable.Auditable, models.Model),
        )
    ]
