from django.contrib.auth import get_user_model
from django.db import models


class Auditable:
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        to=get_user_model(),
        on_delete=models.PROTECT,
        related_name="+",  # no related lookup
        null=True,
    )
    modified_by = models.ForeignKey(
        to=get_user_model(),
        on_delete=models.PROTECT,
        related_name="+",  # no related lookup
        null=True,
    )
