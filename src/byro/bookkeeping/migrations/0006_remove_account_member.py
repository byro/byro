# Generated by Django 1.11.4 on 2017-09-19 18:40

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("bookkeeping", "0005_auto_20170919_1832")]

    operations = [migrations.RemoveField(model_name="account", name="member")]
