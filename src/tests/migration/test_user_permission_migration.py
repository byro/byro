import importlib

import pytest
from django.contrib.auth import get_user_model
from django.db import connection, migrations
from django.db.migrations.loader import MigrationLoader

MIGRATION = ("common", "0021_grant_existing_users_backend_access")

migration_module = importlib.import_module(
    "byro.common.migrations.0021_grant_existing_users_backend_access"
)


@pytest.fixture
def run_migration():
    """Run the data migration with the historical models it receives during
    ``migrate``. The SQLite schema editor cannot run inside the transaction
    of a test, so the migration executor itself is not used here."""
    historical_apps = MigrationLoader(connection).project_state(MIGRATION).apps

    def run():
        migration_module.grant_existing_users_backend_access(historical_apps, None)

    return run


@pytest.mark.django_db
def test_existing_users_keep_full_access(run_migration):
    User = get_user_model()
    for username, is_staff, is_superuser, is_active in (
        ("none", False, False, True),
        ("staff", True, False, True),
        ("superuser", False, True, True),
        ("both", True, True, True),
        ("inactive", False, False, False),
    ):
        User.objects.create(
            username=username,
            is_staff=is_staff,
            is_superuser=is_superuser,
            is_active=is_active,
        )

    run_migration()

    users = {user.username: user for user in User.objects.all()}
    assert set(users) == {"none", "staff", "superuser", "both", "inactive"}
    for user in users.values():
        assert user.is_staff, user.username
        assert user.is_superuser, user.username
    # the migration only grants access, it never reactivates an account
    assert not users["inactive"].is_active
    assert all(user.is_active for name, user in users.items() if name != "inactive")


@pytest.mark.django_db
def test_migration_works_without_users(run_migration):
    run_migration()
    assert get_user_model().objects.count() == 0


@pytest.mark.django_db
def test_migration_is_wired_up_and_reversible_as_noop():
    loader = MigrationLoader(connection)
    migration = loader.graph.nodes[MIGRATION]
    assert ("common", "0020_alter_configuration_language") in migration.dependencies
    assert any(app == "auth" for app, _name in migration.dependencies)
    assert loader.graph.leaf_nodes("common") == [MIGRATION]

    (operation,) = migration.operations
    assert isinstance(operation, migrations.RunPython)
    assert operation.code is migration_module.grant_existing_users_backend_access
    # going back does not restore the previous flags, nobody loses access
    assert operation.reverse_code is migrations.RunPython.noop
