# Generated by Django 1.11.6 on 2017-10-12 20:32

import annoying.fields
from django.db import migrations
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("profile", "0002_auto_20171012_1915")]

    operations = [
        migrations.AlterField(
            model_name="memberprofile",
            name="member",
            field=annoying.fields.AutoOneToOneField(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="profile_profile",
                to="members.Member",
            ),
        )
    ]
