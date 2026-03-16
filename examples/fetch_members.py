#!/usr/bin/env python3
"""Fetch all members from the byro REST API.

Usage:
    python fetch_members.py

Configuration via environment variables:
    BYRO_URL    Base URL of your byro instance (default: http://localhost:8000)
    BYRO_TOKEN  API token (from /settings/api-token in the byro office)

Or edit the constants below directly.

Dependencies:
    pip install requests
"""

import os

import requests

BYRO_URL = os.environ.get("BYRO_URL", "http://localhost:8000").rstrip("/")
BYRO_TOKEN = os.environ.get("BYRO_TOKEN", "your-token-here")

session = requests.Session()
session.headers["Authorization"] = f"Token {BYRO_TOKEN}"


def fetch_all_members():
    """Fetch all members, following pagination automatically."""
    members = []
    url = f"{BYRO_URL}/api/v1/members/"
    while url:
        response = session.get(url)
        response.raise_for_status()
        data = response.json()
        members.extend(data["results"])
        url = data.get("next")  # None when last page reached
    return members


def main():
    members = fetch_all_members()
    print(f"Total members: {len(members)}\n")
    for member in members:
        status = "active" if member["is_active"] else "inactive"
        print(
            f"  [{member['id']:>4}] #{member['number'] or '—':>6}  "
            f"{member['name'] or '(no name)':<30}  "
            f"{member['email'] or '':<30}  "
            f"{status}  balance: {member['balance']}"
        )


if __name__ == "__main__":
    main()
