# Generated by Django 2.2.12 on 2020-08-09 19:16

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("members", "0010_memberbalance"),
    ]

    operations = [
        migrations.AddField(
            model_name="member",
            name="direct_address_name",
            field=models.CharField(
                blank=True,
                max_length=100,
                null=True,
                verbose_name="Name for direct address",
            ),
        ),
        migrations.AddField(
            model_name="member",
            name="order_name",
            field=models.CharField(
                blank=True, max_length=100, null=True, verbose_name="Name (sort order)"
            ),
        ),
    ]
