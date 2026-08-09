import pytest
from django.urls import reverse

from byro.public.models import MemberChangeProposal, get_proposable_fields


def base_proposal_data(member):
    """POST data mirroring current values for every proposable field, so
    unchanged fields cause no diff regardless of which fields are editable."""
    data = {}
    for field_id, field in get_proposable_fields(member).items():
        value = field.getter(member)
        if value is None:
            value = ""
        elif hasattr(value, "isoformat"):
            value = value.isoformat()
        else:
            value = str(value)
        data[field_id] = value
    return data


def propose_url(member):
    return reverse(
        "public:memberpage:member.propose",
        kwargs={"secret_token": member.profile_memberpage.secret_token},
    )


# --- member page: submitting proposals ---------------------------------------


@pytest.mark.django_db
def test_propose_change_creates_proposal(member, membership, client, configuration):
    data = base_proposal_data(member)
    data["member__name"] = "New Name"
    response = client.post(propose_url(member), data)

    assert response.status_code == 302
    proposals = member.change_proposals.all()
    assert proposals.count() == 1
    assert proposals.first().field_id == "member__name"
    assert proposals.first().new_value == "New Name"
    # nothing was applied to the member itself
    member.refresh_from_db()
    assert member.name == "Jona Than"


@pytest.mark.django_db
def test_propose_unchanged_creates_nothing(member, membership, client, configuration):
    response = client.post(propose_url(member), base_proposal_data(member))
    assert response.status_code == 302
    assert member.change_proposals.count() == 0


@pytest.mark.django_db
def test_reproposing_same_field_overwrites(member, membership, client, configuration):
    data = base_proposal_data(member)
    data["member__email"] = "first@example.com"
    client.post(propose_url(member), data)
    data["member__email"] = "second@example.com"
    client.post(propose_url(member), data)

    proposals = member.change_proposals.filter(field_id="member__email")
    assert proposals.count() == 1
    assert proposals.first().new_value == "second@example.com"


@pytest.mark.django_db
def test_propose_ignores_non_allowlisted_fields(
    member, membership, client, configuration
):
    original_token = member.profile_memberpage.secret_token
    data = base_proposal_data(member)
    # crafted fields that must never become proposals
    data["memberpage__secret_token"] = "hacked"
    data["_internal_balance"] = "9999"
    data["member__number"] = "666"
    client.post(propose_url(member), data)

    assert member.change_proposals.count() == 0
    member.profile_memberpage.refresh_from_db()
    assert member.profile_memberpage.secret_token == original_token


@pytest.mark.django_db
def test_propose_invalid_date_rejected(member, membership, client, configuration):
    data = base_proposal_data(member)
    data["MemberProfile__birth_date"] = "not-a-date"
    client.post(propose_url(member), data)
    assert member.change_proposals.count() == 0


@pytest.mark.django_db
def test_dashboard_shows_proposal_form(member, membership, client, configuration):
    response = client.get(
        reverse(
            "public:memberpage:member.dashboard",
            kwargs={"secret_token": member.profile_memberpage.secret_token},
        )
    )
    content = response.content.decode()
    assert response.status_code == 200
    assert any(s in content for s in ["Propose changes", "Änderungen"])


# --- office: accepting / rejecting -------------------------------------------


@pytest.mark.django_db
def test_office_accept_applies_change(
    member, membership, logged_in_client, configuration
):
    proposal = MemberChangeProposal.objects.create(
        member=member, field_id="member__name", new_value="Accepted Name"
    )
    response = logged_in_client.post(
        reverse("office:members.data", kwargs={"pk": member.pk}),
        {f"accept_{proposal.pk}": "1"},
    )
    assert response.status_code == 302
    member.refresh_from_db()
    assert member.name == "Accepted Name"
    assert member.change_proposals.count() == 0


@pytest.mark.django_db
def test_office_accept_profile_field(
    member, membership, logged_in_client, configuration
):
    proposal = MemberChangeProposal.objects.create(
        member=member, field_id="MemberProfile__phone_number", new_value="+49 123"
    )
    logged_in_client.post(
        reverse("office:members.data", kwargs={"pk": member.pk}),
        {f"accept_{proposal.pk}": "1"},
    )
    member.profile_profile.refresh_from_db()
    assert member.profile_profile.phone_number == "+49 123"


@pytest.mark.django_db
def test_office_accept_sepa_account_owner(
    member_with_sepa_profile, membership, logged_in_client, configuration
):
    member = member_with_sepa_profile
    proposal = MemberChangeProposal.objects.create(
        member=member, field_id="MemberSepa__fullname", new_value="New Owner"
    )
    logged_in_client.post(
        reverse("office:members.data", kwargs={"pk": member.pk}),
        {f"accept_{proposal.pk}": "1"},
    )
    member.profile_sepa.refresh_from_db()
    assert member.profile_sepa.fullname == "New Owner"


@pytest.mark.django_db
def test_office_accept_sepa_iban_validated(
    member_with_sepa_profile, membership, logged_in_client, configuration
):
    member = member_with_sepa_profile
    # An invalid IBAN must not be applied (IBANField validation via formfield).
    proposal = MemberChangeProposal.objects.create(
        member=member, field_id="MemberSepa__iban", new_value="not-an-iban"
    )
    logged_in_client.post(
        reverse("office:members.data", kwargs={"pk": member.pk}),
        {f"accept_{proposal.pk}": "1"},
    )
    member.profile_sepa.refresh_from_db()
    assert member.profile_sepa.iban == "DE89370400440532013000"


@pytest.mark.django_db
def test_office_reject_discards_change(
    member, membership, logged_in_client, configuration
):
    proposal = MemberChangeProposal.objects.create(
        member=member, field_id="member__name", new_value="Rejected Name"
    )
    logged_in_client.post(
        reverse("office:members.data", kwargs={"pk": member.pk}),
        {f"reject_{proposal.pk}": "1"},
    )
    member.refresh_from_db()
    assert member.name == "Jona Than"
    assert member.change_proposals.count() == 0


@pytest.mark.django_db
def test_data_page_lists_proposals(member, membership, logged_in_client, configuration):
    MemberChangeProposal.objects.create(
        member=member, field_id="member__name", new_value="Proposed Name"
    )
    response = logged_in_client.get(
        reverse("office:members.data", kwargs={"pk": member.pk})
    )
    content = response.content.decode()
    assert response.status_code == 200
    assert "Proposed Name" in content


# --- member list: indicator + filter -----------------------------------------


@pytest.mark.django_db
def test_member_list_pending_filter(
    member, membership, inactive_member, logged_in_client, configuration
):
    MemberChangeProposal.objects.create(
        member=member, field_id="member__name", new_value="X"
    )
    response = logged_in_client.get(reverse("office:members.list") + "?filter=pending")
    content = response.content.decode()
    assert response.status_code == 200
    assert member.name in content
    assert inactive_member.name not in content


@pytest.mark.django_db
def test_member_list_shows_indicator(
    member, membership, logged_in_client, configuration
):
    MemberChangeProposal.objects.create(
        member=member, field_id="member__name", new_value="X"
    )
    response = logged_in_client.get(reverse("office:members.list"))
    content = response.content.decode()
    assert "fa-exclamation-circle" in content
