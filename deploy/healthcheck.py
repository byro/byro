Ja bitt#!/usr/bin/env python3
"""Container health check for the byro image (standard library plus, as a
fallback, the byro settings).

Requests ``/healthz`` on the local gunicorn and sends the configured site host
as ``Host`` header, so Django's ``ALLOWED_HOSTS`` check stays fully intact.
The host comes from ``BYRO_SITE_URL``; deployments that configure byro through
a mounted ``byro.cfg`` only (the legacy production/docker-compose.yml) have no
such variable, so the site URL is then read from the byro settings.
Exit code 0 means healthy.
"""

import contextlib
import io
import json
import os
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit


def site_host() -> str:
    site_url = os.environ.get("BYRO_SITE_URL")
    if not site_url:
        # Importing the settings prints byro's startup banner; keep it out of
        # the health check output.
        with contextlib.redirect_stdout(io.StringIO()):
            from django.conf import settings

            site_url = settings.SITE_URL
    return urlsplit(site_url).hostname or "localhost"


def main() -> int:
    try:
        host = site_host()
    except Exception as exc:  # settings unreadable -> unhealthy
        print(f"healthcheck failed: cannot determine site host: {exc}", file=sys.stderr)
        return 1
    port = os.environ.get("BYRO_HEALTHCHECK_PORT", "8345")
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/healthz", headers={"Host": host}
    )
    try:
        with urllib.request.urlopen(request, timeout=4) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, ValueError, OSError) as exc:
        print(f"healthcheck failed: {exc}", file=sys.stderr)
        return 1
    if body.get("status") != "ok":
        print(f"healthcheck failed: unexpected response {body!r}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
