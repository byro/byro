import functools

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.shortcuts import reverse

from byro.common.models.configuration import Configuration


@pytest.fixture
def configuration():
    config = Configuration.get_solo()
    config.name = "Der Verein e.V."
    config.backoffice_mail = "associationname@example.com"
    config.mail_from = "associationname@example.com"
    config.save()
    return config


@pytest.fixture
def full_testdata(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command("make_testdata")


@pytest.fixture
def user():
    user = get_user_model().objects.create(
        username="charlotte", last_name="Charlotte Holmes", is_staff=True
    )
    user.set_password("test_password")
    user.save()
    yield user
    user.delete()


@pytest.fixture
def client(live_server, selenium, user, configuration):
    selenium.implicitly_wait(10)

    def go_to(url, *args, **kwargs):
        return selenium.get(live_server.url + reverse(url, *args, **kwargs))

    selenium.go_to = go_to
    return selenium


@pytest.fixture
def logged_in_client(live_server, client, user):
    client.go_to("common:login")
    client.implicitly_wait(10)

    client.find_element_by_css_selector("form input[name=username]").send_keys(
        user.username
    )
    client.find_element_by_css_selector("form input[name=password]").send_keys(
        "test_password"
    )
    client.find_element_by_css_selector("form button[type=submit]").click()
    return client


@pytest.fixture
def chrome_options(chrome_options):
    chrome_options.add_argument("headless")
    chrome_options.add_argument("window-size=1488x837")
    return chrome_options


@pytest.fixture(autouse=True)
def hide_data():
    import byro.common.utils

    byro.common.utils.get_version = lambda: None

    import byro.common.context_processors

    orig = byro.common.context_processors.byro_information

    @functools.wraps(orig)
    def byro_information(request):
        ctx = orig(request)
        ctx["log_end"] = {
            "auth_hash": "blake2b:428c6368597439c4fd935d9941c3554e29ad6c675a4aa20163dbb79a242bf8f6c6e76a5f7ba484f048cc916d1072bc2f5eea754cfb6f994e8b2a03f0c02cfa30"
        }
        return ctx

    byro.common.context_processors.byro_information = byro_information
