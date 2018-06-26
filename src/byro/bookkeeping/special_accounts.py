from django.utils.decorators import classproperty
from django.utils.translation import ugettext_lazy as _

from .models import Account, AccountCategory, AccountTag


class SpecialAccounts:

    @classmethod
    def special_account(cls, tag, category, name=None):
        tag, _ignore = AccountTag.objects.get_or_create(name=str(tag).lower())
        account = Account.objects.filter(account_category=category, tags=tag).first()
        if not account:
            account = Account.objects.filter(account_category=category, name=name).first()
            if not account:
                account = Account.objects.create(account_category=category, name=name)
            account.tags.add(tag)
            account.save()
        return account

    @classproperty
    def fees(cls):
        return cls.special_account('fees', AccountCategory.INCOME, _('Member fees'))

    @classproperty
    def donations(cls):
        return cls.special_account('donations', AccountCategory.INCOME, _('Donations'))

    @classproperty
    def fees_receivable(cls):
        return cls.special_account('fees_receivable', AccountCategory.ASSET, _('Member fees receivable'))

    @classproperty
    def bank(cls):
        return cls.special_account('bank', AccountCategory.ASSET, _('Bank'))
