import pytest
from django.shortcuts import reverse

from byro.mails.models import EMail, PGPConfiguration, PGPPolicy


@pytest.mark.django_db
def test_outbox_send_shows_error_when_pgp_blocks_mail(
    member, logged_in_client, configuration
):
    pgp_config = PGPConfiguration.get_solo()
    pgp_config.encryption_enabled = True
    pgp_config.missing_key_policy = PGPPolicy.BLOCK
    pgp_config.save()
    mail = EMail.objects.create(to=member.email, subject="Test", text="Text")

    response = logged_in_client.get(
        reverse("office:mails.mail.send", kwargs={"pk": mail.pk})
    )

    assert response.status_code == 302
    assert response.url == reverse("office:mails.outbox.list")
    mail.refresh_from_db()
    assert mail.sent is None
