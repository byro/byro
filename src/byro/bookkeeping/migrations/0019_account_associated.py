# Generated by Django 2.2.9 on 2020-12-13 03:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bookkeeping', '0018_auto_20201115_0208'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='associated',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='bookkeeping.Account'),
        ),
    ]