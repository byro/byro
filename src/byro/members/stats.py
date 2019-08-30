from typing import Tuple

from dateutil.relativedelta import relativedelta

from byro.members.models import Membership


def get_member_statistics_for_month(month, year) -> Tuple[int, int]:
    joins = Membership.objects.filter(start__month=month, start__year=year).count()
    quits = Membership.objects.filter(end__month=month, end__year=year).count()
    return joins, quits


def get_member_statistics():
    """
    Returns a list of tuples of the form ((year, month), joins, quits).
    """
    first_member = Membership.objects.order_by("start").first()
    if not first_member:
        return []

    date = first_member.start
    end_member = Membership.objects.filter(end__isnull=False).order_by("-end").first()
    if not end_member:
        return []
    end = end_member.end
    result = []

    while date <= end:
        result.append(
            (
                (date.year, date.month),
                *get_member_statistics_for_month(date.month, date.year),
            )
        )
        date += relativedelta(months=1)
    return result
