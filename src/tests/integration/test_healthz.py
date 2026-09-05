import json

import pytest
from django.db import OperationalError
from django.urls import reverse

from byro.common import views


@pytest.mark.django_db
def test_healthz_is_reachable_without_login(client):
    response = client.get(reverse("common:healthz"))

    assert response.status_code == 200
    assert json.loads(response.content) == {"status": "ok"}
    assert "no-store" in response["Cache-Control"]


@pytest.mark.django_db
def test_healthz_reports_database_failure(client, monkeypatch):
    class BrokenConnection:
        def ensure_connection(self):
            raise OperationalError("database unavailable")

    monkeypatch.setattr(views, "connection", BrokenConnection())

    response = client.get(reverse("common:healthz"))

    assert response.status_code == 503
    assert json.loads(response.content) == {"status": "error"}


@pytest.mark.django_db
def test_healthz_for_logged_in_user(logged_in_client):
    response = logged_in_client.get(reverse("common:healthz"))

    assert response.status_code == 200


@pytest.mark.django_db
def test_healthz_url_path(client):
    assert reverse("common:healthz") == "/healthz"
