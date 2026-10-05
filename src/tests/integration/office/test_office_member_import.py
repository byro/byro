"""Regression tests for #569: a failed CSV import must leave no members.

`default_csv_form_valid()` creates the member for a row with
`Member.objects.create()` before it knows whether the row is usable. A CSV that
carries an account balance but no "Last Member Fee Transaction Timestamp"
column then hits an early `return redirect(...)`, so the row is never
completed -- but the INSERT has already happened, and the enclosing
`transaction.atomic` commits, because a redirect is a normal return and not
an exception. The import reports failure while a half-imported member stays
in the database.

The fix raises instead of returning, so the atomic block rolls the import
back, and the view turns the exception back into the redirect the user sees.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from byro.common.models import LogEntry
from byro.members.models import Member

pytestmark = pytest.mark.usefixtures("configuration")

IMPORTER = "byro.office.members.import.default_csv"
IMPORT_URL = "office:members.list.import"

# The CSV from the issue: a balance, but no timestamp column. The first row
# is the one that trips the check.
BROKEN_CSV = "Name,Account balance\nJane Doe,10\nJohn Doe,5\n"
# The same file without the balance column, which is the supported case.
WORKING_CSV = "Name\nJane Doe\nJohn Doe\n"
# A column that cannot be mapped exits before any row is written.
UNMAPPABLE_CSV = "Name,Nonexistent column\nJane Doe,x\n"


def post_csv(client, body, importer=IMPORTER):
    upload = SimpleUploadedFile("members.csv", body.encode(), content_type="text/csv")
    return client.post(
        reverse(IMPORT_URL),
        {"importer": importer, "upload_file": upload},
    )


@pytest.mark.django_db
def test_failed_import_does_not_leave_a_member_behind(logged_in_client):
    """#569: a member named "Jane Doe" survived a failed import."""
    post_csv(logged_in_client, BROKEN_CSV)

    assert not Member.objects.filter(name="Jane Doe").exists()
    assert not Member.objects.filter(name="John Doe").exists()


@pytest.mark.django_db
def test_failed_import_rolls_back_every_row(logged_in_client):
    """Rows before the failing one were imported; roll the file back too."""
    post_csv(logged_in_client, BROKEN_CSV)

    assert Member.objects.count() == 0


@pytest.mark.django_db
def test_failed_import_still_redirects(logged_in_client):
    """Rolling back must not turn the failure into a 500."""
    response = post_csv(logged_in_client, BROKEN_CSV)

    assert response.status_code == 302
    assert response.url == reverse(IMPORT_URL)


@pytest.mark.django_db
def test_failed_import_keeps_the_audit_log_entry(logged_in_client):
    """The import attempt stays on record; only the members are rolled back."""
    post_csv(logged_in_client, BROKEN_CSV)

    assert LogEntry.objects.filter(action_type="byro.members.import").exists()


@pytest.mark.django_db
def test_working_import_still_creates_members(logged_in_client):
    """The fix must not break the import that does work."""
    post_csv(logged_in_client, WORKING_CSV)

    assert Member.objects.filter(name="Jane Doe").exists()
    assert Member.objects.filter(name="John Doe").exists()


@pytest.mark.django_db
def test_unmappable_column_still_redirects(logged_in_client):
    """This failure path already ran before any row was written."""
    response = post_csv(logged_in_client, UNMAPPABLE_CSV)

    assert response.status_code == 302
    assert response.url == reverse(IMPORT_URL)
    assert Member.objects.count() == 0
