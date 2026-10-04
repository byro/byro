import threading

import pytest
from dateutil.relativedelta import relativedelta
from django.contrib.messages import get_messages
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import include, path, reverse
from django.utils.timezone import now

from byro.bookkeeping.models import Transaction
from byro.common.models import LogEntry
from byro.mails.models import MemberPGPKey, PGPKeySource, PGPKeyStatus
from byro.members.models import Member, Membership
from byro.office.views import members as members_views

pytestmark = pytest.mark.usefixtures("configuration")

# URLconf for tests marked with ``pytest.mark.urls(__name__)``: the regular
# byro URLs plus a second, unnamed path to the member list.
urlpatterns = [
    path("members/list-alias", members_views.MemberListView.as_view()),
    path("", include("byro.urls")),
]


@pytest.mark.django_db
def test_members_list(member, membership, inactive_member, logged_in_client):
    response = logged_in_client.get(reverse("office:members.list"))
    content = response.content.decode()
    assert response.status_code == 200, content
    assert member.name in content
    assert inactive_member.name not in content


@pytest.mark.django_db
def test_filtered_members_list(member, membership, inactive_member, logged_in_client):
    response = logged_in_client.get(
        reverse("office:members.list") + "?filter=all&q=" + member.name[:4]
    )
    content = response.content.decode()
    assert response.status_code == 200, content
    assert member.name in content
    assert inactive_member.name not in content


@pytest.mark.django_db
def test_inactive_members_list(member, membership, inactive_member, logged_in_client):
    response = logged_in_client.get(reverse("office:members.list") + "?filter=inactive")
    content = response.content.decode()
    assert response.status_code == 200, content
    assert member.name not in content
    assert inactive_member.name in content


@pytest.mark.django_db
def test_all_members_list(member, membership, inactive_member, logged_in_client):
    response = logged_in_client.get(reverse("office:members.list") + "?filter=all")
    content = response.content.decode()
    assert response.status_code == 200, content
    assert member.name in content
    assert inactive_member.name in content


@pytest.fixture
def balance_refresh(monkeypatch):
    started = threading.Event()
    monkeypatch.setattr(members_views, "_run_balance_refresh", started.set)
    yield started
    cache.delete(members_views._BALANCE_REFRESH_LOCK)


@pytest.mark.django_db
def test_members_list_post_starts_balance_refresh(logged_in_client, balance_refresh):
    response = logged_in_client.post(
        reverse("office:members.list"),
        query_params={"filter": "all", "next": "https://evil.example/"},
    )
    assert response.status_code == 302
    assert response["Location"] == reverse("office:members.list")
    assert balance_refresh.wait(timeout=5)
    assert [str(message) for message in get_messages(response.wsgi_request)] == [
        "Balance refresh has been started in the background."
    ]


@pytest.mark.django_db
@pytest.mark.urls(__name__)
def test_members_list_post_redirects_to_named_route_from_other_path(
    logged_in_client, balance_refresh
):
    response = logged_in_client.post("/members/list-alias")
    assert response.status_code == 302
    assert response["Location"] == reverse("office:members.list")
    assert response["Location"] == "/members/list"


@pytest.mark.django_db
def test_members_list_post_while_balance_refresh_is_running(
    logged_in_client, balance_refresh
):
    cache.add(members_views._BALANCE_REFRESH_LOCK, True)
    response = logged_in_client.post(reverse("office:members.list"))
    assert response.status_code == 302
    assert response["Location"] == reverse("office:members.list")
    assert not balance_refresh.is_set()
    assert [str(message) for message in get_messages(response.wsgi_request)] == [
        "Balance refresh is already running in the background."
    ]


@pytest.mark.django_db
def test_member_view(member, membership, logged_in_client):
    response = logged_in_client.get(
        reverse("office:members.dashboard", kwargs={"pk": member.pk})
    )
    content = response.content.decode()
    assert response.status_code == 200, content
    assert member.name in content


@pytest.mark.django_db
@override_settings(BYRO_PGP_BACKEND="")
def test_member_pgp_keyserver_import_view(member, membership, logged_in_client):
    response = logged_in_client.post(
        reverse("office:members.pgp", kwargs={"pk": member.pk}),
        {
            "fingerprint-fingerprint": "0123456789ABCDEF0123456789ABCDEF01234567",
            "submit_fingerprint": "",
        },
    )

    assert response.status_code == 302
    key = member.pgp_keys.get()
    assert key.source == PGPKeySource.KEYSERVER
    assert key.status == PGPKeyStatus.PENDING


