"""LinkedIn token lifecycle: read, refresh, persist atomically.

Usage:
    from linkedin_auth import get_access_token
    token = get_access_token()  # refreshes if needed
"""
import sys
import json
import time
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import TOKEN_PATH, LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET

REFRESH_MARGIN_SECONDS = 60 * 60 * 24 * 3  # refresh if <3 days remaining
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"


def _atomic_write(path: Path, content: str):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content)
    tmp.replace(path)


def _load_token() -> dict:
    if not TOKEN_PATH.exists():
        raise FileNotFoundError(
            f"Missing {TOKEN_PATH}. Run scripts/oauth_linkedin.py to mint a token."
        )
    return json.loads(TOKEN_PATH.read_text())


def _is_expired(token_data: dict) -> bool:
    """True if expiry is recorded AND within REFRESH_MARGIN.

    Legacy tokens (no issued_at / expires_at) are treated as valid — we have
    no way to know when they expire, so we let the LinkedIn API tell us via
    401 on the next call. Re-run oauth_linkedin.py to upgrade.
    """
    expires_at = token_data.get("expires_at")
    issued_at = token_data.get("issued_at")
    if not expires_at and not issued_at:
        return False  # legacy token, can't tell — trust it until API says no
    if not expires_at:
        expires_at = issued_at + token_data.get("expires_in", 5184000)
    return time.time() >= (expires_at - REFRESH_MARGIN_SECONDS)


def _refresh(token_data: dict) -> dict:
    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        raise RuntimeError(
            "No refresh_token in linkedin_token.json. "
            "Re-run scripts/oauth_linkedin.py to obtain one."
        )
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": LINKEDIN_CLIENT_ID,
            "client_secret": LINKEDIN_CLIENT_SECRET,
        },
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Token refresh failed: HTTP {resp.status_code} — {resp.text}")
    new_data = resp.json()
    new_data["issued_at"] = int(time.time())
    new_data["expires_at"] = new_data["issued_at"] + new_data.get("expires_in", 5184000)
    if "refresh_token" not in new_data and refresh_token:
        new_data["refresh_token"] = refresh_token
    _atomic_write(TOKEN_PATH, json.dumps(new_data, indent=2))
    return new_data


def get_access_token() -> str:
    """Return a valid LinkedIn access token, refreshing if needed."""
    data = _load_token()
    if _is_expired(data):
        data = _refresh(data)
    return data["access_token"]


if __name__ == "__main__":
    # Diagnostic: print status without leaking the token
    data = _load_token()
    expires_at = data.get("expires_at") or (
        data.get("issued_at", 0) + data.get("expires_in", 5184000)
    )
    remaining_days = (expires_at - time.time()) / 86400
    print(json.dumps({
        "has_token": True,
        "has_refresh_token": "refresh_token" in data,
        "expires_in_days": round(remaining_days, 1),
        "needs_refresh": _is_expired(data),
    }, indent=2))
