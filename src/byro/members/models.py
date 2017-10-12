from django.db import models

from byro.common.models.auditable import Auditable


class Member(Auditable, models.Model):

    # TODO: flesh out
    email = models.EmailField()

    @property
    def profiles(self) -> list:
        pass
