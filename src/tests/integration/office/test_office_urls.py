import pytest
from django.urls import Resolver404, resolve

OFFICE_ROUTES = (
    (
        "/transactions/1/",
        "/transactions/1/unexpected",
        "office:finance.transactions.detail",
    ),
    ("/upload/list", "/upload/listing", "office:finance.uploads.list"),
    ("/upload/process/1", "/upload/process/1a", "office:finance.uploads.process"),
    ("/upload/match/1", "/upload/match/1a", "office:finance.uploads.match"),
    ("/upload/add", "/upload/additional", "office:finance.uploads.add"),
    ("/documents/add", "/documents/additional", "office:documents.add"),
    (
        "/documents/1/minutes.pdf",
        "/documents/1/minutes.pdf/unexpected",
        "office:documents.download",
    ),
    ("/documents/1", "/documents/1a", "office:documents.detail"),
)


@pytest.mark.parametrize(("url", "_invalid_url", "view_name"), OFFICE_ROUTES)
def test_office_route_resolves_canonical_url(url, _invalid_url, view_name):
    assert resolve(url).view_name == view_name


@pytest.mark.parametrize(
    "invalid_url", tuple(invalid_url for _url, invalid_url, _view_name in OFFICE_ROUTES)
)
def test_office_route_rejects_suffix(invalid_url):
    with pytest.raises(Resolver404):
        resolve(invalid_url)
