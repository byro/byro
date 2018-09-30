import pytest

from byro.common.models.log import LogEntry
from byro.office.templatetags.log_entry import (
    format_log_entry, format_log_source,
)


@pytest.mark.django_db
def test_log_entry_formatting(mail_template, user):
    assert (
        format_log_entry(
            LogEntry(
                content_object=mail_template,
                user=user,
                data={'source': 'value'},
                action_type='action.type',
            )
        )
        == 'action.type (Test Mail)'
    )
    assert format_log_entry(
        LogEntry(
            content_object=user,
            user=user,
            data={'source': 'value'},
            action_type='action.type',
        )
    ) == 'action.type (<a href="/settings/users/{u.id}/">{u.username}</a>)'.format(
        u=user
    )


@pytest.mark.django_db
def test_log_entry_source_formatting(mail_template, user):
    assert (
        format_log_source(
            LogEntry(
                content_object=mail_template,
                data={'source': 'value'},
                action_type='action.type',
            )
        )
        == 'value'
    )
    assert (
        format_log_source(
            LogEntry(
                content_object=mail_template,
                user=user,
                data={'source': 'value'},
                action_type='action.type',
            )
        )
        == 'value (via regular_user)'
    )