@pytest.mark.django_db
@pytest.mark.parametrize(
    "data, form_name",
    [
        (
            {
                "fingerprint-fingerprint": "not a fingerprint",
                "submit_fingerprint": "",
            },
            "fingerprint_form",
        ),
        (
            {
                "upload-fingerprint": "not a fingerprint",
                "upload-public_key": "public key",
                "submit_upload": "",
            },
            "upload_form",
        ),
    ],
)
def test_member_pgp_view_shows_invalid_form_errors(
    member, membership, logged_in_client, data, form_name
):
    response = logged_in_client.post(
        reverse("office:members.pgp", kwargs={"pk": member.pk}), data
    )

    form = response.context[form_name]
    assert response.status_code == 200
    assert form.is_bound
    assert form.errors
    assert form["fingerprint"].value() == "not a fingerprint"


@pytest.mark.django_db
def test_member_pgp_key_delete_view(member, membership, logged_in_client):
    key = MemberPGPKey.objects.create(
        member=member,
        fingerprint="0123456789ABCDEF0123456789ABCDEF01234567",
        status=PGPKeyStatus.VALID,
    )

    response = logged_in_client.post(
        reverse("office:members.pgp", kwargs={"pk": member.pk}),
        {"delete_key": str(key.pk)},
    )

    assert response.status_code == 302
    assert not member.pgp_keys.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "action, key_pk", [("deactivate_key", "not-a-key-id"), ("delete_key", "999999")]
)
def test_member_pgp_key_actions_handle_invalid_key_ids(
    member, membership, logged_in_client, action, key_pk
):
    response = logged_in_client.post(
        reverse("office:members.pgp", kwargs={"pk": member.pk}), {action: key_pk}
    )

    assert response.status_code == 302
    assert not member.pgp_keys.exists()


@pytest.mark.django_db
def test_member_pgp_key_actions_do_not_modify_another_members_key(
    member, membership, inactive_member, logged_in_client
):
    key = MemberPGPKey.objects.create(
        member=inactive_member,
        fingerprint="0123456789ABCDEF0123456789ABCDEF01234567",
        status=PGPKeyStatus.VALID,
    )

    response = logged_in_client.post(
        reverse("office:members.pgp", kwargs={"pk": member.pk}),
        {"delete_key": str(key.pk)},
    )

    assert response.status_code == 302
    assert MemberPGPKey.objects.filter(pk=key.pk).exists()


@pytest.mark.django_db
def test_member_view_different_public_address(
    member, membership, logged_in_client, configuration
):
    configuration.public_base_url = "https://complicated.long.url.example.org"
    configuration.save()
    response = logged_in_client.get(
        reverse("office:members.dashboard", kwargs={"pk": member.pk})
    )
    content = response.content.decode()
    assert response.status_code == 200, content
    assert member.name in content
    assert configuration.public_base_url in content


@pytest.mark.django_db
def test_members_export_list_csv(member, membership, inactive_member, logged_in_client):
    response = logged_in_client.post(
        reverse("office:members.list.export"),
        {
            "member_filter": "all",
            "export_format": "csv",
            "field_list": ["_internal_id", "member__name"],
        },
    )
    content = b"".join(response.streaming_content).decode()
    assert response.status_code == 200, content
    assert response["Content-Type"].startswith("text/csv")
    assert response["Content-Disposition"].startswith("attachment; ")
    assert (
        "\r\n{},{}\r\n{},{}\r\n".format(
            inactive_member.pk, inactive_member.name, member.pk, member.name
        )
        in content
    )


@pytest.mark.django_db
def test_members_export_list_csv_de(
    member, membership, inactive_member, logged_in_client
):
    response = logged_in_client.post(
        reverse("office:members.list.export"),
        {
            "member_filter": "all",
            "export_format": "csv_de",
            "field_list": ["_internal_id", "member__name"],
        },
    )
    content = b"".join(response.streaming_content).decode()
    assert response.status_code == 200, content
    assert response["Content-Type"].startswith("text/csv")
    assert response["Content-Disposition"].startswith("attachment; ")
    assert (
        "\r\n{};{}\r\n{};{}\r\n".format(
            inactive_member.pk, inactive_member.name, member.pk, member.name
        )
        in content
    )


