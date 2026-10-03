import pytest

from byro.common.forms import ConfigurationForm
from byro.common.models import Configuration
from byro.common.templatetags.format_with_currency import format_with_currency


def test_new_configuration_defaults_to_euro():
    config = Configuration()

    assert config.currency == "EUR"
    assert config.currency_symbol == "€"


@pytest.mark.django_db
def test_freshly_migrated_installation_uses_euro():
    # the migrations create the configuration themselves, so this is the
    # state a new installation starts with
    config = Configuration.get_solo()

    assert config.currency == "EUR"
    assert config.currency_symbol == "€"


@pytest.mark.django_db
def test_settings_form_offers_default_currency_without_requiring_it():
    form = ConfigurationForm(instance=Configuration.get_solo())

    assert form["currency"].value() == "EUR"
    assert form["currency_symbol"].value() == "€"
    assert not form.fields["currency"].required


@pytest.mark.django_db
def test_default_currency_code_and_symbol_stay_separate():
    Configuration.get_solo()

    assert format_with_currency(5, long_form=True) == "5 EUR"
    assert format_with_currency(5) == "5 €"


@pytest.mark.django_db
def test_empty_currency_stays_empty():
    config = Configuration.get_solo()
    config.currency = None
    config.save()

    assert Configuration.get_solo().currency is None
    assert format_with_currency(5, long_form=True) == "5"
