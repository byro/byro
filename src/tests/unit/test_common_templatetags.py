import pytest
from django.http.request import QueryDict
from django.utils import translation

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


@pytest.mark.django_db
def test_rejected_login_is_rendered_readably(user):
    entry = LogEntry.objects.create(
        content_object=user, user=user, action_type="byro.common.login.no_access"
    )

    with translation.override("en"):
        rendered = format_log_entry(entry)
    assert "Login rejected: account has no backend access" in rendered
    assert user.username in rendered
    # not just the technical action type of the default formatter
    assert "byro.common.login.no_access" not in rendered

    with translation.override("de"):
        rendered = format_log_entry(entry)
    assert "Anmeldung abgelehnt: Konto hat keinen Backend-Zugriff" in rendered


@pytest.mark.django_db
def test_oidc_permission_sync_is_rendered_readably(user):
    entry = LogEntry.objects.create(
        content_object=user,
        action_type="byro.common.user.oidc_permissions_synced",
        data={
            "source": "internal: oidc_group_sync",
            "changes": {"is_staff": [True, False], "is_superuser": [False, True]},
        },
    )

    with translation.override("en"):
        rendered = format_log_entry(entry)
        source = format_log_source(entry)
    assert "Permissions changed by OIDC group synchronization" in rendered
    assert user.username in rendered
    assert "is_staff" in rendered and "is_superuser" in rendered
    assert "byro.common.user.oidc_permissions_synced" not in rendered
    # shown as an automatic process, not as an action of the user
    assert source == '<span class="fa fa-gears"></span> oidc_group_sync'

    with translation.override("de"):
        rendered = format_log_entry(entry)
    assert "Rechte durch OIDC-Gruppensynchronisation geändert" in rendered
