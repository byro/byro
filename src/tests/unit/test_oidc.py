import json

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.models.signals import post_save
from django.test.utils import CaptureQueriesContext

from byro.common import oidc
from byro.common.models import LogEntry
from byro.common.oidc import SYNCED_FLAGS

STAFF = "byro-staff"
SUPER = "byro-superusers"
MISSING = object()
SYNCED = "byro.common.user.oidc_permissions_synced"


@pytest.fixture
def oidc_settings(settings):
    settings.OIDC_USERNAME_FIELD = "preferred_username"
    settings.OIDC_STAFF_GROUP = ""
    settings.OIDC_SUPERUSER_GROUP = ""
    settings.OIDC_SYNC_GROUPS = False
    settings.OIDC_GROUP_CONFLICT = False
    settings.OIDC_AUTO_CREATE_ACCOUNT = True
    return settings


@pytest.fixture(autouse=True)
def userinfo(monkeypatch):
    """The userinfo endpoint. Any request fails the test unless a response
    was set; ``calls`` counts the requests."""

    class Userinfo:
        response = None
        calls = 0

    def get_userinfo(access_token):
        Userinfo.calls += 1
        if Userinfo.response is None:
            raise AssertionError("unexpected userinfo request")
        if isinstance(Userinfo.response, Exception):
            raise Userinfo.response
        return Userinfo.response

    monkeypatch.setattr(oidc, "get_userinfo", get_userinfo)
    return Userinfo


@pytest.fixture
def account():
    def create(is_staff=False, is_superuser=False, **kwargs):
        return get_user_model().objects.create(
            username="known", is_staff=is_staff, is_superuser=is_superuser, **kwargs
        )

    return create


def login(username, groups=MISSING):
    claims = {"preferred_username": username}
    if groups is not MISSING:
        claims["groups"] = groups
    return oidc.get_or_create_user(claims, "token")


def flags(user):
    user.refresh_from_db()
    return user.is_staff, user.is_superuser


def synced_entries():
    return LogEntry.objects.filter(action_type=SYNCED)


# -- account creation --------------------------------------------------------


@pytest.mark.parametrize(
    "staff_group,superuser_group,groups,expected",
    (
        # no mapping: regular backend access, never superuser (as in #531)
        pytest.param("", "", MISSING, (True, False), id="no-mapping"),
        pytest.param("", "", [STAFF, SUPER], (True, False), id="no-mapping-groups"),
        # staff group only: it is the gate, superuser is never granted
        pytest.param(STAFF, "", [STAFF], (True, False), id="staff-only-member"),
        pytest.param(STAFF, "", [STAFF, SUPER], (True, False), id="staff-only-both"),
        pytest.param(STAFF, "", [SUPER], None, id="staff-only-other-group"),
        pytest.param(STAFF, "", [], None, id="staff-only-no-group"),
        # superuser group only: no gate, staff by default
        pytest.param("", SUPER, [SUPER], (True, True), id="super-only-member"),
        pytest.param("", SUPER, [STAFF], (True, False), id="super-only-other-group"),
        pytest.param("", SUPER, [], (True, False), id="super-only-no-group"),
        # both groups: each flag follows its own group
        pytest.param(STAFF, SUPER, [STAFF], (True, False), id="both-staff"),
        pytest.param(STAFF, SUPER, [SUPER], (False, True), id="both-superuser"),
        pytest.param(STAFF, SUPER, [STAFF, SUPER], (True, True), id="both-both"),
        pytest.param(STAFF, SUPER, [], None, id="both-no-group"),
    ),
)
@pytest.mark.django_db
def test_account_creation(
    oidc_settings, staff_group, superuser_group, groups, expected
):
    oidc_settings.OIDC_STAFF_GROUP = staff_group
    oidc_settings.OIDC_SUPERUSER_GROUP = superuser_group
    User = get_user_model()

    if expected is None:
        with pytest.raises(oidc.OIDCError):
            login("newcomer", groups)
        assert not User.objects.filter(username="newcomer").exists()
        return

    user = login("newcomer", groups)
    assert flags(user) == expected
    assert user.is_active
    assert not user.has_usable_password()
    # creating an account is not a synchronization
    assert not synced_entries().exists()


