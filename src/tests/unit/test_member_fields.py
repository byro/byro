import pytest

from byro.members.models import Field, Member


def test_internal_follow_path():
    # Test of an internal function, just to check that it works
    class A:
        class B:
            c = 3

        d = 1

        def e(self):
            class F:
                g = 4

            return F()

    a = A()

    assert Field._follow_path(a, "d") == (a, "d")
    assert Field._follow_path(a, "B.c") == (a.B, "c")

    o, p = Field._follow_path(a, "e().g")
    assert getattr(o, p) == 4

    # Negative tests
    assert Field._follow_path(a, "A.a") == (None, "a")
    assert Field._follow_path(a, "A().a") == (None, "a")
    assert Field._follow_path(a, "e().A.a") == (None, "a")


@pytest.mark.django_db
def test_member_field_reading(member, membership, inactive_member):
    f = Member.get_fields()

    assert "_internal_id" in f
    assert f["_internal_id"].computed
    assert f["_internal_id"].read_only
    assert f["_internal_id"].getter(member) == member.pk

    assert f["member__name"].getter(member) == member.name

    assert f["_internal_active"].getter(member) is True
    assert f["_internal_active"].getter(inactive_member) is False


@pytest.mark.django_db
def test_member_field_writing(member):
    f = Member.get_fields()

    assert member.name != "Fnord"
    f["member__name"].setter(member, "Fnord")
    assert member.name == "Fnord"


@pytest.mark.django_db
def test_member_field_writing_sepa_iban(member):
    f = Member.get_fields()

    f["MemberSepa__iban"].setter(member, "DE491234567890")
    assert member.profile_sepa.iban == "DE491234567890"