@pytest.mark.django_db
def test_members_export_list_rejects_unsupported_format(member, logged_in_client):
    response = logged_in_client.post(
        reverse("office:members.list.export"),
        {
            "member_filter": "all",
            "export_format": "xlsx",
            "field_list": ["_internal_id", "member__name"],
        },
    )
    assert response.status_code == 200
    assert "Content-Disposition" not in response
    assert "export_format" in response.context["form"].errors
    assert not LogEntry.objects.filter(action_type="byro.members.export").exists()


@pytest.mark.django_db
def test_members_adjust_account_initial(member, logged_in_client):
    assert member.balance == 0
    response = logged_in_client.post(
        reverse("office:members.operations", kwargs={"pk": member.pk}),
        {
            "member_account_adjustment-date": str(now().date()),
            "member_account_adjustment-adjustment_reason": "initial",
            "member_account_adjustment-adjustment_type": "absolute",
            "member_account_adjustment-amount": "23",
            "submit_member_account_adjustment_adjust": "adjust",
        },
    )
    content = response.content.decode()
    assert response.status_code == 302, content
    assert response["Location"] == reverse(
        "office:members.operations", kwargs={"pk": member.pk}
    )
    assert member.balance == 23


@pytest.mark.django_db
def test_members_adjust_account_waiver(member, logged_in_client):
    assert member.balance == 0
    response = logged_in_client.post(
        reverse("office:members.operations", kwargs={"pk": member.pk}),
        {
            "member_account_adjustment-date": str(now().date()),
            "member_account_adjustment-adjustment_reason": "waiver",
            "member_account_adjustment-adjustment_type": "relative",
            "member_account_adjustment-amount": "-2",
            "submit_member_account_adjustment_adjust": "adjust",
        },
    )
    content = response.content.decode()
    assert response.status_code == 302, content
    assert response["Location"] == reverse(
        "office:members.operations", kwargs={"pk": member.pk}
    )
    assert member.balance == 2


@pytest.mark.django_db
def test_members_end_membership(member, membership, logged_in_client):
    assert member.is_active
    response = logged_in_client.post(
        reverse("office:members.operations", kwargs={"pk": member.pk}),
        {
            f"ms_{membership.pk}_leave-end": (now() + relativedelta(days=-1)).date(),
            f"submit_ms_{membership.pk}_leave_end": "end",
        },
    )
    content = response.content.decode()
    assert response.status_code == 302, content
    assert response["Location"] == reverse(
        "office:members.operations", kwargs={"pk": member.pk}
    )
    member.refresh_from_db()
    assert not member.is_active


@pytest.mark.django_db
def test_members_operations_redirect_ignores_query_string(member, logged_in_client):
    response = logged_in_client.post(
        reverse("office:members.operations", kwargs={"pk": member.pk}),
        query_params={"next": "https://evil.example/"},
    )
    assert response.status_code == 302
    assert response["Location"] == reverse(
        "office:members.operations", kwargs={"pk": member.pk}
    )


@pytest.mark.django_db
def test_member_download_and_edit(member, membership, logged_in_client):
    response = logged_in_client.post(
        reverse("office:members.list.export"),
        {
            "field_list": ["_internal_id", "member__name", "MemberSepa__iban"],
            "member_filter": "all",
            "export_format": "csv",
        },
    )

    assert response["Content-Type"].startswith("text/csv")

    response_body = b"".join(response.streaming_content)

    assert member.name.encode("utf-8") in response_body

    new_body = response_body.replace(
        f",{member.name},".encode(),
        ",{},{}".format("Fnord!", "DE11520513735120710131").encode("utf-8"),
    )

    new_response = logged_in_client.post(
        reverse("office:members.list.import"),
        {
            "importer": "byro.office.members.import.default_csv",
            "upload_file": SimpleUploadedFile(
                "members.csv", new_body, content_type=response["Content-Type"]
            ),
        },
    )

    assert new_response.status_code == 302

    new_member = Member.objects.filter(pk=member.pk).first()
    assert new_member.name == "Fnord!"
    assert new_member.profile_sepa.iban == "DE11520513735120710131"