@pytest.mark.parametrize("sync_groups", (True, False))
@pytest.mark.django_db
def test_no_account_is_created_without_auto_creation(oidc_settings, sync_groups):
    oidc_settings.OIDC_AUTO_CREATE_ACCOUNT = False
    oidc_settings.OIDC_STAFF_GROUP = STAFF
    oidc_settings.OIDC_SYNC_GROUPS = sync_groups

    with pytest.raises(oidc.OIDCError):
        login("newcomer", [STAFF])
    assert not get_user_model().objects.filter(username="newcomer").exists()


@pytest.mark.django_db
def test_existing_accounts_work_without_auto_creation(oidc_settings, account):
    oidc_settings.OIDC_AUTO_CREATE_ACCOUNT = False
    oidc_settings.OIDC_STAFF_GROUP = STAFF
    oidc_settings.OIDC_SYNC_GROUPS = True
    user = account()

    assert login("known", [STAFF]).pk == user.pk
    assert flags(user) == (True, False)


# -- existing accounts without synchronization -------------------------------


@pytest.mark.parametrize(
    "is_staff,is_superuser",
    ((False, False), (True, False), (False, True), (True, True)),
)
@pytest.mark.parametrize("groups", ([STAFF], [SUPER], [STAFF, SUPER]))
@pytest.mark.django_db
def test_without_sync_existing_accounts_are_never_changed(
    oidc_settings, account, is_staff, is_superuser, groups
):
    oidc_settings.OIDC_STAFF_GROUP = STAFF
    oidc_settings.OIDC_SUPERUSER_GROUP = SUPER
    user = account(is_staff=is_staff, is_superuser=is_superuser)

    assert login("known", groups).pk == user.pk
    assert flags(user) == (is_staff, is_superuser)
    assert not synced_entries().exists()


@pytest.mark.django_db
def test_without_sync_the_staff_group_still_limits_who_may_sign_in(
    oidc_settings, account
):
    # this is what the deprecated admin_group has always done
    oidc_settings.OIDC_STAFF_GROUP = STAFF
    user = account(is_staff=True, is_superuser=True)

    with pytest.raises(oidc.OIDCError):
        login("known", ["somewhere-else"])
    assert flags(user) == (True, True)
    assert login("known", [STAFF]).pk == user.pk


@pytest.mark.django_db
def test_superuser_group_is_a_second_way_through_the_gate(oidc_settings, account):
    oidc_settings.OIDC_STAFF_GROUP = STAFF
    oidc_settings.OIDC_SUPERUSER_GROUP = SUPER
    user = account(is_staff=True)

    assert login("known", [SUPER]).pk == user.pk
    # without sync the membership grants nothing
    assert flags(user) == (True, False)


@pytest.mark.django_db
def test_without_staff_group_everybody_may_sign_in(oidc_settings, account):
    oidc_settings.OIDC_SUPERUSER_GROUP = SUPER
    user = account(is_staff=True)

    assert login("known", []).pk == user.pk
    assert login("known", ["somewhere-else"]).pk == user.pk


# -- synchronization ---------------------------------------------------------


@pytest.fixture
def sync(oidc_settings):
    oidc_settings.OIDC_SYNC_GROUPS = True
    return oidc_settings


@pytest.mark.django_db
def test_sync_grants_and_revokes_staff(sync, account):
    sync.OIDC_STAFF_GROUP = STAFF
    sync.OIDC_SUPERUSER_GROUP = SUPER
    user = account()

    login("known", [STAFF])
    assert flags(user) == (True, False)

    # still allowed in through the superuser group, but no longer staff
    login("known", [SUPER])
    assert flags(user) == (False, True)


@pytest.mark.django_db
def test_sync_grants_and_revokes_superuser(sync, account):
    sync.OIDC_SUPERUSER_GROUP = SUPER
    user = account(is_staff=True)

    login("known", [SUPER])
    assert flags(user) == (True, True)

    login("known", [])
    assert flags(user) == (True, False)


@pytest.mark.django_db
def test_sync_leaves_unconfigured_staff_dimension_alone(sync, account):
    sync.OIDC_SUPERUSER_GROUP = SUPER

    user = account(is_staff=True, is_superuser=True)
    login("known", [])
    assert flags(user) == (True, False)

    user.is_staff = False
    user.save()
    login("known", [STAFF, SUPER])
    # being in a group called like a staff group means nothing here
    assert flags(user) == (False, True)


@pytest.mark.django_db
def test_sync_leaves_unconfigured_superuser_dimension_alone(sync, account):
    sync.OIDC_STAFF_GROUP = STAFF

    user = account(is_staff=False, is_superuser=True)
    login("known", [STAFF, SUPER])
    assert flags(user) == (True, True)

    user.is_superuser = False
    user.save()
    login("known", [STAFF, SUPER])
    assert flags(user) == (True, False)


