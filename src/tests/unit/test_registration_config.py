from decimal import Decimal

import pytest
from django.utils import translation
from django.utils.timezone import now

from byro.common.forms.registration import (
    DEFAULT_FIELDS,
    DefaultDates,
    RegistrationConfigForm,
    get_mandatory_fields,
)
from byro.common.models import Configuration
from byro.members.forms import CreateMemberForm
from byro.members.models import FeeIntervals, Membership

MANDATORY_FIELDS = ["membership__start", "membership__interval", "membership__amount"]


def positions(*keys):
    return {f"{key}__position": str(index + 1) for index, key in enumerate(keys)}


def test_mandatory_fields_are_the_required_membership_fields():
    assert get_mandatory_fields() == MANDATORY_FIELDS


@pytest.mark.django_db
def test_empty_config_preselects_default_fields(configuration):
    form = RegistrationConfigForm()

    for index, key in enumerate(DEFAULT_FIELDS):
        assert form.fields[f"{key}__position"].initial == index + 1
    assert form.fields["membership__end__position"].initial is None
    assert (
        form.fields["membership__start__default_date"].initial
        == DefaultDates.BEGINNING_MONTH
    )
    assert list(form.fields_extra)[: len(DEFAULT_FIELDS)] == DEFAULT_FIELDS
    mandatory = [key for key, info in form.fields_extra.items() if info[2]]
    assert mandatory == MANDATORY_FIELDS


@pytest.mark.django_db
def test_existing_config_appends_missing_mandatory_fields(configuration):
    configuration.registration_form = [
        {"name": "member__name", "position": 1},
        {"name": "member__email", "position": 2},
    ]
    configuration.save()

    form = RegistrationConfigForm()

    assert form.fields["membership__start__position"].initial == 3
    assert form.fields["membership__interval__position"].initial == 4
    assert form.fields["membership__amount__position"].initial == 5
    assert form.fields["member__number__position"].initial is None
    assert (
        list(form.fields_extra)[:5]
        == ["member__name", "member__email"] + MANDATORY_FIELDS
    )


@pytest.mark.django_db
def test_mandatory_field_without_position_is_invalid(configuration):
    form = RegistrationConfigForm(data=positions("member__name"))

    with translation.override("en"):
        assert not form.is_valid()
        errors = form.non_field_errors()

    assert len(errors) == 1
    for verbose_name in ("start", "payment interval", "membership fee"):
        assert verbose_name in errors[0]


@pytest.mark.django_db
def test_duplicate_positions_are_reported(configuration):
    data = positions("member__name", *MANDATORY_FIELDS)
    data["member__email__position"] = data["member__name__position"]
    form = RegistrationConfigForm(data=data)

    with translation.override("en"):
        assert not form.is_valid()
        assert form.non_field_errors() == ["Every position must be unique!"]


@pytest.mark.django_db
def test_save_persists_mandatory_fields(configuration):
    form = RegistrationConfigForm(data=positions(*DEFAULT_FIELDS))

    assert form.is_valid(), form.errors
    form.save()

    saved = {
        entry["name"]: entry for entry in Configuration.get_solo().registration_form
    }
    assert set(saved) == set(DEFAULT_FIELDS)
    for key in MANDATORY_FIELDS:
        assert saved[key]["position"] == DEFAULT_FIELDS.index(key) + 1


@pytest.mark.django_db
def test_create_member_form_tolerates_entry_without_position(configuration):
    configuration.registration_form = [
        {"name": "member__name", "position": 1},
        {"name": "membership__start", "default_date": DefaultDates.TODAY},
    ]
    configuration.save()

    form = CreateMemberForm()

    assert form.fields["membership__start"].initial == now().date()


@pytest.mark.django_db
def test_create_member_form_adds_missing_mandatory_fields(configuration):
    configuration.registration_form = [{"name": "member__name", "position": 1}]
    configuration.save()

    form = CreateMemberForm()

    assert (
        list(form.fields)
        == [
            "member__name",
            "member__direct_address_name",
            "member__order_name",
        ]
        + MANDATORY_FIELDS
    )


@pytest.mark.django_db
def test_create_member_form_saves_membership_without_configured_fields(
    configuration,
):
    configuration.registration_form = [{"name": "member__name", "position": 1}]
    configuration.save()

    form = CreateMemberForm(
        data={
            "member__name": "Torsten Est",
            "member__direct_address_name": "Torsten",
            "member__order_name": "Est",
            "membership__start": "2026-09-01",
            "membership__interval": FeeIntervals.MONTHLY,
            "membership__amount": "10",
        }
    )

    assert form.is_valid(), form.errors
    form.save()

    membership = Membership.objects.get(member__name="Torsten Est")
    assert str(membership.start) == "2026-09-01"
    assert membership.interval == FeeIntervals.MONTHLY
    assert membership.amount == Decimal("10")


@pytest.mark.django_db
def test_create_member_form_stays_empty_without_config(configuration):
    configuration.registration_form = None
    configuration.save()

    assert CreateMemberForm().fields == {}
