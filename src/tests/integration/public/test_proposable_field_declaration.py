import pytest

from byro.public.models import get_proposable_fields


@pytest.mark.django_db
def test_declared_fields_are_proposable(member, member_with_sepa_profile):
    proposable = set(get_proposable_fields(member))
    # Declared on Member and MemberProfile:
    assert "member__name" in proposable
    assert "member__address" in proposable
    assert "member__email" in proposable
    assert "MemberProfile__nick" in proposable
    assert "MemberProfile__birth_date" in proposable
    assert "MemberProfile__phone_number" in proposable


@pytest.mark.django_db
def test_undeclared_fields_are_not_proposable(member):
    proposable = set(get_proposable_fields(member))
    # Core fields not opted in:
    assert "member__number" not in proposable
    assert "member__order_name" not in proposable
    # Computed / internal fields:
    assert "_internal_balance" not in proposable


@pytest.mark.django_db
def test_sepa_bank_data_is_not_proposable(member_with_sepa_profile):
    # The SEPA plugin declares member_editable_fields = (); its bank data must
    # never be member-editable.
    proposable = set(get_proposable_fields(member_with_sepa_profile))
    assert not any(field_id.startswith("MemberSepa__") for field_id in proposable)


@pytest.mark.django_db
def test_flag_follows_model_declaration(member, monkeypatch):
    # A plugin opting a field in makes it proposable; opting out removes it.
    from byro.plugins.profile.models import MemberProfile

    monkeypatch.setattr(MemberProfile, "member_editable_fields", ("nick",))
    proposable = set(get_proposable_fields(member))
    assert "MemberProfile__nick" in proposable
    assert "MemberProfile__phone_number" not in proposable


@pytest.mark.django_db
def test_declaring_missing_field_is_ignored(member, monkeypatch):
    # A declared field name that does not exist on the model (typo, or a field a
    # plugin has not added yet) must be silently ignored, not crash.
    from byro.plugins.profile.models import MemberProfile

    monkeypatch.setattr(
        MemberProfile, "member_editable_fields", ("nick", "does_not_exist")
    )
    proposable = set(get_proposable_fields(member))
    assert "MemberProfile__nick" in proposable
    assert not any("does_not_exist" in field_id for field_id in proposable)


@pytest.mark.django_db
def test_model_without_declaration_is_ignored(member, monkeypatch):
    # A profile model that does not declare member_editable_fields at all
    # contributes no proposable fields (getattr default), without error.
    from byro.plugins.profile.models import MemberProfile

    monkeypatch.delattr(MemberProfile, "member_editable_fields", raising=False)
    proposable = set(get_proposable_fields(member))
    assert not any(field_id.startswith("MemberProfile__") for field_id in proposable)
