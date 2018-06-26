from django.apps import apps
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase


# from https://www.caktusgroup.com/blog/2016/02/02/writing-unit-tests-django-migrations/
class TestMigrations(TestCase):

    @property
    def app(self):
        return apps.get_containing_app_config(type(self).__module__).name

    migrate_from = None
    migrate_fixtures = None
    migrate_to = None

    def setUp(self):
        assert self.migrate_from and self.migrate_to, \
            "TestCase '{}' must define migrate_from and migrate_to properties".format(type(self).__name__)
        self.migrate_from = [(self.app, self.migrate_from)]
        self.migrate_to = [(self.app, self.migrate_to)]
        executor = MigrationExecutor(connection)
        old_apps = executor.loader.project_state(self.migrate_from).apps

        # Reverse to the original migration
        executor.migrate(self.migrate_from)

        # From django/test/testcases.py
        if self.migrate_fixtures:
            for db_name in self._databases_names(include_mirrors=False):
                    try:
                        call_command('loaddata', *self.migrate_fixtures, **{
                            'verbosity': 0,
                            'commit': False,
                            'database': db_name,
                        })
                    except Exception:
                        self._rollback_atomics(self.cls_atomics)
                        raise

        self.setUpBeforeMigration(old_apps)

        # Run the migration to test
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()  # reload.
        executor.migrate(self.migrate_to)

        self.apps = executor.loader.project_state(self.migrate_to).apps

    def setUpBeforeMigration(self, apps):
        pass
