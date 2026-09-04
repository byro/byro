import pytest
from dateutil.relativedelta import relativedelta
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils.timezone import now

from byro.mails.models import MemberPGPKey, PGPKeySource, PGPKeyStatus
from byro.members.models import Member

pytestmark = pytest.mark.usefixtures("configuration")


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
    assert (
        "\r\n{},{}\r\n{},{}\r\n".format(
            inactive_member.pk, inactive_member.name, member.pk, member.name
        )
        in content
    )


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
    member.refresh_from_db()
    assert not member.is_active


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
