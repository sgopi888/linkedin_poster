import os
import secrets
from urllib.parse import urlencode

from flask import Flask, request
from dotenv import load_dotenv
import requests

load_dotenv()

CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI")

STATE = secrets.token_hex(16)

SCOPES = [
    "openid",
    "profile",
    "email",
    "w_member_social"
]

app = Flask(__name__)

@app.route("/callback")
def callback():

    code = request.args.get("code")
    state = request.args.get("state")

    if state != STATE:
        return "State mismatch"

    token_url = "https://www.linkedin.com/oauth/v2/accessToken"

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    response = requests.post(token_url, data=data)

    print("\n=== TOKEN RESPONSE ===\n")
    token_data = response.json()
    print(token_data)

    import time as _time
    token_data["issued_at"] = int(_time.time())
    token_data["expires_at"] = token_data["issued_at"] + token_data.get(
        "expires_in", 5184000
    )

    tmp = "linkedin_token.json.tmp"
    with open(tmp, "w") as f:
        json.dump(token_data, f, indent=2)
    os.replace(tmp, "linkedin_token.json")

    return "LinkedIn OAuth success. Token saved."

if __name__ == "__main__":

    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization?"
        + urlencode({
            "response_type": "code",
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "state": STATE,
            "scope": " ".join(SCOPES),
        })
    )

    print("\nOPEN THIS URL IN YOUR MAC BROWSER:\n")
    print(auth_url)

    app.run(host="127.0.0.1", port=8848)