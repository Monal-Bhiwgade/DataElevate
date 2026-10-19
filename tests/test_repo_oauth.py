"""Guard the intentionally public sign-in config in oauth/gdrive-client.json.

It must only ever be a Desktop-app ("installed") OAuth client. A service-account key,
web client, refresh token or private key in that file would be a real secret leak.
"""

import json
from pathlib import Path

import pytest

CLIENT_FILE = Path(__file__).resolve().parents[1] / "oauth" / "gdrive-client.json"
ALLOWED_KEYS = {"client_id", "project_id", "auth_uri", "token_uri",
                "auth_provider_x509_cert_url", "client_secret", "redirect_uris"}


@pytest.mark.skipif(not CLIENT_FILE.exists(), reason="oauth/gdrive-client.json not added yet")
def test_public_client_is_desktop_only():
    text = CLIENT_FILE.read_text()
    data = json.loads(text)
    assert set(data) == {"installed"}, "Only a Desktop-app ('installed') client is allowed"
    section = data["installed"]
    assert section.get("client_id", "").endswith(".apps.googleusercontent.com")
    assert set(section) <= ALLOWED_KEYS, f"Unexpected keys: {set(section) - ALLOWED_KEYS}"
    for forbidden in ("private_key", "refresh_token", "access_token", "service_account"):
        assert forbidden not in text