@pytest.mark.django_db
def test_sync_without_groups_changes_nothing(sync, account):
    user = account(is_staff=True, is_superuser=True)

    login("known", [])
    assert flags(user) == (True, True)
    assert not synced_entries().exists()


@pytest.mark.parametrize("superuser_group", ("", SUPER))
@pytest.mark.django_db
def test_revoked_roles_are_saved_before_the_login_is_rejected(
    sync, account, superuser_group
):
    sync.OIDC_STAFF_GROUP = STAFF
    sync.OIDC_SUPERUSER_GROUP = superuser_group
    user = account(is_staff=True, is_superuser=bool(superuser_group))

    # removed from every group at the provider
    with pytest.raises(oidc.OIDCError):
        login("known", [])

    # the rejection must not leave the old permissions behind
    assert flags(user) == (False, False)
    assert synced_entries().count() == 1


@pytest.mark.django_db
def test_staff_group_alone_does_not_manage_superusers(sync, account):
    sync.OIDC_STAFF_GROUP = STAFF
    user = account(is_staff=True, is_superuser=True)

    with pytest.raises(oidc.OIDCError):
        login("known", [])

    # staff is revoked and OIDC refused, the unmapped superuser flag stays
    assert flags(user) == (False, True)


@pytest.mark.django_db
def test_sync_may_remove_the_last_superuser(sync, account):
    sync.OIDC_SUPERUSER_GROUP = SUPER
    user = account(is_staff=True, is_superuser=True)
    assert get_user_model().objects.filter(is_superuser=True).count() == 1

    # no lockout protection: the provider is the source of truth
    login("known", [])

    assert flags(user) == (True, False)
    assert not get_user_model().objects.filter(is_superuser=True).exists()


@pytest.mark.parametrize("groups", ([], [STAFF, SUPER]))
@pytest.mark.django_db
def test_inactive_accounts_are_never_changed(sync, account, groups):
    sync.OIDC_SUPERUSER_GROUP = SUPER
    user = account(is_staff=True, is_superuser=False, is_active=False)

    returned = login("known", groups)

    # returned for the caller to reject, untouched
    assert returned.pk == user.pk
    assert not returned.is_active
    assert flags(user) == (True, False)
    assert not synced_entries().exists()


@pytest.mark.django_db
def test_inactive_account_outside_the_groups_is_rejected_unchanged(sync, account):
    sync.OIDC_STAFF_GROUP = STAFF
    user = account(is_staff=True, is_superuser=True, is_active=False)

    with pytest.raises(oidc.OIDCError):
        login("known", [])
    assert flags(user) == (True, True)


# -- concurrent changes ------------------------------------------------------


@pytest.fixture
def concurrent_change(monkeypatch):
    """Let another request change the account after the OIDC login has read
    it and before the synchronization runs: exactly the window in which an
    outdated object could be written back."""

    def arrange(**changes):
        original = oidc.sync_permissions

        def sync_after_other_request(user, **kwargs):
            get_user_model().objects.filter(pk=user.pk).update(**changes)
            return original(user, **kwargs)

        monkeypatch.setattr(oidc, "sync_permissions", sync_after_other_request)

    return arrange


@pytest.mark.django_db
def test_sync_does_not_restore_concurrently_revoked_superuser(
    sync, account, concurrent_change
):
    # only the staff dimension is synchronized
    sync.OIDC_STAFF_GROUP = STAFF
    user = account(is_staff=True, is_superuser=True)
    concurrent_change(is_superuser=False)

    # the user left the staff group; the login is rejected afterwards
    with pytest.raises(oidc.OIDCError):
        login("known", [])

    assert flags(user) == (False, False)
    # the log shows what was really stored before and after
    assert synced_entries().get().data["changes"] == {
        "is_staff": [True, False],
        "is_superuser": [False, False],
    }


@pytest.mark.django_db
def test_sync_without_own_change_keeps_concurrently_revoked_superuser(
    sync, account, concurrent_change
):
    sync.OIDC_STAFF_GROUP = STAFF
    user = account(is_staff=True, is_superuser=True)
    concurrent_change(is_superuser=False)

    returned = login("known", [STAFF])

    assert flags(user) == (True, False)
    assert not synced_entries().exists()
    # the caller decides about access with the stored state, not the old one
    assert (returned.is_staff, returned.is_superuser) == (True, False)


