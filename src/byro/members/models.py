from django.db import models, transaction

from byro.common.models.auditable import Auditable


class Member(Auditable, models.Model):

    # TODO: flesh out
    email = models.EmailField()

    @classmethod
    @transaction.atomic
    def create_member(cls, *args, **kwargs):
        ret = cls.objects.create(*args, **kwargs)

        from byro.bookkeeping.models import Account, AccountCategory
        for category in (AccountCategory.MEMBER_DONATION, AccountCategory.MEMBER_FEES):
            Account.objects.create(
                member=ret,
                account_category=category
            )
        return ret

    def get_account(self, category):
        return self.accounts.filter(account_category=category).first()
