import pytest

try:
    import django_securebox  # noqa

    HAVE_SECUREBOX = True
except ImportError:
    HAVE_SECUREBOX = False

with_securebox = pytest.mark.skipif(
    not HAVE_SECUREBOX, reason="django_securebox module required"
)


@pytest.mark.django_db
@with_securebox
def test_securebox_basic(client, user):
    pass
