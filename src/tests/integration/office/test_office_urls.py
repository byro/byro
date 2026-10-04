import pytest
from django.urls import Resolver404, resolve, reverse

# Canonical URL, view name and the arguments that reverse to that URL.
CANONICAL_ROUTES = (
    ("/transactions/1/", "office:finance.transactions.detail", {"pk": 1}),
    ("/upload/list", "office:finance.uploads.list", {}),
    ("/upload/process/1", "office:finance.uploads.process", {"pk": 1}),
    ("/upload/match/1", "office:finance.uploads.match", {"pk": 1}),
    ("/upload/add", "office:finance.uploads.add", {}),
    ("/documents/add", "office:documents.add", {}),
    (
        "/documents/1/minutes.pdf",
        "office:documents.download",
        {"pk": 1, "filename": "minutes.pdf"},
    ),
    ("/documents/1", "office:documents.detail", {"pk": 1}),
)

# "/documents/1/extra" is missing on purpose: it is a download URL with the
# filename "extra".
EXTRA_SEGMENT_URLS = (
    "/transactions/1/extra",
    "/upload/list/extra",
    "/upload/process/1/extra",
    "/upload/match/1/extra",
    "/upload/add/extra",
    "/documents/add/extra",
    "/documents/1/minutes.pdf/extra",
)

PREFIX_MATCH_URLS = (
    "/upload/listing",
    "/upload/additional",
    "/documents/additional",
    "/upload/process/1a",
    "/upload/match/1a",
    "/documents/1a",
)

TRAILING_SLASH_URLS = (
    "/transactions/1//",
    "/upload/list/",
    "/upload/process/1/",
    "/upload/match/1/",
    "/upload/add/",
    "/documents/add/",
    "/documents/1/minutes.pdf/",
    "/documents/1/",
)


@pytest.mark.parametrize(("url", "view_name", "kwargs"), CANONICAL_ROUTES)
def test_canonical_url_resolves_to_named_route(url, view_name, kwargs):
    assert resolve(url).view_name == view_name
    assert reverse(view_name, kwargs=kwargs) == url


@pytest.mark.parametrize("url", EXTRA_SEGMENT_URLS)
def test_extra_path_segment_is_rejected(url):
    with pytest.raises(Resolver404):
        resolve(url)
    # APPEND_SLASH must not find a redirect target either.
    with pytest.raises(Resolver404):
        resolve(url + "/")


@pytest.mark.parametrize("url", PREFIX_MATCH_URLS)
def test_prefix_match_is_rejected(url):
    with pytest.raises(Resolver404):
        resolve(url)
    # APPEND_SLASH must not find a redirect target either.
    with pytest.raises(Resolver404):
        resolve(url + "/")


@pytest.mark.parametrize("url", TRAILING_SLASH_URLS)
def test_non_canonical_trailing_slash_is_rejected(url):
    with pytest.raises(Resolver404):
        resolve(url)


@pytest.mark.parametrize(
    "filename", ("minutes.pdf", "Protokoll 2024 (1).pdf", "Satzung-ä.pdf", "extra")
)
def test_document_download_accepts_filename_as_single_segment(filename):
    match = resolve(f"/documents/1/{filename}")
    assert match.view_name == "office:documents.download"
    assert match.kwargs["filename"] == filename


def test_transaction_detail_requires_trailing_slash():
    with pytest.raises(Resolver404):
        resolve("/transactions/1")


@pytest.mark.parametrize(
    ("url", "view_name"),
    (
        ("/transactions/001/", "office:finance.transactions.detail"),
        ("/upload/process/001", "office:finance.uploads.process"),
        ("/upload/match/001", "office:finance.uploads.match"),
        ("/documents/001/minutes.pdf", "office:documents.download"),
        ("/documents/001", "office:documents.detail"),
    ),
)
def test_pk_reaches_the_view_as_unchanged_string(url, view_name):
    match = resolve(url)
    assert match.view_name == view_name
    assert match.kwargs["pk"] == "001"


def test_pk_accepts_unicode_digit():
    # ARABIC-INDIC DIGIT ONE: "\d" has always matched more than 0-9 here.
    match = resolve("/documents/\u0661")
    assert match.view_name == "office:documents.detail"
    assert match.kwargs["pk"] == "\u0661"
