import pytest
from django.http.request import QueryDict

from byro.common.models.log import LogEntry
from byro.common.templatetags.log_entry import format_log_entry, format_log_source
from byro.common.templatetags.url_replace import url_replace


class request:
    def __init__(self, get):
        self.GET = QueryDict(get)


@pytest.mark.parametrize(
    "GET,key,value,expected",
    (
        ("foo=bar", "foo", "baz", ["foo=baz"]),
        ("foo=bar", "fork", "baz", ["foo=bar", "fork=baz"]),
    ),
)
def test_templatetag_url_replace(GET, key, value, expected):
    result = url_replace(request(GET), key, value)
    assert all(e in result for e in expected)


@pytest.mark.django_db
def test_log_entry_formatting(mail_template, user):
    assert format_log_entry(
        LogEntry(
            content_object=mail_template,
            user=user,
            data={"source": "value"},
            action_type="action.type",
        )
    ) == 'action.type (<a href="/mails/templates/{}">Test Mail</a>)'.format(
        mail_template.pk
    )
    assert format_log_entry(
        LogEntry(
            content_object=user,
            user=user,
            data={"source": "value"},
            action_type="action.type",
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
                data={"source": "value"},
                action_type="action.type",
            )
        )
        == "value"
    )
    assert (
        format_log_source(
            LogEntry(
                content_object=mail_template,
                user=user,
                data={"source": "value"},
                action_type="action.type",
            )
        )
        == 'value (via <span class="fa fa-user"></span> regular_user)'
    )
