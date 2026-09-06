from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="TestpluginMarker",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("note", models.CharField(max_length=100)),
            ],
        ),
    ]
