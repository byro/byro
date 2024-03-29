# Generated by Django 1.11.9 on 2018-01-13 18:49

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("members", "0005_auto_20171206_1919")]

    operations = [
        migrations.AlterField(
            model_name="member",
            name="number",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=100,
                null=True,
                verbose_name="Membership number/ID",
            ),
        )
    ]