@pytest.mark.parametrize(
    "groups,expected,logged_superuser",
    (([], (False, False), [True, False]), ([SUPER], (False, True), [True, True])),
)
@pytest.mark.django_db
def test_sync_does_not_restore_concurrently_revoked_staff(
    sync, account, concurrent_change, groups, expected, logged_superuser
):
    # the reverse case: only the superuser dimension is synchronized
    sync.OIDC_SUPERUSER_GROUP = SUPER
    user = account(is_staff=True, is_superuser=True)
    concurrent_change(is_staff=False)

    returned = login("known", groups)

    assert flags(user) == expected
    assert (returned.is_staff, returned.is_superuser) == expected
    if logged_superuser[0] == logged_superuser[1]:
        assert not synced_entries().exists()
    else:
        assert synced_entries().get().data["changes"] == {
            "is_staff": [False, False],
            "is_superuser": logged_superuser,
        }


@pytest.mark.django_db
def test_sync_ignores_the_outdated_object_it_is_given(account):
    user = account(is_staff=True, is_superuser=True)
    outdated = get_user_model().objects.get(pk=user.pk)
    get_user_model().objects.filter(pk=user.pk).update(is_superuser=False)

    assert oidc.sync_permissions(outdated, is_staff=False) is True

    assert flags(user) == (False, False)
    # and the object is brought up to date
    assert (outdated.is_staff, outdated.is_superuser) == (False, False)


@pytest.mark.parametrize(
    "start,wanted,written",
    (
        # both dimensions mapped, only one differs: only that one is written
        ((True, True), {"is_staff": False, "is_superuser": True}, {"is_staff"}),
        ((True, True), {"is_staff": True, "is_superuser": False}, {"is_superuser"}),
        ((True, True), {"is_staff": False, "is_superuser": False}, set(SYNCED_FLAGS)),
        # an unmapped dimension is never part of the write
        ((True, True), {"is_staff": False}, {"is_staff"}),
        ((False, True), {"is_superuser": False}, {"is_superuser"}),
    ),
)
@pytest.mark.django_db
def test_sync_only_writes_mapped_fields_that_changed(account, start, wanted, written):
    user = account(is_staff=start[0], is_superuser=start[1])
    saves = []

    def record(sender, instance, update_fields, **kwargs):
        saves.append(update_fields)

    post_save.connect(record, sender=get_user_model(), dispatch_uid="test-sync")
    try:
        assert oidc.sync_permissions(user, **wanted) is True
    finally:
        post_save.disconnect(sender=get_user_model(), dispatch_uid="test-sync")

    assert saves == [frozenset(written)]


@pytest.mark.django_db
def test_sync_writes_nothing_if_nothing_changed(account):
    user = account(is_staff=True, is_superuser=False)

    with CaptureQueriesContext(connection) as queries:
        assert oidc.sync_permissions(user, is_staff=True, is_superuser=False) is False

    assert not [q for q in queries if q["sql"].lstrip().upper().startswith("UPDATE")]
    assert not synced_entries().exists()


@pytest.mark.parametrize("entry_was_written", (False, True))
@pytest.mark.django_db(transaction=True)
def test_sync_is_rolled_back_if_the_audit_entry_fails(
    account, monkeypatch, entry_was_written
):
    """Without the surrounding test transaction of a regular test, so that
    only the transaction of the synchronization itself can undo the write.
    A permission change must never be stored without its audit entry."""
    user = account(is_staff=True, is_superuser=True)
    callers_user = get_user_model().objects.get(pk=user.pk)
    create_entry = LogEntry.objects.create

    def failing_create(*args, **kwargs):
        if entry_was_written:
            create_entry(*args, **kwargs)
        raise RuntimeError("audit log is not available")

    monkeypatch.setattr(LogEntry.objects, "create", failing_create)

    with pytest.raises(RuntimeError):
        oidc.sync_permissions(callers_user, is_staff=False, is_superuser=False)

    # the flags were already written when the audit entry failed
    assert flags(user) == (True, True)
    assert (callers_user.is_staff, callers_user.is_superuser) == (True, True)
    assert callers_user.is_active
    assert not synced_entries().exists()


