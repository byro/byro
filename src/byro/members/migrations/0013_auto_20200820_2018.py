# Generated by Django 3.1 on 2020-08-20 20:18

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("members", "0012_split_names"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="member",
            options={"ordering": (("direct_address_name", "name"),)},
        ),
    ]
