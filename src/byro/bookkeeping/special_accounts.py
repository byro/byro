from contextlib import suppress

import django.db.utils
from django.db import transaction
from django.utils.decorators import classproperty
from django.utils.translation import ugettext_lazy as _

from .models import Account, AccountCategory, AccountTag


class SpecialAccounts:
    @classmethod
    def special_account(cls, tag, category, name=None):
        tag, _ignore = AccountTag.objects.get_or_create(name=str(tag).lower())
        accounts = list(
            Account.objects.filter(account_category=category, tags=tag).all()
        )
        if len(accounts) > 1:
            raise Account.MultipleObjectsReturned()
        if accounts:
            account = accounts[0]
        else:
            # Old mechanism: Return an account that is named as the special one would.
            #  But also tag it.
            account = Account.objects.filter(
                account_category=category, name=str(name)
            ).first()
            if not account:
                account = Account.objects.create(
                    account_category=category, name=str(name)
                )
                with suppress(django.db.utils.ProgrammingError):
                    with transaction.atomic():
                        account.log(
                            None,
                            "byro.bookkeeping.account.created",
                            source="Automatic creation of special account",
                        )
            account.tags.add(tag)
            account.save()
        return account

    @classproperty
    def fees(cls):
        return cls.special_account("fees", AccountCategory.INCOME, _("Member fees"))

    @classproperty
    def donations(cls):
        return cls.special_account("donations", AccountCategory.INCOME, _("Donations"))

    @classproperty
    def fees_receivable(cls):
        return cls.special_account(
            "fees_receivable", AccountCategory.ASSET, _("Member fees receivable")
        )

    @classproperty
    def bank(cls):
        return cls.special_account("bank", AccountCategory.ASSET, _("Bank"))

    @classproperty
    def opening_balance(cls):
        return cls.special_account(
            "opening_balance", AccountCategory.ASSET, _("Opening balance")
        )

    @classproperty
    def lost_income(cls):
        return cls.special_account(
            "lost_income", AccountCategory.EXPENSE, _("Lost income")
        )