def post_member_import(client, body):
    return client.post(
        reverse("office:members.list.import"),
        {
            "importer": "byro.office.members.import.default_csv",
            "upload_file": SimpleUploadedFile(
                "members.csv", body.encode(), content_type="text/csv"
            ),
        },
        query_params={"next": "https://evil.example/"},
    )


@pytest.mark.django_db
def test_member_import_unmapped_column_redirects_to_import(logged_in_client):
    response = post_member_import(logged_in_client, "No such column\r\nvalue\r\n")

    assert response.status_code == 302
    assert response["Location"] == reverse("office:members.list.import")
    assert [str(message) for message in get_messages(response.wsgi_request)] == [
        "Couldn't map input column 'No such column' to field"
    ]


@pytest.mark.django_db
def test_member_import_balance_without_timestamp_redirects_to_import(
    logged_in_client,
):
    fields = Member.get_fields()
    balance = fields["_internal_balance"].name
    timestamp = fields["_internal_last_transaction"].name
    response = post_member_import(
        logged_in_client,
        "{},{}\r\nJane Doe,10\r\n".format(fields["member__name"].name, balance),
    )

    assert response.status_code == 302
    assert response["Location"] == reverse("office:members.list.import")
    assert [str(message) for message in get_messages(response.wsgi_request)] == [
        "Either both or none columns has to be given: '{}' and '{}'".format(
            balance, timestamp
        )
    ]
    assert not Member.all_objects.exists()


@pytest.mark.django_db
def test_member_import_failure_rolls_back_previous_rows(member, logged_in_client):
    fields = Member.get_fields()
    previous_logs = set(LogEntry.objects.values_list("pk", flat=True))
    previous_transactions = set(Transaction.objects.values_list("pk", flat=True))
    previous_memberships = set(Membership.objects.values_list("pk", flat=True))
    response = post_member_import(
        logged_in_client,
        "{},{},{},{},{},{}\r\n"
        "Earlier member,10,2026-01-01,2026-01-01,20,12\r\n"
        "Failing member,5,,,,\r\n".format(
            fields["member__name"].name,
            fields["_internal_balance"].name,
            fields["_internal_last_transaction"].name,
            fields["membership__start"].name,
            fields["membership__amount"].name,
            fields["membership__interval"].name,
        ),
    )

    assert response.status_code == 302
    assert response["Location"] == reverse("office:members.list.import")
    member.refresh_from_db()
    assert member.name == "Jona Than"
    assert list(Member.all_objects.values_list("pk", flat=True)) == [member.pk]
    assert set(Membership.objects.values_list("pk", flat=True)) == previous_memberships
    assert (
        set(Transaction.objects.values_list("pk", flat=True)) == previous_transactions
    )
    assert (
        set(
            LogEntry.objects.exclude(action_type="byro.members.import").values_list(
                "pk", flat=True
            )
        )
        == previous_logs
    )


@pytest.mark.django_db
def test_member_import_with_balance_and_timestamp_commits(logged_in_client):
    fields = Member.get_fields()
    response = post_member_import(
        logged_in_client,
        "{},{},{}\r\nJane Doe,10,2026-01-01\r\n".format(
            fields["member__name"].name,
            fields["_internal_balance"].name,
            fields["_internal_last_transaction"].name,
        ),
    )

    assert response.status_code == 302
    assert response["Location"] == reverse("office:members.list")
    imported = Member.all_objects.get(name="Jane Doe")
    assert imported.balance == 10
    assert imported.log_entries().filter(action_type="byro.members.created").exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "name,search",
    (
        ("Jona Than", "Jona"),
        ('<span id="byro-xss-test">XSS test</span>', "byro-xss-test"),
        (
            "<img src=x onerror=\"document.documentElement.dataset.byroXss='executed'\">",
            "onerror",
        ),
    ),
)
def test_members_typeahead_returns_name_unchanged_as_json(
    member, logged_in_client, name, search
):
    # Markup is valid member data: the endpoint returns it unchanged as JSON and
    # leaves the output encoding to the consumer. This covers the data contract
    # only, not the rendering in office/members.js, which needs a browser.
    member.name = name
    member.full_clean()
    member.save()

    response = logged_in_client.get(
        reverse("office:members.typeahead"), {"search": search}
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    assert response.json() == {
        "count": 1,
        "results": [{"id": member.pk, "nick": None, "name": name}],
    }
