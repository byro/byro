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

    def load_fixtures(self, fixtures, apps):
        # Via https://stackoverflow.com/questions/25960850/loading-initial-data-with-django-1-7-and-data-migrations/39743581#39743581
        #  we need to monkeypatch a Django internal in order to provide it with
        #  the correct (old) view of the model
        from django.core.serializers import base, python

        # Define new _get_model() function here, which utilizes the apps argument to
        # get the historical version of a model. This piece of code is directly stolen
        # from django.core.serializers.python._get_model, unchanged.
        def _get_model(model_identifier):
            try:
                return apps.get_model(model_identifier)
            except (LookupError, TypeError):
                raise base.DeserializationError(
                    "Invalid model identifier: '%s'" % model_identifier
                )

        # Save the old _get_model() function
        old_get_model = python._get_model

        # Replace the _get_model() function on the module, so loaddata can utilize it.
        python._get_model = _get_model

        try:
            # From django/test/testcases.py
            for db_name in self._databases_names(include_mirrors=False):
                try:
                    call_command(
                        "loaddata",
                        *fixtures,
                        **{"verbosity": 0, "commit": False, "database": db_name}
                    )
                except Exception:
                    self._rollback_atomics(self.cls_atomics)
                    raise

        finally:
            # Restore old _get_model() function
            python._get_model = old_get_model

    def setUp(self):
        assert (
            self.migrate_from and self.migrate_to
        ), "TestCase '{}' must define migrate_from and migrate_to properties".format(
            type(self).__name__
        )
        self.migrate_from = [(self.app, self.migrate_from)]
        self.migrate_to = [(self.app, self.migrate_to)]
        executor = MigrationExecutor(connection)
        old_apps = executor.loader.project_state(self.migrate_from).apps

        # Reverse to the original migration
        executor.migrate(self.migrate_from)

        if self.migrate_fixtures:
            self.load_fixtures(self.migrate_fixtures, apps=old_apps)

        self.setUpBeforeMigration(old_apps)

        # Run the migration to test
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()  # reload.
        executor.migrate(self.migrate_to)

        self.apps = executor.loader.project_state(self.migrate_to).apps

    def setUpBeforeMigration(self, apps):
        pass