@pytest.mark.django_db
def test_sync_reads_the_account_under_a_row_lock_first(account):
    user = account(is_staff=True)

    with CaptureQueriesContext(connection) as queries:
        oidc.sync_permissions(user, is_staff=False)

    statements = [q["sql"] for q in queries if "auth_user" in q["sql"]]
    assert statements[0].lstrip().upper().startswith("SELECT")
    assert statements[1].lstrip().upper().startswith("UPDATE")
    # SQLite has no row locks, it serializes writers as a whole
    if connection.features.has_select_for_update:
        assert "FOR UPDATE" in statements[0].upper()


@pytest.mark.django_db
def test_sync_leaves_a_concurrently_deactivated_account_alone(account):
    user = account(is_staff=True, is_superuser=True)
    outdated = get_user_model().objects.get(pk=user.pk)
    get_user_model().objects.filter(pk=user.pk).update(is_active=False)

    assert oidc.sync_permissions(outdated, is_staff=False, is_superuser=False) is False

    assert flags(user) == (True, True)
    assert not outdated.is_active
    assert not synced_entries().exists()


@pytest.mark.django_db
def test_sync_fails_cleanly_if_the_account_was_removed(account):
    user = account(is_staff=True)
    outdated = get_user_model().objects.get(pk=user.pk)
    get_user_model().objects.filter(pk=user.pk).delete()

    with pytest.raises(oidc.OIDCError):
        oidc.sync_permissions(outdated, is_staff=False)
    assert not synced_entries().exists()


@pytest.mark.django_db
def test_sync_without_mapped_flags_does_nothing(account):
    user = account(is_staff=True, is_superuser=True)

    with CaptureQueriesContext(connection) as queries:
        assert oidc.sync_permissions(user) is False

    assert len(queries) == 0


# -- audit log ---------------------------------------------------------------


@pytest.mark.django_db
def test_sync_logs_changes_with_old_and_new_flags_only(sync, account):
    sync.OIDC_STAFF_GROUP = STAFF
    sync.OIDC_SUPERUSER_GROUP = SUPER
    user = account(is_staff=True)

    oidc.get_or_create_user(
        {
            "preferred_username": "known",
            "groups": [SUPER, "some-private-group"],
            "email": "known@example.org",
        },
        "secret-access-token",
    )

    entry = synced_entries().get()
    assert entry.content_object == user
    # the change was made by the synchronization, not by a person
    assert entry.user is None
    assert entry.data == {
        "source": "internal: oidc_group_sync",
        "changes": {"is_staff": [True, False], "is_superuser": [False, True]},
    }
    # no claims, group names or tokens
    stored = json.dumps(entry.data)
    for secret in (SUPER, STAFF, "some-private-group", "example.org", "secret"):
        assert secret not in stored


@pytest.mark.django_db
def test_sync_logs_both_flags_even_if_only_one_changed(sync, account):
    sync.OIDC_SUPERUSER_GROUP = SUPER
    account(is_staff=True)

    login("known", [SUPER])

    assert synced_entries().get().data["changes"] == {
        "is_staff": [True, True],
        "is_superuser": [False, True],
    }


@pytest.mark.django_db
def test_sync_logs_nothing_if_nothing_changed(sync, account):
    sync.OIDC_STAFF_GROUP = STAFF
    sync.OIDC_SUPERUSER_GROUP = SUPER
    account(is_staff=True, is_superuser=True)

    login("known", [STAFF, SUPER])
    login("known", [STAFF, SUPER])

    assert not synced_entries().exists()


# -- where the groups come from ----------------------------------------------


@pytest.fixture
def mapped(sync, account):
    """An existing staff and superuser account with the superuser group
    mapped and synchronization on: whether it is still a superuser shows
    which groups byro has seen."""
    sync.OIDC_SUPERUSER_GROUP = SUPER
    return account(is_staff=True, is_superuser=True)


@pytest.mark.parametrize(
    "groups", ([STAFF, SUPER], (STAFF, SUPER), f"{STAFF} {SUPER}", SUPER)
)
@pytest.mark.django_db
def test_groups_from_id_token(mapped, userinfo, groups):
    login("known", groups)

    assert flags(mapped) == (True, True)
    assert userinfo.calls == 0


@pytest.mark.parametrize("groups", ([], "", ()))
@pytest.mark.django_db
def test_empty_groups_claim_is_a_valid_answer(mapped, userinfo, groups):
    # userinfo would say something else, but it must not be asked: an empty
    # claim means "member of no group"
    userinfo.response = {"groups": [SUPER]}

    login("known", groups)

    assert userinfo.calls == 0
    assert flags(mapped) == (True, False)


