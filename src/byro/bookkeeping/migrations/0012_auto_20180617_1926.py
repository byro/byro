# Generated by Django 1.11.13 on 2018-06-17 19:26

from django.conf import settings
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("members", "0009_auto_20180512_1810"),
        ("bookkeeping", "0011_auto_20180303_1745"),
    ]

    operations = [
        migrations.CreateModel(
            name="AccountTag",
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
                ("name", models.CharField(max_length=300, unique=True)),
                ("description", models.CharField(max_length=1000, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="Booking",
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
                ("memo", models.CharField(max_length=1000, null=True)),
                ("booking_datetime", models.DateTimeField(null=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=8)),
                ("importer", models.CharField(max_length=500, null=True)),
                ("data", django.contrib.postgres.fields.jsonb.JSONField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name="Transaction",
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
                ("memo", models.CharField(max_length=1000, null=True)),
                ("booking_datetime", models.DateTimeField(null=True)),
                ("value_datetime", models.DateTimeField()),
                ("modified", models.DateTimeField(auto_now=True)),
                ("data", django.contrib.postgres.fields.jsonb.JSONField(null=True)),
                (
                    "modified_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "reverses",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reversed_by",
                        to="bookkeeping.Transaction",
                    ),
                ),
            ],
        ),
        migrations.AlterField(
            model_name="account",
            name="account_category",
            field=models.CharField(
                choices=[
                    ("member_donation", "Donation account"),
                    ("member_fees", "Membership fee account"),
                    ("asset", "Asset account"),
                    ("liability", "Liability account"),
                    ("income", "Income account"),
                    ("expense", "Expense account"),
                    ("equity", "Equity account"),
                ],
                max_length=15,
            ),
        ),
        migrations.AddField(
            model_name="booking",
            name="credit_account",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="credits",
                to="bookkeeping.Account",
            ),
        ),
        migrations.AddField(
            model_name="booking",
            name="debit_account",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="debits",
                to="bookkeeping.Account",
            ),
        ),
        migrations.AddField(
            model_name="booking",
            name="member",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="bookings",
                to="members.Member",
            ),
        ),
        migrations.AddField(
            model_name="booking",
            name="modified_by",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="booking",
            name="source",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="bookings",
                to="bookkeeping.RealTransactionSource",
            ),
        ),
        migrations.AddField(
            model_name="booking",
            name="transaction",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="bookings",
                to="bookkeeping.Transaction",
            ),
        ),
        migrations.AddField(
            model_name="account",
            name="tags",
            field=models.ManyToManyField(
                related_name="accounts", to="bookkeeping.AccountTag"
            ),
        ),
    ]
