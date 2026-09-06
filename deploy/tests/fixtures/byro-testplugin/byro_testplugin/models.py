from django.db import models


class TestpluginMarker(models.Model):
    """One table, so that the plugin ships a migration."""

    note = models.CharField(max_length=100)