@pytest.mark.parametrize("claims", ({}, {"groups": None}))
@pytest.mark.parametrize(
    "userinfo_groups,expected",
    (([SUPER], (True, True)), (SUPER, (True, True)), ([], (True, False))),
)
@pytest.mark.django_db
def test_missing_groups_claim_falls_back_to_userinfo(
    mapped, userinfo, claims, userinfo_groups, expected
):
    userinfo.response = {"groups": userinfo_groups}

    oidc.get_or_create_user({"preferred_username": "known", **claims}, "token")

    assert userinfo.calls == 1
    assert flags(mapped) == expected


@pytest.mark.django_db
def test_groups_missing_everywhere_means_no_groups(mapped, userinfo):
    userinfo.response = {"preferred_username": "known"}

    login("known")

    assert userinfo.calls == 1
    assert flags(mapped) == (True, False)


@pytest.mark.django_db
def test_userinfo_is_requested_only_once(mapped, userinfo):
    # neither the username nor the groups are part of the ID token
    userinfo.response = {"preferred_username": "known", "groups": [SUPER]}

    oidc.get_or_create_user({}, "token")

    assert userinfo.calls == 1
    assert flags(mapped) == (True, True)


@pytest.mark.django_db
def test_failing_userinfo_request_changes_nothing(mapped, userinfo):
    userinfo.response = oidc.OIDCError("Userinfo request failed")

    with pytest.raises(oidc.OIDCError):
        login("known")

    assert flags(mapped) == (True, True)
    assert not synced_entries().exists()


MALFORMED_GROUPS = (
    pytest.param([None], id="none-in-list"),
    pytest.param([{"name": "staff"}], id="object-in-list"),
    pytest.param([SUPER, None], id="valid-and-none"),
    pytest.param([STAFF, {"name": SUPER}], id="valid-and-object"),
    pytest.param([SUPER, 7], id="valid-and-number"),
    pytest.param((SUPER, None), id="tuple"),
    pytest.param({"name": SUPER}, id="object"),
    pytest.param(7, id="number"),
)


def malformed_login(userinfo, source, username, groups):
    """A login whose ``groups`` claim is malformed, either in the ID token
    or in the userinfo response."""
    if source == "id_token":
        return login(username, groups)
    userinfo.response = {"groups": groups}
    return login(username)


@pytest.mark.parametrize("source", ("id_token", "userinfo"))
@pytest.mark.parametrize("groups", MALFORMED_GROUPS)
@pytest.mark.django_db
def test_malformed_groups_never_change_an_existing_account(
    mapped, oidc_settings, userinfo, source, groups
):
    oidc_settings.OIDC_STAFF_GROUP = STAFF

    with pytest.raises(oidc.OIDCError):
        malformed_login(userinfo, source, "known", groups)

    # not read as "member of no group": nothing is revoked, nothing is logged
    assert flags(mapped) == (True, True)
    assert not synced_entries().exists()
    assert userinfo.calls == (1 if source == "userinfo" else 0)


@pytest.mark.parametrize("source", ("id_token", "userinfo"))
@pytest.mark.parametrize("groups", MALFORMED_GROUPS)
@pytest.mark.parametrize("staff_group", ("", STAFF))
@pytest.mark.django_db
def test_malformed_groups_never_create_an_account(
    sync, userinfo, source, groups, staff_group
):
    # with and without a gate: the claim is rejected before any provisioning
    sync.OIDC_STAFF_GROUP = staff_group
    sync.OIDC_SUPERUSER_GROUP = SUPER

    with pytest.raises(oidc.OIDCError):
        malformed_login(userinfo, source, "newcomer", groups)

    assert not get_user_model().objects.filter(username="newcomer").exists()
    assert not LogEntry.objects.filter(action_type="byro.common.user.created").exists()


@pytest.mark.django_db
def test_groups_are_not_requested_without_a_mapping(oidc_settings, account, userinfo):
    oidc_settings.OIDC_SYNC_GROUPS = True
    user = account(is_staff=True)

    # no claim, and the autouse fixture would fail on a userinfo request
    assert login("known").pk == user.pk
    assert userinfo.calls == 0


# -- configuration -----------------------------------------------------------


def test_configuration_error_for_conflicting_groups(oidc_settings):
    assert oidc.get_configuration_error() is None

    oidc_settings.OIDC_GROUP_CONFLICT = True
    assert "admin_group" in oidc.get_configuration_error()
